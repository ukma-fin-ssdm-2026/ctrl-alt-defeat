"""
Hardening after the project review: login attempt limit, activation link lifetime, sessions ending after
a password change, one token check for comments, security headers and the compact catalog list.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base, upgrade_user_columns
from src.api.db.models import Comment, Content, Review, User
from src.api.main import app
from src.api.routers import auth as auth_router
from src.api.routers import comments as comments_router
from src.api.routers import movies as movies_router
from src.api.security_headers import CONTENT_SECURITY_POLICY
from src.api.services.auth import create_access_token, hash_password, verification_expired
from src.api.services.rate_limit import AttemptLimiter, login_limiter

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)
PASSWORD = "Password123"
MOVIE = uuid.UUID("11111111-1111-4111-8111-111111111111")


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
    for model in (Comment, Review, Content, User):
        db.query(model).delete()
    db.add(
        Content(
            id=1,
            content_id=MOVIE,
            title="Дюна",
            title_en="Dune",
            category="Movie",
            genre="Фантастика",
            year=2024,
            description="Пол Атрід об'єднується з фременами.",
            description_en="Paul Atreides unites with the Fremen.",
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

    for router in (auth_router, comments_router, movies_router):
        app.dependency_overrides[router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(db, nickname="viewer"):
    user = User(
        user_id=uuid.uuid4(),
        email=f"{nickname}@example.com",
        password_hash=hash_password(PASSWORD),
        nickname=nickname,
        role="user",
        email_verified=True,
        status="active",
    )
    db.add(user)
    db.commit()
    return user


def login(client, email="viewer@example.com", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


# Login attempt limit


def test_limiter_counts_failures_in_a_sliding_window():
    # Trace: T-046
    now = [0.0]
    limiter = AttemptLimiter(max_failures=3, window_seconds=60, clock=lambda: now[0])
    for _ in range(3):
        assert limiter.retry_after("1.2.3.4") is None
        limiter.record_failure("1.2.3.4")
        now[0] += 10

    # The oldest failure (t=0) leaves the window at t=60
    assert limiter.retry_after("1.2.3.4") == 30
    assert limiter.retry_after("5.6.7.8") is None
    now[0] = 60
    assert limiter.retry_after("1.2.3.4") is None
    limiter.record_failure("1.2.3.4")
    limiter.reset("1.2.3.4")
    assert limiter.retry_after("1.2.3.4") is None


def test_login_is_blocked_after_too_many_wrong_passwords(client, db_session):
    # Trace: T-046
    make_user(db_session)
    for _ in range(login_limiter.max_failures):
        assert login(client, password="wrong-password").status_code == 401

    blocked = login(client)

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
    assert 1 <= int(blocked.headers["Retry-After"]) <= login_limiter.window_seconds
    # The limit is per address and ends with the window; a successful login clears the record
    login_limiter.clear()
    assert login(client).status_code == 200
    assert login(client, password="wrong-password").status_code == 401
    assert login(client).status_code == 200


# Activation link lifetime


def test_activation_link_expires_after_a_day(client, db_session, monkeypatch):
    # Trace: T-046
    sent = []
    monkeypatch.setattr(auth_router, "send_verification_email", lambda *args: sent.append(args))
    client.post("/api/v1/auth/register", json={"email": "new@example.com", "nickname": "newbie", "password": PASSWORD})
    user = db_session.query(User).filter(User.email == "new@example.com").one()
    assert user.verification_sent_at is not None
    user.verification_sent_at = datetime.now(timezone.utc) - timedelta(hours=25)
    db_session.commit()

    expired = client.get("/api/v1/auth/verify", params={"token": sent[0][2]})

    assert expired.status_code == 400
    assert expired.json()["error"]["code"] == "VERIFICATION_TOKEN_EXPIRED"
    # A new link works again
    client.post("/api/v1/auth/resend-verification", json={"email": "new@example.com"})
    assert client.get("/api/v1/auth/verify", params={"token": sent[1][2]}).status_code == 200


def test_expiry_check_handles_old_links_and_naive_dates():
    # Trace: T-046
    now = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)
    assert verification_expired(None, now) is False  # sent before the check existed
    assert verification_expired(datetime(2026, 11, 13, 1), now) is False  # SQLite: naive UTC
    assert verification_expired(datetime(2026, 11, 12, 11, tzinfo=timezone.utc), now) is True


# Sessions end after a password change


def test_password_change_ends_other_sessions(client, db_session):
    # Trace: T-046
    make_user(db_session)
    other_device = login(client).json()["access_token"]
    this_device = login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {this_device}"}

    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "NewSecret456"},
        headers=headers,
    )

    assert changed.status_code == 200
    old = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {other_device}"})
    assert old.status_code == 401
    assert old.json()["error"]["code"] == "TOKEN_REVOKED"
    # This device continues with the new session cookie
    new_cookie = changed.cookies.get("access_token")
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_cookie}"}).status_code == 200


def test_comments_use_the_same_token_check(client, db_session):
    # Trace: T-046
    user = make_user(db_session)
    review = Review(user_id=user.user_id, content_id=MOVIE, rating=8, review_text="Дуже сильне кіно, раджу")
    db_session.add(review)
    user.token_version = 1  # the password was changed after this token was issued
    db_session.commit()
    outdated = create_access_token({"sub": str(user.user_id), "ver": 0})
    body = {"review_id": str(review.review_id), "text": "Згоден!"}

    response = client.post("/api/v1/comments", json=body, headers={"Authorization": f"Bearer {outdated}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_REVOKED"
    assert client.post("/api/v1/comments", json=body).json()["error"]["code"] == "AUTH_REQUIRED"
    current = create_access_token({"sub": str(user.user_id), "ver": 1})
    assert client.post("/api/v1/comments", json=body, headers={"Authorization": f"Bearer {current}"}).status_code == 201


def test_old_users_table_gets_the_new_columns():
    # Trace: T-046
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE users (user_id VARCHAR PRIMARY KEY, email VARCHAR)")
        connection.exec_driver_sql("INSERT INTO users VALUES ('u1', 'old@example.com')")

    assert upgrade_user_columns(engine) == ["verification_sent_at", "token_version"]
    assert upgrade_user_columns(engine) == []
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    assert {"verification_sent_at", "token_version"} <= columns
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT token_version FROM users").scalar() == 0
    engine.dispose()


# Security headers


def test_security_headers_on_pages_and_errors(client):
    # Trace: T-047
    for response in (client.get("/health/live"), client.get("/api/v1/movies/missing")):
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert response.headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert "frame-ancestors 'none'" in CONTENT_SECURITY_POLICY
    assert "https://image.tmdb.org" in CONTENT_SECURITY_POLICY


def test_api_docs_keep_working_without_the_csp(client):
    # Trace: T-047
    # Swagger UI loads its scripts from a CDN with inline code: the CSP would block it
    docs = client.get("/api-docs")
    assert docs.status_code == 200
    assert "Content-Security-Policy" not in docs.headers
    assert docs.headers["X-Content-Type-Options"] == "nosniff"


# Compact catalog list


def test_compact_catalog_leaves_out_the_synopses(client):
    # Trace: T-048
    full = client.get("/api/v1/movies").json()["items"][0]
    compact = client.get("/api/v1/movies", params={"compact": "true"}).json()["items"][0]

    assert full["description"].startswith("Пол Атрід")
    assert compact["description"] is None and compact["description_en"] is None
    assert {key: value for key, value in compact.items() if not key.startswith("description")} == {
        key: value for key, value in full.items() if not key.startswith("description")
    }
    # The page of the title still gets everything
    details = client.get(f"/api/v1/movies/{MOVIE}").json()
    assert details["description_en"] == "Paul Atreides unites with the Fremen."


def test_large_answers_are_compressed(client, db_session):
    # Trace: T-048
    for number in range(2, 40):
        db_session.add(Content(id=number, content_id=uuid.uuid4(), title=f"Фільм {number}", genre="Драма", year=2020))
    db_session.commit()

    response = client.get("/api/v1/movies", params={"limit": 100}, headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers["Content-Encoding"] == "gzip"
