import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt

logger = logging.getLogger(__name__)

# JWT Security Configuration: the signing key comes only from the environment. Without it a random
# key is generated per process (fine for local development; sessions end on every restart).
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(64)
if not os.getenv("JWT_SECRET_KEY"):
    logger.warning("JWT_SECRET_KEY is not set: using a random key, sessions will not survive a restart.")
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
