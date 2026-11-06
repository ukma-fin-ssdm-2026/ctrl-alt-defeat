from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.db.database import SessionLocal
from src.api.db.models import ContentGenre, Genre
from src.api.schemas.movie import GenreResponse

router = APIRouter(prefix="/api/v1/genres", tags=["Movies & Series Catalog"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "",
    response_model=List[GenreResponse],
    summary="Genres of the catalog with the number of titles (FR-012)",
    description="Genres sorted by name. By default only genres that have at least one title are returned.",
)
def list_genres(
    include_empty: bool = Query(False, description="Also return genres without titles"),
    db: Session = Depends(get_db),
):
    titles_count = func.count(ContentGenre.content_id)
    query = (
        db.query(Genre.genre_id, Genre.name, Genre.name_en, titles_count.label("titles_count"))
        .outerjoin(ContentGenre, ContentGenre.genre_id == Genre.genre_id)
        .group_by(Genre.genre_id, Genre.name, Genre.name_en)
        .order_by(Genre.name)
    )
    if not include_empty:
        query = query.having(titles_count > 0)
    return [GenreResponse(**row._asdict()) for row in query.all()]
