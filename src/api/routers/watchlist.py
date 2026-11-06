from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.db.models import Content, User, WatchlistItem
from src.api.routers.auth import get_current_active_user, get_db
from src.api.schemas.errors import STANDARD_ERRORS, ErrorResponse
from src.api.schemas.movie import ContentResponse
from src.api.schemas.watchlist import WatchlistAddRequest, WatchlistResponse

# Content id is sent in the body / query string, so client request URLs stay constant
router = APIRouter(prefix="/api/v1/watchlist", tags=["Watchlist"])

AUTH_ERRORS = {
    401: {"model": ErrorResponse, "description": "User is not authenticated"},
    403: {"model": ErrorResponse, "description": "Email is not verified or the account is banned"},
}


@router.get(
    "",
    response_model=WatchlistResponse,
    summary="Get my watchlist (FR-005)",
    responses={**STANDARD_ERRORS, **AUTH_ERRORS},
)
def get_watchlist(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(Content)
        .join(WatchlistItem, WatchlistItem.content_id == Content.content_id)
        .filter(WatchlistItem.user_id == user.user_id)
        .order_by(WatchlistItem.added_at.desc(), Content.id.asc())
        .all()
    )
    return WatchlistResponse(items=items, total=len(items))


@router.post(
    "",
    response_model=ContentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a movie or series to my watchlist (FR-005)",
    responses={
        **STANDARD_ERRORS,
        **AUTH_ERRORS,
        409: {"model": ErrorResponse, "description": "The title is already in the watchlist"},
    },
)
def add_to_watchlist(
    payload: WatchlistAddRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    content = db.query(Content).filter(Content.content_id == payload.content_id).first()
    if content is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "CONTENT_NOT_FOUND", "message": "Movie or series not found in catalog"},
        )

    exists = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.user_id, WatchlistItem.content_id == payload.content_id)
        .first()
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_IN_WATCHLIST", "message": "This title is already in your watchlist"},
        )

    db.add(WatchlistItem(user_id=user.user_id, content_id=payload.content_id, added_at=datetime.now(UTC)))
    try:
        db.commit()
    except IntegrityError:
        # Race condition defense (REL-002): two simultaneous requests passed the check above,
        # the UNIQUE (user_id, content_id) constraint in the DB catches the second one.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_IN_WATCHLIST", "message": "This title is already in your watchlist"},
        )
    return content


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a movie or series from my watchlist (FR-005)",
    responses={**STANDARD_ERRORS, **AUTH_ERRORS},
)
def remove_from_watchlist(
    content_id: UUID4 = Query(..., description="Movie or series to remove"),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    deleted = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.user_id, WatchlistItem.content_id == content_id)
        .delete(synchronize_session=False)
    )
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_IN_WATCHLIST", "message": "This title is not in your watchlist"},
        )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
