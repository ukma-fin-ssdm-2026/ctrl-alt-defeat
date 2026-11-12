"""Genres of the catalog (FR-012, US-012, issue #61): Genre / ContentGenre, TMDB genres, filter and dictionary."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Content, ContentGenre, Genre
from src.api.main import app
from src.api.routers import genres as genres_router
from src.api.routers import movies as movies_router
from src.api.services.genres import (
    TMDB_MOVIE_GENRES,
    clean_genre_names,
    genres_from_tmdb,
    link_catalog_genres,
    set_content_genres,
    sync_genre_links,
)
from src.api.services.tmdb import fetch_tmdb_movies, seed_movies_to_database

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    engine_test.dispose()


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    for model in (ContentGenre, Genre, Content):
        db.query(model).delete()
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

    for router in (genres_router, movies_router):
        app.dependency_overrides[router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def add_title(db, item_id, title, genre, genres=None, category="Movie"):
    content = Content(
        id=item_id,
        content_id=uuid.uuid4(),
        title=title,
        category=category,
        genre=genre,
        genres=genres,
        year=2024,
        rating=8.0,
    )
    db.add(content)
    db.commit()
    return content


def linked_names(db, content):
    rows = (
        db.query(Genre.name)
        .join(ContentGenre, ContentGenre.genre_id == Genre.genre_id)
        .filter(ContentGenre.content_id == content.content_id)
        .order_by(ContentGenre.position)
    )
    return [name for (name,) in rows]


def test_tmdb_genre_ids_become_real_genres():
    # Trace: T-039
    results = [
        {
            "id": 1,
            "title": "Фільм",
            "release_date": "2024-01-01",
            "poster_path": "/a.jpg",
            "genre_ids": [878, 53, 99999],
            "overview": "Опис",
        },
        {
            "id": 2,
            "title": "Без жанрів",
            "release_date": "2023-01-01",
            "poster_path": "/b.jpg",
            "genre_ids": [],
            "overview": "Опис",
        },
    ]

    def fake_tmdb(path, params, api_key):
        if path == "/discover/movie" and params.get("without_genres") == "16" and params["page"] == 1:
            return {"results": results}
        return {"results": []} if path.startswith("/discover/") else {}

    with patch("src.api.services.tmdb._tmdb_get", side_effect=fake_tmdb):
        movies = fetch_tmdb_movies(api_key="test-key")

    assert movies[0]["genre"] == "Фантастика"
    assert movies[0]["genres"] == ["Фантастика", "Трилер"]
    # A title without known genres gets the default one instead of a made-up genre
    assert movies[1]["genres"] == ["Драма"]
    assert genres_from_tmdb([28, 12]) == ["Бойовик", "Пригоди"]
    assert genres_from_tmdb([10759, 10765], "tv") == ["Бойовик", "Пригоди", "Фантастика", "Фентезі"]
    assert genres_from_tmdb(None) == []


def test_seed_links_genres_and_refreshes_them(db_session):
    # Trace: T-039
    source = {"id": 7, "title": "Тест", "genre": "Комедія", "genres": ["Комедія", "Сімейний"], "year": 2020}
    seed_movies_to_database(db_session, [source])
    content = db_session.query(Content).filter(Content.id == 7).one()
    assert linked_names(db_session, content) == ["Комедія", "Сімейний"]

    seed_movies_to_database(db_session, [{**source, "genres": ["Мультфільм", "Комедія"]}])

    db_session.refresh(content)
    assert linked_names(db_session, content) == ["Мультфільм", "Комедія"]
    assert (content.genre, content.genres) == ("Мультфільм", ["Мультфільм", "Комедія"])


def test_filter_by_any_genre_of_the_title(client, db_session):
    # Trace: T-040
    add_title(db_session, 1, "Дюна", "Фантастика", ["Фантастика", "Бойовик"])
    add_title(db_session, 2, "Оппенгеймер", "Драма", ["Драма", "Біографія"])
    add_title(db_session, 3, "Джон Вік", "Бойовик", ["Бойовик", "Трилер"])
    sync_genre_links(db_session)

    def titles(genre):
        response = client.get("/api/v1/movies", params={"genre": genre})
        assert response.status_code == 200
        return sorted(item["title"] for item in response.json()["items"])

    # A secondary genre counts too ("Дюна" is also an action movie)
    assert titles("Бойовик") == ["Джон Вік", "Дюна"]
    # English names and any letter case work
    assert titles("action") == ["Джон Вік", "Дюна"]
    assert titles("Біографія") == ["Оппенгеймер"]
    # Exact genre, not a part of a name
    assert titles("Бой") == []
    assert titles("Вестерн") == []


def test_genre_dictionary_with_counts(client, db_session):
    # Trace: T-041
    add_title(db_session, 1, "Дюна", "Фантастика", ["Фантастика", "Бойовик"])
    add_title(db_session, 2, "Джон Вік", "Бойовик", ["Бойовик"])
    sync_genre_links(db_session)

    response = client.get("/api/v1/genres")

    assert response.status_code == 200
    by_name = {item["name"]: item for item in response.json()}
    assert set(by_name) == {"Бойовик", "Фантастика"}
    assert by_name["Бойовик"]["titles_count"] == 2
    assert by_name["Фантастика"]["name_en"] == "Sci-Fi"

    every = client.get("/api/v1/genres", params={"include_empty": True}).json()
    assert len(every) >= len(TMDB_MOVIE_GENRES)
    assert {"name": "Вестерн", "titles_count": 0}.items() <= next(g for g in every if g["name"] == "Вестерн").items()


def test_startup_backfill_links_old_titles_once(db_session):
    # Trace: T-041
    old = add_title(db_session, 1, "Стара назва", "Драма", ["драма", " Мелодрама ", "", None])
    no_list = add_title(db_session, 2, "Без списку", "Жахи", None)

    assert sync_genre_links(db_session) == 2
    assert linked_names(db_session, old) == ["Драма", "Мелодрама"]
    assert linked_names(db_session, no_list) == ["Жахи"]
    # Already linked titles are left alone; the dictionary is not duplicated
    assert sync_genre_links(db_session) == 0
    assert db_session.query(Genre).filter(Genre.name == "Драма").count() == 1


def test_unknown_genre_is_added_to_the_dictionary(db_session):
    content = add_title(db_session, 1, "Аніме", "Драма")

    assert set_content_genres(db_session, content, ["Аніме", "Драма"]) == ["Аніме", "Драма"]
    assert db_session.query(Genre).filter(Genre.name == "Аніме").one().name_en is None
    # Without names the title keeps its primary genre
    assert set_content_genres(db_session, content, [None, " "]) == ["Аніме"]


def test_set_content_genres_needs_a_content_id(db_session):
    with pytest.raises(ValueError):
        set_content_genres(db_session, Content(title="x", genre="Драма"), ["Драма"])


def test_clean_genre_names():
    assert clean_genre_names(["Драма", "драма", " Трилер ", "", None, 5]) == ["Драма", "Трилер"]


def test_startup_link_never_blocks_the_api():
    db = MagicMock()
    with patch("src.api.services.genres.sync_genre_links", side_effect=OperationalError("SELECT", {}, Exception())):
        assert link_catalog_genres(db) == 0
    db.rollback.assert_called_once()
