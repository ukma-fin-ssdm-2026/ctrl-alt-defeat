"""
Reliability, finding 3 (error handling):
- Global unhandled exception handler catches all unexpected non-HTTP exceptions.

Reaction: safe failure with HTTP 500, standardized ErrorResponse schema, unique request_id
for correlation, and logger.exception tracking.
"""

import logging
import uuid

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routers import movies as movies_router
from src.api.routers import health as health_router

LOGGER_NAME = "src.api.main"


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_unhandled_exception_returns_unified_500_json_with_request_id(client, caplog):
    """
    Finding 3: An unhandled exception returns standardized ErrorResponse (JSON), not raw HTML/text.
    """
    def broken_db():
        raise ZeroDivisionError("unexpected math glitch")

    app.dependency_overrides[health_router.get_db] = broken_db

    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
        response = client.get("/health")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert "error" in data
    error = data["error"]
    assert error["code"] == "INTERNAL_SERVER_ERROR"
    assert error["message"] == "An unexpected error occurred. Please try again later."
    assert "request_id" in error

    req_id = uuid.UUID(error["request_id"])
    assert str(req_id) in caplog.text
    assert "unexpected math glitch" in caplog.text


def test_unhandled_runtime_error_in_catalog_returns_structured_error(client, caplog):
    """
    Finding 3: A runtime error in business logic is intercepted cleanly by the global handler.
    """
    def broken_query():
        raise RuntimeError("corrupted memory state")

    app.dependency_overrides[movies_router.get_db] = broken_query

    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
        response = client.get("/api/v1/movies")

    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "documentation" in data["error"]
    assert "corrupted memory state" in caplog.text
