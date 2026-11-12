"""
Reliability, findings 1 and 17 (error handling, data integrity):
- Finding 1: Silent suppression of JWT decoding exceptions and fallback to unauthenticated request body.
- Finding 17: Client-supplied user_id and author_name in body must never be trusted.

Reaction: fast failure with 401 for missing/invalid tokens, warning in log, and author identity
derived strictly from verified JWT claims and database lookup (no impersonation).
"""

import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Comment, Review, User
from src.api.main import app
from src.api.routers import auth as auth_router
from src.api.routers import comments as comments_router
from src.api.services.auth import create_access_token

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

URL = "/api/v1/comments"
LOGGER_NAME = "src.api.routers.comments"
REVIEW_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
ALICE_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
VICTIM_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    db.query(Comment).delete()
    db.query(Review).delete()
    db.query(User).delete()

    alice = User(
        user_id=ALICE_ID,
        email="alice@example.com",
        nickname="AliceReal",
        password_hash="fakehash",
        role="user",
        email_verified=True,
        status="active",
    )
    victim = User(
        user_id=VICTIM_ID,
        email="victim@example.com",
        nickname="VictimUser",
        password_hash="fakehash",
        role="user",
        email_verified=True,
        status="active",
    )
    review = Review(
        review_id=REVIEW_ID,
        user_id=VICTIM_ID,
        content_id=uuid.uuid4(),
        rating=8,
        review_text="Sample review text",
    )
    db.add_all([alice, victim, review])
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
    app.dependency_overrides[auth_router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_post_comment_without_token_is_rejected_even_with_user_id_in_body(client, db_session):
    """
    Finding 1: A guest cannot impersonate another user simply by passing their user_id in the JSON body.
    """
    payload = {
        "review_id": str(REVIEW_ID),
        "user_id": str(VICTIM_ID),
        "author_name": "VictimUser",
        "text": "Fake comment from victim",
    }
    response = client.post(URL, json=payload)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
    assert db_session.query(Comment).count() == 0


def test_post_comment_with_invalid_jwt_token_logs_warning_and_returns_401(client, caplog):
    """
    Finding 1: Invalid/malformed JWT token is not silently swallowed; emits warning log and returns 401 INVALID_TOKEN.
    """
    payload = {
        "review_id": str(REVIEW_ID),
        "text": "Comment with bad token",
    }
    headers = {"Authorization": "Bearer not-a-valid-jwt-token"}

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        response = client.post(URL, json=payload, headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
    assert "Invalid access token provided for comment" in caplog.text


def test_comment_author_is_derived_from_jwt_token_ignoring_body_fields(client, db_session):
    """
    Finding 17: When Alice is authenticated, any user_id or author_name in request body is ignored.
    """
    token = create_access_token(data={"sub": str(ALICE_ID), "role": "user"})
    payload = {
        "review_id": str(REVIEW_ID),
        "user_id": str(VICTIM_ID),
        "author_name": "SpoofedVictim",
        "text": "Authentic comment by Alice",
    }
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(URL, json=payload, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == str(ALICE_ID)
    assert data["author_name"] == "AliceReal"

    saved = db_session.query(Comment).one()
    assert saved.user_id == ALICE_ID
    assert saved.author_name == "AliceReal"


def test_comment_with_token_for_deleted_user_returns_user_not_found(client, db_session):
    """
    Finding 17: Valid token for a user that no longer exists in DB fails safely with 401 USER_NOT_FOUND.
    """
    ghost_user_id = uuid.uuid4()
    token = create_access_token(data={"sub": str(ghost_user_id), "role": "user"})
    payload = {
        "review_id": str(REVIEW_ID),
        "text": "Comment by a ghost account",
    }
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(URL, json=payload, headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"
    assert db_session.query(Comment).count() == 0
