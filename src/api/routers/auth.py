import uuid
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.api.db.database import SessionLocal
from src.api.db.models import User
from src.api.schemas.auth import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    DemoAccount,
    DemoAccountsResponse,
    ForgotPasswordRequest,
    MessageResponse,
    ResendVerificationRequest,
    RegisterResponse,
    ResetPasswordRequest,
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
    as_utc,
    generate_verification_token,
    hash_password,
    hash_reset_token,
    password_reset_expired,
    verification_expired,
    verify_password,
)
from src.api.services.rate_limit import (
    AttemptLimiter,
    login_limiter,
    password_reset_limiter,
    register_limiter,
    resend_limiter,
)
from src.api.services.account import change_password, delete_account, remove_user_with_data
from src.api.services.bans import active_ban
from src.api.services.demo_accounts import get_public_demo_accounts, is_seed_account
from src.api.services.email import send_password_reset_email, send_verification_email
from src.api.services.email_identity import canonical_email, is_disposable_email

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & User Management"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# A new activation email for the same account is sent at most once per this many seconds
RESEND_COOLDOWN_SECONDS = 60


def client_address(request: Request) -> str:
    """The client IP address (behind Render's proxy uvicorn takes it from X-Forwarded-For, see Dockerfile)."""
    return request.client.host if request.client else "unknown"


def ensure_within_limit(limiter: AttemptLimiter, client: str, message: str) -> None:
    """429 TOO_MANY_ATTEMPTS with Retry-After when the address has used up the limit."""
    wait = limiter.retry_after(client)
    if wait is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "TOO_MANY_ATTEMPTS", "message": f"{message} Try again in {wait} seconds."},
            headers={"Retry-After": str(wait)},
        )


def recently_sent(sent_at: Optional[datetime]) -> bool:
    """True within RESEND_COOLDOWN_SECONDS of the last email to the account (no mailbox flooding)."""
    sent_at = as_utc(sent_at)
    if sent_at is None:
        return False
    return (datetime.now(timezone.utc) - sent_at).total_seconds() < RESEND_COOLDOWN_SECONDS


def abandoned_registration(user: User) -> bool:
    """A pending account whose activation link expired: nobody proved the mailbox, so its email and
    nickname are free for a new registration (otherwise anyone could hold someone else's email forever)."""
    return not user.email_verified and verification_expired(user.verification_sent_at)


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
        400: {"model": ErrorResponse, "description": "Email of a throwaway mailbox service (DISPOSABLE_EMAIL)"},
        409: {"model": ErrorResponse, "description": "Email (the same mailbox) or nickname already registered"},
        429: {"model": ErrorResponse, "description": "Too many new accounts from this address; see Retry-After"},
    },
)
def register_user(
    req: UserRegisterRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    client = client_address(request)
    ensure_within_limit(register_limiter, client, "Too many new accounts from this address.")

    email_clean = req.email.strip().lower()
    nickname_clean = req.nickname.strip()

    if is_disposable_email(email_clean):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "DISPOSABLE_EMAIL", "message": "Temporary (throwaway) email addresses cannot register"},
        )

    # One mailbox, one account: `name+tag@...` and Gmail dots are the same mailbox (email_identity.py)
    same_mailbox = (
        db.query(User)
        .filter(or_(User.email == email_clean, User.email_canonical == canonical_email(email_clean)))
        .all()
    )
    # Nicknames differing only in letter case would look the same to other users
    same_nickname = db.query(User).filter(func.lower(User.nickname) == nickname_clean.lower()).all()

    if any(not abandoned_registration(user) for user in same_mailbox):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_ALREADY_EXISTS", "message": "An account with this email already exists"},
        )
    if any(not abandoned_registration(user) for user in same_nickname):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "NICKNAME_ALREADY_EXISTS", "message": "An account with this nickname already exists"},
        )
    for stale in {user.user_id: user for user in same_mailbox + same_nickname}.values():
        remove_user_with_data(db, stale)
    db.flush()

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
    register_limiter.record(client)

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
    responses={
        **STANDARD_ERRORS,
        429: {"model": ErrorResponse, "description": "Too many activation emails from this address; see Retry-After"},
    },
)
def resend_verification(
    req: ResendVerificationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    client = client_address(request)
    ensure_within_limit(resend_limiter, client, "Too many activation emails requested.")
    resend_limiter.record(client)

    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if user is not None and not user.email_verified and not recently_sent(user.verification_sent_at):
        user.verification_token = generate_verification_token()
        user.verification_sent_at = datetime.now(timezone.utc)
        db.commit()
        background_tasks.add_task(send_verification_email, user.email, user.nickname, user.verification_token)
    return MessageResponse(message="If the account exists and is not verified yet, a new activation link was sent.")


PASSWORD_RESET_SENT = "If an account with this email exists, we sent a link to set a new password."


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send a password reset link (forgot password)",
    description=(
        "Emails a link to set a new password; it works for one hour. The answer is the same whether or not "
        "the email is registered, so it cannot be used to find accounts. Demo (seed) accounts get no link."
    ),
    responses={
        **STANDARD_ERRORS,
        429: {"model": ErrorResponse, "description": "Too many reset emails from this address; see Retry-After"},
    },
)
def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    client = client_address(request)
    ensure_within_limit(password_reset_limiter, client, "Too many password reset emails requested.")
    password_reset_limiter.record(client)

    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if user is not None and not is_seed_account(user.email) and not recently_sent(user.password_reset_sent_at):
        token = generate_verification_token()
        user.password_reset_token = hash_reset_token(token)
        user.password_reset_sent_at = datetime.now(timezone.utc)
        db.commit()
        background_tasks.add_task(send_password_reset_email, user.email, user.nickname, token)
    return MessageResponse(message=PASSWORD_RESET_SENT)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Set a new password with the link from the email",
    description=(
        "Sets the new password (minimum 8 characters), ends every session of the account and makes the link "
        "unusable. The link also confirms the mailbox, so a pending account becomes active."
    ),
    responses={
        **STANDARD_ERRORS,
        400: {"model": ErrorResponse, "description": "Invalid, used or expired reset link"},
    },
)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.password_reset_token == hash_reset_token(req.token)).first()
    if user is None or is_seed_account(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RESET_TOKEN", "message": "The password reset link is invalid or already used"},
        )
    if password_reset_expired(user.password_reset_sent_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "RESET_TOKEN_EXPIRED",
                "message": "The password reset link has expired. Request a new one from the login window.",
            },
        )

    user.password_hash = hash_password(req.new_password)
    user.token_version = (user.token_version or 0) + 1
    user.password_reset_token = None
    user.password_reset_sent_at = None
    if not user.email_verified:
        user.email_verified = True
        user.status = "active"
        user.verification_token = None
        user.verification_sent_at = None
    db.commit()
    return MessageResponse(message="Password changed. You can now log in with the new password.")


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
    client = client_address(request)
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
    403: {"model": ErrorResponse, "description": "Demo (seed) or administrator account; deletion while banned"},
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
        "watchlist, watched list and ban history, and clears the session cookie. "
        "Not available while the account is banned (403 ACCOUNT_BANNED)."
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
