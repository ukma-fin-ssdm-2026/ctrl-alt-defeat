"""
Reliability, finding 13 (fault injection): the startup never waits for TMDB.

Fault injected: every TMDB request times out. Chosen reaction: safe failure — the service starts at once
with the built-in catalog, the TMDB import runs in a background thread and its failure is stored for the
administrator instead of blocking the startup.
"""

import threading
import time
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.db.models import CatalogSyncRun, Content
from src.api.main import app
from src.api.services import catalog_sync, tmdb
from src.api.services.tmdb import FALLBACK_MOVIES


def wait_until_finished(session_factory, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        db = session_factory()
        try:
            status = catalog_sync.get_status(db)
        finally:
            db.close()
        if status["state"] != "running":
            return status
        time.sleep(0.05)
    raise AssertionError("the background catalog update did not finish")


def test_startup_does_not_wait_for_a_hanging_tmdb(startup_db, monkeypatch):
    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    calls_from = []

    def tmdb_times_out(path, params, api_key):
        calls_from.append(threading.current_thread().name)
        raise TimeoutError("TMDB timed out")

    with patch.object(tmdb, "_tmdb_get", side_effect=tmdb_times_out):
        started = time.monotonic()
        with TestClient(app) as client:
            startup_seconds = time.monotonic() - started
            assert client.get("/health/live").status_code == 200
            status = wait_until_finished(startup_db)

    # The service answered right away: no TMDB request ran inside the startup itself
    assert startup_seconds < 5
    assert calls_from and set(calls_from) == {"tmdb-catalog-sync"}
    # The catalog is usable with the built-in titles while TMDB is down
    db = startup_db()
    try:
        assert db.query(Content).count() == len(FALLBACK_MOVIES)
    finally:
        db.close()
    # The failure is not silent: the administrator sees it in the update state
    assert status["state"] == "failed"
    assert "TMDB timed out" in status["error"]


def test_existing_catalog_does_not_start_an_import(startup_db, monkeypatch):
    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    db = startup_db()
    tmdb.seed_movies_to_database(db, FALLBACK_MOVIES[:1])
    db.close()

    with patch.object(tmdb, "_tmdb_get") as tmdb_get, TestClient(app):
        pass

    tmdb_get.assert_not_called()
    db = startup_db()
    try:
        assert db.query(CatalogSyncRun).count() == 0
    finally:
        db.close()
