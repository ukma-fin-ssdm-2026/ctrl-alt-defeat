"""Votes for reviews: "Support" / "Don't support" (FR-003, FR-004), one vote per user, stored on the server."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Ban, Comment, Content, Review, ReviewVote, User, WatchedItem
from src.api.main import app
from src.api.routers import admin as admin_router
from src.api.routers import auth as auth_router
from src.api.routers import reviews as reviews_router
from src.api.services.account import remove_user_with_data
from src.api.services.auth import create_access_token, hash_password

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

REVIEWS = "/api/v1/reviews"
VOTES = "/api/v1/reviews/votes"
MOVIE = uuid.UUID("11111111-1111-4111-8111-111111111111")
OTHER_MOVIE = uuid.UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    engine_test.dispose()


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    for model in (ReviewVote, Comment, Ban, Review, WatchedItem, User, Content):
        db.query(model).delete()
    db.add(Content(id=1, content_id=MOVIE, title="Дюна", category="Movie", genre="Фантастика", year=2024))
    db.add(Content(id=2, content_id=OTHER_MOVIE, title="Шрек", category="Movie", genre="Комедія", year=2001))
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

    for router in (admin_router, auth_router, reviews_router):
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


def auth(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id)})}"}


def add_review(db, author, content_id=MOVIE):
    item = Review(user_id=author.user_id, content_id=content_id, rating=8, review_text="Дуже сильне кіно, раджу")
    db.add(item)
    db.commit()
    return item.review_id


def vote(client, user, review_id, value):
    return client.put(VOTES, json={"review_id": str(review_id), "value": value}, headers=auth(user))


@pytest.fixture
def author(db_session):
    return make_user(db_session, "author")


@pytest.fixture
def fan(db_session):
    return make_user(db_session, "fan")


def test_support_is_counted_once_per_user(client, db_session, author, fan):
    review_id = add_review(db_session, author)

    first = vote(client, fan, review_id, 1)
    second = vote(client, fan, review_id, 1)

    assert first.status_code == 200
    assert first.json() == {"review_id": str(review_id), "likes": 1, "dislikes": 0, "my_vote": 1}
    assert second.json()["likes"] == 1
    listed = client.get(REVIEWS, params={"content_id": str(MOVIE)}).json()["items"][0]
    assert (listed["likes"], listed["dislikes"]) == (1, 0)


def test_switching_to_dont_support_and_taking_the_vote_back(client, db_session, author, fan):
    review_id = add_review(db_session, author)
    other = make_user(db_session, "other")
    vote(client, other, review_id, -1)
    vote(client, fan, review_id, 1)

    switched = vote(client, fan, review_id, -1)
    assert switched.json() == {"review_id": str(review_id), "likes": 0, "dislikes": 2, "my_vote": -1}

    removed = vote(client, fan, review_id, 0)
    assert removed.json() == {"review_id": str(review_id), "likes": 0, "dislikes": 1, "my_vote": 0}
    # Removing a vote that does not exist is not an error
    assert vote(client, fan, review_id, 0).json()["dislikes"] == 1
    assert client.get(f"{REVIEWS}/{review_id}").json()["dislikes"] == 1


def test_author_cannot_vote_for_own_review(client, db_session, author):
    review_id = add_review(db_session, author)

    response = vote(client, author, review_id, 1)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "OWN_REVIEW_VOTE"


def test_guest_and_unknown_review(client, db_session, fan):
    assert client.put(VOTES, json={"review_id": str(uuid.uuid4()), "value": 1}).status_code == 401

    response = vote(client, fan, uuid.uuid4(), 1)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REVIEW_NOT_FOUND"


@pytest.mark.parametrize("value", [2, -2, "yes", None])
def test_invalid_vote_value_returns_422(client, db_session, author, fan, value):
    review_id = add_review(db_session, author)
    assert vote(client, fan, review_id, value).status_code == 422


def test_banned_user_cannot_vote(client, db_session, author, fan):
    review_id = add_review(db_session, author)
    admin = make_user(db_session, "moderator", role="admin")
    client.post(
        "/api/v1/admin/bans",
        json={"user_id": str(fan.user_id), "ban_type": "permanent"},
        headers=auth(admin),
    )

    response = vote(client, fan, review_id, 1)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_BANNED"


def test_my_votes_for_a_movie(client, db_session, author, fan):
    liked = add_review(db_session, author)
    other_author = make_user(db_session, "critic")
    disliked = add_review(db_session, other_author)
    elsewhere = add_review(db_session, author, OTHER_MOVIE)
    vote(client, fan, liked, 1)
    vote(client, fan, disliked, -1)
    vote(client, fan, elsewhere, 1)

    response = client.get(f"{VOTES}/mine", params={"content_id": str(MOVIE)}, headers=auth(fan))

    assert response.status_code == 200
    assert sorted((item["review_id"], item["value"]) for item in response.json()["items"]) == sorted(
        [(str(liked), 1), (str(disliked), -1)]
    )
    assert client.get(f"{VOTES}/mine", params={"content_id": str(MOVIE)}).status_code == 401


def test_votes_go_away_with_the_review_and_with_the_account(client, db_session, author, fan):
    first = add_review(db_session, author)
    second = add_review(db_session, author, OTHER_MOVIE)
    vote(client, fan, first, 1)
    vote(client, fan, second, -1)

    assert client.delete(REVIEWS, params={"review_id": str(first)}, headers=auth(author)).status_code == 204
    assert db_session.query(ReviewVote).filter(ReviewVote.review_id == first).count() == 0

    remove_user_with_data(db_session, fan)
    assert db_session.query(ReviewVote).count() == 0


def test_deleting_the_author_removes_votes_under_their_reviews(client, db_session, author, fan):
    review_id = add_review(db_session, author)
    vote(client, fan, review_id, 1)

    remove_user_with_data(db_session, author)

    assert db_session.query(ReviewVote).count() == 0
