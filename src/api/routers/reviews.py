import uuid
from datetime import datetime, UTC
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from src.api.db import models
from src.api.db.database import SessionLocal
from src.api.schemas.errors import STANDARD_ERRORS
from src.api.schemas.review import (
    PaginatedReviewsResponse,
    ReviewCreate,
    ReviewResponse,
    ReviewStatus,
    ReviewUpdate,
)
from src.api.utils import check_review_policy_violations

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
    responses=STANDARD_ERRORS,
)
async def create_review(
    review: ReviewCreate,
    db: Session = Depends(get_db),
):
    violations = check_review_policy_violations(review.review_text)
    if violations:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "POLICY_VIOLATION",
                "message": f"Review contains forbidden content: {', '.join(violations)}",
            },
        )

    review_id = uuid.uuid4()
    new_review = ReviewResponse(
        review_id=review_id, status=ReviewStatus.published, created_at=datetime.now(UTC), **review.model_dump()
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
    db.commit()
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
    summary="Partially update a review",
    responses=STANDARD_ERRORS,
)
async def update_review(
    review_update: ReviewUpdate,
    review_id: UUID4 = Path(..., description="ID of the review to update"),
    db: Session = Depends(get_db),
):
    existing_review = db.query(models.Review).filter(models.Review.review_id == review_id).first()

    if existing_review is None:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_NOT_FOUND", "message": "Review not found"})

    update_data = review_update.model_dump(exclude_unset=True)

    if "review_text" in update_data:
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


@router.delete(
    "/{review_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a review", responses=STANDARD_ERRORS
)
async def delete_review(
    review_id: UUID4 = Path(..., description="ID of the review to delete"),
    db: Session = Depends(get_db),
):
    existing_review = db.query(models.Review).filter(models.Review.review_id == review_id).first()

    if existing_review is None:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_NOT_FOUND", "message": "Review not found"})
    db.delete(existing_review)
    db.commit()
    return None
