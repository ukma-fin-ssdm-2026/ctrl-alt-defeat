import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas.ban import BanInfo

# Minimum password length for new passwords (registration, change, reset); older shorter passwords still log in
PASSWORD_MIN_LENGTH = 8


class UserRegisterRequest(BaseModel):
    email: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        description="User email address (must be valid email format)",
    )
    nickname: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Unique display name (nickname) on the platform",
    )
    password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=100,
        description="User password (minimum 8 characters)",
    )


class UserLoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID = Field(..., description="Unique UUID identifier of the user")
    email: str = Field(..., description="User email address")
    nickname: str = Field(..., description="Display nickname")
    role: str = Field(..., description="User role: 'user' or 'admin'")
    email_verified: bool = Field(..., description="Whether the user's email has been verified")
    status: str = Field(..., description="Account status: 'pending', 'active', or 'banned'")
    created_at: datetime = Field(..., description="Account creation timestamp")
    ban: Optional[BanInfo] = Field(
        None, description="The ban in force (FR-009): the user can log in but cannot review, rate or comment"
    )


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="Stateless JWT access token")
    token_type: str = Field("bearer", description="Token type, always 'bearer'")
    user: UserResponse = Field(..., description="Current user information")


class RegisterResponse(BaseModel):
    message: str = Field(..., description="Status message")
    email: str = Field(..., description="Registered email address")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., max_length=100, description="Current password for confirmation")
    new_password: str = Field(
        ..., min_length=PASSWORD_MIN_LENGTH, max_length=100, description="New password (minimum 8 characters)"
    )


class DeleteAccountRequest(BaseModel):
    password: str = Field(..., max_length=100, description="Current password for confirmation")


class ResendVerificationRequest(BaseModel):
    email: str = Field(..., max_length=255, description="Email the account was registered with")


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., max_length=255, description="Email of the account")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=255, description="Token from the password reset email")
    new_password: str = Field(
        ..., min_length=PASSWORD_MIN_LENGTH, max_length=100, description="New password (minimum 8 characters)"
    )


class MessageResponse(BaseModel):
    message: str = Field(..., description="Status message")


class VerifyEmailResponse(BaseModel):
    message: str = Field(..., description="Status message")
    email: str = Field(..., description="Verified email address")
    status: str = Field(..., description="Updated account status")


class DemoAccount(BaseModel):
    role: str = Field(..., description="admin or user")
    email: str
    password: str


class DemoAccountsResponse(BaseModel):
    enabled: bool = Field(..., description="True only on demo deployments (DEMO_MODE=true)")
    accounts: List[DemoAccount] = Field(default_factory=list)
