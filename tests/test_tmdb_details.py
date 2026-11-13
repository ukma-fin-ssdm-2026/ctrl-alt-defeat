"""
Details of the page of a title from TMDB (US-013): trailers, cast and crew, seasons of a series,
film series and similar titles; stored by the catalog import and served by the API.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import CONTENT_COLUMNS, Base, add_missing_columns
from src.api.db.models import Content
from src.api.main import app
from src.api.routers import movies as movies_router
from src.api.security_headers import CONTENT_SECURITY_POLICY
from src.api.services import tmdb
from src.api.services.tmdb import build_catalog_item, page_details, pick_trailer, sync_catalog

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def video(key, language, kind="Trailer", official=True, published="2024-01-01"):
    return {
        "key": key,
        "iso_639_1": language,
        "site": "YouTube",
        "type": kind,
        "official": official,
        "published_at": published,
    }


MOVIE_DETAILS = {
    "id": 121,
    "title": "Володар перснів: Дві вежі",
    "release_date": "2002-12-18",
    "poster_path": "/ttt.jpg",
    "overview": "Братство розпалося.",
    "runtime": 179,
    "genres": [{"id": 12}],
    "belongs_to_collection": {"id": 119, "name": "Володар перснів (Колекція)"},
    "videos": {
        "results": [
            video("ukTeaser01", "uk", kind="Teaser"),
            video("ukTrailer1", "uk", official=False),
            video("ukTrailer2", "uk", published="2020-05-01"),
            video("enOld00001", "en", published="2002-01-01"),
            video("enNew00001", "en", published="2021-01-01"),
            video("bad key!", "en", published="2030-01-01"),
            {**video("vimeo00001", "en"), "site": "Vimeo"},
        ]
    },
    "credits": {
        "cast": [
            {"name": f"Actor {n}", "character": f"Role {n}", "order": n, "profile_path": f"/a{n}.jpg"}
            for n in range(12, 0, -1)
        ]
        + [{"name": "Elijah Wood", "character": "Frodo", "order": 0, "profile_path": None}],
        "crew": [
            {"name": "Peter Jackson", "job": "Director"},
            {"name": "Peter Jackson", "job": "Screenplay"},
            {"name": "Fran Walsh", "job": "Screenplay"},
            {"name": "Fran Walsh", "job": "Writer"},
            {"name": "J.R.R. Tolkien", "job": "Novel"},
            {"name": "Howard Shore", "job": "Original Music Composer"},
        ],
    },
    "recommendations": {"results": [{"id": 122}, {"id": 120}, {"id": "bad"}]},
}

SERIES_DETAILS = {
    "id": 1399,
    "name": "Гра престолів",
    "first_air_date": "2011-04-17",
    "poster_path": "/got.jpg",
    "overview": "Сім королівств.",
    "created_by": [{"name": "David Benioff"}, {"name": "D. B. Weiss"}],
    "status": "Ended",
    "number_of_seasons": 8,
    "number_of_episodes": 73,
    "last_air_date": "2019-05-19",
    "next_episode_to_air": None,
    "seasons": [
        {
            "season_number": 2,
            "name": "Сезон 2",
            "episode_count": 10,
            "air_date": "2012-04-01",
            "poster_path": "/s2.jpg",
        },
        {"season_number": 1, "name": "Сезон 1", "episode_count": 10, "air_date": "2011-04-17", "poster_path": None},
    ],
    "videos": {"results": []},
    "credits": {"cast": [], "crew": []},
    "recommendations": {"results": [{"id": 1402}]},
}


def test_best_trailer_per_language():
    # Trace: T-049
    videos = MOVIE_DETAILS["videos"]
    # Official trailer before an unofficial one and before a teaser
    assert pick_trailer(videos, "uk") == "ukTrailer2"
    # Newest of the official trailers; a key that is not a YouTube id and other sites are ignored
    assert pick_trailer(videos, "en") == "enNew00001"
    assert pick_trailer(videos, "de") is None
    assert pick_trailer(None, "uk") is None


def test_page_details_of_a_movie():
    # Trace: T-049
    page = page_details("movie", MOVIE_DETAILS)

    assert (page["trailer_uk"], page["trailer_en"]) == ("ukTrailer2", "enNew00001")
    # Billing order, at most 10 actors, photos as full URLs
    assert [person["name"] for person in page["cast_members"]][:3] == ["Elijah Wood", "Actor 1", "Actor 2"]
    assert len(page["cast_members"]) == 10
    assert page["cast_members"][0]["photo"] is None
    assert page["cast_members"][1]["photo"] == "https://image.tmdb.org/t/p/w185/a1.jpg"
    # Each name once, at most 3; music is not crew we show
    assert page["crew_members"] == {
        "directors": ["Peter Jackson"],
        "writers": ["Peter Jackson", "Fran Walsh", "J.R.R. Tolkien"],
        "creators": [],
    }
    assert page["series_details"] is None
    assert (page["collection_id"], page["collection_name"]) == (119, "Володар перснів (Колекція)")
    assert page["similar_tmdb_ids"] == [122, 120]


def test_page_details_of_a_series_and_without_details():
    # Trace: T-049
    page = page_details("tv", SERIES_DETAILS)

    assert page["crew_members"]["creators"] == ["David Benioff", "D. B. Weiss"]
    series = page["series_details"]
    assert (series["status"], series["number_of_seasons"], series["number_of_episodes"]) == ("Ended", 8, 73)
    assert series["next_episode"] is None
    assert [season["season_number"] for season in series["seasons"]] == [1, 2]
    assert series["seasons"][1]["poster"] == "https://image.tmdb.org/t/p/w185/s2.jpg"
    assert page["trailer_uk"] is None and page["collection_id"] is None
    # The details request failed: nothing to store, nothing to erase
    assert page_details("movie", {}) == {}


def test_import_asks_tmdb_for_the_page_details_in_one_request(monkeypatch):
    # Trace: T-049
    calls = []

    def fake_get(path, params, api_key):
        calls.append((path, params))
        return MOVIE_DETAILS

    monkeypatch.setattr(tmdb, "_tmdb_get", fake_get)
    details = tmdb._details("movie", 121, "key")

    assert details is MOVIE_DETAILS
    assert calls[0][1]["append_to_response"] == "translations,videos,credits,recommendations"
    assert calls[0][1]["include_video_language"] == "uk,en"
    item = build_catalog_item("Movie", "movie", {"id": 121}, details)
    assert item["trailer_uk"] == "ukTrailer2" and item["collection_id"] == 119


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine_test)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine_test)


def stored(db, tmdb_id, category="Movie"):
    return db.query(Content).filter(Content.tmdb_id == tmdb_id, Content.category == category).one()


def test_sync_stores_replaces_and_keeps_page_details(db_session):
    # Trace: T-049
    item = build_catalog_item("Movie", "movie", {"id": 121}, MOVIE_DETAILS)
    sync_catalog(db_session, [item])
    movie = stored(db_session, 121)
    assert movie.trailer_uk == "ukTrailer2" and len(movie.cast_members) == 10

    # The trailer was removed on TMDB: the next import clears it
    without_trailer = {**MOVIE_DETAILS, "videos": {"results": []}}
    sync_catalog(db_session, [build_catalog_item("Movie", "movie", {"id": 121}, without_trailer)])
    assert stored(db_session, 121).trailer_uk is None

    # The details request failed this time: the stored cast and film series stay
    list_only = build_catalog_item("Movie", "movie", {**MOVIE_DETAILS, "videos": None, "credits": None}, {})
    sync_catalog(db_session, [list_only])
    kept = stored(db_session, 121)
    assert len(kept.cast_members) == 10 and kept.collection_id == 119


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[movies_router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def add(db, tmdb_id, title, year, category="Movie", **fields):
    content = Content(
        content_id=uuid.uuid4(), tmdb_id=tmdb_id, title=title, category=category, genre="Пригоди", year=year, **fields
    )
    db.add(content)
    db.commit()
    return content


def test_movie_page_returns_the_details_and_lists_stay_light(client, db_session):
    # Trace: T-049
    sync_catalog(db_session, [build_catalog_item("Movie", "movie", {"id": 121}, MOVIE_DETAILS)])
    movie = stored(db_session, 121)

    page = client.get(f"/api/v1/movies/{movie.content_id}").json()

    assert (page["trailer_uk"], page["trailer_en"]) == ("ukTrailer2", "enNew00001")
    assert page["cast"][0] == {"name": "Elijah Wood", "character": "Frodo", "photo": None}
    assert page["crew"]["directors"] == ["Peter Jackson"]
    assert page["collection"] == {"id": 119, "name": "Володар перснів (Колекція)"}
    assert page["series"] is None
    listed = client.get("/api/v1/movies").json()["items"][0]
    assert "cast" not in listed and "trailer_uk" not in listed


def test_series_page_has_seasons(client, db_session):
    # Trace: T-049
    sync_catalog(db_session, [build_catalog_item("Series", "tv", {"id": 1399}, SERIES_DETAILS)])
    series = stored(db_session, 1399, "Series")

    page = client.get(f"/api/v1/movies/{series.id}").json()

    assert page["series"]["number_of_episodes"] == 73
    assert page["series"]["seasons"][0] == {
        "season_number": 1,
        "name": "Сезон 1",
        "episode_count": 10,
        "air_date": "2011-04-17",
        "poster": None,
    }
    assert page["crew"]["creators"] == ["David Benioff", "D. B. Weiss"]


def test_related_titles_of_the_film_series_and_similar(client, db_session):
    # Trace: T-049
    two_towers = add(
        db_session,
        121,
        "Дві вежі",
        2002,
        collection_id=119,
        collection_name="Володар перснів",
        similar_tmdb_ids=[122, 999, 1399, 120],
    )
    add(db_session, 122, "Повернення короля", 2003, collection_id=119, collection_name="Володар перснів")
    add(db_session, 120, "Хранителі персня", 2001, collection_id=119, collection_name="Володар перснів")
    # A series with the number of a recommended movie is a different title
    add(db_session, 1399, "Гра престолів", 2011, category="Series")

    related = client.get(f"/api/v1/movies/{two_towers.content_id}/related").json()

    assert related["collection"] == {"id": 119, "name": "Володар перснів"}
    assert [title["title"] for title in related["collection_items"]] == ["Хранителі персня", "Повернення короля"]
    # TMDB order; titles missing from the catalog and of another media type are left out
    assert [title["title"] for title in related["similar"]] == ["Повернення короля", "Хранителі персня"]
    assert len(client.get(f"/api/v1/movies/{two_towers.id}/related", params={"limit": 1}).json()["similar"]) == 1


def test_title_without_tmdb_details(client, db_session):
    # Trace: T-049
    plain = add(db_session, None, "Вбудований фільм", 2020)

    page = client.get(f"/api/v1/movies/{plain.id}").json()
    related = client.get(f"/api/v1/movies/{plain.id}/related").json()

    assert page["cast"] == [] and page["crew"] == {"directors": [], "writers": [], "creators": []}
    assert page["trailer_uk"] is None and page["collection"] is None
    assert related == {"collection": None, "collection_items": [], "similar": []}
    assert client.get("/api/v1/movies/missing/related").status_code == 404


def test_old_content_table_gets_the_new_columns():
    # Trace: T-049
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE content (id INTEGER PRIMARY KEY, title VARCHAR)")

    assert add_missing_columns(engine, "content", CONTENT_COLUMNS) == list(CONTENT_COLUMNS)
    assert add_missing_columns(engine, "content", CONTENT_COLUMNS) == []
    assert set(CONTENT_COLUMNS) <= {column["name"] for column in inspect(engine).get_columns("content")}
    engine.dispose()


def test_trailer_player_is_allowed_by_the_content_security_policy():
    # Trace: T-049
    assert "frame-src https://www.youtube-nocookie.com" in CONTENT_SECURITY_POLICY
