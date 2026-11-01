"""API tests for threaded comments under reviews (FR-011, US-010)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Comment, Review
from src.api.main import app
from src.api.routers import comments as comments_router
from src.api.routers import reviews as reviews_router

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

USER = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
OTHER_USER = "9b2f6a3e-1c4d-4e8f-a1b2-3c4d5e6f7a8b"
REVIEW_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
OTHER_REVIEW_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")


URL = "/api/v1/comments"


def get_thread(client, review_id=REVIEW_ID):
    return client.get(URL, params={"review_id": str(review_id)})


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    db.query(Comment).delete()
    db.query(Review).delete()
    for review_id in (REVIEW_ID, OTHER_REVIEW_ID):
        db.add(
            Review(
                review_id=review_id,
                user_id=uuid.UUID(OTHER_USER),
                content_id=uuid.uuid4(),
                rating=9,
                review_text="A thoughtful review of the movie",
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

    app.dependency_overrides[comments_router.get_db] = override_get_db
    app.dependency_overrides[reviews_router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def post(client, text="I totally agree with you", parent_id=None, review_id=REVIEW_ID, **extra):
    payload = {"review_id": str(review_id), "user_id": USER, "author_name": "admin", "text": text, **extra}
    if parent_id:
        payload["parent_id"] = parent_id
    return client.post(URL, json=payload)


def test_create_comment_shows_author_and_time(client):
    # Trace: T-029
    response = post(client)

    assert response.status_code == 201
    body = response.json()
    assert body["author_name"] == "admin"
    assert body["text"] == "I totally agree with you"
    assert body["created_at"]
    assert body["depth"] == 0
    assert body["parent_id"] is None


def test_created_comment_appears_under_the_review(client):
    # Trace: T-029
    post(client, text="First comment here")

    body = get_thread(client).json()

    assert body["total"] == 1
    assert [item["text"] for item in body["items"]] == ["First comment here"]


def test_replies_form_a_multi_level_thread(client):
    # Trace: T-029
    root = post(client, text="Root comment").json()
    reply = post(client, text="Reply level 1", parent_id=root["comment_id"]).json()
    post(client, text="Reply level 2", parent_id=reply["comment_id"])
    post(client, text="Second root")

    body = get_thread(client).json()

    assert body["total"] == 4
    assert [item["text"] for item in body["items"]] == ["Root comment", "Second root"]
    level1 = body["items"][0]["replies"]
    assert [c["text"] for c in level1] == ["Reply level 1"]
    assert level1[0]["depth"] == 1
    assert [c["text"] for c in level1[0]["replies"]] == ["Reply level 2"]
    assert level1[0]["replies"][0]["depth"] == 2


def test_reply_depth_is_limited(client):
    # Trace: T-029
    parent_id = None
    for level in range(comments_router.MAX_COMMENT_DEPTH + 1):
        response = post(client, text=f"Level {level} comment", parent_id=parent_id)
        assert response.status_code == 201
        parent_id = response.json()["comment_id"]

    response = post(client, text="Too deep reply", parent_id=parent_id)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MAX_DEPTH_EXCEEDED"


def test_reply_to_comment_from_another_review_is_rejected(client):
    # Trace: T-029
    foreign = post(client, text="Comment on other review", review_id=OTHER_REVIEW_ID).json()

    response = post(client, text="Reply in wrong thread", parent_id=foreign["comment_id"])

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PARENT_COMMENT_NOT_FOUND"


def test_reply_to_missing_comment_is_rejected(client):
    # Trace: T-029
    response = post(client, text="Reply to nothing", parent_id=str(uuid.uuid4()))

    assert response.status_code == 404


@pytest.mark.parametrize("text", ["", "    "])
def test_empty_comment_is_rejected(client, db_session, text):
    # Trace: T-030
    response = post(client, text=text)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "Comment text cannot be empty" in error["details"][0]["message"]
    assert db_session.query(Comment).count() == 0


def test_comment_without_authentication_is_rejected(client, db_session):
    # Trace: T-031
    response = client.post(URL, json={"review_id": str(REVIEW_ID), "author_name": "guest", "text": "Anonymous comment"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
    assert db_session.query(Comment).count() == 0


@pytest.mark.parametrize(
    "text",
    ["<script>alert('xss')</script>", "Nice one <img src=x onerror=alert(1)>", "javascript:alert(1)"],
)
def test_xss_in_comment_is_rejected(client, db_session, text):
    # Trace: T-032
    response = post(client, text=text)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "POLICY_VIOLATION"
    assert "html_markup" in response.json()["error"]["message"]
    assert db_session.query(Comment).count() == 0


def test_comments_for_missing_review_return_404(client):
    # Trace: T-029
    missing = uuid.uuid4()

    assert get_thread(client, missing).status_code == 404
    assert post(client, review_id=missing).status_code == 404


def test_review_without_comments_returns_empty_thread(client):
    # Trace: T-029
    assert get_thread(client).json() == {"items": [], "total": 0}


def test_deleting_review_removes_its_comments(client, db_session):
    # Trace: T-029
    root = post(client, text="Will be removed").json()
    post(client, text="Reply removed too", parent_id=root["comment_id"])
    post(client, text="Other thread stays", review_id=OTHER_REVIEW_ID)

    assert client.delete(f"/api/v1/reviews/{REVIEW_ID}").status_code == 204

    assert db_session.query(Comment).count() == 1
    assert db_session.query(Comment).one().text == "Other thread stays"


@pytest.mark.parametrize("review_id", [None, "../../admin", "not-a-uuid"])
def test_comments_require_a_valid_review_id(client, review_id):
    # Trace: T-029
    params = {} if review_id is None else {"review_id": review_id}
    assert client.get(URL, params=params).status_code == 422
    body = {"user_id": USER, "author_name": "admin", "text": "Some text"}
    if review_id is not None:
        body["review_id"] = review_id
    assert client.post(URL, json=body).status_code == 422


def test_comments_get_db_generator():
    # Trace: T-029
    generator = comments_router.get_db()
    assert next(generator) is not None
    generator.close()


def test_create_comment_with_authenticated_jwt_token(client, db_session):
    # Trace: T-029
    from src.api.db.models import User
    from src.api.services.auth import create_access_token

    user_id = uuid.uuid4()
    db_session.add(
        User(
            user_id=user_id,
            email="verified_commenter@example.com",
            nickname="SuperCommenter",
            password_hash="fakehash",
            role="user",
            email_verified=True,
            status="active",
        )
    )
    db_session.commit()
    token = create_access_token(data={"sub": str(user_id), "role": "user"})

    response = client.post(
        URL,
        json={"review_id": str(REVIEW_ID), "text": "Comment using real JWT auth"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["author_name"] == "SuperCommenter"
    assert data["user_id"] == str(user_id)
    assert data["text"] == "Comment using real JWT auth"
