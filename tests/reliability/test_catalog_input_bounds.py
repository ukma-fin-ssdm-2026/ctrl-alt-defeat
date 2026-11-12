"""
Reliability, findings 5 and 9 (input validation and boundary checks):
- Finding 5: Catalog search string length constraint and release year boundaries.
- Finding 9: Numeric movie ID out-of-range integer bounds handling.

Reaction: fast failure with 422 for malformed/out-of-bounds query parameters, and 404 (not 500)
for out-of-range integer IDs.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Content
from src.api.main import app
from src.api.routers import movies as movies_router

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
URL = "/api/v1/movies"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    db.query(Content).delete()
    db.add(
        Content(
            id=1,
            title="Dune",
            title_en="Dune",
            category="Movie",
            genre="Фантастика",
            year=2024,
            rating=8.5,
        )
    )
    db.commit()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[movies_router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_search_query_longer_than_100_chars_returns_422(client):
    """
    Finding 5: search query cannot exceed 100 chars, preventing CPU-exhausting ILIKE scans.
    """
    oversized = "a" * 101
    response = client.get(URL, params={"search": oversized})

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert any(d["field"] == "search" for d in data["error"]["details"])


def test_year_exceeding_max_bound_returns_422_not_500(client):
    """
    Finding 5: year=99999999999999999999 fails fast with 422 instead of crashing with 500 DB integer overflow.
    """
    response = client.get(URL, params={"year": 99999999999999999999})

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert any(d["field"] == "year" for d in data["error"]["details"])


def test_year_below_min_bound_returns_422(client):
    """
    Finding 5: year before 1888 (the first film in history) fails fast with 422.
    """
    response = client.get(URL, params={"year": 1800})

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_numeric_movie_id_exceeding_32bit_integer_returns_404_not_500(client):
    """
    Finding 9: huge numeric ID (e.g. 99999999999999999999999) returns 404 instead of causing driver overflow error (500).
    """
    huge_id = "99999999999999999999999"
    response = client.get(f"{URL}/{huge_id}")

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "CONTENT_NOT_FOUND"


def test_numeric_movie_id_above_max_signed_int_returns_404(client):
    """
    Finding 9: numeric ID 2147483648 (2^31) returns 404 instead of integer overflow.
    """
    above_max = "2147483648"
    response = client.get(f"{URL}/{above_max}")

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "CONTENT_NOT_FOUND"


def test_valid_numeric_id_and_bounds_work_normally(client):
    """
    Valid queries within boundaries continue to work as expected.
    """
    response = client.get(URL, params={"search": "Dune", "year": 2024})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    single = client.get(f"{URL}/1")
    assert single.status_code == 200
    assert single.json()["title"] == "Dune"
