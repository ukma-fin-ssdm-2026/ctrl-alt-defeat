import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt
from sqlalchemy.orm import Session

from src.api.db.models import User

# JWT Security Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "ctrl-alt-defeat-super-secret-jwt-key-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours


def hash_password(password: str) -> str:
    """
    Hash a plain password using bcrypt with a unique salt (SEC-001).
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against the stored bcrypt hash (SEC-001).
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a stateless signed JWT access token (US-011).
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"iat": int(now.timestamp()), "exp": int(expire.timestamp())})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token's signature and expiration (US-011).
    Raises jwt.PyJWTError if invalid or expired.
    """
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def generate_verification_token() -> str:
    """
    Generate a cryptographically secure random token for email verification (FR-001).
    """
    return secrets.token_urlsafe(32)


def seed_default_users(db: Session) -> None:
    """
    Seed initial admin and regular demo users into database if they do not already exist.
    """
    admin_email = "admin@gmail.com"
    existing_admin = db.query(User).filter(User.email == admin_email).first()
    if not existing_admin:
        admin_user = User(
            email=admin_email,
            nickname="admin",
            password_hash=hash_password("password12345"),
            role="admin",
            email_verified=True,
            status="active",
        )
        db.add(admin_user)

    user_email = "user@example.com"
    existing_user = db.query(User).filter(User.email == user_email).first()
    if not existing_user:
        demo_user = User(
            email=user_email,
            nickname="cinema_fan",
            password_hash=hash_password("password123"),
            role="user",
            email_verified=True,
            status="active",
        )
        db.add(demo_user)

    db.commit()
