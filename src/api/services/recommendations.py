"""
Genre-based recommendation engine (FR-007, US-007).

Algorithm (content-based filtering, resolves OQ-001 for the first version):
1. Take the user's reviews with a high rating (>= LIKED_RATING_THRESHOLD).
2. Build genre weights: every liked title adds (rating - LIKED_RATING_THRESHOLD + 1) to each of its genres,
   so a 10/10 counts four times more than a 7/10. A newly liked genre is taken into account immediately.
3. Score every title the user has not reviewed yet as the sum of weights of its genres.
4. Return titles with a positive score first (score desc, catalog rating desc, id asc), then fill the
   remaining slots with the best-rated unseen titles so the block is never empty.
Users without liked titles (cold start) get the best-rated unseen titles (personalized=False).
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List
from uuid import UUID

from sqlalchemy.orm import Session

from src.api.db.models import Content, Review

LIKED_RATING_THRESHOLD = 7
FAVORITE_GENRES_COUNT = 3


@dataclass
class RecommendationResult:
    items: List[Content]
    personalized: bool
    favorite_genres: List[str] = field(default_factory=list)


def content_genres(content: Content) -> List[str]:
    """All genres of a title: the `genres` list plus the primary `genre`, without duplicates."""
    raw = list(content.genres or [])
    if content.genre:
        raw.append(content.genre)

    result: List[str] = []
    seen = set()
    for genre in raw:
        if not isinstance(genre, str) or not genre.strip():
            continue
        key = genre.strip().lower()
        if key not in seen:
            seen.add(key)
            result.append(genre.strip())
    return result


def build_genre_weights(liked: Iterable[tuple]) -> Dict[str, float]:
    """liked: iterable of (Content, rating). Returns {lowercased genre: weight}."""
    weights: Dict[str, float] = defaultdict(float)
    for content, rating in liked:
        weight = rating - LIKED_RATING_THRESHOLD + 1
        if weight <= 0:
            continue
        for genre in content_genres(content):
            weights[genre.lower()] += weight
    return dict(weights)


def score_content(content: Content, weights: Dict[str, float]) -> float:
    return sum(weights.get(genre.lower(), 0.0) for genre in content_genres(content))


def _catalog_order_key(content: Content):
    return (-(content.rating or 0.0), content.id)


def recommend_for_user(db: Session, user_id: UUID, limit: int = 10) -> RecommendationResult:
    reviewed = (
        db.query(Content, Review.rating)
        .join(Review, Review.content_id == Content.content_id)
        .filter(Review.user_id == user_id)
        .all()
    )
    reviewed_ids = {content.content_id for content, _ in reviewed}
    liked = [(content, rating) for content, rating in reviewed if rating >= LIKED_RATING_THRESHOLD]

    candidates = [content for content in db.query(Content).all() if content.content_id not in reviewed_ids]
    weights = build_genre_weights(liked)

    if not weights:
        return RecommendationResult(items=sorted(candidates, key=_catalog_order_key)[:limit], personalized=False)

    scores = {content.content_id: score_content(content, weights) for content in candidates}
    matched = sorted(
        (content for content in candidates if scores[content.content_id] > 0),
        key=lambda content: (-scores[content.content_id], *_catalog_order_key(content)),
    )
    matched_ids = {content.content_id for content in matched}
    fillers = sorted((c for c in candidates if c.content_id not in matched_ids), key=_catalog_order_key)

    return RecommendationResult(
        items=(matched + fillers)[:limit],
        personalized=True,
        favorite_genres=_favorite_genres(liked, weights),
    )


def _favorite_genres(liked: List[tuple], weights: Dict[str, float]) -> List[str]:
    """Top genres by weight, keeping the original spelling from the catalog."""
    labels: Dict[str, str] = {}
    for content, _ in liked:
        for genre in content_genres(content):
            labels.setdefault(genre.lower(), genre)
    top = sorted(weights.items(), key=lambda item: (-item[1], item[0]))[:FAVORITE_GENRES_COUNT]
    return [labels[key] for key, _ in top]
