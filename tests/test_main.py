from unittest.mock import patch, mock_open
import pytest
from fastapi.testclient import TestClient
from src.api.main import app, save_openapi_spec, lifespan

client = TestClient(app)


def test_global_404_exception_handler():
    # Trace: T-019
    response = client.get("/api/v1/this-route-does-not-exist")

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Not Found"


def test_global_validation_exception_handler():
    # Trace: T-005
    # Public endpoint: creating reviews now requires authentication, which is checked before validation
    response = client.get("/api/v1/reviews", params={"content_id": "not-a-valid-uuid", "min_rating": 15})

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert len(data["error"]["details"]) > 0
    assert {detail["field"] for detail in data["error"]["details"]} == {"content_id", "min_rating"}


def test_save_openapi_spec():
    # Trace: T-005
    with patch("builtins.open", mock_open()) as mock_file:
        save_openapi_spec(app)
        mock_file.assert_called()


@pytest.mark.anyio
async def test_lifespan():
    # Trace: T-005
    with patch("src.api.main.save_openapi_spec") as mock_save:
        async with lifespan(app):
            mock_save.assert_called_once_with(app)
