"""Tests for Watched List (FR-006, US-004, T-011, T-012, T-013)."""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Content, User, WatchedItem
from src.api.main import app
from src.api.routers import auth as auth_router
from src.api.routers import watched as watched_router
from src.api.services.auth import create_access_token

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

WATCHED_URL = "/api/v1/users/me/watched"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    db.query(WatchedItem).delete()
    db.query(Content).delete()
    db.query(User).delete()
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

    app.dependency_overrides[auth_router.get_db] = override_get_db
    app.dependency_overrides[watched_router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_and_token(db_session):
    user_id = uuid.uuid4()
    user = User(
        user_id=user_id,
        email="viewer@example.com",
        nickname="MovieViewer",
        password_hash="fakehash",
        role="user",
        email_verified=True,
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    token = create_access_token(data={"sub": str(user_id), "role": "user"})
    return user, token


@pytest.fixture
def second_user_and_token(db_session):
    user_id = uuid.uuid4()
    user = User(
        user_id=user_id,
        email="second_viewer@example.com",
        nickname="OtherViewer",
        password_hash="fakehash",
        role="user",
        email_verified=True,
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    token = create_access_token(data={"sub": str(user_id), "role": "user"})
    return user, token


def test_mark_movie_as_watched_t011(client: TestClient, db_session, test_user_and_token):
    """
    US-004 / FR-006: User marks a movie as watched.
    """
    # Trace: T-011
    user, token = test_user_and_token
    content_id = uuid.uuid4()

    # 1. Post to mark as watched
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(WATCHED_URL, json={"content_id": str(content_id)}, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["content_id"] == str(content_id)
    assert data["user_id"] == str(user.user_id)
    assert data["created_at"] is not None

    # 2. Check list contains the item
    list_res = client.get(WATCHED_URL, headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["content_id"] == str(content_id)

    # 3. Check single content status check
    status_res = client.get(f"{WATCHED_URL}/{content_id}", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["is_watched"] is True
    assert status_data["content_id"] == str(content_id)
    assert status_data["watched_at"] is not None


def test_remove_movie_from_watched_t012(client: TestClient, db_session, test_user_and_token):
    """
    US-004 / FR-006: User unmarks (removes) a movie from watched list.
    """
    # Trace: T-012
    _, token = test_user_and_token
    content_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {token}"}

    # Add first
    client.post(WATCHED_URL, json={"content_id": str(content_id)}, headers=headers)

    # Remove
    del_res = client.delete(f"{WATCHED_URL}/{content_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify no longer in list
    list_res = client.get(WATCHED_URL, headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 0
    assert list_res.json()["items"] == []

    # Verify status is false
    status_res = client.get(f"{WATCHED_URL}/{content_id}", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["is_watched"] is False


def test_user_isolation_watched_t013(client: TestClient, db_session, test_user_and_token, second_user_and_token):
    """
    US-004 / FR-006 / SEC-001: Data isolation between different users.
    User A cannot see or delete User B's watched list items.
    """
    # Trace: T-013
    _, token_a = test_user_and_token
    _, token_b = second_user_and_token

    content_a = uuid.uuid4()
    content_b = uuid.uuid4()

    # User A watches content_a
    client.post(WATCHED_URL, json={"content_id": str(content_a)}, headers={"Authorization": f"Bearer {token_a}"})
    # User B watches content_b
    client.post(WATCHED_URL, json={"content_id": str(content_b)}, headers={"Authorization": f"Bearer {token_b}"})

    # Check isolation for User A
    res_a = client.get(WATCHED_URL, headers={"Authorization": f"Bearer {token_a}"}).json()
    assert res_a["total"] == 1
    assert res_a["items"][0]["content_id"] == str(content_a)

    # Check isolation for User B
    res_b = client.get(WATCHED_URL, headers={"Authorization": f"Bearer {token_b}"}).json()
    assert res_b["total"] == 1
    assert res_b["items"][0]["content_id"] == str(content_b)

    # User A tries to delete User B's content_b -> should return 404 (not in A's list)
    del_res = client.delete(f"{WATCHED_URL}/{content_b}", headers={"Authorization": f"Bearer {token_a}"})
    assert del_res.status_code == 404

    # Content B is still in User B's watched list
    res_b_after = client.get(WATCHED_URL, headers={"Authorization": f"Bearer {token_b}"}).json()
    assert res_b_after["total"] == 1


def test_watched_unauthorized_requires_login(client: TestClient):
    """
    Unauthenticated requests are rejected with 401.
    """
    content_id = uuid.uuid4()
    assert client.get(WATCHED_URL).status_code == 401
    assert client.post(WATCHED_URL, json={"content_id": str(content_id)}).status_code == 401
    assert client.delete(f"{WATCHED_URL}/{content_id}").status_code == 401
    assert client.get(f"{WATCHED_URL}/{content_id}").status_code == 401


def test_mark_as_watched_idempotent(client: TestClient, db_session, test_user_and_token):
    """
    Marking the same content as watched twice returns 200 and doesn't duplicate.
    """
    _, token = test_user_and_token
    content_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(WATCHED_URL, json={"content_id": str(content_id)}, headers=headers)
    assert first.status_code == 201

    second = client.post(WATCHED_URL, json={"content_id": str(content_id)}, headers=headers)
    assert second.status_code == 200
    assert second.json()["content_id"] == str(content_id)

    assert db_session.query(WatchedItem).count() == 1


def test_remove_nonexistent_watched_returns_404(client: TestClient, test_user_and_token):
    """
    Attempting to remove content not in the watched list returns 404.
    """
    _, token = test_user_and_token
    random_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete(f"{WATCHED_URL}/{random_id}", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_watched_list_with_movie_metadata(client: TestClient, db_session, test_user_and_token):
    """
    When content exists in Content table, watched items include metadata for UI rendering.
    """
    _, token = test_user_and_token
    content_id = uuid.uuid4()

    db_session.add(
        Content(
            content_id=content_id,
            title="Дюна: Частина друга",
            title_en="Dune: Part Two",
            category="Movie",
            genre="Фантастика",
            year=2024,
            rating=8.9,
            img="https://example.com/dune2.jpg",
        )
    )
    db_session.commit()

    headers = {"Authorization": f"Bearer {token}"}
    client.post(WATCHED_URL, json={"content_id": str(content_id)}, headers=headers)

    res = client.get(WATCHED_URL, headers=headers).json()
    item = res["items"][0]
    assert item["title"] == "Дюна: Частина друга"
    assert item["title_en"] == "Dune: Part Two"
    assert item["year"] == 2024
    assert item["genre"] == "Фантастика"
    assert item["rating"] == 8.9


def test_banned_user_cannot_access_watched(client: TestClient, db_session):
    """
    Banned users are rejected with 403.
    """
    user_id = uuid.uuid4()
    user = User(
        user_id=user_id,
        email="banned@example.com",
        nickname="BannedViewer",
        password_hash="fakehash",
        role="user",
        email_verified=True,
        status="banned",
    )
    db_session.add(user)
    db_session.commit()
    token = create_access_token(data={"sub": str(user_id), "role": "user"})

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(WATCHED_URL, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_BANNED"


def test_unverified_email_user_cannot_access_watched(client: TestClient, db_session):
    """
    Users with unverified emails are rejected with 403.
    """
    user_id = uuid.uuid4()
    user = User(
        user_id=user_id,
        email="unverified@example.com",
        nickname="UnverifiedViewer",
        password_hash="fakehash",
        role="user",
        email_verified=False,
        status="pending",
    )
    db_session.add(user)
    db_session.commit()
    token = create_access_token(data={"sub": str(user_id), "role": "user"})

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(WATCHED_URL, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"