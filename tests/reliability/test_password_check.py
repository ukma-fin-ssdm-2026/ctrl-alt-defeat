"""
Reliability, finding 7 (error handling): a damaged password hash in the database.

Chosen reaction: safe failure for the user (an ordinary 401, no 500 and no internal details) plus an error
in the log, because only an administrator can repair the account.
"""

import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import User
from src.api.main import app
from src.api.routers import auth as auth_router
from src.api.services.auth import hash_password, verify_password

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
LOGGER = "src.api.services.auth"
VALID_HASH = hash_password("another-password")


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.query(User).delete()
    for nickname, stored in (("damaged", "not-a-bcrypt-hash"), ("truncated", "$2b$12$short")):
        db.add(
            User(
                user_id=uuid.uuid4(),
                email=f"{nickname}@example.com",
                password_hash=stored,
                nickname=nickname,
                role="user",
                email_verified=True,
                status="active",
            )
        )
    db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[auth_router.get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    db.close()


@pytest.mark.parametrize(
    "email, stored",
    [
        ("damaged@example.com", "not-a-bcrypt-hash"),
        # bcrypt panics on this one (PanicException is not an Exception): before the fix the login answered 500
        ("truncated@example.com", "$2b$12$short"),
    ],
)
def test_login_with_a_damaged_hash_is_an_ordinary_401(client, caplog, email, stored):
    with caplog.at_level(logging.ERROR, logger=LOGGER):
        response = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert stored not in response.text
    # The problem is visible to the developers, without the hash or the password in the log
    assert "stored password hash is invalid" in caplog.text
    assert stored not in caplog.text and "Password123!" not in caplog.text


@pytest.mark.parametrize(
    "password, stored, logged",
    [
        ("Password123!", None, True),  # account without a hash
        ("Password123!", "", True),
        ("", VALID_HASH, False),  # empty password
        (None, VALID_HASH, False),
        ("Password123!", "$2b$12$short", True),  # truncated hash: bcrypt itself would panic
        ("Password123!", VALID_HASH[:-1], True),  # one character missing
        ("Password123!", VALID_HASH + "x", True),  # one character too many
        ("Password123!", 12345, True),  # not text at all
    ],
)
def test_bad_inputs_never_raise(caplog, password, stored, logged):
    with caplog.at_level(logging.ERROR, logger=LOGGER):
        assert verify_password(password, stored) is False

    assert ("Password check failed" in caplog.text) is logged


def test_wrong_password_is_not_an_error():
    stored = hash_password("Password123!")

    assert verify_password("Password123!", stored) is True
    assert verify_password("wrong", stored) is False
