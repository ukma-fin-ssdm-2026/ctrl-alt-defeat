import uuid
from datetime import datetime, UTC
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.db import models
from src.api.db.database import SessionLocal
from src.api.routers.auth import get_current_active_user
from src.api.schemas.errors import STANDARD_ERRORS, ErrorResponse
from src.api.schemas.review import (
    PaginatedReviewsResponse,
    ReviewCreate,
    ReviewResponse,
    ReviewStatus,
    ReviewUpdate,
)
from src.api.utils import check_review_policy_violations

DUPLICATE_REVIEW_ERROR = {
    "code": "DUPLICATE_REVIEW",
    "message": "You have already reviewed this content. Edit your existing review instead.",
}

NOT_WATCHED_ERROR = {
    "code": "CONTENT_NOT_WATCHED",
    "message": "Mark this title as watched before rating or reviewing it",
}

AUTH_ERRORS = {
    401: {"model": ErrorResponse, "description": "User is not authenticated"},
    403: {
        "model": ErrorResponse,
        "description": "Not allowed (title not watched, not the author, banned or unverified)",
    },
}

router = APIRouter(
    prefix="/api/v1/reviews",
    tags=["reviews"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new review",
    responses={
        **STANDARD_ERRORS,
        **AUTH_ERRORS,
        409: {"model": ErrorResponse, "description": "User has already reviewed this content"},
    },
)
async def create_review(
    review: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    user_id = current_user.user_id

    # FR-003 / FR-004: only titles from the user's watched list can be rated and reviewed
    is_watched = db.query(
        db.query(models.WatchedItem)
        .filter(models.WatchedItem.user_id == user_id, models.WatchedItem.content_id == review.content_id)
        .exists()
    ).scalar()
    if not is_watched:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=NOT_WATCHED_ERROR)

    if review.review_text:
        violations = check_review_policy_violations(review.review_text)
        if violations:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "POLICY_VIOLATION",
                    "message": f"Review contains forbidden content: {', '.join(violations)}",
                },
            )

    # One review per user per content
    existing_review = (
        db.query(models.Review)
        .filter(
            models.Review.user_id == user_id,
            models.Review.content_id == review.content_id,
        )
        .first()
    )
    if existing_review is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_REVIEW_ERROR)

    review_id = uuid.uuid4()
    new_review = ReviewResponse(
        review_id=review_id,
        user_id=user_id,
        author_nickname=current_user.nickname,
        status=ReviewStatus.published,
        created_at=datetime.now(UTC),
        **review.model_dump(),
    )
    db_review = models.Review(
        review_id=new_review.review_id,
        user_id=new_review.user_id,
        content_id=new_review.content_id,
        rating=new_review.rating,
        review_text=new_review.review_text,
        contains_spoilers=new_review.contains_spoilers,
        status=new_review.status.value,
        created_at=new_review.created_at,
    )

    db.add(db_review)
    try:
        db.commit()
    except IntegrityError:
        # Race condition: two simultaneous requests passed the check above,
        # the UNIQUE (user_id, content_id) constraint in the DB catches the second one.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_REVIEW_ERROR)
    return new_review


@router.get(
    "",
    response_model=PaginatedReviewsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a list of reviews (with pagination)",
)
async def get_reviews(
    content_id: Optional[UUID4] = Query(None, description="Filter by content ID"),
    user_id: Optional[UUID4] = Query(None, description="Filter by user ID"),
    min_rating: Annotated[Optional[int], Query(ge=1, le=10, description="Filter by minimum rating (1-10)")] = None,
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of items per page"),
    db: Session = Depends(get_db),
):
    query = db.query(models.Review)

    if content_id:
        query = query.filter(models.Review.content_id == content_id)

    if user_id:
        query = query.filter(models.Review.user_id == user_id)

    if min_rating:
        query = query.filter(models.Review.rating >= min_rating)

    total = query.count()
    paginated_items = query.offset(skip).limit(limit).all()
    has_more = (skip + limit) < total

    return PaginatedReviewsResponse(items=paginated_items, total=total, skip=skip, limit=limit, has_more=has_more)


@router.get(
    "/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a specific review by ID",
    responses=STANDARD_ERRORS,
)
async def get_review(
    review_id: UUID4 = Path(..., description="ID of the review"),
    db: Session = Depends(get_db),
):
    db_review = db.query(models.Review).filter(models.Review.review_id == review_id).first()

    if db_review is None:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_NOT_FOUND", "message": "Review not found"})
    return db_review


@router.patch(
    "/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update my review",
    responses={**STANDARD_ERRORS, **AUTH_ERRORS},
)
async def update_review(
    review_update: ReviewUpdate,
    review_id: UUID4 = Path(..., description="ID of the review to update"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    existing_review = db.query(models.Review).filter(models.Review.review_id == review_id).first()

    if existing_review is None:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_NOT_FOUND", "message": "Review not found"})

    if existing_review.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "NOT_REVIEW_AUTHOR", "message": "You can edit only your own reviews"},
        )

    update_data = review_update.model_dump(exclude_unset=True)

    if update_data.get("review_text"):
        violations = check_review_policy_violations(update_data["review_text"])
        if violations:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "POLICY_VIOLATION",
                    "message": f"Review contains forbidden content: {', '.join(violations)}",
                },
            )

    for key, value in update_data.items():
        setattr(existing_review, key, value)

    db.commit()
    db.refresh(existing_review)

    return existing_review


def _delete_review(db: Session, current_user: models.User, review_id) -> Response:
    existing_review = db.query(models.Review).filter(models.Review.review_id == review_id).first()

    if existing_review is None:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_NOT_FOUND", "message": "Review not found"})

    # BOLA check (FR-008, US-006): only author or admin can delete
    if current_user.role != "admin" and str(existing_review.user_id) != str(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You do not have permission to delete this review"},
        )

    # Remove the comment thread too (bulk delete works on SQLite without FK enforcement)
    db.query(models.Comment).filter(models.Comment.review_id == review_id).delete(synchronize_session=False)
    db.delete(existing_review)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


DELETE_RESPONSES = {
    **STANDARD_ERRORS,
    401: {"model": ErrorResponse, "description": "Authentication required"},
    403: {"model": ErrorResponse, "description": "Forbidden: BOLA violation (author or admin required)"},
}


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a review by query parameter (FR-008, US-006)",
    description="Same as DELETE /reviews/{review_id}, with the id as a query parameter (constant client URLs).",
    responses=DELETE_RESPONSES,
)
async def delete_review_by_query(
    review_id: UUID4 = Query(..., description="ID of the review to delete"),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return _delete_review(db, current_user, review_id)


@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a review (FR-008, US-006)",
    responses=DELETE_RESPONSES,
)
async def delete_review(
    review_id: UUID4 = Path(..., description="ID of the review to delete"),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return _delete_review(db, current_user, review_id)
