import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, defer
from sqlalchemy import func, or_, select

from src.api.db.database import SessionLocal
from src.api.db.models import Content, ContentGenre, Genre
from src.api.schemas.movie import ContentResponse, ContentSortField, PaginatedContentResponse, SortOrder

# Maps public sort keys to DB columns (FR-010). "release_date" uses the release year.
SORT_COLUMNS = {
    ContentSortField.rating: Content.rating,
    ContentSortField.release_date: Content.year,
    ContentSortField.runtime: Content.runtime,
}

router = APIRouter(prefix="/api/v1/movies", tags=["Movies & Series Catalog"])

# Long texts left out of a compact list (`compact=true`): the page of a title loads them with GET /movies/{id}
LONG_FIELDS = ("description", "description_en")
LIST_FIELDS = [name for name in ContentResponse.model_fields if name not in LONG_FIELDS]


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
        "filters by category, genre, year, sorting (rating, release date, runtime) and offset pagination. "
        "Sorting is applied to the filtered result set; items with unknown values are always placed last. "
        "Without sort_by the most recently added titles come first."
    ),
)
def get_movies(
    search: Optional[str] = Query(None, max_length=100, description="Search term in title (Ukrainian or English)"),
    category: Optional[str] = Query(None, description="Category: 'Movie' or 'Series'"),
    genre: Optional[str] = Query(
        None,
        description="Genre filter, Ukrainian or English name (e.g. 'Фантастика' or 'Sci-Fi'); "
        "matches any genre of the title, not only the primary one",
    ),
    year: Optional[int] = Query(None, ge=1888, le=2100, description="Release year filter (e.g., 2024)"),
    sort_by: Optional[ContentSortField] = Query(
        None, description="Sort criterion: 'rating', 'release_date' (release year) or 'runtime'"
    ),
    order: SortOrder = Query(SortOrder.desc, description="Sort direction: 'desc' (default) or 'asc'"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum items per page"),
    compact: bool = Query(
        False,
        description="Leave out the synopses (`description`, `description_en` are null): a list for cards and "
        "search is several times smaller; the details of one title come from GET /movies/{movie_id}",
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Content)
    if compact:
        # The synopses are not even read from the database
        query = query.options(*(defer(getattr(Content, name)) for name in LONG_FIELDS))

    if search and search.strip():
        # `%` and `_` typed by the user are plain characters, not LIKE wildcards
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_filter = f"%{escaped}%"
        query = query.filter(
            or_(
                Content.title.ilike(search_filter, escape="\\"),
                Content.title_en.ilike(search_filter, escape="\\"),
            )
        )

    if category:
        query = query.filter(Content.category.ilike(category.strip()))

    if genre and genre.strip():
        # Issue #61: titles linked to the genre through ContentGenre (any position)
        # Exact name first: SQLite lower() changes only ASCII letters, PostgreSQL also handles Cyrillic
        name = genre.strip()
        titles_of_genre = (
            select(ContentGenre.content_id)
            .join(Genre, Genre.genre_id == ContentGenre.genre_id)
            .where(
                or_(
                    Genre.name == name,
                    func.lower(Genre.name) == name.lower(),
                    func.lower(Genre.name_en) == name.lower(),
                )
            )
        )
        query = query.filter(Content.content_id.in_(titles_of_genre))

    if year is not None:
        query = query.filter(Content.year == year)

    total = query.count()
    if sort_by is not None:
        column = SORT_COLUMNS[sort_by]
        direction = column.desc() if order == SortOrder.desc else column.asc()
        # NULLs last in both directions (portable across SQLite and PostgreSQL), id as a stable tie-breaker
        query = query.order_by(column.is_(None), direction, Content.id.asc())
    else:
        # Recently added first: new titles from TMDB get the next numbers
        query = query.order_by(Content.id.desc())

    items = query.offset(skip).limit(limit).all()
    has_more = (skip + limit) < total
    if compact:
        # Only the loaded columns are read: touching a deferred one would load it row by row
        items = [ContentResponse.model_validate({name: getattr(row, name) for name in LIST_FIELDS}) for row in items]

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

    # If not UUID or not found by UUID, try integer ID within valid 32-bit range (finding 9)
    if not content and movie_id.isdigit() and len(movie_id) <= 10:
        numeric_id = int(movie_id)
        if numeric_id <= 2_147_483_647:
            content = db.query(Content).filter(Content.id == numeric_id).first()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CONTENT_NOT_FOUND",
                "message": f"Content with ID '{movie_id}' was not found in catalog",
            },
        )

    return content
