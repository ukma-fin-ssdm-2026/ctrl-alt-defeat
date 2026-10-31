import pytest
import uuid
from datetime import datetime, UTC
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from src.api.main import app
from src.api.routers.reviews import get_db
from src.api.db.models import Review
from src.api.schemas.review import ReviewStatus


@pytest.fixture
def mock_db_session():
    """Мок для SQLAlchemy сесії."""
    return MagicMock()


@pytest.fixture
def client(mock_db_session):
    """Mocking database dependencies for test isolation"""

    def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def valid_payload():
    return {
        "user_id": str(uuid.uuid4()),
        "content_id": str(uuid.uuid4()),
        "rating": 10,
        "review_text": "Absolutely fantastic! " * 2,
        "contains_spoilers": False,
    }


@pytest.fixture
def mock_review(valid_payload):
    """Stub with model data"""
    return Review(
        review_id=uuid.uuid4(),
        user_id=uuid.UUID(valid_payload["user_id"]),
        content_id=uuid.UUID(valid_payload["content_id"]),
        rating=valid_payload["rating"],
        review_text=valid_payload["review_text"],
        contains_spoilers=valid_payload["contains_spoilers"],
        status=ReviewStatus.published.value,
        created_at=datetime.now(UTC),
    )


def test_create_review_success(client, mock_db_session, valid_payload):
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    response = client.post("/api/v1/reviews", json=valid_payload)

    assert response.status_code == 201
    assert response.json()["rating"] == valid_payload["rating"]
    mock_db_session.add.assert_called_once()


@pytest.mark.parametrize("valid_score", [1, 2, 5, 9, 10])
def test_create_review_valid_ratings_boundary(client, mock_db_session, valid_payload, valid_score):
    """Parameterized test verifying all valid rating values on the 1-10 scale."""
    payload = valid_payload.copy()
    payload["rating"] = valid_score

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 201
    assert response.json()["rating"] == valid_score


@pytest.mark.parametrize("invalid_score", [0, -1, -10, 11, 100, 999])
def test_create_review_invalid_ratings_boundary(client, valid_payload, invalid_score):
    """Parameterized test ensuring ratings outside 1-10 are rejected with 422."""
    payload = valid_payload.copy()
    payload["rating"] = invalid_score

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("text_len, expected_status", [
    (9, 422),       # Below min 10 chars
    (10, 201),      # Exact minimum boundary
    (200, 201),     # Normal text
    (5000, 201),    # Exact maximum boundary
    (5001, 422),    # Above max 5000 chars
])
def test_create_review_text_length_boundaries(client, mock_db_session, valid_payload, text_len, expected_status):
    """Parameterized verification of review text length boundaries (10 to 5000 chars)."""
    payload = valid_payload.copy()
    # Use normal mixed case text to test length boundary without triggering shouting policy
    base_sample = "Valid movie review text. "
    payload["review_text"] = (base_sample * (text_len // len(base_sample) + 1))[:text_len]

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == expected_status


def test_get_reviews_pagination(client, mock_db_session, mock_review):
    mock_query = mock_db_session.query.return_value
    mock_query.count.return_value = 1
    mock_query.offset.return_value.limit.return_value.all.return_value = [mock_review]

    response = client.get("/api/v1/reviews?skip=0&limit=5")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1


def test_get_reviews_with_content_filter(client, mock_db_session, mock_review):
    mock_query = mock_db_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.count.return_value = 1
    mock_filter.offset.return_value.limit.return_value.all.return_value = [mock_review]
    content_id = str(mock_review.content_id)

    response = client.get(f"/api/v1/reviews?content_id={content_id}")

    assert response.status_code == 200
    mock_query.filter.assert_called_once()


def test_get_review_by_id_success(client, mock_db_session, mock_review):
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review

    response = client.get(f"/api/v1/reviews/{mock_review.review_id}")

    assert response.status_code == 200
    assert response.json()["review_text"] == mock_review.review_text


def test_get_review_by_id_not_found(client, mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    response = client.get(f"/api/v1/reviews/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REVIEW_NOT_FOUND"


def test_update_review_success(client, mock_db_session, mock_review):
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review
    update_payload = {"rating": 5}

    response = client.patch(f"/api/v1/reviews/{mock_review.review_id}", json=update_payload)

    assert response.status_code == 200
    assert response.json()["rating"] == 5
    mock_db_session.commit.assert_called_once()


def test_delete_review_success(client, mock_db_session, mock_review):
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review

    response = client.delete(f"/api/v1/reviews/{mock_review.review_id}")

    assert response.status_code == 204
    mock_db_session.delete.assert_called_once_with(mock_review)


def test_delete_review_not_found_edge_case(client, mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    response = client.delete(f"/api/v1/reviews/{uuid.uuid4()}")

    assert response.status_code == 404


@pytest.mark.parametrize("min_val", [1, 5, 8, 10])
def test_get_reviews_min_rating_filter(client, mock_db_session, mock_review, min_val):
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
    response = client.get("/api/v1/reviews?min_rating=15")
    assert response.status_code == 422

def test_create_review_short_text(client, valid_payload):
    """Validation check for the minimum length of the review text."""
    payload = valid_payload.copy()
    payload["review_text"] = "Short"  # Less than 10 symbols

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 422


def test_update_review_not_found(client, mock_db_session):
    """Verification of a 404 error when attempting to update a non-existent review"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    update_payload = {"rating": 5}

    response = client.patch(f"/api/v1/reviews/{uuid.uuid4()}", json=update_payload)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REVIEW_NOT_FOUND"


def test_update_review_invalid_data(client, mock_db_session, mock_review):
    """Validation check (422) when submitting incorrect data for an update"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review
    update_payload = {"rating": 999}

    response = client.patch(f"/api/v1/reviews/{mock_review.review_id}", json=update_payload)

    assert response.status_code == 422


def test_get_reviews_with_user_filter(client, mock_db_session, mock_review):
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
    """Test that creating a review with profanity/spam triggers a 400 POLICY_VIOLATION."""
    payload = valid_payload.copy()
    payload["review_text"] = "This movie is terrible and the director is an idiot."

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "POLICY_VIOLATION"


def test_update_review_policy_violation(client, mock_db_session, mock_review):
    """Test that updating a review text with policy violations returns 400."""
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_review
    update_payload = {"review_text": "This movie is terrible and the director is an idiot."}

    response = client.patch(f"/api/v1/reviews/{mock_review.review_id}", json=update_payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "POLICY_VIOLATION"
