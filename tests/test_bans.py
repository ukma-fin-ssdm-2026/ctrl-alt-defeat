"""Account bans (FR-009, US-006): admin endpoints, temporary/permanent bans and what a ban blocks."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Ban, Comment, Content, Review, User, WatchedItem
from src.api.main import app
from src.api.routers import admin as admin_router
from src.api.routers import auth as auth_router
from src.api.routers import comments as comments_router
from src.api.routers import reviews as reviews_router
from src.api.routers import watchlist as watchlist_router
from src.api.services.auth import create_access_token, hash_password
from src.api.services.bans import active_ban, ban_message

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

BANS = "/api/v1/admin/bans"
USERS = "/api/v1/admin/users"
MOVIE = uuid.UUID("11111111-1111-4111-8111-111111111111")


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    engine_test.dispose()


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    for model in (Comment, Ban, Review, WatchedItem, User, Content):
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

    for router in (admin_router, auth_router, comments_router, reviews_router, watchlist_router):
        app.dependency_overrides[router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(db, nickname, role="user"):
    user = User(
        user_id=uuid.uuid4(),
        email=f"{nickname}@example.com",
        password_hash=hash_password("Password123!"),
        nickname=nickname,
        role=role,
        email_verified=True,
        status="active",
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def admin(db_session):
    return make_user(db_session, "moderator", role="admin")


@pytest.fixture
def viewer(db_session):
    user = make_user(db_session, "spammer")
    db_session.add(WatchedItem(user_id=user.user_id, content_id=MOVIE))
    db_session.commit()
    return user


def auth(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id)})}"}


def ban(client, admin, user, **body):
    body = {"user_id": str(user.user_id), "ban_type": "temporary", "duration_days": 7, **body}
    return client.post(BANS, json=body, headers=auth(admin))


def review(client, user):
    return client.post(
        "/api/v1/reviews",
        json={"content_id": str(MOVIE), "rating": 9, "review_text": "A really strong and moving film"},
        headers=auth(user),
    )


def test_admin_bans_temporarily_and_the_user_cannot_review(client, admin, viewer):
    # Trace: T-036
    response = ban(client, admin, viewer, reason="Spoilers in every review")

    assert response.status_code == 201
    body = response.json()
    assert body["ban_type"] == "temporary"
    assert body["reason"] == "Spoilers in every review"
    ends_at = datetime.fromisoformat(body["ends_at"])
    assert timedelta(days=6, hours=23) < ends_at - datetime.now(UTC) <= timedelta(days=7)

    blocked = review(client, viewer)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "ACCOUNT_BANNED"
    assert "banned until" in blocked.json()["error"]["message"]
    assert "Spoilers in every review" in blocked.json()["error"]["message"]


def test_permanent_ban_has_no_end(client, admin, viewer):
    # Trace: T-036
    body = ban(client, admin, viewer, ban_type="permanent", duration_days=None).json()

    assert body["ban_type"] == "permanent"
    assert body["ends_at"] is None
    assert "permanently banned" in review(client, viewer).json()["error"]["message"]


def test_banned_user_sees_the_ban_and_keeps_other_features(client, admin, viewer):
    # Trace: T-036
    ban(client, admin, viewer, reason="Insults")

    me = client.get("/api/v1/auth/me", headers=auth(viewer))
    assert me.status_code == 200
    assert me.json()["ban"]["ban_type"] == "temporary"
    assert me.json()["ban"]["reason"] == "Insults"
    # Watchlist is not affected (FR-009: only reviews, ratings and comments)
    added = client.post("/api/v1/watchlist", json={"content_id": str(MOVIE)}, headers=auth(viewer))
    assert added.status_code == 201


def test_banned_user_cannot_edit_a_review_or_comment(client, db_session, admin, viewer):
    # Trace: T-036
    review_id = review(client, viewer).json()["review_id"]
    ban(client, admin, viewer)

    edit = client.patch(f"/api/v1/reviews/{review_id}", json={"rating": 2}, headers=auth(viewer))
    comment = client.post("/api/v1/comments", json={"review_id": review_id, "text": "Still here"}, headers=auth(viewer))

    assert edit.status_code == 403
    assert comment.status_code == 403
    assert comment.json()["error"]["code"] == "ACCOUNT_BANNED"
    assert db_session.query(Comment).count() == 0


def test_expired_temporary_ban_is_no_longer_in_force(client, db_session, viewer):
    # Trace: T-036
    now = datetime.now(UTC)
    db_session.add(
        Ban(
            user_id=viewer.user_id,
            ban_type="temporary",
            starts_at=now - timedelta(days=8),
            ends_at=now - timedelta(days=1),
        )
    )
    db_session.commit()

    assert active_ban(db_session, viewer) is None
    assert review(client, viewer).status_code == 201


def test_unban_restores_reviews(client, admin, viewer):
    # Trace: T-036
    ban(client, admin, viewer, ban_type="permanent", duration_days=None)

    response = client.delete(BANS, params={"user_id": str(viewer.user_id)}, headers=auth(admin))

    assert response.status_code == 200
    assert client.get("/api/v1/auth/me", headers=auth(viewer)).json()["ban"] is None
    assert review(client, viewer).status_code == 201


def test_unban_of_a_user_without_ban_returns_404(client, admin, viewer):
    response = client.delete(BANS, params={"user_id": str(viewer.user_id)}, headers=auth(admin))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "BAN_NOT_FOUND"


def test_new_ban_replaces_the_previous_one_and_keeps_history(client, db_session, admin, viewer):
    ban(client, admin, viewer, duration_days=3)
    ban(client, admin, viewer, ban_type="permanent", duration_days=None)

    assert active_ban(db_session, viewer).ban_type == "permanent"
    history = db_session.query(Ban).filter(Ban.user_id == viewer.user_id).all()
    assert len(history) == 2
    assert sum(item.is_active for item in history) == 1
    assert {item.admin_id for item in history} == {admin.user_id}


def test_legacy_banned_status_counts_as_permanent_and_unban_clears_it(client, db_session, admin, viewer):
    viewer.status = "banned"
    db_session.commit()

    assert review(client, viewer).status_code == 403
    assert client.delete(BANS, params={"user_id": str(viewer.user_id)}, headers=auth(admin)).status_code == 200
    db_session.refresh(viewer)
    assert viewer.status == "active"


@pytest.mark.parametrize(
    "body, field",
    [
        ({"ban_type": "temporary", "duration_days": None}, "duration_days is required"),
        ({"ban_type": "permanent", "duration_days": 5}, "must not be set"),
        ({"ban_type": "temporary", "duration_days": 0}, "greater than or equal"),
        ({"ban_type": "temporary", "duration_days": 366}, "less than or equal"),
        ({"ban_type": "forever"}, "Input should be"),
        ({"reason": "x" * 501}, "at most 500"),
    ],
)
def test_invalid_ban_request_returns_422(client, admin, viewer, body, field):
    response = ban(client, admin, viewer, **body)

    assert response.status_code == 422
    assert field in str(response.json()["error"]["details"])


def test_admin_cannot_ban_self_or_another_admin(client, db_session, admin):
    other_admin = make_user(db_session, "second_admin", role="admin")

    myself = ban(client, admin, admin)
    other = ban(client, admin, other_admin)

    assert myself.json()["error"]["code"] == "CANNOT_BAN_SELF"
    assert other.json()["error"]["code"] == "CANNOT_BAN_ADMIN"


def test_ban_of_unknown_user_returns_404(client, admin):
    response = client.post(BANS, json={"user_id": str(uuid.uuid4()), "ban_type": "permanent"}, headers=auth(admin))

    assert response.status_code == 404


@pytest.mark.parametrize("method", ["get", "post", "delete"])
def test_only_admins_can_use_admin_endpoints(client, viewer, method):
    url = USERS if method == "get" else BANS
    kwargs = {"json": {"user_id": str(viewer.user_id), "ban_type": "permanent"}} if method == "post" else {}
    if method == "delete":
        kwargs = {"params": {"user_id": str(viewer.user_id)}}

    as_user = getattr(client, method)(url, headers=auth(viewer), **kwargs)
    as_guest = getattr(client, method)(url, **kwargs)

    assert as_user.status_code == 403
    assert as_guest.status_code == 401


def test_admin_lists_and_searches_users_with_their_ban(client, admin, viewer):
    ban(client, admin, viewer, reason="Spam")

    everyone = client.get(USERS, headers=auth(admin)).json()
    found = client.get(USERS, params={"q": "SPAM"}, headers=auth(admin)).json()

    assert everyone["total"] == 2
    assert found["total"] == 1
    assert found["items"][0]["nickname"] == "spammer"
    assert found["items"][0]["ban"]["reason"] == "Spam"
    assert "password_hash" not in found["items"][0]


def test_ban_message_without_reason():
    from src.api.schemas.ban import BanInfo

    assert ban_message(BanInfo(ban_type="permanent")) == "Your account is permanently banned."


def test_unban_of_unknown_user_returns_404(client, admin):
    response = client.delete(BANS, params={"user_id": str(uuid.uuid4())}, headers=auth(admin))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


def test_admin_get_db_yields_a_session():
    generator = admin_router.get_db()
    assert next(generator) is not None
    generator.close()
