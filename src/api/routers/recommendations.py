from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.db.database import SessionLocal
from src.api.db.models import User
from src.api.routers.auth import get_current_active_user
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


@router.get(
    "",
    response_model=RecommendationsResponse,
    summary='Get my personal recommendations ("Recommended for you")',
    description=(
        "Movies and series the authenticated user has not reviewed yet, ranked by how well their genres match "
        "the user's highly rated titles (FR-007). New users get the best-rated titles. "
        "The user is always taken from the access token, so nobody can read another user's recommendations."
    ),
    responses={
        **STANDARD_ERRORS,
        401: {"model": ErrorResponse, "description": "User is not authenticated"},
        403: {"model": ErrorResponse, "description": "Email is not verified or the account is banned"},
    },
)
def get_recommendations(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of recommendations"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    result = recommend_for_user(db, current_user.user_id, limit)
    return RecommendationsResponse(
        items=result.items,
        personalized=result.personalized,
        favorite_genres=result.favorite_genres,
    )
