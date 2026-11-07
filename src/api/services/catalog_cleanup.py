"""
Removal of the built-in placeholder titles after a TMDB update (FR-012).

The built-in catalog (FALLBACK_MOVIES) only fills an empty database while TMDB is not available.
Older databases store these titles with made-up TMDB ids (100001-100030), which TMDB did not
recognise, so an import added the real titles next to them (duplicates). A made-up id could also
belong to a real TMDB title and make the import overwrite a placeholder with another film.

- release_placeholder_ids() runs before an import: placeholders lose the made-up ids, so the import
  adopts them by title and year (the row keeps its content_id, and with it reviews and user lists).
- retire_placeholders() runs after an import: a placeholder that still exists next to its real
  title is merged into it (reviews, ratings, watchlist and watched move over) and removed; one
  without a real twin is removed when nobody used it and kept otherwise.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.api.db.models import (
    Comment,
    Content,
    ContentGenre,
    Rating,
    Review,
    ReviewVote,
    WatchedItem,
    WatchlistItem,
)
from src.api.services.tmdb import FALLBACK_MOVIES

logger = logging.getLogger(__name__)

# Made-up TMDB ids that older versions stored for the built-in titles
PLACEHOLDER_TMDB_IDS = set(range(100001, 100031))
PLACEHOLDER_TITLES = {(item["title"], item["year"]) for item in FALLBACK_MOVIES}


@dataclass
class CleanupResult:
    merged: int = 0
    removed: int = 0
    kept: int = 0


def _placeholders(db: Session):
    """Built-in titles that TMDB has not adopted (no real tmdb_id)."""
    rows = db.query(Content).filter(or_(Content.tmdb_id.is_(None), Content.tmdb_id.in_(PLACEHOLDER_TMDB_IDS)))
    return [row for row in rows if (row.title, row.year) in PLACEHOLDER_TITLES]


def release_placeholder_ids(db: Session) -> int:
    """Clear the made-up TMDB ids of placeholders before an import."""
    released = 0
    for row in _placeholders(db):
        if row.tmdb_id is not None:
            row.tmdb_id = None
            released += 1
    db.commit()
    return released


def _real_twin(db: Session, placeholder: Content) -> Optional[Content]:
    """The imported title with the same name (Ukrainian or English) and release year."""
    names = [Content.title == placeholder.title]
    if placeholder.title_en:
        names.append(Content.title_en == placeholder.title_en)
    return (
        db.query(Content)
        .filter(
            Content.content_id != placeholder.content_id,
            Content.tmdb_id.isnot(None),
            Content.tmdb_id.notin_(PLACEHOLDER_TMDB_IDS),
            Content.year.between(placeholder.year - 1, placeholder.year + 1),
            or_(*names),
        )
        .order_by(Content.id)
        .first()
    )


def _has_activity(db: Session, content_id) -> bool:
    return any(
        db.query(model).filter(model.content_id == content_id).first() is not None
        for model in (Review, Rating, WatchlistItem, WatchedItem)
    )


def _delete_reviews(db: Session, review_ids) -> None:
    if not review_ids:
        return
    db.query(ReviewVote).filter(ReviewVote.review_id.in_(review_ids)).delete(synchronize_session=False)
    db.query(Comment).filter(Comment.review_id.in_(review_ids)).delete(synchronize_session=False)
    db.query(Review).filter(Review.review_id.in_(review_ids)).delete(synchronize_session=False)


def _move_user_data(db: Session, source, target) -> None:
    """Move reviews, ratings and list entries; where the user already has one for the target, keep that."""
    for model in (Review, Rating, WatchlistItem, WatchedItem):
        target_users = {user_id for (user_id,) in db.query(model.user_id).filter(model.content_id == target)}
        rows = db.query(model).filter(model.content_id == source).all()
        duplicates = [row for row in rows if row.user_id in target_users]
        if model is Review:
            _delete_reviews(db, [row.review_id for row in duplicates])
        else:
            for row in duplicates:
                db.delete(row)
        db.flush()
        db.query(model).filter(model.content_id == source).update({model.content_id: target}, synchronize_session=False)


def _delete_title(db: Session, content: Content) -> None:
    content_id = content.content_id
    _delete_reviews(
        db, [review_id for (review_id,) in db.query(Review.review_id).filter(Review.content_id == content_id)]
    )
    for model in (Rating, WatchlistItem, WatchedItem, ContentGenre):
        db.query(model).filter(model.content_id == content_id).delete(synchronize_session=False)
    db.delete(content)


def retire_placeholders(db: Session) -> CleanupResult:
    """Merge or remove the built-in titles once the real catalog is imported."""
    result = CleanupResult()
    for placeholder in _placeholders(db):
        twin = _real_twin(db, placeholder)
        if twin is not None:
            _move_user_data(db, placeholder.content_id, twin.content_id)
            _delete_title(db, placeholder)
            result.merged += 1
        elif not _has_activity(db, placeholder.content_id):
            _delete_title(db, placeholder)
            result.removed += 1
        else:
            result.kept += 1
        db.flush()
    db.commit()
    if result.merged or result.removed or result.kept:
        logger.info("Placeholder titles: %s", result)
    return result
