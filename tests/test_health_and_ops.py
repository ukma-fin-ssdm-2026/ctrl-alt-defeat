"""Operational endpoints and deployment helpers (REL-001)."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from src.api.db.database import normalize_database_url
from src.api.frontend import mount_frontend
from src.api.main import app
from src.api.routers.health import get_db


def test_health_reports_ok_when_database_answers():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_liveness_answers_without_the_database():
    broken = MagicMock()
    broken.execute.side_effect = OperationalError("SELECT 1", {}, Exception("connection refused"))
    app.dependency_overrides[get_db] = lambda: broken
    try:
        response = TestClient(app).get("/health/live")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    broken.execute.assert_not_called()


def test_health_reports_503_when_database_is_down():
    broken = MagicMock()
    broken.execute.side_effect = OperationalError("SELECT 1", {}, Exception("connection refused"))
    app.dependency_overrides[get_db] = lambda: broken
    try:
        response = TestClient(app).get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}


@pytest.mark.parametrize(
    "url, expected",
    [
        ("postgres://u:p@host:5432/db", "postgresql+psycopg2://u:p@host:5432/db"),
        ("postgresql://u:p@host/db", "postgresql+psycopg2://u:p@host/db"),
        ("postgresql+psycopg2://u:p@host/db", "postgresql+psycopg2://u:p@host/db"),
        ("sqlite:///./app.db", "sqlite:///./app.db"),
    ],
)
def test_database_url_from_hosting_provider_is_normalized(url, expected):
    assert normalize_database_url(url) == expected


@pytest.fixture
def frontend_client(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>SPA</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('app')", encoding="utf-8")
    (dist / "logo.png").write_bytes(b"PNG")
    (tmp_path / "secret.txt").write_text("top secret", encoding="utf-8")

    site = FastAPI()

    @site.get("/api/v1/ping")
    def ping():
        return {"pong": True}

    assert mount_frontend(site, str(dist)) is True
    return TestClient(site)


@pytest.mark.parametrize("path", ["/", "/movies/42", "/profile"])
def test_frontend_routes_fall_back_to_index(frontend_client, path):
    response = frontend_client.get(path)

    assert response.status_code == 200
    assert response.text == "<html>SPA</html>"


def test_frontend_static_files_are_served(frontend_client):
    assert frontend_client.get("/assets/app.js").text == "console.log('app')"
    assert frontend_client.get("/logo.png").content == b"PNG"


def test_api_routes_are_not_shadowed_by_the_frontend(frontend_client):
    assert frontend_client.get("/api/v1/ping").json() == {"pong": True}
    assert frontend_client.get("/api/v1/missing").status_code == 404
    assert frontend_client.get("/health").status_code == 404


@pytest.mark.parametrize("path", ["/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"])
def test_frontend_never_serves_files_outside_dist(frontend_client, path):
    response = frontend_client.get(path)

    assert "top secret" not in response.text


def test_mount_frontend_needs_a_built_index(tmp_path):
    assert mount_frontend(FastAPI(), str(tmp_path)) is False


def test_empty_database_url_falls_back_to_sqlite():
    import os
    import subprocess
    import sys
    from pathlib import Path

    env = {**os.environ, "DATABASE_URL": ""}
    code = "from src.api.db.database import DATABASE_URL; print(DATABASE_URL)"
    root = Path(__file__).resolve().parents[1]

    result = subprocess.run([sys.executable, "-c", code], cwd=root, env=env, capture_output=True, text=True, check=True)

    assert result.stdout.strip() == "sqlite:///./app.db"
