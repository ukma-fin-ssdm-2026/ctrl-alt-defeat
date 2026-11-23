"""GET /auth/session: the site checks the session on startup without a 401 for guests (issue #276)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import User
from src.api.main import app
from src.api.routers import auth as auth_router
from src.api.services.auth import create_access_token, hash_password

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)
URL = "/api/v1/auth/session"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    engine_test.dispose()


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(db, nickname, verified=True, token_version=0):
    user = User(
        user_id=uuid.uuid4(),
        email=f"{nickname}@example.com",
        password_hash=hash_password("Password123"),
        nickname=nickname,
        role="user",
        email_verified=verified,
        status="active" if verified else "pending",
        token_version=token_version,
    )
    db.add(user)
    db.commit()
    return user


def bearer(user, ver=0):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id), 'ver': ver})}"}


def test_guest_gets_null_user_without_error(client):
    # Trace: T-037
    response = client.get(URL)
    assert response.status_code == 200
    assert response.json() == {"user": None}


def test_signed_in_user_is_returned(client, db_session):
    # Trace: T-037
    user = make_user(db_session, "viewer")
    response = client.get(URL, headers=bearer(user))
    assert response.status_code == 200
    body = response.json()["user"]
    assert body["nickname"] == "viewer"
    assert body["user_id"] == str(user.user_id)


def test_session_cookie_is_accepted(client, db_session):
    # Trace: T-037
    user = make_user(db_session, "cookie_user")
    token = create_access_token({"sub": str(user.user_id), "ver": 0})
    client.cookies.set("access_token", token)
    try:
        assert client.get(URL).json()["user"]["nickname"] == "cookie_user"
    finally:
        client.cookies.clear()


@pytest.mark.parametrize("header", ["Bearer not-a-jwt", "Bearer "])
def test_invalid_token_means_guest(client, header):
    # Trace: T-037
    response = client.get(URL, headers={"Authorization": header})
    assert response.status_code == 200
    assert response.json() == {"user": None}


def test_revoked_token_means_guest(client, db_session):
    # Trace: T-037
    user = make_user(db_session, "changed_password", token_version=1)
    response = client.get(URL, headers=bearer(user, ver=0))
    assert response.status_code == 200
    assert response.json() == {"user": None}


def test_unverified_account_means_guest(client, db_session):
    # Trace: T-037
    user = make_user(db_session, "pending_user", verified=False)
    assert client.get(URL, headers=bearer(user)).json() == {"user": None}


def test_auth_me_still_requires_a_session(client):
    # Trace: T-037
    assert client.get("/api/v1/auth/me").status_code == 401
