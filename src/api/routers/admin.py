"""Administration: user list and account bans (FR-009, US-006). Every endpoint requires the admin role."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.api.db.database import SessionLocal
from src.api.db.models import User
from src.api.routers.auth import get_current_admin
from src.api.schemas.ban import AdminUser, AdminUserList, BanCreate, BanInfo
from src.api.schemas.errors import STANDARD_ERRORS, ErrorResponse
from src.api.services.account import admin_delete_user
from src.api.services.bans import active_ban, ban_user, unban_user

router = APIRouter(prefix="/api/v1/admin", tags=["Administration"])

ADMIN_ERRORS = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Administrator privileges required"},
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class MessageResponse(BaseModel):
    message: str


def to_admin_user(db: Session, user: User) -> AdminUser:
    return AdminUser(
        user_id=user.user_id,
        email=user.email,
        nickname=user.nickname,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        ban=active_ban(db, user),
    )


@router.get(
    "/users",
    response_model=AdminUserList,
    summary="List users with their current ban (FR-009)",
    responses={**STANDARD_ERRORS, **ADMIN_ERRORS},
)
def list_users(
    q: Optional[str] = Query(None, max_length=100, description="Search by nickname or email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    query = db.query(User)
    if q and q.strip():
        pattern = f"%{q.strip().lower()}%"
        query = query.filter(or_(func.lower(User.nickname).like(pattern), func.lower(User.email).like(pattern)))
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return AdminUserList(items=[to_admin_user(db, user) for user in users], total=total)


@router.post(
    "/bans",
    response_model=BanInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Ban a user temporarily or permanently (FR-009)",
    description=(
        "A temporary ban needs `duration_days` (1-365); a permanent ban has no end. "
        "A new ban replaces the current one. Administrators cannot be banned."
    ),
    responses={**STANDARD_ERRORS, **ADMIN_ERRORS},
)
def create_ban(request: BanCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return ban_user(db, admin, request)


@router.delete(
    "/bans",
    response_model=MessageResponse,
    summary="Lift the current ban of a user (FR-009)",
    responses={**STANDARD_ERRORS, **ADMIN_ERRORS},
)
def delete_ban(
    user_id: uuid.UUID = Query(..., description="User whose ban is lifted"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    unban_user(db, user_id)
    return MessageResponse(message="Ban lifted")


@router.delete(
    "/users",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user with all their data",
    description=(
        "Removes the account with its reviews, ratings, comments, lists and ban history (e.g. spam accounts). "
        "Administrators, the administrator themselves and demo (seed) accounts cannot be deleted."
    ),
    responses={**STANDARD_ERRORS, **ADMIN_ERRORS},
)
def delete_user(
    user_id: uuid.UUID = Query(..., description="User to delete"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    admin_delete_user(db, admin, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
