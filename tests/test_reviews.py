import pytest
import uuid
from datetime import datetime, UTC
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from sqlalchemy.exc import IntegrityError

from src.api.main import app
from src.api.routers.auth import get_current_active_user
from src.api.routers.reviews import get_db
from src.api.db.models import Review, User
from src.api.schemas.review import ReviewStatus


@pytest.fixture
def mock_db_session():
    """Мок для SQLAlchemy сесії."""
    session = MagicMock()
    # By default the user has no review for this content yet (duplicate check passes)
    session.query.return_value.filter.return_value.first.return_value = None
    # By default the title is in the user's watched list (EXISTS query returns True)
    session.query.return_value.scalar.return_value = True
    return session


@pytest.fixture
def current_user():
    """Authenticated, verified user (FR-001) who writes the reviews in these tests."""
    return User(user_id=uuid.uuid4(), email="viewer@example.com", nickname="viewer", role="user", status="active")


@pytest.fixture
def client(mock_db_session, current_user):
    """Mocking database and authentication dependencies for test isolation"""

    def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = lambda: current_user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def valid_payload():
    return {
        "content_id": str(uuid.uuid4()),
        "rating": 10,
        "review_text": "Absolutely fantastic! " * 2,
        "contains_spoilers": False,
    }


@pytest.fixture
def mock_review(valid_payload, current_user):
    """Stub with model data, written by the current user"""
    return Review(
        review_id=uuid.uuid4(),
        user_id=current_user.user_id,
        content_id=uuid.UUID(valid_payload["content_id"]),
        rating=valid_payload["rating"],
        review_text=valid_payload["review_text"],
        contains_spoilers=valid_payload["contains_spoilers"],
        status=ReviewStatus.published.value,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def admin_user():
    return User(
        user_id=uuid.uuid4(),
        email="admin@platform.local",
        nickname="PlatformAdmin",
        role="admin",
        email_verified=True,
        status="active",
    )


@pytest.fixture
def author_user(mock_review):
    return User(
        user_id=mock_review.user_id,
        email="author@platform.local",
        nickname="ReviewAuthor",
        role="user",
        email_verified=True,
        status="active",
    )


@pytest.fixture
def stranger_user():
    return User(
        user_id=uuid.uuid4(),
        email="stranger@platform.local",
        nickname="OtherUser",
        role="user",
        email_verified=True,
        status="active",
    )


def test_create_review_success(client, mock_db_session, valid_payload):
    # Trace: T-005
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    response = client.post("/api/v1/reviews", json=valid_payload)

    assert response.status_code == 201
    assert response.json()["rating"] == valid_payload["rating"]
    mock_db_session.add.assert_called_once()


@pytest.mark.parametrize("valid_score", [1, 2, 5, 9, 10])
def test_create_review_valid_ratings_boundary(client, mock_db_session, valid_payload, valid_score):
    # Trace: T-005
    """Parameterized test verifying all valid rating values on the 1-10 scale."""
    payload = valid_payload.copy()
    payload["rating"] = valid_score

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 201
    assert response.json()["rating"] == valid_score


@pytest.mark.parametrize("invalid_score", [0, -1, -10, 11, 100, 999])
def test_create_review_invalid_ratings_boundary(client, valid_payload, invalid_score):
    # Trace: T-005
    """Parameterized test ensuring ratings outside 1-10 are rejected with 422."""
    payload = valid_payload.copy()
    payload["rating"] = invalid_score

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "text_len, expected_status",
    [
        (9, 422),  # Below min 10 chars
        (10, 201),  # Exact minimum boundary
        (200, 201),  # Normal text
        (5000, 201),  # Exact maximum boundary
        (5001, 422),  # Above max 5000 chars
    ],
)
def test_create_review_text_length_boundaries(client, mock_db_session, valid_payload, text_len, expected_status):
    # Trace: T-005
    """Parameterized verification of review text length boundaries (10 to 5000 chars)."""
    payload = valid_payload.copy()
    # Use normal mixed case text to test length boundary without triggering shouting policy
    base_sample = "Valid movie review text. "
    payload["review_text"] = (base_sample * (text_len // len(base_sample) + 1))[:text_len]

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == expected_status


def test_get_reviews_pagination(client, mock_db_session, mock_review):
    # Trace: T-038
    mock_query = mock_db_session.query.return_value
    mock_query.count.return_value = 1
    mock_query.offset.return_value.limit.return_value.all.return_value = [mock_review]

    response = client.get("/api/v1/reviews?skip=0&limit=5")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1


def test_get_reviews_with_content_filter(client, mock_db_session, mock_review):
    # Trace: T-038
    mock_query = mock_db_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.count.return_value = 1
    mock_filter.offset.return_value.limit.return_value.all.return_value = [mock_review]
    content_id = str(mock_review.content_id)

    response = client.get(f"/api/v1/reviews?content_id={content_id}")

    assert response.status_code == 200
    mock_query.filter.assert_called_once()


def test_get_review_by_id_success(client, mock_db_session, mock_review):
    # Trace: T-005
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review

    response = client.get(f"/api/v1/reviews/{mock_review.review_id}")

    assert response.status_code == 200
    assert response.json()["review_text"] == mock_review.review_text


def test_get_review_by_id_not_found(client, mock_db_session):
    # Trace: T-019
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    response = client.get(f"/api/v1/reviews/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REVIEW_NOT_FOUND"


def test_update_review_success(client, mock_db_session, mock_review):
    # Trace: T-005
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review
    update_payload = {"rating": 5}

    response = client.patch(f"/api/v1/reviews/{mock_review.review_id}", json=update_payload)

    assert response.status_code == 200
    assert response.json()["rating"] == 5
    mock_db_session.commit.assert_called_once()


def test_delete_review_success(client, mock_db_session, mock_review, admin_user):
    # Trace: T-017
    """
    US-006 / FR-008: Administrator successfully deletes a review.
    """
    app.dependency_overrides[get_current_active_user] = lambda: admin_user
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review

    response = client.delete(f"/api/v1/reviews/{mock_review.review_id}")

    assert response.status_code == 204
    mock_db_session.delete.assert_called_once_with(mock_review)


def test_delete_review_by_author_success(client, mock_db_session, mock_review, author_user):
    """
    FR-008 / BOLA: Review author successfully deletes their own review.
    """
    app.dependency_overrides[get_current_active_user] = lambda: author_user
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review

    response = client.delete(f"/api/v1/reviews/{mock_review.review_id}")

    assert response.status_code == 204
    mock_db_session.delete.assert_called_once_with(mock_review)


def test_delete_review_forbidden_for_other_user(client, mock_db_session, mock_review, stranger_user):
    # Trace: T-018
    """
    US-006 / FR-008 / SEC-001 (BOLA): A regular user cannot delete another user's review.
    """
    app.dependency_overrides[get_current_active_user] = lambda: stranger_user
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review

    response = client.delete(f"/api/v1/reviews/{mock_review.review_id}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_delete_review_unauthenticated_fails(client, mock_review):
    """
    FR-008 / SEC-001: Unauthenticated request to delete review is rejected with 401.
    """
    app.dependency_overrides.pop(get_current_active_user, None)
    response = client.delete(f"/api/v1/reviews/{mock_review.review_id}")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_delete_review_not_found_edge_case(client, mock_db_session, admin_user):
    # Trace: T-019
    """
    US-006 / FR-008: Deleting a non-existent review returns 404.
    """
    app.dependency_overrides[get_current_active_user] = lambda: admin_user
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    response = client.delete(f"/api/v1/reviews/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REVIEW_NOT_FOUND"


@pytest.mark.parametrize("min_val", [1, 5, 8, 10])
def test_get_reviews_min_rating_filter(client, mock_db_session, mock_review, min_val):
    # Trace: T-038
    """
    Test filtering reviews by minimum rating.
    Verifies that the database query receives the rating filter condition
    with the exact threshold, and that returned reviews satisfy rating >= min_val.
    """
    mock_query = mock_db_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.count.return_value = 1
    mock_review.rating = 10
    mock_filter.offset.return_value.limit.return_value.all.return_value = [mock_review]

    response = client.get(f"/api/v1/reviews?min_rating={min_val}")

    assert response.status_code == 200
    mock_query.filter.assert_called_once()

    # Deep verification of the filter expression passed to SQLAlchemy
    filter_expr = mock_query.filter.call_args[0][0]
    assert filter_expr.right.value == min_val
    assert "reviews.rating >=" in str(filter_expr)

    # Response verification
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["rating"] >= min_val


def test_get_reviews_min_rating_validation_error(client):
    # Trace: T-038
    response = client.get("/api/v1/reviews?min_rating=15")
    assert response.status_code == 422


def test_create_review_short_text(client, valid_payload):
    # Trace: T-005
    """Validation check for the minimum length of the review text."""
    payload = valid_payload.copy()
    payload["review_text"] = "Short"  # Less than 10 symbols

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 422


def test_update_review_not_found(client, mock_db_session):
    # Trace: T-019
    """Verification of a 404 error when attempting to update a non-existent review"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    update_payload = {"rating": 5}

    response = client.patch(f"/api/v1/reviews/{uuid.uuid4()}", json=update_payload)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REVIEW_NOT_FOUND"


def test_update_review_invalid_data(client, mock_db_session, mock_review):
    # Trace: T-005
    """Validation check (422) when submitting incorrect data for an update"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review
    update_payload = {"rating": 999}

    response = client.patch(f"/api/v1/reviews/{mock_review.review_id}", json=update_payload)

    assert response.status_code == 422


def test_get_reviews_with_user_filter(client, mock_db_session, mock_review):
    # Trace: T-038
    """Verifying the filtering of the reviews list by user_id"""
    mock_query = mock_db_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.count.return_value = 1
    mock_filter.offset.return_value.limit.return_value.all.return_value = [mock_review]
    user_id = str(mock_review.user_id)

    response = client.get(f"/api/v1/reviews?user_id={user_id}")

    assert response.status_code == 200
    mock_query.filter.assert_called_once()


def test_create_review_policy_violation(client, valid_payload):
    # Trace: T-007
    """Test that creating a review with profanity/spam triggers a 400 POLICY_VIOLATION."""
    payload = valid_payload.copy()
    payload["review_text"] = "This movie is terrible and the director is an idiot."

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "POLICY_VIOLATION"


def test_update_review_policy_violation(client, mock_db_session, mock_review):
    # Trace: T-007
    """Test that updating a review text with policy violations returns 400."""
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review
    update_payload = {"review_text": "This movie is terrible and the director is an idiot."}

    response = client.patch(f"/api/v1/reviews/{mock_review.review_id}", json=update_payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "POLICY_VIOLATION"


# ---------- One review per user per content ----------


def test_create_review_duplicate_returns_409(client, mock_db_session, valid_payload, mock_review):
    # Trace: T-005
    """A user cannot leave a second review for the same content."""
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review

    response = client.post("/api/v1/reviews", json=valid_payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_REVIEW"
    mock_db_session.add.assert_not_called()


def test_create_review_duplicate_race_condition(client, mock_db_session, valid_payload):
    # Trace: T-005
    """If the DB unique constraint fires (concurrent requests), API returns 409 and rolls back."""
    mock_db_session.commit.side_effect = IntegrityError("INSERT", {}, Exception("uq_reviews_user_content"))

    response = client.post("/api/v1/reviews", json=valid_payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_REVIEW"
    mock_db_session.rollback.assert_called_once()


# ---------- Rating-only reviews ----------


def test_create_review_rating_only(client, mock_db_session, valid_payload):
    # Trace: T-005
    """Review without text (rating only) is valid."""
    payload = valid_payload.copy()
    del payload["review_text"]

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 201
    assert response.json()["review_text"] is None
    assert response.json()["rating"] == payload["rating"]


@pytest.mark.parametrize("empty_text", [None, "", "   ", "\n\t "])
def test_create_review_empty_text_is_rating_only(client, mock_db_session, valid_payload, empty_text):
    # Trace: T-005
    """null / empty / whitespace-only text is treated as a rating-only review."""
    payload = valid_payload.copy()
    payload["review_text"] = empty_text

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 201
    assert response.json()["review_text"] is None


def test_create_review_text_is_trimmed_before_length_check(client, mock_db_session, valid_payload):
    # Trace: T-005
    """9 real chars padded with spaces must still be rejected."""
    payload = valid_payload.copy()
    payload["review_text"] = "   123456789     "

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 422


def test_create_review_without_rating_rejected(client, valid_payload):
    # Trace: T-005
    """Rating is always required, even if text is present."""
    payload = valid_payload.copy()
    del payload["rating"]

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 422


def test_update_review_remove_text(client, mock_db_session, mock_review):
    # Trace: T-005
    """Sending review_text = null turns the review into a rating-only one."""
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review

    response = client.patch(f"/api/v1/reviews/{mock_review.review_id}", json={"review_text": None})

    assert response.status_code == 200
    assert response.json()["review_text"] is None
