"""Demo / seed accounts come only from the environment (SEC-001), one source for seeding and the UI hint."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import User
from src.api.main import app
from src.api.services.auth import hash_password, verify_password
from src.api.services.demo_accounts import get_seed_accounts, seed_default_users

SEED_VARIABLES = [
    "DEMO_MODE",
    "SEED_ADMIN_EMAIL",
    "SEED_ADMIN_PASSWORD",
    "SEED_ADMIN_NICKNAME",
    "SEED_USER_EMAIL",
    "SEED_USER_PASSWORD",
    "SEED_USER_NICKNAME",
]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in SEED_VARIABLES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def both_accounts(monkeypatch):
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin-from-env")
    monkeypatch.setenv("SEED_USER_PASSWORD", "user-from-env")


def test_no_passwords_means_no_accounts(db):
    assert get_seed_accounts() == []
    seed_default_users(db)
    assert db.query(User).count() == 0


def test_account_is_created_only_for_a_configured_password(monkeypatch, db):
    monkeypatch.setenv("SEED_USER_PASSWORD", "user-from-env")

    seed_default_users(db)

    users = db.query(User).all()
    assert [(u.email, u.nickname, u.role) for u in users] == [("user@example.com", "cinema_fan", "user")]


def test_seed_creates_verified_active_accounts_with_env_passwords(both_accounts, monkeypatch, db):
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "  Boss@Example.COM ")

    seed_default_users(db)

    admin = db.query(User).filter(User.role == "admin").one()
    user = db.query(User).filter(User.role == "user").one()
    assert admin.email == "boss@example.com"
    assert verify_password("admin-from-env", admin.password_hash)
    assert verify_password("user-from-env", user.password_hash)
    assert admin.email_verified and user.email_verified
    assert admin.status == user.status == "active"


def test_seed_is_idempotent(both_accounts, db):
    seed_default_users(db)
    seed_default_users(db)

    assert db.query(User).count() == 2


def test_existing_account_gets_the_configured_password_and_role_but_keeps_a_ban(both_accounts, db):
    db.add(
        User(
            email="admin@gmail.com",
            nickname="admin",
            password_hash=hash_password("old-hardcoded-password"),
            role="user",
            email_verified=False,
            status="banned",
        )
    )
    db.commit()

    seed_default_users(db)

    admin = db.query(User).filter(User.email == "admin@gmail.com").one()
    assert verify_password("admin-from-env", admin.password_hash)
    assert admin.role == "admin"
    assert admin.email_verified is True
    assert admin.status == "banned"


def test_taken_nickname_skips_the_seed_account(monkeypatch, db):
    monkeypatch.setenv("SEED_USER_PASSWORD", "user-from-env")
    db.add(User(email="someone@else.com", nickname="cinema_fan", password_hash=hash_password("x" * 8)))
    db.commit()

    seed_default_users(db)

    assert db.query(User).filter(User.email == "user@example.com").first() is None


def test_demo_hint_is_hidden_without_demo_mode(both_accounts):
    response = TestClient(app).get("/api/v1/auth/demo-accounts")

    assert response.status_code == 200
    assert response.json() == {"enabled": False, "accounts": []}


def test_demo_hint_lists_the_seed_accounts_in_demo_mode(both_accounts, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")

    response = TestClient(app).get("/api/v1/auth/demo-accounts")

    assert response.json() == {
        "enabled": True,
        "accounts": [
            {"role": "admin", "email": "admin@gmail.com", "password": "admin-from-env"},
            {"role": "user", "email": "user@example.com", "password": "user-from-env"},
        ],
    }


def test_demo_mode_without_accounts_shows_nothing(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "yes")

    assert TestClient(app).get("/api/v1/auth/demo-accounts").json() == {"enabled": False, "accounts": []}


def test_jwt_secret_is_random_per_process_when_not_configured():
    root = Path(__file__).resolve().parents[1]
    env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET_KEY"}
    code = "from src.api.services.auth import JWT_SECRET_KEY as k; print(k)"

    first, second = (
        subprocess.run(
            [sys.executable, "-c", code], cwd=root, env=env, capture_output=True, text=True, check=True
        ).stdout.strip()
        for _ in range(2)
    )

    assert len(first) >= 64
    assert first != second
    assert "ctrl-alt-defeat" not in first


def test_jwt_secret_comes_from_the_environment():
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "JWT_SECRET_KEY": "configured-secret"}
    code = "from src.api.services.auth import JWT_SECRET_KEY as k; print(k)"

    result = subprocess.run([sys.executable, "-c", code], cwd=root, env=env, capture_output=True, text=True, check=True)

    assert result.stdout.strip() == "configured-secret"
