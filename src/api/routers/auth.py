import uuid
from typing import Optional

import jwt
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from src.api.db.database import SessionLocal
from src.api.db.models import User
from src.api.schemas.auth import (
    RegisterResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    VerifyEmailResponse,
)
from src.api.schemas.errors import STANDARD_ERRORS, ErrorResponse
from src.api.services.auth import (
    create_access_token,
    decode_access_token,
    generate_verification_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & User Management"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate JWT access token from Authorization header or HttpOnly cookie (US-011).
    """
    token = None
    if authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
    if not token and access_token_cookie:
        token = access_token_cookie

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Authentication required. Please log in."},
        )

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

    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """
    Ensure the authenticated user is verified and not banned.
    """
    if user.status == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_BANNED", "message": "Account has been suspended"},
        )
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
        "Registers a new account with email and password. Generates a verification token "
        "and leaves account in pending unverified state until email verification."
    ),
    responses={
        **STANDARD_ERRORS,
        409: {"model": ErrorResponse, "description": "Email or nickname already registered"},
    },
)
def register_user(
    req: UserRegisterRequest,
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
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(
        message="Account created successfully. Please verify your email before logging in.",
        email=user.email,
        verification_token=verification_token,
    )


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

    user.email_verified = True
    user.status = "active"
    user.verification_token = None
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
        403: {"model": ErrorResponse, "description": "Account is unverified or banned"},
    },
)
def login(
    req: UserLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    email_clean = req.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
        )

    if user.status == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_BANNED", "message": "Your account has been suspended by an administrator"},
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "EMAIL_NOT_VERIFIED",
                "message": "Please verify your email before logging in. Check your mailbox for the activation link.",
            },
        )

    access_token = create_access_token(
        {
            "sub": str(user.user_id),
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role,
        }
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=86400,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
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
):
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    summary="Log out and clear session cookie",
    description="Clears the HttpOnly access_token cookie.",
)
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Successfully logged out"}
