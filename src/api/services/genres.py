"""
Genres of the catalog (FR-012, issue #61): the Genre dictionary and the ContentGenre links.

ContentGenre is the source of truth for genre filters and GET /api/v1/genres. The `genre` (primary genre)
and `genres` (ordered list) columns of Content are kept as a denormalised copy for API responses and
recommendations; set_content_genres() always updates both together.
"""

import logging
from typing import Iterable, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.db.models import Content, ContentGenre, Genre

logger = logging.getLogger(__name__)

DEFAULT_GENRE = "Драма"

# TMDB movie genres (GET /3/genre/movie/list) with the names used in the catalog
TMDB_MOVIE_GENRES = {
    28: ("Бойовик", "Action"),
    12: ("Пригоди", "Adventure"),
    16: ("Мультфільм", "Animation"),
    35: ("Комедія", "Comedy"),
    80: ("Кримінал", "Crime"),
    99: ("Документальний", "Documentary"),
    18: ("Драма", "Drama"),
    10751: ("Сімейний", "Family"),
    14: ("Фентезі", "Fantasy"),
    36: ("Історія", "History"),
    27: ("Жахи", "Horror"),
    10402: ("Музика", "Music"),
    9648: ("Детектив", "Mystery"),
    10749: ("Мелодрама", "Romance"),
    878: ("Фантастика", "Sci-Fi"),
    10770: ("Телефільм", "TV Movie"),
    53: ("Трилер", "Thriller"),
    10752: ("Воєнний", "War"),
    37: ("Вестерн", "Western"),
}

# Genres of the built-in catalog that TMDB does not have as a separate genre
EXTRA_GENRES = [("Біографія", "Biography")]


def clean_genre_names(names: Iterable[Optional[str]]) -> List[str]:
    """Trimmed names in their original order, without empty values and case-insensitive duplicates."""
    result: List[str] = []
    seen = set()
    for name in names:
        if not isinstance(name, str) or not name.strip():
            continue
        key = name.strip().casefold()
        if key not in seen:
            seen.add(key)
            result.append(name.strip())
    return result


def genres_from_tmdb(genre_ids: Iterable[int]) -> List[str]:
    """Catalog genre names for TMDB `genre_ids` (unknown ids are skipped)."""
    return [TMDB_MOVIE_GENRES[genre_id][0] for genre_id in genre_ids or [] if genre_id in TMDB_MOVIE_GENRES]


def ensure_genre_dictionary(db: Session) -> None:
    """Create the known genres once (idempotent)."""
    known = {name for (name,) in db.query(Genre.name)}
    for tmdb_id, (name, name_en) in TMDB_MOVIE_GENRES.items():
        if name not in known:
            db.add(Genre(name=name, name_en=name_en, tmdb_id=tmdb_id))
    for name, name_en in EXTRA_GENRES:
        if name not in known:
            db.add(Genre(name=name, name_en=name_en))
    db.flush()


def get_or_create_genre(db: Session, name: str) -> Genre:
    genre = db.query(Genre).filter(Genre.name == name).first()
    if genre is None:
        genre = Genre(name=name)
        db.add(genre)
        db.flush()
    return genre


def set_content_genres(db: Session, content: Content, names: Iterable[Optional[str]]) -> List[str]:
    """
    Replace the genres of a title: ContentGenre links in the given order plus the `genre`/`genres` columns.
    Without any name the title keeps its primary genre (or gets the default one).
    """
    cleaned = clean_genre_names(names) or clean_genre_names([content.genre]) or [DEFAULT_GENRE]
    if content.content_id is None:
        raise ValueError("content_id is required to link genres")

    db.query(ContentGenre).filter(ContentGenre.content_id == content.content_id).delete(synchronize_session=False)
    for position, name in enumerate(cleaned):
        genre = get_or_create_genre(db, name)
        db.add(ContentGenre(content_id=content.content_id, genre_id=genre.genre_id, position=position))
    content.genre = cleaned[0]
    content.genres = cleaned
    db.flush()
    return cleaned


def sync_genre_links(db: Session) -> int:
    """
    Startup backfill: link every title that has no ContentGenre rows yet, using its `genres`/`genre`
    columns (titles added before the genre tables existed). Returns the number of linked titles.
    """
    ensure_genre_dictionary(db)
    linked_ids = {content_id for (content_id,) in db.query(ContentGenre.content_id).distinct()}
    count = 0
    for content in db.query(Content).filter(Content.content_id.isnot(None)).order_by(Content.id):
        if content.content_id in linked_ids:
            continue
        set_content_genres(db, content, [content.genre, *(content.genres or [])])
        count += 1
    db.commit()
    if count:
        logger.info("Linked genres for %s titles.", count)
    return count


def link_catalog_genres(db: Session) -> int:
    """sync_genre_links() for the application startup: a failure is logged and never blocks the API."""
    try:
        return sync_genre_links(db)
    except SQLAlchemyError as error:
        db.rollback()
        logger.warning("Genre links were not synced (%s).", error.__class__.__name__)
        return 0
