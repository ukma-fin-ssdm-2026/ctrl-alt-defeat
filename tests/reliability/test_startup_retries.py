from unittest.mock import Mock

from sqlalchemy.exc import OperationalError

from src.api import main


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
    actual_delays = [
        call.args[0]
        for call in sleep_mock.call_args_list
    ]

    assert len(actual_delays) == 4

    for delay, max_delay in zip(actual_delays, expected_max_delays):
        assert 0 <= delay <= max_delay

from fastapi.testclient import TestClient


def test_application_starts_in_degraded_mode(monkeypatch):
    """Application remains alive when database initialization fails."""

    monkeypatch.setattr(
        main,
        "initialize_database_with_retry",
        lambda: False,
    )

    with TestClient(main.app) as client:
        assert main.app.state.database_available is False

        response = client.get("/health/live")
        assert response.status_code == 200

        response = client.get("/health")
        assert response.status_code == 503