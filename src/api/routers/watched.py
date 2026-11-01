from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from src.api.db import models
from src.api.db.database import SessionLocal
from src.api.routers.auth import get_current_active_user
from src.api.schemas.errors import STANDARD_ERRORS, ErrorResponse
from src.api.schemas.watched import (
    WatchedItemCreate,
    WatchedItemResponse,
    WatchedListResponse,
    WatchedStatusResponse,
)

router = APIRouter(
    prefix="/api/v1/users/me/watched",
    tags=["watched"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _build_watched_response(watched: models.WatchedItem, db: Session) -> WatchedItemResponse:
    content = db.query(models.Content).filter(models.Content.content_id == watched.content_id).first()
    return WatchedItemResponse(
        id=watched.id,
        user_id=watched.user_id,
        content_id=watched.content_id,
        created_at=watched.created_at,
        title=content.title if content else None,
        title_en=content.title_en if content else None,
        category=content.category if content else None,
        genre=content.genre if content else None,
        year=content.year if content else None,
        rating=content.rating if content else None,
        img=content.img if content else None,
    )


@router.get(
    "",
    response_model=WatchedListResponse,
    summary="Get user's watched list (FR-006, US-004)",
    description="Returns all movies and series marked as watched by the current user.",
    responses={
        **STANDARD_ERRORS,
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
def get_watched_list(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    watched_items = (
        db.query(models.WatchedItem)
        .filter(models.WatchedItem.user_id == current_user.user_id)
        .order_by(models.WatchedItem.created_at.desc())
        .all()
    )

    items = [_build_watched_response(item, db) for item in watched_items]
    return WatchedListResponse(items=items, total=len(items))


@router.post(
    "",
    response_model=WatchedItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mark content as watched (FR-006, US-004, T-011)",
    description="Adds a movie or series to the current user's watched list.",
    responses={
        **STANDARD_ERRORS,
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
def mark_as_watched(
    payload: WatchedItemCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    existing = (
        db.query(models.WatchedItem)
        .filter(
            models.WatchedItem.user_id == current_user.user_id,
            models.WatchedItem.content_id == payload.content_id,
        )
        .first()
    )

    if existing:
        response.status_code = status.HTTP_200_OK
        return _build_watched_response(existing, db)

    new_item = models.WatchedItem(
        user_id=current_user.user_id,
        content_id=payload.content_id,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return _build_watched_response(new_item, db)


@router.get(
    "/{content_id}",
    response_model=WatchedStatusResponse,
    summary="Check if content is in watched list",
    description="Checks whether the specified content has been marked as watched by the current user.",
    responses={
        **STANDARD_ERRORS,
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
)
def check_is_watched(
    content_id: UUID4 = Path(..., description="Content ID to check"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    watched = (
        db.query(models.WatchedItem)
        .filter(
            models.WatchedItem.user_id == current_user.user_id,
            models.WatchedItem.content_id == content_id,
        )
        .first()
    )
    if not watched:
        return WatchedStatusResponse(
            is_watched=False,
            content_id=content_id,
            watched_at=None,
        )

    return WatchedStatusResponse(
        is_watched=True,
        content_id=content_id,
        watched_at=watched.created_at,
    )


@router.delete(
    "/{content_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove content from watched list (FR-006, US-004, T-012)",
    description="Removes a movie or series from the current user's watched list.",
    responses={
        **STANDARD_ERRORS,
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Content not in watched list"},
    },
)
def remove_from_watched(
    content_id: UUID4 = Path(..., description="Content ID to remove"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    watched = (
        db.query(models.WatchedItem)
        .filter(
            models.WatchedItem.user_id == current_user.user_id,
            models.WatchedItem.content_id == content_id,
        )
        .first()
    )

    if not watched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Content not found in your watched list"},
        )

    db.delete(watched)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
