from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_global_404_exception_handler():
    response = client.get("/api/v1/this-route-does-not-exist")

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Not Found"


def test_global_validation_exception_handler():
    bad_payload = {
        "user_id": "not-a-valid-uuid",
        "content_id": "not-a-valid-uuid",
        "rating": 10,
        "review_text": "Good",
        "contains_spoilers": False,
    }

    response = client.post("/api/v1/reviews", json=bad_payload)

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert len(data["error"]["details"]) > 0
    assert data["error"]["details"][0]["field"] == "user_id"
