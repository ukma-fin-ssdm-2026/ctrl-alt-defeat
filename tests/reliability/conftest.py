"""Shared fixtures of the reliability tests (Lab 9): an isolated database for the application startup."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api import main
from src.api.db.database import Base
from src.api.services import catalog_sync


@pytest.fixture
def startup_db(monkeypatch, tmp_path):
    """
    A fresh temporary database used by the application startup
    and the background catalog update.
    """
    db_path = tmp_path / "startup.db"

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "SessionLocal", session_factory)
    monkeypatch.setattr(catalog_sync, "SessionLocal", session_factory)
    monkeypatch.delenv("AUTO_SEED_CATALOG", raising=False)

    yield session_factory

    engine.dispose()
