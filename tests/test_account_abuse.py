"""
One mailbox, one account (T-051): canonical emails, case-insensitive nicknames, abandoned registrations,
limits on new accounts and activation emails, and no account deletion while banned.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base, backfill_canonical_emails, upgrade_user_columns
from src.api.db.models import Ban, User
from src.api.main import app
from src.api.routers import auth as auth_router
from src.api.services.auth import create_access_token, hash_password
from src.api.services.email_identity import canonical_email, is_disposable_email
from src.api.services.rate_limit import register_limiter, resend_limiter

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)
PASSWORD = "Password123"


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
    for model in (Ban, User):
        db.query(model).delete()
    db.commit()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(auth_router, "send_verification_email", lambda *args: calls.append(args))
    return calls


@pytest.fixture
def client(db_session, sent):
    def override_get_db():
        yield db_session

    app.dependency_overrides[auth_router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register(client, email, nickname="viewer"):
    return client.post("/api/v1/auth/register", json={"email": email, "nickname": nickname, "password": PASSWORD})


def make_user(db, email="viewer@example.com", nickname="viewer", verified=True, sent_at=None):
    user = User(
        user_id=uuid.uuid4(),
        email=email,
        password_hash=hash_password(PASSWORD),
        nickname=nickname,
        role="user",
        email_verified=verified,
        status="active" if verified else "pending",
        verification_token=None if verified else "token-" + nickname,
        verification_sent_at=sent_at,
    )
    db.add(user)
    db.commit()
    return user


@pytest.mark.parametrize(
    "email, expected",
    [
        ("Na.Me+promo@GoogleMail.com", "name@gmail.com"),
        ("n.a.m.e@gmail.com", "name@gmail.com"),
        ("first.last+news@ukma.edu.ua", "first.last@ukma.edu.ua"),
        ("plain@example.com", "plain@example.com"),
        ("+only@example.com", "+only@example.com"),
        ("not-an-email", "not-an-email"),
    ],
)
def test_canonical_email(email, expected):
    # Trace: T-051
    assert canonical_email(email) == expected


def test_model_keeps_the_canonical_email_in_step(db_session):
    # Trace: T-051
    user = make_user(db_session, email="j.doe+films@gmail.com")
    assert user.email_canonical == "jdoe@gmail.com"
    user.email = "other@example.com"
    assert user.email_canonical == "other@example.com"


@pytest.mark.parametrize("alias", ["j.doe+second@gmail.com", "JDOE@googlemail.com", "jdoe+x@gmail.com"])
def test_same_mailbox_cannot_register_twice(client, db_session, alias):
    # Trace: T-051
    make_user(db_session, email="jdoe@gmail.com", nickname="first")

    response = register(client, alias, nickname="second")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"
    assert db_session.query(User).count() == 1


def test_nickname_is_unique_regardless_of_letter_case(client, db_session):
    # Trace: T-051
    make_user(db_session, nickname="Viewer")

    response = register(client, "new@example.com", nickname="vIEWER")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NICKNAME_ALREADY_EXISTS"


def test_abandoned_registration_frees_email_and_nickname(client, db_session, sent):
    # Trace: T-051
    long_ago = datetime.now(timezone.utc) - timedelta(days=3)
    make_user(db_session, email="owner@example.com", nickname="squatter", verified=False, sent_at=long_ago)

    response = register(client, "owner+real@example.com", nickname="Squatter")

    assert response.status_code == 201
    users = db_session.query(User).all()
    assert [(u.email, u.nickname) for u in users] == [("owner+real@example.com", "Squatter")]
    assert len(sent) == 1


def test_fresh_pending_registration_still_holds_the_email(client, db_session):
    # Trace: T-051
    make_user(db_session, email="owner@example.com", verified=False, sent_at=datetime.now(timezone.utc))

    assert register(client, "owner@example.com", nickname="another").status_code == 409


def test_new_accounts_per_address_are_limited(client, db_session, monkeypatch):
    # Trace: T-051
    monkeypatch.setattr(register_limiter, "max_failures", 2)
    assert register(client, "a@example.com", "a1").status_code == 201
    assert register(client, "b@example.com", "b1").status_code == 201

    blocked = register(client, "c@example.com", "c1")

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
    assert 1 <= int(blocked.headers["Retry-After"]) <= register_limiter.window_seconds
    assert db_session.query(User).count() == 2


def test_rejected_registration_does_not_use_the_limit(client, db_session, monkeypatch):
    # Trace: T-051
    monkeypatch.setattr(register_limiter, "max_failures", 1)
    make_user(db_session, email="taken@example.com", nickname="taken")
    assert register(client, "taken@example.com", "x1").status_code == 409

    assert register(client, "free@example.com", "free").status_code == 201


def test_resend_waits_between_emails_and_is_limited(client, db_session, sent, monkeypatch):
    # Trace: T-051
    user = make_user(db_session, email="wait@example.com", nickname="wait", verified=False, sent_at=None)
    resend = lambda: client.post("/api/v1/auth/resend-verification", json={"email": "wait@example.com"})  # noqa: E731

    assert resend().status_code == 202
    assert resend().status_code == 202
    assert len(sent) == 1  # the second request came within the cooldown
    db_session.refresh(user)
    user.verification_sent_at = datetime.now(timezone.utc) - timedelta(minutes=2)
    db_session.commit()
    assert resend().status_code == 202
    assert len(sent) == 2

    monkeypatch.setattr(resend_limiter, "max_failures", 3)
    blocked = resend()
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"


def test_banned_user_cannot_delete_the_account(client, db_session):
    # Trace: T-051
    user = make_user(db_session)
    db_session.add(Ban(user_id=user.user_id, ban_type="permanent", starts_at=datetime.now(timezone.utc)))
    db_session.commit()
    token = create_access_token({"sub": str(user.user_id), "ver": 0})

    response = client.request(
        "DELETE", "/api/v1/auth/me", json={"password": PASSWORD}, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_BANNED"
    assert db_session.query(User).count() == 1


def test_old_accounts_get_canonical_emails_on_startup():
    # Trace: T-051
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE users (user_id VARCHAR PRIMARY KEY, email VARCHAR, created_at DATETIME)"
        )
        connection.exec_driver_sql(
            "INSERT INTO users VALUES ('u1', 'j.doe@gmail.com', '2026-01-01'),"
            " ('u2', 'jdoe+x@gmail.com', '2026-02-01'), ('u3', 'other@example.com', '2026-03-01')"
        )
    upgrade_user_columns(engine)

    assert backfill_canonical_emails(engine) == 2
    assert backfill_canonical_emails(engine) == 0
    with engine.connect() as connection:
        rows = connection.exec_driver_sql("SELECT user_id, email_canonical FROM users ORDER BY user_id").fetchall()
        indexes = connection.exec_driver_sql("PRAGMA index_list('users')").fetchall()
    # The older account keeps the mailbox; the later alias stays empty, so the unique index can be created
    assert [tuple(row) for row in rows] == [("u1", "jdoe@gmail.com"), ("u2", None), ("u3", "other@example.com")]
    assert any(index[1] == "ix_users_email_canonical" and index[2] == 1 for index in indexes)
    engine.dispose()


@pytest.mark.parametrize("email", ["x@mailinator.com", "Y@YOPMAIL.COM", "z@inbox.guerrillamail.com"])
def test_throwaway_mailboxes_cannot_register(client, db_session, email):
    # Trace: T-051
    response = register(client, email, nickname="temp")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DISPOSABLE_EMAIL"
    assert db_session.query(User).count() == 0


def test_disposable_check_keeps_regular_mailboxes():
    # Trace: T-051
    assert is_disposable_email("sub.mailinator.com@gmail.com") is False
    assert is_disposable_email("student@ukma.edu.ua") is False
    assert is_disposable_email("nobody") is False
