import uuid
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.api.db.database import SessionLocal
from src.api.db.models import User
from src.api.schemas.auth import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    DemoAccount,
    DemoAccountsResponse,
    MessageResponse,
    ResendVerificationRequest,
    RegisterResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    VerifyEmailResponse,
)
from src.api.schemas.errors import STANDARD_ERRORS, ErrorResponse
from src.api.services.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    decode_access_token,
    generate_verification_token,
    hash_password,
    verification_expired,
    verify_password,
)
from src.api.services.rate_limit import login_limiter
from src.api.services.account import change_password, delete_account
from src.api.services.bans import active_ban
from src.api.services.demo_accounts import get_public_demo_accounts
from src.api.services.email import send_verification_email

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & User Management"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def user_response(db: Session, user: User) -> UserResponse:
    """Profile with the ban in force, so the UI can tell a banned user why and until when (FR-009)."""
    return UserResponse.model_validate(user).model_copy(update={"ban": active_ban(db, user)})


def token_from_request(authorization: Optional[str], access_token_cookie: Optional[str]) -> Optional[str]:
    """The access token from the `Authorization: Bearer` header, otherwise from the HttpOnly cookie."""
    if authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    return access_token_cookie or None


def access_token_for(user: User) -> str:
    """A signed access token of the user; `ver` ties it to the current password (see token_version)."""
    return create_access_token(
        {
            "sub": str(user.user_id),
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role,
            "ver": user.token_version or 0,
        }
    )


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=True,
        # The cookie lives exactly as long as the token inside it
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate JWT access token from Authorization header or HttpOnly cookie (US-011).
    """
    token = token_from_request(authorization, access_token_cookie)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Authentication required. Please log in."},
        )
    return user_from_token(db, token)


def user_from_token(db: Session, token: str) -> User:
    """
    The user of a valid access token; 401 for a bad, expired or outdated token (shared by every endpoint
    that needs a signed-in user, comments included).
    """
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired access token"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token missing subject identifier"},
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token subject is not a valid UUID"},
        )

    user = db.query(User).filter(User.user_id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User associated with token not found"},
        )

    # Tokens issued before the last password change are no longer accepted (old tokens have no `ver`: 0)
    if payload.get("ver", 0) != (user.token_version or 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_REVOKED", "message": "The session ended after a password change. Please log in."},
        )

    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """
    Ensure the authenticated user has verified the email. A banned user stays logged in and keeps
    the watchlist, watched list and recommendations; reviews, ratings and comments check the ban
    separately (FR-009, services/bans.py).
    """
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "EMAIL_NOT_VERIFIED", "message": "Please verify your email address"},
        )
    return user


def get_current_admin(user: User = Depends(get_current_active_user)) -> User:
    """
    Ensure the user has administrator privileges (FR-008, FR-009).
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Administrator privileges required"},
        )
    return user


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account (FR-001)",
    description=(
        "Registers a new account with email and password and sends an activation link to the email "
        "(FR-001). The account stays pending until the link is opened; the token is never returned by the API."
    ),
    responses={
        **STANDARD_ERRORS,
        409: {"model": ErrorResponse, "description": "Email or nickname already registered"},
    },
)
def register_user(
    req: UserRegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    email_clean = req.email.strip().lower()
    nickname_clean = req.nickname.strip()

    if db.query(User).filter(User.email == email_clean).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_ALREADY_EXISTS", "message": "An account with this email already exists"},
        )

    if db.query(User).filter(User.nickname == nickname_clean).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "NICKNAME_ALREADY_EXISTS", "message": "An account with this nickname already exists"},
        )

    verification_token = generate_verification_token()
    user = User(
        email=email_clean,
        nickname=nickname_clean,
        password_hash=hash_password(req.password),
        role="user",
        email_verified=False,
        status="pending",
        verification_token=verification_token,
        verification_sent_at=datetime.now(timezone.utc),
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "USER_ALREADY_EXISTS",
                "message": "An account with this email or nickname already exists",
            },
        )

    db.refresh(user)

    # Sent after the response, so a slow mail provider does not delay registration
    background_tasks.add_task(send_verification_email, user.email, user.nickname, verification_token)

    return RegisterResponse(
        message="Account created. We sent an activation link to your email; open it before logging in.",
        email=user.email,
    )


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send the activation link again (FR-001)",
    description=(
        "Issues a new activation link for an account that is not verified yet. The answer is the same "
        "whether or not the email is registered, so it cannot be used to find accounts."
    ),
    responses={**STANDARD_ERRORS},
)
def resend_verification(
    req: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if user is not None and not user.email_verified:
        user.verification_token = generate_verification_token()
        user.verification_sent_at = datetime.now(timezone.utc)
        db.commit()
        background_tasks.add_task(send_verification_email, user.email, user.nickname, user.verification_token)
    return MessageResponse(message="If the account exists and is not verified yet, a new activation link was sent.")


@router.get(
    "/verify",
    response_model=VerifyEmailResponse,
    summary="Confirm email address and activate account (FR-001, US-011)",
    description="Validates verification token, activates user status, and sets email_verified to true.",
    responses={
        **STANDARD_ERRORS,
        400: {"model": ErrorResponse, "description": "Invalid or expired verification token"},
    },
)
def verify_email(
    token: str = Query(..., description="Verification token sent in email"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_VERIFICATION_TOKEN", "message": "Invalid or expired email verification token"},
        )
    if verification_expired(user.verification_sent_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VERIFICATION_TOKEN_EXPIRED",
                "message": "The activation link has expired. Request a new one from the login window.",
            },
        )

    user.email_verified = True
    user.status = "active"
    user.verification_token = None
    user.verification_sent_at = None
    db.commit()

    return VerifyEmailResponse(
        message="Email successfully verified! Your account is now active.",
        email=user.email,
        status="active",
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login and JWT token issuance (T-037, US-011)",
    description=(
        "Authenticates user by email and password using bcrypt. "
        "Returns signed JWT access token in response body and sets HttpOnly cookie."
    ),
    responses={
        **STANDARD_ERRORS,
        401: {"model": ErrorResponse, "description": "Invalid email or password"},
        403: {"model": ErrorResponse, "description": "Email is not verified"},
        429: {"model": ErrorResponse, "description": "Too many failed attempts from this address; see Retry-After"},
    },
)
def login(
    req: UserLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    # Brute-force protection: a few wrong passwords per minute from one address (rate_limit.py)
    client = request.client.host if request.client else "unknown"
    wait = login_limiter.retry_after(client)
    if wait is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "TOO_MANY_ATTEMPTS",
                "message": f"Too many failed login attempts. Try again in {wait} seconds.",
            },
            headers={"Retry-After": str(wait)},
        )

    email_clean = req.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()

    if not user or not verify_password(req.password, user.password_hash):
        login_limiter.record_failure(client)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
        )
    login_limiter.reset(client)

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "EMAIL_NOT_VERIFIED",
                "message": "Please verify your email before logging in. Check your mailbox for the activation link.",
            },
        )

    access_token = access_token_for(user)
    set_session_cookie(response, access_token)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response(db, user),
    )


