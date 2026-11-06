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

# Isolated in-memory SQLite database with StaticPool for test suite
engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


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
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def seed_test_movies(db_session):
    db_session.query(ContentGenre).delete()
    db_session.query(Content).delete()
    m1 = Content(
        id=1,
        content_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        title="Дюна: Частина друга",
        title_en="Dune: Part Two",
        category="Movie",
        genre="Фантастика",
        genres=["Фантастика", "Бойовик"],
        year=2024,
        rating=8.8,
        rotten_rating="93%",
        img="https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2TGpiom05.jpg",
        description="Пол Атрід об'єднується з фременами.",
    )
    m2 = Content(
        id=2,
        content_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        title="Дивні дива",
        title_en="Stranger Things",
        category="Series",
        genre="Фантастика",
        genres=["Фантастика", "Містика"],
        year=2016,
        rating=8.7,
        rotten_rating="92%",
        img="https://image.tmdb.org/t/p/w500/49WJfeN0moxb9IPfGn8AIqMGskD.jpg",
        description="У містечку зникає хлопчик.",
    )
    m3 = Content(
        id=3,
        content_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        title="Оппенгеймер",
        title_en="Oppenheimer",
        category="Movie",
        genre="Драма",
        genres=["Драма", "Біографія"],
        year=2023,
        rating=8.4,
        rotten_rating="93%",
        img="https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg",
        description="Історія створення атомної бомби.",
    )
    db_session.add_all([m1, m2, m3])
    db_session.commit()
    # The application links genres on startup (issue #61); the test titles are added directly
    sync_genre_links(db_session)


def test_get_movies_list(client):
    # Trace: T-009, FR-002
    response = client.get("/api/v1/movies")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["has_more"] is False


def test_get_movies_pagination(client):
    response = client.get("/api/v1/movies?skip=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["has_more"] is True


def test_get_movies_search_ukrainian(client):
    # Trace: T-009, FR-002
    response = client.get("/api/v1/movies?search=Дюна")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Дюна: Частина друга"


def test_get_movies_search_english(client):
    # Trace: T-009, FR-002
    response = client.get("/api/v1/movies?search=Oppenheimer")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Оппенгеймер"


def test_get_movies_search_not_found(client):
    # Trace: T-010, FR-002
    response = client.get("/api/v1/movies?search=НеіснуючийФільм")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_get_movies_filter_category(client):
    # Trace: T-014, FR-002
    response = client.get("/api/v1/movies?category=Series")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Дивні дива"


def test_get_movies_filter_genre(client):
    # Trace: T-014, FR-002
    response = client.get("/api/v1/movies?genre=Драма")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Оппенгеймер"


def test_get_movies_filter_year(client):
    # Trace: T-014, FR-002
    response = client.get("/api/v1/movies?year=2024")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["year"] == 2024


def test_get_movie_by_numeric_id(client):
    response = client.get("/api/v1/movies/1")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Дюна: Частина друга"
    assert data["id"] == 1


def test_get_movie_by_uuid(client):
    response = client.get("/api/v1/movies/22222222-2222-2222-2222-222222222222")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Дивні дива"
    assert data["category"] == "Series"


def test_get_movie_by_id_not_found(client):
    # Trace: T-010
    response = client.get("/api/v1/movies/99999")
    assert response.status_code == 404
    error_data = response.json()
    assert error_data["error"]["code"] == "CONTENT_NOT_FOUND"


def test_get_movies_multi_filter(client):
    # Trace: T-014, FR-002
    response = client.get("/api/v1/movies?category=Movie&genre=Фантастика&year=2024")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Дюна: Частина друга"


def test_get_movie_by_invalid_string_id(client):
    # Trace: T-010
    response = client.get("/api/v1/movies/invalid-not-uuid-or-int")
    assert response.status_code == 404
    error_data = response.json()
    assert error_data["error"]["code"] == "CONTENT_NOT_FOUND"


def test_movies_get_db_generator():
    from src.api.routers.movies import get_db

    gen = get_db()
    session = next(gen)
    assert session is not None
    try:
        next(gen)
    except StopIteration:
        pass
