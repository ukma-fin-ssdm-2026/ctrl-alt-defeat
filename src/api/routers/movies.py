import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, defer, undefer_group
from sqlalchemy import func, or_, select

from src.api.db.database import SessionLocal
from src.api.db.models import TMDB_DETAILS, Content, ContentGenre, Genre
from src.api.schemas.movie import (
    CollectionInfo,
    ContentDetailsResponse,
    ContentResponse,
    ContentSortField,
    PaginatedContentResponse,
    RelatedContentResponse,
    SortOrder,
)
from src.api.services.tmdb import tmdb_kind

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


def find_content(db: Session, movie_id: str, with_details: bool = False) -> Content:
    """A title by its UUID `content_id` or numeric id; 404 CONTENT_NOT_FOUND otherwise."""
    query = db.query(Content)
    if with_details:
        # The deferred TMDB details of the page (trailers, cast, seasons…) in the same query
        query = query.options(undefer_group(TMDB_DETAILS))
    content = None
    # Check if movie_id is a valid UUID
    try:
        content_uuid = uuid.UUID(movie_id)
        content = query.filter(Content.content_id == content_uuid).first()
    except (ValueError, AttributeError):
        pass

    # If not UUID or not found by UUID, try integer ID within valid 32-bit range (finding 9)
    if not content and movie_id.isdigit() and len(movie_id) <= 10:
        numeric_id = int(movie_id)
        if numeric_id <= 2_147_483_647:
            content = query.filter(Content.id == numeric_id).first()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CONTENT_NOT_FOUND",
                "message": f"Content with ID '{movie_id}' was not found in catalog",
            },
        )
    return content


def collection_of(content: Content) -> Optional[CollectionInfo]:
    if content.collection_id is None or not content.collection_name:
        return None
    return CollectionInfo(id=content.collection_id, name=content.collection_name, name_en=content.collection_name_en)


@router.get(
    "/{movie_id}",
    response_model=ContentDetailsResponse,
    summary="Get movie details by ID or content UUID",
    description=(
        "Retrieve a single movie or series by its numeric ID or UUID content_id, with the details of its page "
        "from TMDB (US-013): Ukrainian and English trailers, cast, directors and writers or creators, "
        "seasons and episodes of a series, and the film series it belongs to."
    ),
)
def get_movie_by_id(
    movie_id: str,
    db: Session = Depends(get_db),
):
    content = find_content(db, movie_id, with_details=True)
    return ContentDetailsResponse(
        **ContentResponse.model_validate(content).model_dump(),
        trailer_uk=content.trailer_uk,
        trailer_en=content.trailer_en,
        cast=content.cast_members or [],
        crew=content.crew_members or {},
        series=content.series_details,
        collection=collection_of(content),
    )


@router.get(
    "/{movie_id}/related",
    response_model=RelatedContentResponse,
    summary="Other parts of the film series and similar titles",
    description=(
        "Titles of the catalog related to one title (US-013): the other parts of its film series by year, "
        "and the TMDB recommendations for it that are present in the catalog, in TMDB order (up to `limit`)."
    ),
)
def get_related(
    movie_id: str,
    limit: int = Query(12, ge=1, le=20, description="Maximum number of similar titles"),
    db: Session = Depends(get_db),
):
    content = find_content(db, movie_id, with_details=True)

    parts = []
    if content.collection_id is not None:
        parts = (
            db.query(Content)
            .filter(Content.collection_id == content.collection_id, Content.id != content.id)
            .order_by(Content.year.asc(), Content.id.asc())
            .all()
        )

    similar = []
    wanted = [tmdb_id for tmdb_id in content.similar_tmdb_ids or [] if isinstance(tmdb_id, int)]
    if wanted:
        # TMDB numbers movies and series separately: a recommendation is of the same media type
        kind = tmdb_kind(content.category)
        found = {
            row.tmdb_id: row
            for row in db.query(Content).filter(Content.tmdb_id.in_(wanted), Content.id != content.id)
            if tmdb_kind(row.category) == kind
        }
        similar = [found[tmdb_id] for tmdb_id in wanted if tmdb_id in found][:limit]

    return RelatedContentResponse(collection=collection_of(content), collection_items=parts, similar=similar)
