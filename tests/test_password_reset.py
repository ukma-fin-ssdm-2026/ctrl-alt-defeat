"""Forgot password (T-052): reset link by email, one hour lifetime, sessions end, 8+ characters."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import User
from src.api.main import app
from src.api.routers import auth as auth_router
from src.api.services.auth import create_access_token, hash_password, hash_reset_token, password_reset_expired
from src.api.services.email import password_reset_link
from src.api.services.rate_limit import password_reset_limiter

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)
OLD_PASSWORD = "old-pass"
NEW_PASSWORD = "brand-new-pass"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    engine_test.dispose()


@pytest.fixture(autouse=True)
def no_seed_accounts(monkeypatch):
    for name in ("SEED_ADMIN_PASSWORD", "SEED_USER_PASSWORD", "SEED_ADMIN_EMAIL", "SEED_USER_EMAIL"):
        monkeypatch.delenv(name, raising=False)


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
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(auth_router, "send_password_reset_email", lambda *args: calls.append(args))
    return calls


@pytest.fixture
def client(db_session, sent):
    def override_get_db():
        yield db_session

    app.dependency_overrides[auth_router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(db, email="viewer@example.com", verified=True):
    user = User(
        user_id=uuid.uuid4(),
        email=email,
        password_hash=hash_password(OLD_PASSWORD),  # 8 characters were not required before
        nickname=email.split("@")[0],
        role="user",
        email_verified=verified,
        status="active" if verified else "pending",
    )
    db.add(user)
    db.commit()
    return user


def forgot(client, email="viewer@example.com"):
    return client.post("/api/v1/auth/forgot-password", json={"email": email})


def reset(client, token, password=NEW_PASSWORD):
    return client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": password})


def login(client, password, email="viewer@example.com"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_reset_link_sets_a_new_password_and_ends_sessions(client, db_session, sent):
    # Trace: T-052
    user = make_user(db_session)
    old_session = create_access_token({"sub": str(user.user_id), "ver": 0})
    assert login(client, OLD_PASSWORD).status_code == 200  # an old shorter password still logs in

    assert forgot(client, " Viewer@Example.com ").status_code == 202
    ((to, nickname, token),) = sent
    assert to == "viewer@example.com" and nickname == "viewer"
    db_session.refresh(user)
    assert user.password_reset_token == hash_reset_token(token) != token  # only the hash is stored

    response = reset(client, token)

    assert response.status_code == 200
    assert login(client, OLD_PASSWORD).status_code == 401
    assert login(client, NEW_PASSWORD).status_code == 200
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_session}"})
    assert me.json()["error"]["code"] == "TOKEN_REVOKED"
    # The link works once
    assert reset(client, token, "another-pass").json()["error"]["code"] == "INVALID_RESET_TOKEN"


def test_answer_is_the_same_for_unknown_email(client, db_session, sent):
    # Trace: T-052
    make_user(db_session)
    known, unknown = forgot(client), forgot(client, "nobody@example.com")
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(sent) == 1


def test_reset_link_expires_after_an_hour(client, db_session, sent):
    # Trace: T-052
    user = make_user(db_session)
    forgot(client)
    user.password_reset_sent_at = datetime.now(timezone.utc) - timedelta(minutes=61)
    db_session.commit()

    response = reset(client, sent[0][2])

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "RESET_TOKEN_EXPIRED"
    now = datetime.now(timezone.utc)
    assert password_reset_expired(None)
    assert not password_reset_expired(now - timedelta(minutes=59), now)


def test_new_password_needs_eight_characters(client, db_session, sent):
    # Trace: T-052
    make_user(db_session)
    forgot(client)

    assert reset(client, sent[0][2], "short7c").status_code == 422
    assert reset(client, "made-up-token").json()["error"]["code"] == "INVALID_RESET_TOKEN"


def test_reset_confirms_a_pending_account(client, db_session, sent):
    # Trace: T-052
    user = make_user(db_session, verified=False)
    forgot(client)

    assert reset(client, sent[0][2]).status_code == 200
    db_session.refresh(user)
    assert user.email_verified is True and user.status == "active"


def test_reset_emails_are_limited(client, db_session, sent, monkeypatch):
    # Trace: T-052
    user = make_user(db_session)
    forgot(client)
    forgot(client)
    assert len(sent) == 1  # the second request came within the cooldown
    user.password_reset_sent_at = datetime.now(timezone.utc) - timedelta(minutes=2)
    db_session.commit()
    forgot(client)
    assert len(sent) == 2

    monkeypatch.setattr(password_reset_limiter, "max_failures", 3)
    blocked = forgot(client)
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"


def test_seed_account_gets_no_reset_link(client, db_session, sent, monkeypatch):
    # Trace: T-052
    monkeypatch.setenv("SEED_USER_EMAIL", "viewer@example.com")
    monkeypatch.setenv("SEED_USER_PASSWORD", "demo-pass")
    make_user(db_session)

    assert forgot(client).status_code == 202
    assert sent == []


def test_registration_and_password_change_need_eight_characters(client, db_session):
    # Trace: T-052
    response = client.post(
        "/api/v1/auth/register", json={"email": "short@example.com", "nickname": "short", "password": "1234567"}
    )
    assert response.status_code == 422
    user = make_user(db_session)
    token = create_access_token({"sub": str(user.user_id), "ver": 0})
    change = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": OLD_PASSWORD, "new_password": "1234567"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change.status_code == 422


def test_reset_link_points_to_the_site(monkeypatch):
    # Trace: T-052
    monkeypatch.setenv("APP_BASE_URL", "https://example.org/")
    assert password_reset_link("a b") == "https://example.org/reset-password?token=a+b"
