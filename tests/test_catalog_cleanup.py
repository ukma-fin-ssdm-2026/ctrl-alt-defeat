"""Built-in placeholder titles after a TMDB update (FR-012, US-012): adopted, merged with user data or removed."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import (
    Comment,
    Content,
    ContentGenre,
    Genre,
    Rating,
    Review,
    ReviewVote,
    User,
    WatchedItem,
    WatchlistItem,
)
from src.api.services import catalog_sync
from src.api.services.catalog_cleanup import release_placeholder_ids, retire_placeholders
from src.api.services.tmdb import FALLBACK_MOVIES, seed_movies_to_database, sync_catalog

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

DUNE = next(item for item in FALLBACK_MOVIES if item["title"] == "Дюна: Частина друга")
SHREK = next(item for item in FALLBACK_MOVIES if item["title"] == "Шрек")


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    engine_test.dispose()


@pytest.fixture
def db():
    session = TestingSessionLocal()
    for model in (ReviewVote, Comment, Review, Rating, WatchedItem, WatchlistItem, ContentGenre, Genre, Content, User):
        session.query(model).delete()
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def user(db, name):
    item = User(user_id=uuid.uuid4(), email=f"{name}@example.com", password_hash="x", nickname=name, role="user")
    db.add(item)
    db.commit()
    return item


def by_title(db, title):
    return db.query(Content).filter(Content.title == title).all()


def real(item, tmdb_id, **changes):
    """The same title as TMDB returns it."""
    return {**item, "id": None, "tmdb_id": tmdb_id, "img": f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg", **changes}


def test_built_in_titles_have_no_made_up_tmdb_ids():
    # Trace: T-044
    assert all(item.get("tmdb_id") is None for item in FALLBACK_MOVIES)


def test_import_adopts_a_built_in_title_and_keeps_its_reviews(db):
    # Trace: T-044
    seed_movies_to_database(db, FALLBACK_MOVIES)
    dune = by_title(db, DUNE["title"])[0]
    fan = user(db, "fan")
    db.add(Review(user_id=fan.user_id, content_id=dune.content_id, rating=9))
    db.commit()

    sync_catalog(db, [real(DUNE, 693134)])
    result = retire_placeholders(db)

    [adopted] = by_title(db, DUNE["title"])
    assert (adopted.content_id, adopted.tmdb_id) == (dune.content_id, 693134)
    assert db.query(Review).filter(Review.content_id == adopted.content_id).count() == 1
    # Every other built-in title was not used by anybody and is gone
    assert result.removed == len(FALLBACK_MOVIES) - 1
    assert db.query(Content).count() == 1


def test_made_up_ids_of_an_older_database_are_released_and_duplicates_merged(db):
    # Trace: T-044
    """An older database: placeholders with ids 100001+ and the real titles imported next to them."""
    seed_movies_to_database(db, [DUNE, SHREK])
    placeholder_dune, placeholder_shrek = by_title(db, DUNE["title"])[0], by_title(db, SHREK["title"])[0]
    placeholder_dune.tmdb_id, placeholder_shrek.tmdb_id = 100001, 100021
    db.commit()
    sync_catalog(db, [real(DUNE, 693134, title="Дюна. Частина друга"), real(SHREK, 808)])
    real_dune = db.query(Content).filter(Content.tmdb_id == 693134).one()

    fan, critic = user(db, "fan"), user(db, "critic")
    old_review = Review(
        user_id=fan.user_id, content_id=placeholder_dune.content_id, rating=8, review_text="Стара рецензія"
    )
    duplicate = Review(user_id=critic.user_id, content_id=placeholder_dune.content_id, rating=5)
    kept = Review(user_id=critic.user_id, content_id=real_dune.content_id, rating=7)
    db.add_all([old_review, duplicate, kept])
    db.add(WatchlistItem(user_id=fan.user_id, content_id=placeholder_dune.content_id, added_at=datetime.now(UTC)))
    db.add(WatchedItem(user_id=fan.user_id, content_id=placeholder_dune.content_id))
    db.commit()
    db.add(Comment(review_id=duplicate.review_id, user_id=fan.user_id, author_name="fan", text="Згоден", depth=0))
    db.commit()

    # Both placeholders kept their made-up ids during the old import, so both were duplicated
    assert release_placeholder_ids(db) == 2
    result = retire_placeholders(db)

    assert result.merged == 2
    assert by_title(db, DUNE["title"]) == []
    assert [row.tmdb_id for row in by_title(db, SHREK["title"])] == [808]
    moved = db.query(Review).filter(Review.content_id == real_dune.content_id).all()
    # The fan's review moved; the critic already had a review of the real title, so the duplicate is gone
    assert sorted(review.rating for review in moved) == [7, 8]
    assert db.query(Comment).count() == 0
    assert db.query(WatchedItem).filter(WatchedItem.content_id == real_dune.content_id).count() == 1
    assert db.query(WatchlistItem).filter(WatchlistItem.content_id == real_dune.content_id).count() == 1


def test_used_placeholder_without_a_real_twin_is_kept(db):
    # Trace: T-044
    seed_movies_to_database(db, [SHREK])
    shrek = by_title(db, SHREK["title"])[0]
    fan = user(db, "fan")
    db.add(Rating(user_id=fan.user_id, content_id=shrek.content_id, score=10))
    db.commit()

    result = retire_placeholders(db)

    assert (result.merged, result.removed, result.kept) == (0, 0, 1)
    assert by_title(db, SHREK["title"])


def test_admin_update_reports_removed_placeholders(db, monkeypatch):
    # Trace: T-044
    seed_movies_to_database(db, FALLBACK_MOVIES)
    monkeypatch.setattr(catalog_sync, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(catalog_sync, "fetch_tmdb_catalog", lambda key: [real(DUNE, 693134)])
    catalog_sync.try_start()

    catalog_sync.run_sync("key")

    status = catalog_sync.get_status()
    assert (status["state"], status["updated"], status["placeholders_removed"]) == ("done", 1, len(FALLBACK_MOVIES) - 1)
    db.expire_all()
    assert db.query(Content).count() == 1
