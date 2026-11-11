"""
Reliability, finding 10: time limits of the PostgreSQL connection.

The statement timeout is set per transaction with `SET LOCAL`, not with the startup parameter
`options=-c statement_timeout=...`: the pooled Neon connection string (PgBouncer) rejects startup options
with "unsupported startup parameter", which would leave the site without a database.
"""

from unittest.mock import Mock

from sqlalchemy import event

from src.api.db import database

POOLED_NEON_URL = "postgresql+psycopg2://user:secret@ep-test-pooler.eu-central-1.aws.neon.tech/neondb"


def test_statement_timeout_is_set_for_each_transaction():
    connection = Mock()

    database.set_statement_timeout(connection)

    connection.exec_driver_sql.assert_called_once_with("SET LOCAL statement_timeout = 10000")


def test_postgres_engine_limits_time_without_startup_options(monkeypatch):
    created = {}

    def fake_create_engine(url, **kwargs):
        created.update(url=url, **kwargs)
        return Mock()

    listeners = []
    monkeypatch.setattr(database, "create_engine", fake_create_engine)
    monkeypatch.setattr(event, "listen", lambda target, name, fn: listeners.append((name, fn)))

    database.build_engine(POOLED_NEON_URL)

    # Only parameters a pooled Neon connection accepts
    assert created["connect_args"] == {"connect_timeout": 5}
    assert created["pool_timeout"] == 10
    assert created["pool_pre_ping"] is True
    assert listeners == [("begin", database.set_statement_timeout)]


def test_sqlite_engine_has_no_postgres_settings(monkeypatch):
    created = {}
    monkeypatch.setattr(database, "create_engine", lambda url, **kwargs: created.update(kwargs) or Mock())

    database.build_engine("sqlite:///./app.db")

    assert created["connect_args"] == {"check_same_thread": False}
    assert "pool_timeout" not in created
