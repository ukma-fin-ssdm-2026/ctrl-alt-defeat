"""Shared fixtures of the reliability tests (Lab 9): an isolated database for the application startup."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api import main
from src.api.db.database import Base
from src.api.services import catalog_sync


@pytest.fixture
def startup_db(monkeypatch):
    """
    A fresh in-memory database used by the application startup (lifespan) and the background catalog update,
    so the tests never touch the database of other tests or of the developer.
    """
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "SessionLocal", session_factory)
    monkeypatch.setattr(catalog_sync, "SessionLocal", session_factory)
    monkeypatch.delenv("AUTO_SEED_CATALOG", raising=False)
    yield session_factory
    engine.dispose()
