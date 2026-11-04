"""Account bans (FR-009): which ban is in force, banning and lifting a ban."""

from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.api.db.models import Ban, User
from src.api.schemas.ban import BanCreate, BanInfo, BanType


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite returns naive datetimes; everything is stored in UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def active_ban(db: Session, user: User, now: Optional[datetime] = None) -> Optional[BanInfo]:
    """The ban in force for the user, or None. A temporary ban stops being in force after ends_at."""
    now = now or datetime.now(UTC)
    bans = (
        db.query(Ban).filter(Ban.user_id == user.user_id, Ban.is_active.is_(True)).order_by(Ban.starts_at.desc()).all()
    )
    for ban in bans:
        ends_at = _as_utc(ban.ends_at)
        if ends_at is None or ends_at > now:
            return BanInfo(ban_type=ban.ban_type, reason=ban.reason, starts_at=_as_utc(ban.starts_at), ends_at=ends_at)
    if user.status == "banned":
        # Accounts banned before the bans table existed are treated as permanently banned
        return BanInfo(ban_type=BanType.permanent)
    return None


def ban_message(ban: BanInfo) -> str:
    if ban.ban_type == BanType.permanent:
        text = "Your account is permanently banned"
    else:
        text = f"Your account is banned until {ban.ends_at.strftime('%Y-%m-%d %H:%M')} UTC"
    return f"{text}. Reason: {ban.reason}" if ban.reason else f"{text}."


def ensure_can_contribute(db: Session, user: User) -> None:
    """Banned users cannot write reviews, rate or comment (FR-009); everything else stays available."""
    ban = active_ban(db, user)
    if ban is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_BANNED", "message": ban_message(ban)},
        )


def ban_user(db: Session, admin: User, request: BanCreate) -> BanInfo:
    target = db.query(User).filter(User.user_id == request.user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "User not found"})
    if target.user_id == admin.user_id:
        raise HTTPException(status_code=400, detail={"code": "CANNOT_BAN_SELF", "message": "You cannot ban yourself"})
    if target.role == "admin":
        raise HTTPException(
            status_code=400, detail={"code": "CANNOT_BAN_ADMIN", "message": "Administrators cannot be banned"}
        )

    now = datetime.now(UTC)
    # A new ban replaces the previous one; the old rows stay as history
    db.query(Ban).filter(Ban.user_id == target.user_id, Ban.is_active.is_(True)).update({Ban.is_active: False})
    ends_at = now + timedelta(days=request.duration_days) if request.ban_type == BanType.temporary else None
    ban = Ban(
        user_id=target.user_id,
        admin_id=admin.user_id,
        ban_type=request.ban_type.value,
        reason=request.reason,
        starts_at=now,
        ends_at=ends_at,
        is_active=True,
    )
    db.add(ban)
    db.commit()
    return BanInfo(ban_type=request.ban_type, reason=request.reason, starts_at=now, ends_at=ends_at)


def unban_user(db: Session, user_id) -> None:
    target = db.query(User).filter(User.user_id == user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "User not found"})
    if active_ban(db, target) is None:
        raise HTTPException(status_code=404, detail={"code": "BAN_NOT_FOUND", "message": "The user is not banned"})
    db.query(Ban).filter(Ban.user_id == target.user_id, Ban.is_active.is_(True)).update({Ban.is_active: False})
    if target.status == "banned":
        target.status = "active"
    db.commit()