@router.get(
    "/demo-accounts",
    response_model=DemoAccountsResponse,
    summary="Demo accounts for the login window",
    description=(
        "Public hint for demo deployments: the seed accounts configured in the environment. "
        "Returns `enabled: false` and no accounts unless the server runs with DEMO_MODE=true."
    ),
    responses={**STANDARD_ERRORS},
)
def list_demo_accounts():
    accounts = get_public_demo_accounts()
    return DemoAccountsResponse(
        enabled=bool(accounts),
        accounts=[DemoAccount(role=a.role, email=a.email, password=a.password) for a in accounts],
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
    description="Returns profile information for the authenticated user using Bearer token or cookie.",
    responses={
        **STANDARD_ERRORS,
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return user_response(db, current_user)


ACCOUNT_ERRORS = {
    400: {"model": ErrorResponse, "description": "Wrong current password or invalid new password"},
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Demo (seed) or administrator account"},
}


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change my password",
    description=(
        "Requires the current password. Demo (seed) accounts are managed by the server settings. "
        "All other sessions of the account end; this one continues with a new session cookie."
    ),
    responses={**STANDARD_ERRORS, **ACCOUNT_ERRORS},
)
def change_my_password(
    req: ChangePasswordRequest,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    change_password(db, current_user, req.current_password, req.new_password)
    set_session_cookie(response, access_token_for(current_user))
    return MessageResponse(message="Password changed")


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete my account and all my data",
    description=(
        "Requires the current password. Removes the account with its reviews, ratings, comments, "
        "watchlist, watched list and ban history, and clears the session cookie."
    ),
    responses={**STANDARD_ERRORS, **ACCOUNT_ERRORS},
)
def delete_my_account(
    req: DeleteAccountRequest,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    delete_account(db, current_user, req.password)
    response.delete_cookie(key="access_token", httponly=True, samesite="lax", secure=True)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/logout",
    summary="Log out and clear session cookie",
    description="Clears the HttpOnly access_token cookie.",
)
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        secure=True,
    )
    return {"message": "Successfully logged out"}
