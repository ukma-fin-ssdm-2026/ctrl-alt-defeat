import pytest
import uuid
from datetime import datetime, UTC
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from main import app
from routers.reviews import get_db
from db.models import Review
from schemas.review import ReviewStatus


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


def test_create_review_edge_case_rating(client, valid_payload):
    payload = valid_payload.copy()
    payload["rating"] = 11

    response = client.post("/api/v1/reviews", json=payload)

    assert response.status_code == 422


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


def test_get_reviews_min_rating_filter(client, mock_db_session, mock_review):
    mock_query = mock_db_session.query.return_value
    mock_query.count.return_value = 1
    mock_query.offset.return_value.limit.return_value.all.return_value = [mock_review]
    
    mock_filter = mock_query.filter.return_value
    mock_filter.count.return_value = 1
    mock_filter.offset.return_value.limit.return_value.all.return_value = [mock_review]

    response = client.get("/api/v1/reviews?min_rating=4")

    assert response.status_code == 200
    mock_query.filter.assert_called_once()


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
