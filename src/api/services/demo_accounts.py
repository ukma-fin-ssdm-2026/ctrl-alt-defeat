"""
Demo / seed accounts — the single source of truth for the accounts created on startup and for the
login hint shown in the UI (GET /api/v1/auth/demo-accounts). Credentials come only from environment
variables (a local `.env` file or the hosting platform settings), never from the code.

    SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD   administrator account (created only when the password is set)
    SEED_USER_EMAIL  / SEED_USER_PASSWORD    regular user account (created only when the password is set)
    DEMO_MODE=true                           publish the seed accounts in the login window (demo deployments only)
    DEMO_ROLES=admin,user                    which of them the login window may show (default: both); a public
                                             site uses DEMO_ROLES=user and hands the admin password out privately
"""

import logging
import os
from dataclasses import dataclass
from typing import List

from sqlalchemy.orm import Session

from src.api.db.models import User
from src.api.services.auth import hash_password, verify_password

logger = logging.getLogger(__name__)

TRUE_VALUES = ("1", "true", "yes", "on")


@dataclass(frozen=True)
class SeedAccount:
    role: str
    email: str
    nickname: str
    password: str


def demo_mode_enabled() -> bool:
    return os.getenv("DEMO_MODE", "false").strip().lower() in TRUE_VALUES


def get_seed_accounts() -> List[SeedAccount]:
    """Accounts configured in the environment; an account without a password is skipped."""
    configured = [
        ("admin", "SEED_ADMIN", "admin@gmail.com", "admin"),
        ("user", "SEED_USER", "user@example.com", "cinema_fan"),
    ]
    accounts = []
    for role, prefix, default_email, default_nickname in configured:
        password = os.getenv(f"{prefix}_PASSWORD", "")
        if not password:
            continue
        accounts.append(
            SeedAccount(
                role=role,
                email=os.getenv(f"{prefix}_EMAIL", default_email).strip().lower(),
                nickname=os.getenv(f"{prefix}_NICKNAME", default_nickname).strip(),
                password=password,
            )
        )
    return accounts


def public_demo_roles() -> set:
    raw = os.getenv("DEMO_ROLES", "admin,user")
    return {role.strip().lower() for role in raw.split(",") if role.strip()}


def get_public_demo_accounts() -> List[SeedAccount]:
    """What the login window may show: the seed accounts of the allowed roles, only in demo mode."""
    if not demo_mode_enabled():
        return []
    roles = public_demo_roles()
    return [account for account in get_seed_accounts() if account.role in roles]


def seed_default_users(db: Session) -> None:
    """
    Create the configured accounts (verified and active) or bring an existing one in line with the
    environment, so the password from the configuration (and the UI hint) always works.
    A ban set by an administrator is never lifted here.
    """
    accounts = get_seed_accounts()
    if not accounts:
        logger.info("No SEED_*_PASSWORD configured: demo accounts are not created.")
        return

    for account in accounts:
        user = db.query(User).filter(User.email == account.email).first()
        if user is None:
            if db.query(User.user_id).filter(User.nickname == account.nickname).first() is not None:
                logger.warning("Seed account %s skipped: nickname %s is taken.", account.email, account.nickname)
                continue
            db.add(
                User(
                    email=account.email,
                    nickname=account.nickname,
                    password_hash=hash_password(account.password),
                    role=account.role,
                    email_verified=True,
                    status="active",
                )
            )
            continue
        if not verify_password(account.password, user.password_hash):
            user.password_hash = hash_password(account.password)
        user.role = account.role
        user.email_verified = True
    db.commit()
