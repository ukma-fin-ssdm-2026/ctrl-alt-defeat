"""Catalog import from TMDB (FR-012, US-012): sections, details, matching by TMDB id and the admin update."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Content, ContentGenre, Genre, User
from src.api.main import app
from src.api.routers import admin as admin_router
from src.api.routers import auth as auth_router
from src.api.services import catalog_sync, tmdb
from src.api.services.auth import create_access_token, hash_password
from src.api.services.tmdb import (
    FALLBACK_MOVIES,
    NO_DESCRIPTION,
    TmdbError,
    fetch_tmdb_catalog,
    fetch_tmdb_movies,
    seed_movies_to_database,
    sync_catalog,
)

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def movie(tmdb_id, title, genre_ids=(18,), poster="/p.jpg", date="2024-03-01", vote=7.4):
    return {
        "id": tmdb_id,
        "title": title,
        "original_title": f"{title} EN",
        "original_language": "en",
        "genre_ids": list(genre_ids),
        "poster_path": poster,
        "release_date": date,
        "vote_average": vote,
        "overview": f"Опис {title}",
    }


def series(tmdb_id, name, genre_ids=(10765,)):
    return {
        "id": tmdb_id,
        "name": name,
        "original_name": "오징어 게임",
        "original_language": "ko",
        "genre_ids": list(genre_ids),
        "poster_path": "/s.jpg",
        "first_air_date": "2021-09-17",
        "vote_average": 7.9,
        "overview": "",
    }


class FakeTmdb:
    """Answers TMDB paths like the real API; records the requests."""

    def __init__(self, movies=(), tv=(), cartoons=(), details=None, fail_lists=False):
        self.lists = {"movie": list(movies), "tv": list(tv), "cartoons": list(cartoons)}
        self.details = details or {}
        self.fail_lists = fail_lists
        self.calls = []

    def __call__(self, path, params, api_key):
        self.calls.append((path, params))
        if path.startswith("/discover/"):
            if self.fail_lists:
                raise OSError("network down")
            kind = path.rsplit("/", 1)[1]
            key = "cartoons" if params.get("with_genres") == "16" else kind
            page = params["page"]
            return {"results": self.lists[key][(page - 1) * 20 : page * 20]}
        detail = self.details.get(path)
        if isinstance(detail, Exception):
            raise detail
        return detail or {}


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    engine_test.dispose()


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    for model in (ContentGenre, Genre, Content, User):
        db.query(model).delete()
    db.commit()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


def test_three_sections_with_details_and_english_fallback():
    # Trace: T-033
    fake = FakeTmdb(
        movies=[movie(1, "Дюна", (878, 12)), movie(2, "Без постера", poster=None), movie(3, "Без дати", date="")],
        tv=[series(100, "Гра в кальмара")],
        cartoons=[movie(200, "Вперед", (16, 10751))],
        details={
            "/movie/1": {
                "runtime": 166,
                "genres": [{"id": 878}, {"id": 12}],
                "translations": {
                    "translations": [
                        {"iso_639_1": "en", "iso_3166_1": "GB", "data": {"title": "Dune GB"}},
                        {"iso_639_1": "en", "iso_3166_1": "US", "data": {"title": "Dune", "overview": "Paul..."}},
                    ]
                },
            },
            "/tv/100": {
                "episode_run_time": [55],
                "translations": {
                    "translations": [{"iso_639_1": "en", "data": {"name": "Squid Game", "overview": "Hwang"}}]
                },
            },
            "/movie/200": OSError("timeout"),
        },
    )
    with patch.object(tmdb, "_tmdb_get", fake):
        catalog = {item["tmdb_id"]: item for item in fetch_tmdb_catalog("key", per_section=5)}

    # Titles without a poster or a year are skipped
    assert set(catalog) == {1, 100, 200}
    dune, squid, onward = catalog[1], catalog[100], catalog[200]
    assert (dune["category"], dune["title_en"], dune["runtime"], dune["genres"]) == (
        "Movie",
        "Dune",
        166,
        ["Фантастика", "Пригоди"],
    )
    assert dune["img"] == "https://image.tmdb.org/t/p/w500/p.jpg"
    assert (dune["rating"], dune["rotten_rating"], dune["description_en"]) == (7.4, "74%", "Paul...")
    # Series: TV genres, episode runtime, English overview when there is no Ukrainian one
    assert (squid["category"], squid["title_en"], squid["runtime"]) == ("Series", "Squid Game", 55)
    assert squid["genres"] == ["Фантастика", "Фентезі"]
    assert squid["description"] == "Hwang"
    # Failed details keep the list data; a cartoon always has the "Мультфільм" genre
    assert (onward["category"], onward["runtime"], onward["genres"][0]) == ("Cartoons", None, "Мультфільм")
    # Movies exclude animation, cartoons are animation only
    discover = [params for path, params in fake.calls if path == "/discover/movie"]
    assert {params.get("without_genres") for params in discover} == {"16", None}
    assert all(params["language"] == "uk-UA" for params in discover)


def test_each_section_is_limited_and_pages_are_followed():
    # Trace: T-033
    fake = FakeTmdb(movies=[movie(i, f"Фільм {i}") for i in range(1, 46)])
    with patch.object(tmdb, "_tmdb_get", fake):
        catalog = fetch_tmdb_catalog("key", per_section=30)

    assert len([item for item in catalog if item["category"] == "Movie"]) == 30
    assert [
        params["page"] for path, params in fake.calls if path == "/discover/movie" and "without_genres" in params
    ] == [1, 2]


def test_list_failure_falls_back_to_the_built_in_catalog():
    # Trace: T-034
    with patch.object(tmdb, "_tmdb_get", FakeTmdb(fail_lists=True)):
        with pytest.raises(TmdbError):
            fetch_tmdb_catalog("key")
        assert fetch_tmdb_movies("key") == FALLBACK_MOVIES
    with pytest.raises(TmdbError):
        fetch_tmdb_catalog("")


def test_v3_key_and_v4_token_are_sent_correctly():
    # Trace: T-033
    response = MagicMock(status=200)
    response.read.return_value = b'{"results": []}'
    response.__enter__.return_value = response
    with patch("urllib.request.urlopen", return_value=response) as urlopen:
        tmdb._tmdb_get("/discover/movie", {"page": 1}, "v3key")
        tmdb._tmdb_get("/discover/movie", {"page": 1}, "eyJtoken")

    v3, v4 = (call.args[0] for call in urlopen.call_args_list)
    assert v3.full_url.startswith("https://api.themoviedb.org/3/discover/movie?")
    assert "api_key=v3key" in v3.full_url and v3.get_header("Authorization") is None
    assert "api_key" not in v4.full_url and v4.get_header("Authorization") == "Bearer eyJtoken"

    response.status = 401
    with patch("urllib.request.urlopen", return_value=response):
        with pytest.raises(TmdbError):
            tmdb._tmdb_get("/discover/movie", {}, "bad")


def test_import_never_overwrites_other_titles_by_internal_id(db_session):
    # Trace: T-042
    seed_movies_to_database(db_session, FALLBACK_MOVIES)
    dune_before = db_session.get(Content, 1)
    dune_tmdb_id, dune_img = dune_before.tmdb_id, dune_before.img
    total = db_session.query(Content).count()

    # An imported title that used to be numbered 1 by the old import must not touch title 1
    new_title = {
        "id": 1,
        "tmdb_id": 987654,
        "category": "Movie",
        "title": "Новий фільм",
        "genre": "Комедія",
        "genres": ["Комедія"],
        "year": 2025,
        "rating": 6.1,
        "img": "https://image.tmdb.org/t/p/w500/new.jpg",
    }
    result = sync_catalog(db_session, [new_title])

    assert (result.added, result.updated) == (1, 0)
    dune = db_session.get(Content, 1)
    assert (dune.title, dune.tmdb_id, dune.img) == ("Дюна: Частина друга", dune_tmdb_id, dune_img)
    added = db_session.query(Content).filter(Content.tmdb_id == 987654).one()
    assert added.id == total + 1


def test_existing_title_is_updated_by_tmdb_id(db_session):
    # Trace: T-042
    seed_movies_to_database(db_session, FALLBACK_MOVIES[:3])
    dune = db_session.get(Content, 1)
    update = {
        "tmdb_id": dune.tmdb_id,
        "category": "Movie",
        "title": "Дюна: Частина друга",
        "title_en": "Dune: Part Two",
        "genre": "Фантастика",
        "genres": ["Фантастика", "Пригоди"],
        "year": 2024,
        "runtime": 167,
        "rating": 8.2,
        "img": "https://image.tmdb.org/t/p/w500/fresh.jpg",
        "description": NO_DESCRIPTION,
    }
    old_description = dune.description

    result = sync_catalog(db_session, [update])

    assert (result.added, result.updated) == (0, 1)
    db_session.refresh(dune)
    assert (dune.rating, dune.runtime, dune.img) == (8.2, 167, "https://image.tmdb.org/t/p/w500/fresh.jpg")
    assert dune.genres == ["Фантастика", "Пригоди"]
    # The placeholder never replaces a real description
    assert dune.description == old_description
    assert db_session.query(Content).count() == 3


def test_movie_and_series_with_the_same_tmdb_number_are_different_titles(db_session):
    # Trace: T-042
    db_session.add(
        Content(id=1, content_id=uuid.uuid4(), title="Фільм", category="Movie", genre="Драма", year=2020, tmdb_id=500)
    )
    db_session.commit()
    show = {
        "tmdb_id": 500,
        "category": "Series",
        "title": "Серіал",
        "genre": "Драма",
        "genres": ["Драма"],
        "year": 2021,
    }

    result = sync_catalog(db_session, [show])

    assert (result.added, result.updated, result.skipped) == (0, 0, 1)
    assert db_session.get(Content, 1).title == "Фільм"


def test_old_title_without_tmdb_id_is_adopted_by_its_name(db_session):
    # Trace: T-042
    db_session.add(
        Content(id=5, content_id=uuid.uuid4(), title="Шрек", category="Cartoons", genre="Комедія", year=2001)
    )
    db_session.commit()
    item = {"tmdb_id": 808, "category": "Cartoons", "title": "Шрек", "genres": ["Мультфільм", "Комедія"], "year": 2001}

    result = sync_catalog(db_session, [item])

    assert result.updated == 1
    shrek = db_session.get(Content, 5)
    assert (shrek.tmdb_id, shrek.genre) == (808, "Мультфільм")


# --- Admin update from TMDB -------------------------------------------------------------------------------


def make_user(db, nickname, role):
    user = User(
        user_id=uuid.uuid4(),
        email=f"{nickname}@example.com",
        password_hash=hash_password("Password123!"),
        nickname=nickname,
        role=role,
        email_verified=True,
        status="active",
    )
    db.add(user)
    db.commit()
    return user


def auth(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id)})}"}


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    for router in (admin_router, auth_router):
        app.dependency_overrides[router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_sync_status():
    catalog_sync._status.update(
        state="idle", started_at=None, finished_at=None, added=0, updated=0, skipped=0, error=None
    )
    yield


SYNC = "/api/v1/admin/catalog/sync"


def test_admin_updates_the_catalog_in_the_background(client, db_session, monkeypatch):
    # Trace: T-043
    admin = make_user(db_session, "moderator", "admin")
    monkeypatch.setenv("TMDB_API_KEY", "key")
    fake = FakeTmdb(movies=[movie(1, "Дюна")], cartoons=[movie(2, "Вперед", (16,))])

    with patch.object(tmdb, "_tmdb_get", fake), patch.object(catalog_sync, "SessionLocal", TestingSessionLocal):
        started = client.post(SYNC, headers=auth(admin))
        status = client.get(SYNC, headers=auth(admin)).json()

    assert started.status_code == 202
    assert started.json()["state"] == "running"
    # TestClient runs background tasks before returning, so the import is already finished
    assert (status["state"], status["added"], status["configured"]) == ("done", 2, True)
    assert db_session.query(Content).filter(Content.category == "Cartoons").count() == 1


def test_sync_reports_a_failure(client, db_session, monkeypatch):
    # Trace: T-043
    admin = make_user(db_session, "moderator", "admin")
    monkeypatch.setenv("TMDB_API_KEY", "key")

    with (
        patch.object(tmdb, "_tmdb_get", FakeTmdb(fail_lists=True)),
        patch.object(catalog_sync, "SessionLocal", TestingSessionLocal),
    ):
        client.post(SYNC, headers=auth(admin))

    status = client.get(SYNC, headers=auth(admin)).json()
    assert status["state"] == "failed"
    assert "network down" in status["error"]


def test_sync_needs_a_key_an_admin_and_one_run_at_a_time(client, db_session, monkeypatch):
    # Trace: T-043
    admin = make_user(db_session, "moderator", "admin")
    viewer = make_user(db_session, "viewer", "user")
    monkeypatch.delenv("TMDB_API_KEY", raising=False)

    missing = client.post(SYNC, headers=auth(admin))
    assert missing.status_code == 503
    assert missing.json()["error"]["code"] == "TMDB_NOT_CONFIGURED"
    assert client.get(SYNC, headers=auth(admin)).json()["configured"] is False

    monkeypatch.setenv("TMDB_API_KEY", "key")
    assert client.post(SYNC, headers=auth(viewer)).status_code == 403
    catalog_sync.try_start()
    busy = client.post(SYNC, headers=auth(admin))
    assert busy.status_code == 409
    assert busy.json()["error"]["code"] == "SYNC_IN_PROGRESS"
