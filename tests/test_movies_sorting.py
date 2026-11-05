"""Catalog sorting tests (FR-010, US-009)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Content, ContentGenre
from src.api.main import app
from src.api.routers.movies import get_db
from src.api.services.genres import sync_genre_links
from src.api.services.tmdb import FALLBACK_MOVIES, seed_movies_to_database

engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# (id, title, category, genre, year, rating, runtime)
SAMPLE = [
    (1, "Drama Old", "Movie", "Драма", 1994, 9.3, 142),
    (2, "SciFi New", "Movie", "Фантастика", 2024, 8.8, 166),
    (3, "Drama New", "Movie", "Драма", 2019, 8.5, 132),
    (4, "Unknown Runtime", "Movie", "Драма", 2026, 7.0, None),
    (5, "SciFi Mid", "Series", "Фантастика", 2016, 8.8, 51),
]


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def seed_sample(db_session):
    db_session.query(ContentGenre).delete()
    db_session.query(Content).delete()
    for item_id, title, category, genre, year, rating, runtime in SAMPLE:
        db_session.add(
            Content(
                id=item_id,
                content_id=uuid.uuid4(),
                title=title,
                category=category,
                genre=genre,
                year=year,
                rating=rating,
                runtime=runtime,
            )
        )
    db_session.commit()
    sync_genre_links(db_session)


def ids(response):
    assert response.status_code == 200
    return [item["id"] for item in response.json()["items"]]


def test_sort_by_rating_desc_highest_first(client):
    # Trace: T-026
    # 8.8 tie (ids 2 and 5) is resolved by id for a stable order
    assert ids(client.get("/api/v1/movies?sort_by=rating")) == [1, 2, 5, 3, 4]


def test_sort_by_rating_asc(client):
    # Trace: T-026
    assert ids(client.get("/api/v1/movies?sort_by=rating&order=asc")) == [4, 3, 2, 5, 1]


def test_sort_by_release_date_newest_first(client):
    # Trace: T-027
    assert ids(client.get("/api/v1/movies?sort_by=release_date")) == [4, 2, 3, 5, 1]


def test_sort_by_release_date_oldest_first(client):
    # Trace: T-027
    assert ids(client.get("/api/v1/movies?sort_by=release_date&order=asc")) == [1, 5, 3, 2, 4]


@pytest.mark.parametrize(
    "order, expected",
    [
        ("desc", [2, 1, 3, 5, 4]),
        ("asc", [5, 3, 1, 2, 4]),
    ],
)
def test_sort_by_runtime_unknown_values_last(client, order, expected):
    # Trace: T-026
    """Runtime sorting: items without runtime go last in both directions."""
    assert ids(client.get(f"/api/v1/movies?sort_by=runtime&order={order}")) == expected


def test_sort_applies_only_to_filtered_results(client):
    # Trace: T-028
    response = client.get("/api/v1/movies?genre=Драма&sort_by=rating")
    assert ids(response) == [1, 3, 4]
    assert response.json()["total"] == 3


def test_sort_combined_with_search_results(client):
    # Trace: T-028
    assert ids(client.get("/api/v1/movies?search=scifi&sort_by=release_date&order=asc")) == [5, 2]


def test_sort_is_applied_before_pagination(client):
    # Trace: T-026
    first = ids(client.get("/api/v1/movies?sort_by=rating&skip=0&limit=2"))
    second = ids(client.get("/api/v1/movies?sort_by=rating&skip=2&limit=2"))
    assert first == [1, 2]
    assert second == [5, 3]


def test_default_order_without_sort_is_by_id(client):
    # Trace: T-026
    assert ids(client.get("/api/v1/movies")) == [1, 2, 3, 4, 5]


@pytest.mark.parametrize("query", ["sort_by=popularity", "sort_by=rating&order=up"])
def test_invalid_sort_params_return_422(client, query):
    # Trace: T-026
    response = client.get(f"/api/v1/movies?{query}")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_response_contains_runtime(client):
    # Trace: T-026
    item = client.get("/api/v1/movies/2").json()
    assert item["runtime"] == 166


def test_fallback_catalog_has_runtime_for_every_title():
    # Trace: T-026
    assert all("runtime" in movie for movie in FALLBACK_MOVIES)
    known = [m for m in FALLBACK_MOVIES if m["runtime"] is not None]
    assert all(isinstance(m["runtime"], int) and m["runtime"] > 0 for m in known)


def test_seed_backfills_runtime_for_existing_titles(db_session):
    # Trace: T-026
    """Re-running the seed fills runtime for titles that were seeded before the column existed."""
    db_session.query(Content).delete()
    source = FALLBACK_MOVIES[0]
    db_session.add(
        Content(
            id=source["id"],
            content_id=uuid.uuid4(),
            title=source["title"],
            category=source["category"],
            genre=source["genre"],
            year=source["year"],
            rating=source["rating"],
            runtime=None,
        )
    )
    db_session.commit()

    seed_movies_to_database(db_session, [source])

    assert db_session.query(Content).filter(Content.id == source["id"]).one().runtime == source["runtime"]
