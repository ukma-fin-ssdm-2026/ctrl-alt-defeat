"""Unit tests for the genre-based recommendation engine (FR-007, US-007)."""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Content, Review
from src.api.services.recommendations import (
    build_genre_weights,
    content_genres,
    recommend_for_user,
    score_content,
)

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OTHER_USER = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

# (id, title, genre, genres, rating)
CATALOG = [
    (1, "Dune", "Фантастика", ["Фантастика", "Пригоди"], 8.8),
    (2, "Interstellar", "Фантастика", ["Фантастика", "Драма"], 8.7),
    (3, "Blade Runner", "Фантастика", ["Фантастика", "Трилер"], 8.0),
    (4, "Shawshank", "Драма", ["Драма"], 9.3),
    (5, "Forrest Gump", "Драма", ["Драма", "Мелодрама"], 8.8),
    (6, "Shrek", "Комедія", ["Комедія", "Пригоди"], 7.9),
    (7, "Coco", "Мультфільм", ["Мультфільм", "Музика"], 8.4),
    (8, "Saw", "Жахи", ["Жахи"], 6.5),
    (9, "Alien", "Фантастика", ["Фантастика", "Жахи"], 8.5),
    (10, "Soul", "Мультфільм", ["Мультфільм", "Музика"], 8.1),
]


def make_content(item_id, title, genre, genres, rating):
    return Content(
        id=item_id,
        content_id=uuid.UUID(int=item_id),
        title=title,
        category="Movie",
        genre=genre,
        genres=genres,
        year=2000 + item_id,
        rating=rating,
    )


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    session.query(Review).delete()
    session.query(Content).delete()
    session.add_all([make_content(*item) for item in CATALOG])
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def review(db, content_num, rating, user_id=USER):
    db.add(
        Review(
            review_id=uuid.uuid4(),
            user_id=user_id,
            content_id=uuid.UUID(int=content_num),
            rating=rating,
        )
    )
    db.commit()


def titles(result):
    return [content.title for content in result.items]


# ---------- pure helpers ----------


def test_content_genres_merges_list_and_primary_without_duplicates():
    # Trace: T-020
    content = Content(genre="Драма", genres=["драма", " Мелодрама ", "", None])
    assert content_genres(content) == ["драма", "Мелодрама"]


def test_content_genres_handles_missing_list():
    # Trace: T-020
    assert content_genres(Content(genre="Жахи", genres=None)) == ["Жахи"]


def test_genre_weights_grow_with_rating_and_ignore_low_ratings():
    # Trace: T-020
    scifi = Content(genre="Фантастика", genres=[])
    drama = Content(genre="Драма", genres=[])
    weights = build_genre_weights([(scifi, 10), (drama, 7), (Content(genre="Жахи", genres=[]), 6)])
    assert weights == {"фантастика": 4, "драма": 1}


def test_score_content_sums_weights_of_all_genres():
    # Trace: T-020
    content = Content(genre="Фантастика", genres=["Фантастика", "Драма"])
    assert score_content(content, {"фантастика": 4, "драма": 1}) == 5


# ---------- recommend_for_user ----------


def test_recommends_titles_from_favorite_genre_first(db):
    # Trace: T-020
    review(db, 1, 10)  # loves sci-fi

    result = recommend_for_user(db, USER, limit=5)

    assert result.personalized is True
    assert "Фантастика" in result.favorite_genres
    # equal genre score -> higher catalog rating first
    assert titles(result)[:3] == ["Interstellar", "Alien", "Blade Runner"]


def test_returns_at_least_five_items_when_catalog_allows(db):
    # Trace: T-020
    review(db, 1, 9)

    result = recommend_for_user(db, USER, limit=10)

    assert len(result.items) >= 5


def test_excludes_already_reviewed_titles(db):
    # Trace: T-020
    review(db, 1, 10)
    review(db, 2, 3)  # reviewed but disliked -> still excluded

    result = recommend_for_user(db, USER, limit=20)

    assert "Dune" not in titles(result)
    assert "Interstellar" not in titles(result)
    assert len(result.items) == len(CATALOG) - 2


def test_new_highly_rated_genre_is_taken_into_account(db):
    # Trace: T-020
    """US-007: after a high rating for a new genre, that genre appears in recommendations."""
    review(db, 1, 8)
    before = recommend_for_user(db, USER, limit=3)
    assert "Soul" not in titles(before)

    review(db, 7, 10)  # first animation title (Coco), rated 10
    after = recommend_for_user(db, USER, limit=3)

    assert "Мультфільм" in after.favorite_genres
    assert titles(after)[0] == "Soul"


def test_cold_start_returns_best_rated_unseen_titles(db):
    # Trace: T-020
    review(db, 4, 5)  # only a low rating -> no preferences yet

    result = recommend_for_user(db, USER, limit=3)

    assert result.personalized is False
    assert result.favorite_genres == []
    assert titles(result) == ["Dune", "Forrest Gump", "Interstellar"]


def test_other_users_reviews_do_not_affect_recommendations(db):
    # Trace: T-020
    review(db, 8, 10, user_id=OTHER_USER)

    result = recommend_for_user(db, USER, limit=3)

    assert result.personalized is False
    assert "Saw" not in titles(result)


def test_fills_remaining_slots_with_best_rated_titles(db):
    # Trace: T-020
    review(db, 8, 10)  # likes horror: only Alien matches

    result = recommend_for_user(db, USER, limit=3)

    assert titles(result) == ["Alien", "Shawshank", "Dune"]


def test_respects_limit(db):
    # Trace: T-020
    review(db, 1, 10)
    assert len(recommend_for_user(db, USER, limit=2).items) == 2
