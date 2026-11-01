import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.api.db.database import SessionLocal
from src.api.db.models import Content
from src.api.schemas.movie import ContentResponse, PaginatedContentResponse

router = APIRouter(prefix="/api/v1/movies", tags=["Movies & Series Catalog"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "",
    response_model=PaginatedContentResponse,
    summary="Get catalog of movies and series",
    description=(
        "Retrieve list of movies and series with search by title, "
        "filters by category, genre, year, and offset pagination."
    ),
)
def get_movies(
    search: Optional[str] = Query(None, description="Search term in title (Ukrainian or English)"),
    category: Optional[str] = Query(None, description="Category: 'Movie' or 'Series'"),
    genre: Optional[str] = Query(None, description="Genre filter (e.g., 'Фантастика', 'Драма')"),
    year: Optional[int] = Query(None, description="Release year filter (e.g., 2024)"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum items per page"),
    db: Session = Depends(get_db),
):
    query = db.query(Content)

    if search:
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Content.title.ilike(search_filter),
                Content.title_en.ilike(search_filter),
            )
        )

    if category:
        query = query.filter(Content.category.ilike(category.strip()))

    if genre:
        query = query.filter(Content.genre.ilike(f"%{genre.strip()}%"))

    if year is not None:
        query = query.filter(Content.year == year)

    total = query.count()
    items = query.order_by(Content.id.asc()).offset(skip).limit(limit).all()
    has_more = (skip + limit) < total

    return PaginatedContentResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


@router.get(
    "/{movie_id}",
    response_model=ContentResponse,
    summary="Get movie details by ID or content UUID",
    description="Retrieve a single movie or series by its numeric ID or UUID content_id.",
)
def get_movie_by_id(
    movie_id: str,
    db: Session = Depends(get_db),
):
    content = None
    # Check if movie_id is a valid UUID
    try:
        content_uuid = uuid.UUID(movie_id)
        content = db.query(Content).filter(Content.content_id == content_uuid).first()
    except (ValueError, AttributeError):
        pass

    # If not UUID or not found by UUID, try integer ID
    if not content and movie_id.isdigit():
        content = db.query(Content).filter(Content.id == int(movie_id)).first()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CONTENT_NOT_FOUND",
                "message": f"Content with ID '{movie_id}' was not found in catalog",
            },
        )

    return content

