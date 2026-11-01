from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from src.api.db.database import SessionLocal
from src.api.schemas.errors import STANDARD_ERRORS, ErrorResponse
from src.api.schemas.recommendation import RecommendationsResponse
from src.api.services.recommendations import recommend_for_user

router = APIRouter(prefix="/api/v1/recommendations", tags=["Recommendations"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_recommendation_user_id(
    user_id: Optional[UUID4] = Query(
        None,
        description="Temporary until authentication (FR-001) is merged: the user to build recommendations for",
    ),
) -> UUID4:
    """
    Resolves the current user. TODO(FR-001): replace with the authenticated user from the access token.
    """
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Log in to get personal recommendations"},
        )
    return user_id


@router.get(
    "",
    response_model=RecommendationsResponse,
    summary='Get personal recommendations ("Recommended for you")',
    description=(
        "Movies and series the user has not reviewed yet, ranked by how well their genres match "
        "the user's highly rated titles (FR-007). New users get the best-rated titles."
    ),
    responses={
        **STANDARD_ERRORS,
        401: {"model": ErrorResponse, "description": "User is not authenticated"},
    },
)
def get_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of recommendations"),
    user_id: UUID4 = Depends(get_recommendation_user_id),
    db: Session = Depends(get_db),
):
    result = recommend_for_user(db, user_id, limit)
    return RecommendationsResponse(
        items=result.items,
        personalized=result.personalized,
        favorite_genres=result.favorite_genres,
    )
