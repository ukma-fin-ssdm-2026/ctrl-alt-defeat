"""
Reliability, finding 16 (fault injection): a restart in the middle of a catalog update is not lost.

Fault injected: the process "dies" while an update is running (a row left in the "running" state), and an
update whose import crashes. Chosen reaction: safe failure with recovery — the state lives in the
database, the interrupted run is reported as failed on the next startup and a new update can be started.
"""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.api.db.models import CatalogSyncRun
from src.api.main import app
from src.api.services import catalog_sync


def test_update_cut_off_by_a_restart_is_reported_after_startup(startup_db):
    db = startup_db()
    db.add(CatalogSyncRun(state="running", started_at=datetime.now(UTC)))
    db.commit()
    db.close()

    with TestClient(app):  # the "restart": the application starts again on the same database
        pass

    db = startup_db()
    try:
        status = catalog_sync.get_status(db)
        assert status["state"] == "failed"
        assert status["error"] == catalog_sync.INTERRUPTED_MESSAGE
        assert status["finished_at"] is not None
        # Recovery: the administrator can start a new update
        assert catalog_sync.try_start(db) is not None
    finally:
        db.close()


def test_crashed_import_is_stored_and_survives_the_process(startup_db, monkeypatch):
    def crash(api_key):
        raise RuntimeError("connection reset by peer")

    monkeypatch.setattr(catalog_sync, "fetch_tmdb_catalog", crash)
    db = startup_db()
    run_id = catalog_sync.try_start(db)
    db.close()

    catalog_sync.run_sync("key", run_id)

    # A new session (another process after a restart) still sees the result
    other = startup_db()
    try:
        status = catalog_sync.get_status(other)
        assert (status["state"], status["error"]) == ("failed", "connection reset by peer")
    finally:
        other.close()


def test_only_one_update_at_a_time(startup_db):
    db = startup_db()
    try:
        assert catalog_sync.try_start(db) is not None
        assert catalog_sync.try_start(db) is None
    finally:
        db.close()
