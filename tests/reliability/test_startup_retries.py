from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from src.api import main
from src.api.routers import health as health_router


def database_error():
    return OperationalError(
        "SELECT 1",
        {},
        Exception("connection refused"),
    )


def test_database_recovers_after_two_failures(monkeypatch):
    """Database fails twice and succeeds on the third attempt."""

    create_all_mock = Mock(
        side_effect=[
            database_error(),
            database_error(),
            None,
        ]
    )

    sleep_mock = Mock()

    monkeypatch.setattr(main.Base.metadata, "create_all", create_all_mock)
    monkeypatch.setattr(main.time, "sleep", sleep_mock)

    result = main.initialize_database_with_retry()

    assert result is True
    assert create_all_mock.call_count == 3
    assert sleep_mock.call_count == 2


def test_database_unavailable_after_five_attempts(monkeypatch):
    """Database remains unavailable after all retry attempts."""

    create_all_mock = Mock(side_effect=database_error())
    sleep_mock = Mock()

    monkeypatch.setattr(main.Base.metadata, "create_all", create_all_mock)
    monkeypatch.setattr(main.time, "sleep", sleep_mock)

    result = main.initialize_database_with_retry()

    assert result is False
    assert create_all_mock.call_count == 5
    assert sleep_mock.call_count == 4


def test_exponential_backoff_with_full_jitter(monkeypatch):
    """Retry delays stay within exponential backoff limits."""

    create_all_mock = Mock(side_effect=database_error())
    sleep_mock = Mock()

    monkeypatch.setattr(main.Base.metadata, "create_all", create_all_mock)
    monkeypatch.setattr(main.time, "sleep", sleep_mock)

    result = main.initialize_database_with_retry(
        max_attempts=5,
        base_delay=0.5,
        max_delay=5.0,
    )

    assert result is False

    expected_max_delays = [0.5, 1.0, 2.0, 4.0]
    actual_delays = [call.args[0] for call in sleep_mock.call_args_list]

    assert len(actual_delays) == 4

    for delay, max_delay in zip(actual_delays, expected_max_delays):
        assert 0 <= delay <= max_delay


class BrokenSession:
    """A database session whose every statement fails, like an unreachable PostgreSQL."""

    def execute(self, *args, **kwargs):
        raise database_error()

    def close(self):
        pass


@pytest.fixture
def restore_app_state():
    yield
    # app.state is shared by all tests: never leave the degraded flag behind
    main.app.state.database_available = True
    main.app.dependency_overrides.clear()


def test_application_starts_in_degraded_mode(monkeypatch, restore_app_state):
    """The process stays alive when the database is unavailable on startup; /health reports it."""

    monkeypatch.setattr(main, "initialize_database_with_retry", lambda: False)
    main.app.dependency_overrides[health_router.get_db] = lambda: BrokenSession()

    with TestClient(main.app) as client:
        assert main.app.state.database_available is False
        assert client.get("/health/live").status_code == 200

        response = client.get("/health")
        assert response.status_code == 503
        assert response.json() == {"status": "degraded", "database": "unavailable"}


def test_health_recovers_when_the_database_comes_back(monkeypatch, restore_app_state):
    """After a degraded start /health does not stay 503 forever once the database answers again."""

    monkeypatch.setattr(main, "initialize_database_with_retry", lambda: False)

    with TestClient(main.app) as client:
        main.app.dependency_overrides[health_router.get_db] = lambda: BrokenSession()
        assert client.get("/health").status_code == 503

        # The database is back: the real session answers SELECT 1
        main.app.dependency_overrides.clear()
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "ok"}
        assert main.app.state.database_available is True
