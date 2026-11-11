import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt

from src.api.settings import env_int

logger = logging.getLogger(__name__)

# JWT Security Configuration: the signing key comes only from the environment. Without it a random
# key is generated per process (fine for local development; sessions end on every restart).
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(64)
if not os.getenv("JWT_SECRET_KEY"):
    logger.warning("JWT_SECRET_KEY is not set: using a random key, sessions will not survive a restart.")
JWT_ALGORITHM = "HS256"
# Modular crypt format of bcrypt: $2b$<cost>$<22 chars of salt><31 chars of hash>
BCRYPT_HASH = re.compile(r"\$2[abxy]\$\d{2}\$[./A-Za-z0-9]{53}")
# 24 hours; a wrong value falls back to the default instead of stopping the API (reliability, finding 15)
ACCESS_TOKEN_EXPIRE_MINUTES = env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 1440, minimum=1, maximum=60 * 24 * 30)


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

    Reliability (finding 7): a wrong password is an ordinary False; a stored hash that bcrypt cannot read
    (damaged, empty, not bcrypt) is also False for the user, so the login fails safely with 401,
    but it is logged as an error, because only an administrator can fix it (password reset).
    """
    if not plain_password:
        return False
    if not hashed_password:
        logger.error("Password check failed: the account has no stored password hash.")
        return False
    # Guard clause: a damaged hash makes the Rust core of bcrypt panic (PanicException is a BaseException,
    # so even `except Exception` did not catch it and the login answered 500)
    if not isinstance(hashed_password, str) or not BCRYPT_HASH.fullmatch(hashed_password):
        logger.error("Password check failed: the stored password hash is invalid (not a bcrypt hash).")
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError) as error:
        # The message of bcrypt never contains the hash or the password; the type is enough to diagnose
        logger.error("Password check failed: the stored password hash is invalid (%s).", type(error).__name__)
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
