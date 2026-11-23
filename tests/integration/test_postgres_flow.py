"""
Integration tests against a real PostgreSQL (Lab 10, bonus 3: the slow suite).

The application is started as in production (lifespan: create_all, upgrade_schema, demo accounts, catalog
seed) on the database from DATABASE_URL, and a user goes through registration, email confirmation, login,
watchlist, watched list, review and recommendations over HTTP. Unlike the rest of the suite, nothing is
replaced by SQLite: PostgreSQL types (UUID, JSON), unique indexes and constraints are the real ones.

    DATABASE_URL=postgresql://postgres@localhost:5432/ci python -m pytest -m slow

In CI the database is a postgres:16 service container of the job `slow` (.github/workflows/ci.yml).
Without a PostgreSQL DATABASE_URL (local runs, the fast suite) the tests are skipped.
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

POSTGRES = os.getenv("DATABASE_URL", "").startswith(("postgres://", "postgresql"))

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not POSTGRES, reason="needs DATABASE_URL of a real PostgreSQL"),
]

PASSWORD = "Password123"


@pytest.fixture(scope="module")
def client():
    from src.api.main import app

    app.dependency_overrides.clear()  # the real database, not a test session of another module
    with TestClient(app) as test_client:  # runs the startup: schema, upgrades, seeds
        yield test_client


@pytest.fixture(scope="module")
def database():
    from src.api.db.database import SessionLocal, engine

    return engine, SessionLocal


@pytest.fixture
def account(client, database):
    """A new user who registered, confirmed the email from the database and logged in."""
    from src.api.db.models import User
    from src.api.services.account import remove_user_with_data

    _, SessionLocal = database
    email = f"it-{uuid.uuid4().hex[:12]}@example.com"
    nickname = f"it{uuid.uuid4().hex[:10]}"

    registered = client.post("/api/v1/auth/register", json={"email": email, "nickname": nickname, "password": PASSWORD})
    assert registered.status_code == 201, registered.text

    with SessionLocal() as db:
        token = db.query(User).filter(User.email == email).one().verification_token
    assert client.get("/api/v1/auth/verify", params={"token": token}).status_code == 200

    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    client.cookies.clear()  # every request below proves itself with the bearer token
    yield {"email": email, "headers": {"Authorization": f"Bearer {login.json()['access_token']}"}}

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if user is not None:
            remove_user_with_data(db, user)


def test_startup_builds_the_schema_in_postgres(client, database):
    engine, _ = database
    assert engine.dialect.name == "postgresql"

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"users", "content", "reviews", "comments", "watchlist", "watched_items", "bans"} <= tables
    user_id = next(column for column in inspector.get_columns("users") if column["name"] == "user_id")
    assert user_id["type"].__class__.__name__.upper() == "UUID"  # a native PostgreSQL type, not CHAR(32)
    indexes = {index["name"]: index for index in inspector.get_indexes("users")}
    assert indexes["ix_users_email_canonical"]["unique"]  # one mailbox, one account (T-051)

    assert client.get("/health").json()["database"] == "ok"
    catalog = client.get("/api/v1/movies", params={"limit": 1, "compact": "true"}).json()
    assert catalog["total"] > 0  # the catalog seed of a fresh database


def test_same_mailbox_is_rejected_by_postgres(client, account):
    local, domain = account["email"].split("@")
    alias = client.post(
        "/api/v1/auth/register",
        json={"email": f"{local}+again@{domain}", "nickname": f"it{uuid.uuid4().hex[:10]}", "password": PASSWORD},
    )

    assert alias.status_code == 409
    assert alias.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_lists_review_and_recommendations_in_postgres(client, account):
    headers = account["headers"]
    movie = client.get("/api/v1/movies", params={"limit": 1, "compact": "true"}).json()["items"][0]
    body = {"content_id": movie["content_id"]}

    assert client.post("/api/v1/watchlist", json=body, headers=headers).status_code == 201
    # The UNIQUE constraint of PostgreSQL, answered as 409 and not as a server error
    assert client.post("/api/v1/watchlist", json=body, headers=headers).status_code == 409

    assert client.post("/api/v1/users/me/watched", json=body, headers=headers).status_code == 201
    review = {**body, "rating": 9, "review_text": "Checked against a real PostgreSQL database"}
    created = client.post("/api/v1/reviews", json=review, headers=headers)
    assert created.status_code == 201, created.text
    assert client.post("/api/v1/reviews", json=review, headers=headers).status_code == 409  # one review a title

    recommended = client.get("/api/v1/recommendations", headers=headers)
    assert recommended.status_code == 200
    items = recommended.json()["items"]
    assert items and movie["content_id"] not in {item["content_id"] for item in items}
