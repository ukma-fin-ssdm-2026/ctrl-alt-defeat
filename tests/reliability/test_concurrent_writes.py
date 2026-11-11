import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import BackgroundTasks, HTTPException, Response
from sqlalchemy.exc import IntegrityError

from src.api.routers import auth, watched
from src.api.schemas.auth import UserRegisterRequest
from src.api.schemas.watched import WatchedItemCreate


def make_integrity_error():
    return IntegrityError(
        statement="INSERT INTO table VALUES (...)",
        params={},
        orig=Exception("UNIQUE constraint failed"),
    )


def test_registration_integrity_error_returns_409(monkeypatch):
    """Registration returns 409 and rolls back after IntegrityError."""

    db = MagicMock()

    # Email and nickname are not found during initial checks.
    db.query.return_value.filter.return_value.first.return_value = None

    # Simulate a concurrent insert violating a UNIQUE constraint.
    db.commit.side_effect = make_integrity_error()

    monkeypatch.setattr(
        auth,
        "hash_password",
        lambda password: "fake-hash",
    )

    monkeypatch.setattr(
        auth,
        "generate_verification_token",
        lambda: "fake-token",
    )

    request = UserRegisterRequest(
        email="test@example.com",
        nickname="testuser",
        password="password123",
    )

    with pytest.raises(HTTPException) as exc_info:
        auth.register_user(
            req=request,
            background_tasks=BackgroundTasks(),
            db=db,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "USER_ALREADY_EXISTS"

    db.rollback.assert_called_once()
    db.commit.assert_called_once()


def test_watched_integrity_error_returns_existing_record(monkeypatch):
    """Concurrent watched insert returns the existing record with HTTP 200."""

    db = MagicMock()

    user_id = uuid.uuid4()
    content_id = uuid.uuid4()

    current_user = MagicMock()
    current_user.user_id = user_id

    existing_item = MagicMock()
    existing_item.user_id = user_id
    existing_item.content_id = content_id

    # First query: no watched record exists.
    # Second query: another request has already created it.
    db.query.return_value.filter.return_value.first.side_effect = [
        None,
        existing_item,
    ]

    db.commit.side_effect = make_integrity_error()

    expected_result = {"content_id": str(content_id)}

    monkeypatch.setattr(
        watched,
        "_build_watched_response",
        lambda item, session: expected_result,
    )

    response = Response()

    result = watched.mark_as_watched(
        payload=WatchedItemCreate(content_id=content_id),
        response=response,
        db=db,
        current_user=current_user,
    )

    assert response.status_code == 200
    assert result == expected_result

    db.rollback.assert_called_once()
    db.commit.assert_called_once()


def test_watched_integrity_error_without_existing_record(monkeypatch):
    """Unexpected IntegrityError is not silently ignored."""

    db = MagicMock()

    current_user = MagicMock()
    current_user.user_id = uuid.uuid4()

    content_id = uuid.uuid4()

    # No record exists before or after the failed commit.
    db.query.return_value.filter.return_value.first.return_value = None

    db.commit.side_effect = make_integrity_error()

    with pytest.raises(IntegrityError):
        watched.mark_as_watched(
            payload=WatchedItemCreate(content_id=content_id),
            response=Response(),
            db=db,
            current_user=current_user,
        )

    db.rollback.assert_called_once()
    db.commit.assert_called_once()