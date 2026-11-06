"""
Catalog update from TMDB started by an administrator (FR-012).

The import takes about a minute (three sections of popular titles plus details of each title),
so it runs in the background and the admin panel polls its status. One import at a time.
"""

import logging
import os
import threading
from datetime import UTC, datetime
from typing import Any, Callable, Dict, Optional

from src.api.db.database import SessionLocal
from src.api.services.tmdb import fetch_tmdb_catalog, sync_catalog

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_status: Dict[str, Any] = {
    "state": "idle",
    "started_at": None,
    "finished_at": None,
    "added": 0,
    "updated": 0,
    "skipped": 0,
    "error": None,
}


def tmdb_api_key() -> Optional[str]:
    return os.getenv("TMDB_API_KEY") or None


def get_status() -> Dict[str, Any]:
    with _lock:
        return {**_status, "configured": tmdb_api_key() is not None}


def try_start() -> bool:
    """Mark a new import as running; False if one is already running."""
    with _lock:
        if _status["state"] == "running":
            return False
        _status.update(
            state="running",
            started_at=datetime.now(UTC),
            finished_at=None,
            added=0,
            updated=0,
            skipped=0,
            error=None,
        )
        return True


def run_sync(api_key: str, session_factory: Optional[Callable] = None) -> None:
    """Background task: fetch the TMDB catalog and merge it into the database."""
    db = (session_factory or SessionLocal)()
    try:
        result = sync_catalog(db, fetch_tmdb_catalog(api_key))
        outcome = {"state": "done", "added": result.added, "updated": result.updated, "skipped": result.skipped}
        logger.info("TMDB catalog sync: %s", outcome)
    except Exception as error:  # the status must leave "running" whatever happened
        db.rollback()
        logger.warning("TMDB catalog sync failed: %s", error)
        outcome = {"state": "failed", "error": str(error)[:300]}
    finally:
        db.close()
    with _lock:
        _status.update(finished_at=datetime.now(UTC), **outcome)
