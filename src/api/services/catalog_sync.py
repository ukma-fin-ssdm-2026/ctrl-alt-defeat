"""
Catalog update from TMDB (FR-012).

The import takes about a minute (three sections of popular titles plus details of each title),
so it runs in the background and the admin panel polls its status. One import at a time.

Reliability (report, findings 13 and 16):
- every run is stored in the `catalog_sync_runs` table, not only in the memory of the process; a run that
  is still "running" when the service starts was cut off by a restart and is marked as failed, so the
  administrator sees it and can start a new one;
- the startup never waits for TMDB: an empty catalog is filled with the built-in titles at once and,
  when a TMDB key is configured, the real catalog is imported in a background thread.
"""

import logging
import os
import threading
from datetime import UTC, datetime
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from src.api.db.database import SessionLocal
from src.api.db.models import CatalogSyncRun
from src.api.services.catalog_cleanup import release_placeholder_ids, retire_placeholders
from src.api.services.tmdb import fetch_tmdb_catalog, sync_catalog

logger = logging.getLogger(__name__)

INTERRUPTED_MESSAGE = "Оновлення перервано: сервер перезапустився під час імпорту. Запустіть оновлення ще раз."
COUNTERS = ("added", "updated", "skipped", "placeholders_removed", "placeholders_kept")

# Two clicks at the same moment in one process must not start two imports
_start_lock = threading.Lock()


def tmdb_api_key() -> Optional[str]:
    return os.getenv("TMDB_API_KEY") or None


def _latest(db: Session) -> Optional[CatalogSyncRun]:
    return db.query(CatalogSyncRun).order_by(CatalogSyncRun.run_id.desc()).first()


def get_status(db: Session) -> Dict[str, Any]:
    """State of the last update (idle when there was none)."""
    run = _latest(db)
    status: Dict[str, Any] = {"configured": tmdb_api_key() is not None, "state": "idle"}
    status.update({counter: 0 for counter in COUNTERS})
    status.update(started_at=None, finished_at=None, error=None)
    if run is not None:
        status.update(
            state=run.state,
            started_at=run.started_at,
            finished_at=run.finished_at,
            error=run.error,
            **{counter: getattr(run, counter) for counter in COUNTERS},
        )
    return status


def try_start(db: Session) -> Optional[int]:
    """Store a new running update; None if one is already running."""
    with _start_lock:
        latest = _latest(db)
        if latest is not None and latest.state == "running":
            return None
        run = CatalogSyncRun(state="running", started_at=datetime.now(UTC))
        db.add(run)
        db.commit()
        return run.run_id


def mark_interrupted_runs(db: Session) -> int:
    """On startup nothing can be importing yet: a "running" run was cut off by a restart."""
    runs = db.query(CatalogSyncRun).filter(CatalogSyncRun.state == "running").all()
    for run in runs:
        run.state = "failed"
        run.finished_at = datetime.now(UTC)
        run.error = INTERRUPTED_MESSAGE
    db.commit()
    if runs:
        logger.warning("Marked %s interrupted catalog update(s) as failed.", len(runs))
    return len(runs)


def run_sync(api_key: str, run_id: int, session_factory: Optional[Callable] = None) -> None:
    """Background task: fetch the TMDB catalog, merge it into the database and store the result."""
    db = (session_factory or SessionLocal)()
    try:
        try:
            catalog = fetch_tmdb_catalog(api_key)
            # Built-in titles: adopted by the import where possible, merged or removed afterwards
            release_placeholder_ids(db)
            result = sync_catalog(db, catalog)
            cleanup = retire_placeholders(db)
            outcome = {
                "state": "done",
                "added": result.added,
                "updated": result.updated,
                "skipped": result.skipped,
                "placeholders_removed": cleanup.merged + cleanup.removed,
                "placeholders_kept": cleanup.kept,
            }
            logger.info("TMDB catalog sync: %s", outcome)
        except Exception as error:  # the run must leave "running" whatever happened
            db.rollback()
            logger.warning("TMDB catalog sync failed: %s", error)
            outcome = {"state": "failed", "error": str(error)[:300]}
        run = db.get(CatalogSyncRun, run_id)
        if run is not None:
            for field, value in outcome.items():
                setattr(run, field, value)
            run.finished_at = datetime.now(UTC)
            db.commit()
    finally:
        db.close()


def start_in_background(db: Session, api_key: str) -> Optional[threading.Thread]:
    """Start an update in a daemon thread (used on startup, where there is no request to attach it to)."""
    run_id = try_start(db)
    if run_id is None:
        return None
    thread = threading.Thread(target=run_sync, args=(api_key, run_id), name="tmdb-catalog-sync", daemon=True)
    thread.start()
    return thread
