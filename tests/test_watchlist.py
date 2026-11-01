"""Watchlist API tests (FR-005, US-001)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Content, User, WatchlistItem
from src.api.main import app
from src.api.routers.auth import get_db
from src.api.services.auth import create_access_token, hash_password

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

URL = "/api/v1/watchlist"
DUNE = uuid.UUID("11111111-1111-4111-8111-111111111111")
CHERNOBYL = uuid.UUID("22222222-2222-4222-8222-222222222222")
SHREK = uuid.UUID("33333333-3333-4333-8333-333333333333")


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    db.query(WatchlistItem).delete()
    db.query(User).delete()
    db.query(Content).delete()
    for item_id, content_id, title, category in [
        (1, DUNE, "Dune", "Movie"),
        (2, CHERNOBYL, "Chernobyl", "Series"),
        (3, SHREK, "Shrek", "Cartoons"),
    ]:
        db.add(
            Content(
                id=item_id,
                content_id=content_id,
                title=title,
                category=category,
                genre="Драма",
                year=2000 + item_id,
                rating=8.0,
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


def make_user(db, nickname="viewer", verified=True, status="active"):
    user = User(
        user_id=uuid.uuid4(),
        email=f"{nickname}@example.com",
        password_hash=hash_password("Password123!"),
        nickname=nickname,
        email_verified=verified,
        status=status,
    )
    db.add(user)
    db.commit()
    return user


def auth(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id)})}"}


def add(client, user, content_id):
    return client.post(URL, json={"content_id": str(content_id)}, headers=auth(user))


def titles(response):
    return [item["title"] for item in response.json()["items"]]


def test_add_title_to_watchlist(client, db_session):
    # Trace: T-001
    user = make_user(db_session)

    response = add(client, user, CHERNOBYL)

    assert response.status_code == 201
    assert response.json()["title"] == "Chernobyl"
    listing = client.get(URL, headers=auth(user))
    assert listing.status_code == 200
    assert titles(listing) == ["Chernobyl"]
    assert listing.json()["total"] == 1


def test_watchlist_is_ordered_by_most_recently_added(client, db_session):
    # Trace: T-001
    user = make_user(db_session)
    for content_id in (DUNE, SHREK, CHERNOBYL):
        add(client, user, content_id)

    assert titles(client.get(URL, headers=auth(user))) == ["Chernobyl", "Shrek", "Dune"]


def test_adding_duplicate_is_rejected(client, db_session):
    # Trace: T-002
    user = make_user(db_session)
    add(client, user, DUNE)

    response = add(client, user, DUNE)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALREADY_IN_WATCHLIST"
    assert db_session.query(WatchlistItem).count() == 1


def test_remove_title_from_watchlist(client, db_session):
    # Trace: T-003
    user = make_user(db_session)
    add(client, user, DUNE)
    add(client, user, SHREK)

    response = client.delete(URL, params={"content_id": str(DUNE)}, headers=auth(user))

    assert response.status_code == 204
    assert titles(client.get(URL, headers=auth(user))) == ["Shrek"]


def test_removing_title_not_in_watchlist_returns_404(client, db_session):
    # Trace: T-003
    user = make_user(db_session)

    response = client.delete(URL, params={"content_id": str(DUNE)}, headers=auth(user))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_IN_WATCHLIST"


def test_watchlist_persists_after_logging_in_again(client, db_session):
    # Trace: T-004
    user = make_user(db_session)
    add(client, user, SHREK)

    # A brand new token simulates a new session after logout / login
    new_session = {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id)})}"}

    assert titles(client.get(URL, headers=new_session)) == ["Shrek"]


def test_watchlists_are_private_per_user(client, db_session):
    # Trace: T-004
    alice = make_user(db_session, "alice")
    bob = make_user(db_session, "bob")
    add(client, alice, DUNE)

    assert titles(client.get(URL, headers=auth(bob))) == []
    # Bob cannot remove Alice's item either
    assert client.delete(URL, params={"content_id": str(DUNE)}, headers=auth(bob)).status_code == 404
    assert titles(client.get(URL, headers=auth(alice))) == ["Dune"]


@pytest.mark.parametrize(
    "method, kwargs",
    [
        ("get", {}),
        ("post", {"json": {"content_id": str(DUNE)}}),
        ("delete", {"params": {"content_id": str(DUNE)}}),
    ],
)
def test_guest_cannot_use_watchlist(client, method, kwargs):
    # Trace: T-001
    response = getattr(client, method)(URL, **kwargs)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "verified, status, code", [(False, "pending", "EMAIL_NOT_VERIFIED"), (True, "banned", "ACCOUNT_BANNED")]
)
def test_unverified_or_banned_user_cannot_use_watchlist(client, db_session, verified, status, code):
    # Trace: T-001
    user = make_user(db_session, verified=verified, status=status)

    response = add(client, user, DUNE)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == code


def test_adding_unknown_title_returns_404(client, db_session):
    # Trace: T-001
    user = make_user(db_session)

    response = add(client, user, uuid.uuid4())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CONTENT_NOT_FOUND"


@pytest.mark.parametrize("content_id", ["../../admin", "not-a-uuid", None])
def test_invalid_content_id_returns_422(client, db_session, content_id):
    # Trace: T-001
    user = make_user(db_session)
    body = {} if content_id is None else {"content_id": content_id}

    assert client.post(URL, json=body, headers=auth(user)).status_code == 422
    params = {} if content_id is None else {"content_id": content_id}
    assert client.delete(URL, params=params, headers=auth(user)).status_code == 422
