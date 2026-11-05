"""Account self-service: change password and delete the account (profile page)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Ban, Comment, Rating, Review, User, WatchedItem, WatchlistItem
from src.api.main import app
from src.api.routers import auth as auth_router
from src.api.services.auth import create_access_token, hash_password, verify_password

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)
MOVIE = uuid.UUID("11111111-1111-4111-8111-111111111111")
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
    for model in (Comment, Ban, Rating, Review, WatchedItem, WatchlistItem, User):
        db.query(model).delete()
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


def make_user(db, nickname, role="user", email=None):
    user = User(
        user_id=uuid.uuid4(),
        email=email or f"{nickname}@example.com",
        password_hash=hash_password(PASSWORD),
        nickname=nickname,
        role=role,
        email_verified=True,
        status="active",
    )
    db.add(user)
    db.commit()
    return user


def auth(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id)})}"}


def delete_me(client, user, password=PASSWORD):
    return client.request("DELETE", "/api/v1/auth/me", json={"password": password}, headers=auth(user))


def test_change_password_with_the_current_one(client, db_session):
    user = make_user(db_session, "viewer")

    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "NewSecret456"},
        headers=auth(user),
    )

    assert response.status_code == 200
    db_session.refresh(user)
    assert verify_password("NewSecret456", user.password_hash)
    login = client.post("/api/v1/auth/login", json={"email": "viewer@example.com", "password": "NewSecret456"})
    assert login.status_code == 200


@pytest.mark.parametrize(
    "body, status, code",
    [
        ({"current_password": "wrong", "new_password": "NewSecret456"}, 400, "INVALID_PASSWORD"),
        ({"current_password": PASSWORD, "new_password": PASSWORD}, 400, "SAME_PASSWORD"),
        ({"current_password": PASSWORD, "new_password": "short"}, 422, "VALIDATION_ERROR"),
    ],
)
def test_change_password_rejections(client, db_session, body, status, code):
    user = make_user(db_session, "viewer")

    response = client.post("/api/v1/auth/change-password", json=body, headers=auth(user))

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    db_session.refresh(user)
    assert verify_password(PASSWORD, user.password_hash)


def test_delete_account_removes_the_user_and_their_data(client, db_session):
    user = make_user(db_session, "leaving")
    other = make_user(db_session, "stays")
    review = Review(user_id=user.user_id, content_id=MOVIE, rating=8, review_text="A really strong film")
    others_review = Review(user_id=other.user_id, content_id=MOVIE, rating=6)
    db_session.add_all([review, others_review])
    db_session.commit()
    db_session.add_all(
        [
            Comment(
                review_id=review.review_id, user_id=other.user_id, author_name="stays", text="Reply under my review"
            ),
            Comment(review_id=others_review.review_id, user_id=user.user_id, author_name="leaving", text="My comment"),
            Comment(review_id=others_review.review_id, user_id=other.user_id, author_name="stays", text="Stays here"),
            Rating(user_id=user.user_id, content_id=MOVIE, score=8),
            WatchedItem(user_id=user.user_id, content_id=MOVIE),
            WatchlistItem(user_id=user.user_id, content_id=MOVIE, added_at=review.created_at),
            Ban(user_id=user.user_id, ban_type="permanent", starts_at=review.created_at, is_active=False),
        ]
    )
    db_session.commit()

    response = delete_me(client, user)

    assert response.status_code == 204
    assert "access_token" in response.headers.get("set-cookie", "")
    assert db_session.query(User).filter(User.user_id == user.user_id).first() is None
    for model in (Review, Rating, WatchedItem, WatchlistItem, Ban):
        assert db_session.query(model).filter(model.user_id == user.user_id).count() == 0
    assert [c.text for c in db_session.query(Comment).all()] == ["Stays here"]
    assert db_session.query(Review).count() == 1
    # The old token no longer works
    assert client.get("/api/v1/auth/me", headers=auth(user)).status_code == 401


def test_delete_account_needs_the_right_password(client, db_session):
    user = make_user(db_session, "viewer")

    response = delete_me(client, user, password="wrong")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PASSWORD"
    assert db_session.query(User).count() == 1


def test_admin_account_cannot_be_deleted_from_the_profile(client, db_session):
    admin = make_user(db_session, "moderator", role="admin")

    response = delete_me(client, admin)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ADMIN_ACCOUNT"


def test_banned_admin_reference_is_cleared(client, db_session):
    user = make_user(db_session, "viewer")
    admin = make_user(db_session, "moderator", role="admin")
    victim = make_user(db_session, "victim")
    db_session.add(
        Ban(user_id=victim.user_id, admin_id=user.user_id, ban_type="permanent", starts_at=victim.created_at)
    )
    db_session.commit()

    assert delete_me(client, user).status_code == 204
    assert db_session.query(Ban).one().admin_id is None
    assert admin is not None


def test_public_demo_account_is_protected(client, db_session, monkeypatch):
    monkeypatch.setenv("SEED_USER_PASSWORD", PASSWORD)
    user = make_user(db_session, "cinema_fan", email="user@example.com")

    deleted = delete_me(client, user)
    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "Hijacked123"},
        headers=auth(user),
    )

    assert deleted.status_code == changed.status_code == 403
    assert deleted.json()["error"]["code"] == "SEED_ACCOUNT_LOCKED"
    db_session.refresh(user)
    assert verify_password(PASSWORD, user.password_hash)


def test_account_endpoints_require_login(client):
    assert (
        client.post(
            "/api/v1/auth/change-password", json={"current_password": "a", "new_password": "bbbbbb"}
        ).status_code
        == 401
    )
    assert client.request("DELETE", "/api/v1/auth/me", json={"password": "a"}).status_code == 401
