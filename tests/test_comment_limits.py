"""Comment spam protection (T-051): comments per user and minute / hour, no identical comment twice in a row."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Comment, Content, Review, User
from src.api.main import app
from src.api.routers import comments as comments_router
from src.api.services.auth import create_access_token, hash_password
from src.api.services.rate_limit import comment_hour_limiter, comment_minute_limiter

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)
MOVIE = uuid.UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    engine_test.dispose()


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    for model in (Comment, Review, Content, User):
        db.query(model).delete()
    db.add(Content(id=1, content_id=MOVIE, title="Дюна", category="Movie", genre="Фантастика", year=2024))
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

    app.dependency_overrides[comments_router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(db, nickname):
    user = User(
        user_id=uuid.uuid4(),
        email=f"{nickname}@example.com",
        password_hash=hash_password("Password123"),
        nickname=nickname,
        role="user",
        email_verified=True,
        status="active",
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def review(db_session):
    author = make_user(db_session, "author")
    item = Review(user_id=author.user_id, content_id=MOVIE, rating=9)
    db_session.add(item)
    db_session.commit()
    return item


def post(client, user, review, text):
    token = create_access_token({"sub": str(user.user_id), "ver": 0})
    return client.post(
        "/api/v1/comments",
        json={"review_id": str(review.review_id), "text": text},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_comments_per_minute_are_limited_per_user(client, db_session, review):
    # Trace: T-051
    spammer, other = make_user(db_session, "spammer"), make_user(db_session, "other")
    for number in range(comment_minute_limiter.max_failures):
        assert post(client, spammer, review, f"Comment number {number}").status_code == 201

    blocked = post(client, spammer, review, "One more")

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
    assert 1 <= int(blocked.headers["Retry-After"]) <= 60
    # Other users are not affected
    assert post(client, other, review, "My own opinion").status_code == 201


def test_comments_per_hour_are_limited(client, db_session, review, monkeypatch):
    # Trace: T-051
    monkeypatch.setattr(comment_hour_limiter, "max_failures", 2)
    user = make_user(db_session, "talker")
    assert post(client, user, review, "First").status_code == 201
    assert post(client, user, review, "Second").status_code == 201

    assert post(client, user, review, "Third").status_code == 429


def test_same_comment_twice_in_a_row_is_rejected(client, db_session, review):
    # Trace: T-051
    user = make_user(db_session, "clicker")
    assert post(client, user, review, "Great review!").status_code == 201

    duplicate = post(client, user, review, "  great REVIEW!  ")

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_COMMENT"
    assert post(client, user, review, "Something else").status_code == 201
    assert post(client, user, review, "Great review!").status_code == 201  # not in a row any more
    assert db_session.query(Comment).count() == 3
