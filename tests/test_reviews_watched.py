"""Reviews require authentication and a watched title (FR-003, FR-004, US-002)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import Content, Review, User, WatchedItem
from src.api.main import app
from src.api.routers import auth as auth_router
from src.api.routers import reviews as reviews_router
from src.api.services.auth import create_access_token, hash_password

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

URL = "/api/v1/reviews"
MOVIE = uuid.UUID("11111111-1111-4111-8111-111111111111")
OTHER_MOVIE = uuid.UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    for model in (Review, WatchedItem, User, Content):
        db.query(model).delete()
    db.add(
        Content(
            id=1,
            content_id=MOVIE,
            title="Дюна: Частина друга",
            title_en="Dune: Part Two",
            img="/dune.jpg",
            img_en="/dune-en.jpg",
            category="Movie",
            genre="Фантастика",
            year=2024,
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

    app.dependency_overrides[reviews_router.get_db] = override_get_db
    app.dependency_overrides[auth_router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(db, nickname="viewer", status="active", verified=True):
    user = User(
        user_id=uuid.uuid4(),
        email=f"{nickname}@example.com",
        password_hash=hash_password("Password123!"),
        nickname=nickname,
        email_verified=verified,
        status=status,
    )
    db.add(user)
    db.commit()
    return user


def mark_watched(db, user, content_id=MOVIE):
    db.add(WatchedItem(user_id=user.user_id, content_id=content_id))
    db.commit()


def auth(user):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id)})}"}


def payload(content_id=MOVIE, **extra):
    return {"content_id": str(content_id), "rating": 9, "review_text": "A really strong and moving film", **extra}


def test_review_for_watched_title_is_published_under_token_user(client, db_session):
    # Trace: T-005
    user = make_user(db_session)
    mark_watched(db_session, user)

    response = client.post(URL, json=payload(), headers=auth(user))

    assert response.status_code == 201
    assert response.json()["user_id"] == str(user.user_id)


def test_rating_only_review_for_watched_title(client, db_session):
    # Trace: T-005
    user = make_user(db_session)
    mark_watched(db_session, user)

    response = client.post(URL, json={"content_id": str(MOVIE), "rating": 7}, headers=auth(user))

    assert response.status_code == 201
    assert response.json()["review_text"] is None


def test_review_without_authentication_is_rejected(client, db_session):
    # Trace: T-006
    response = client.post(URL, json=payload())

    assert response.status_code == 401
    assert db_session.query(Review).count() == 0


def test_review_for_title_not_in_watched_list_is_rejected(client, db_session):
    # Trace: T-035
    user = make_user(db_session)
    mark_watched(db_session, user, OTHER_MOVIE)

    response = client.post(URL, json=payload(MOVIE), headers=auth(user))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CONTENT_NOT_WATCHED"
    assert db_session.query(Review).count() == 0


def test_title_watched_by_another_user_does_not_count(client, db_session):
    # Trace: T-035
    alice = make_user(db_session, "alice")
    bob = make_user(db_session, "bob")
    mark_watched(db_session, alice)

    response = client.post(URL, json=payload(), headers=auth(bob))

    assert response.status_code == 403


def test_client_cannot_post_on_behalf_of_another_user(client, db_session):
    # Trace: T-006
    user = make_user(db_session)
    victim = make_user(db_session, "victim")
    mark_watched(db_session, user)

    response = client.post(URL, json=payload(user_id=str(victim.user_id)), headers=auth(user))

    assert response.status_code == 201
    assert response.json()["user_id"] == str(user.user_id)


@pytest.mark.parametrize(
    "status, verified, code", [("banned", True, "ACCOUNT_BANNED"), ("pending", False, "EMAIL_NOT_VERIFIED")]
)
def test_banned_or_unverified_user_cannot_review(client, db_session, status, verified, code):
    # Trace: T-006
    user = make_user(db_session, status=status, verified=verified)
    mark_watched(db_session, user)

    response = client.post(URL, json=payload(), headers=auth(user))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == code


def test_one_review_per_watched_title(client, db_session):
    # Trace: T-005
    user = make_user(db_session)
    mark_watched(db_session, user)
    client.post(URL, json=payload(), headers=auth(user))

    response = client.post(URL, json=payload(rating=5), headers=auth(user))

    assert response.status_code == 409


def test_author_can_edit_own_review(client, db_session):
    # Trace: T-005
    user = make_user(db_session)
    mark_watched(db_session, user)
    review_id = client.post(URL, json=payload(), headers=auth(user)).json()["review_id"]

    response = client.patch(f"{URL}/{review_id}", json={"rating": 6}, headers=auth(user))

    assert response.status_code == 200
    assert response.json()["rating"] == 6


def test_cannot_edit_someone_elses_review(client, db_session):
    # Trace: T-006
    author = make_user(db_session, "author")
    stranger = make_user(db_session, "stranger")
    mark_watched(db_session, author)
    review_id = client.post(URL, json=payload(), headers=auth(author)).json()["review_id"]

    response = client.patch(f"{URL}/{review_id}", json={"rating": 1}, headers=auth(stranger))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_REVIEW_AUTHOR"
    assert db_session.query(Review).one().rating == 9


def test_editing_without_authentication_is_rejected(client, db_session):
    # Trace: T-006
    response = client.patch(f"{URL}/{uuid.uuid4()}", json={"rating": 5})

    assert response.status_code == 401


@pytest.mark.parametrize("field", ["rating", "contains_spoilers"])
def test_required_fields_cannot_be_nulled(client, db_session, field):
    # Trace: T-005
    user = make_user(db_session)
    mark_watched(db_session, user)
    review_id = client.post(URL, json=payload(), headers=auth(user)).json()["review_id"]

    response = client.patch(f"{URL}/{review_id}", json={field: None}, headers=auth(user))

    assert response.status_code == 422


def test_guests_can_still_read_reviews(client, db_session):
    # Trace: T-005
    user = make_user(db_session)
    mark_watched(db_session, user)
    client.post(URL, json=payload(), headers=auth(user))

    response = client.get(URL, params={"content_id": str(MOVIE)})

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_reviews_show_author_nickname_and_title(client, db_session):
    # Trace: T-038
    user = make_user(db_session, "cinema_fan")
    mark_watched(db_session, user)

    created = client.post(URL, json=payload(), headers=auth(user)).json()
    listed = client.get(URL, params={"content_id": str(MOVIE)}).json()["items"][0]
    single = client.get(f"{URL}/{created['review_id']}").json()

    assert created["author_nickname"] == "cinema_fan"
    assert listed["author_nickname"] == "cinema_fan"
    assert listed["content_title"] == "Дюна: Частина друга"
    assert single["author_nickname"] == "cinema_fan"


def test_my_reviews_can_be_listed_by_user_id(client, db_session):
    # Trace: T-038
    me = make_user(db_session, "me")
    other = make_user(db_session, "other")
    for user in (me, other):
        mark_watched(db_session, user)
        client.post(URL, json=payload(), headers=auth(user))

    items = client.get(URL, params={"user_id": str(me.user_id)}).json()["items"]

    assert [item["author_nickname"] for item in items] == ["me"]
    assert items[0]["content_title"] == "Дюна: Частина друга"
    # The profile shows a small poster and links to the page of the title (T-038)
    assert items[0]["content_title_en"] == "Dune: Part Two"
    assert (items[0]["content_img"], items[0]["content_img_en"]) == ("/dune.jpg", "/dune-en.jpg")


SUMMARY_URL = f"{URL}/summary"


def test_guest_sees_reviews_and_audience_rating(client, db_session):
    # Trace: T-023
    for nickname, rating, text in (
        ("a", 9, "Неймовірна атмосфера фільму"),
        ("b", 8, None),
        ("c", 10, "Шедевр, дивитись усім!"),
    ):
        user = make_user(db_session, nickname)
        mark_watched(db_session, user)
        client.post(URL, json=payload(rating=rating, review_text=text), headers=auth(user))

    reviews = client.get(URL, params={"content_id": str(MOVIE)})
    summary = client.get(SUMMARY_URL, params={"content_id": str(MOVIE)}).json()

    assert reviews.status_code == 200 and reviews.json()["total"] == 3
    assert summary["average_rating"] == 9.0
    assert summary["ratings_count"] == 3
    assert summary["reviews_count"] == 2
    assert summary["distribution"]["8"] == 1 and summary["distribution"]["10"] == 1


def test_movie_without_reviews_has_empty_summary(client):
    # Trace: T-024
    summary = client.get(SUMMARY_URL, params={"content_id": str(OTHER_MOVIE)}).json()

    assert summary["average_rating"] is None
    assert summary["ratings_count"] == 0
    assert summary["reviews_count"] == 0
    assert sum(summary["distribution"].values()) == 0


def test_summary_requires_a_valid_content_id(client):
    # Trace: T-024
    assert client.get(SUMMARY_URL).status_code == 422
    assert client.get(SUMMARY_URL, params={"content_id": "../../admin"}).status_code == 422
