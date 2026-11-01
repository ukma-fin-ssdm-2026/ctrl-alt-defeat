"""API tests for GET /api/v1/recommendations (FR-007, US-007)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Content, Review
from src.api.main import app
from src.api.routers.recommendations import get_db

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

USER = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
URL = "/api/v1/recommendations"

CATALOG = [
    (1, "Dune", "Фантастика", 8.8),
    (2, "Interstellar", "Фантастика", 8.7),
    (3, "Alien", "Фантастика", 8.5),
    (4, "Shawshank", "Драма", 9.3),
    (5, "Forrest Gump", "Драма", 8.8),
    (6, "Shrek", "Комедія", 7.9),
    (7, "Coco", "Мультфільм", 8.4),
]


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    db.query(Review).delete()
    db.query(Content).delete()
    for item_id, title, genre, rating in CATALOG:
        db.add(
            Content(
                id=item_id,
                content_id=uuid.UUID(int=item_id),
                title=title,
                category="Movie",
                genre=genre,
                genres=[genre],
                year=2000 + item_id,
                rating=rating,
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

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def add_review(db, content_num, rating):
    db.add(
        Review(review_id=uuid.uuid4(), user_id=uuid.UUID(USER), content_id=uuid.UUID(int=content_num), rating=rating)
    )
    db.commit()


def test_get_recommendations_personalized(client, db_session):
    # Trace: T-020
    add_review(db_session, 1, 10)

    response = client.get(URL, params={"user_id": USER})

    assert response.status_code == 200
    body = response.json()
    assert body["personalized"] is True
    assert body["favorite_genres"] == ["Фантастика"]
    titles = [item["title"] for item in body["items"]]
    assert titles[:2] == ["Interstellar", "Alien"]
    assert "Dune" not in titles


def test_recommendations_block_has_at_least_five_items(client, db_session):
    # Trace: T-020
    add_review(db_session, 1, 9)

    items = client.get(URL, params={"user_id": USER}).json()["items"]

    assert len(items) >= 5


def test_recommendation_items_have_full_content_fields(client, db_session):
    # Trace: T-020
    item = client.get(URL, params={"user_id": USER, "limit": 1}).json()["items"][0]

    for field in ("id", "content_id", "title", "genre", "year", "rating", "img"):
        assert field in item


def test_new_user_gets_best_rated_titles(client):
    # Trace: T-020
    body = client.get(URL, params={"user_id": USER, "limit": 3}).json()

    assert body["personalized"] is False
    assert body["favorite_genres"] == []
    assert [item["title"] for item in body["items"]] == ["Shawshank", "Dune", "Forrest Gump"]


def test_recommendations_require_authentication(client):
    # Trace: T-021
    response = client.get(URL)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 51}, {"user_id": "not-a-uuid"}])
def test_recommendations_invalid_params_return_422(client, params):
    # Trace: T-020
    response = client.get(URL, params={"user_id": USER, **params})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_recommendations_get_db_generator():
    # Trace: T-020
    generator = get_db()
    session = next(generator)
    assert session is not None
    generator.close()
