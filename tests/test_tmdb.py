import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.db.database import Base
from src.api.db.models import Content
from src.api.services.tmdb import (
    FALLBACK_MOVIES,
    fetch_tmdb_movies,
    seed_movies_to_database,
)

engine_test = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


def test_fetch_tmdb_movies_fallback_without_key():
    # Trace: T-034, FR-012
    movies = fetch_tmdb_movies(api_key=None)
    assert len(movies) >= 8
    assert movies[0]["title"] == "Дюна: Частина друга"


def test_fetch_tmdb_movies_graceful_degradation_on_error():
    # Trace: T-034, FR-012, REL-001
    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        movies = fetch_tmdb_movies(api_key="fake-test-key")
        assert movies == FALLBACK_MOVIES


def test_fetch_tmdb_movies_success():
    # Trace: T-033, FR-012
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.read.return_value = (
        b'{"results": [{"id": 101, "title": "Test Movie", "original_title": "Test Orig", '
        b'"vote_average": 7.5, "release_date": "2024-05-01"}]}'
    )
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response):
        movies = fetch_tmdb_movies(api_key="valid-key")
        assert len(movies) == 1
        assert movies[0]["title"] == "Test Movie"
        assert movies[0]["rating"] == 7.5


def test_seed_movies_to_database():
    db = TestingSessionLocal()
    try:
        count = seed_movies_to_database(db, FALLBACK_MOVIES)
        assert count == len(FALLBACK_MOVIES)
        assert db.query(Content).count() == len(FALLBACK_MOVIES)

        # Seeding second time should not duplicate records
        second_count = seed_movies_to_database(db, FALLBACK_MOVIES)
        assert second_count == 0
        assert db.query(Content).count() == len(FALLBACK_MOVIES)
    finally:
        db.close()

