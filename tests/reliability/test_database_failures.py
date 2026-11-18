from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from src.api.main import app
from src.api.routers.movies import get_db


def test_database_failure_returns_503():
    def broken_db():
        raise OperationalError(
            "SELECT 1",
            {},
            Exception("connection refused"),
        )
        yield

    app.dependency_overrides[get_db] = broken_db

    try:
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/v1/movies")

        assert response.status_code == 503

        data = response.json()

        assert data["error"]["code"] == "DATABASE_UNAVAILABLE"
        assert data["error"]["message"] == "Database is temporarily unavailable"
        assert data["error"]["request_id"]

    finally:
        app.dependency_overrides.pop(get_db, None)


def test_pool_timeout_returns_503():
    """No free connection in the pool within POOL_TIMEOUT_SECONDS: sqlalchemy.exc.TimeoutError is not an
    OperationalError, but the user still gets 503 DATABASE_UNAVAILABLE, not a 500."""
    from sqlalchemy.exc import TimeoutError as PoolTimeoutError

    def exhausted_pool():
        raise PoolTimeoutError("QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 10.00")
        yield

    app.dependency_overrides[get_db] = exhausted_pool
    try:
        response = TestClient(app, raise_server_exceptions=False).get("/api/v1/movies")

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    finally:
        app.dependency_overrides.pop(get_db, None)
