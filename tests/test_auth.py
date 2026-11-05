import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import User
from src.api.main import app
from src.api.routers.auth import get_db, get_current_admin
from src.api.services.auth import (
    decode_access_token,
    hash_password,
    verify_password,
)

# Isolated in-memory SQLite database for authentication tests
engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(autouse=True)
def no_email_transport(monkeypatch):
    """No email is sent in these tests: the activation link is only logged (delivery is covered in
    test_email_verification.py)."""
    for name in ("GOOGLE_SCRIPT_URL", "BREVO_API_KEY", "SMTP_HOST"):
        monkeypatch.delenv(name, raising=False)


def emailed_token(email: str) -> str:
    """The token from the activation email (FR-001): the API never returns it."""
    db = TestingSessionLocal()
    try:
        return db.query(User).filter(User.email == email).one().verification_token
    finally:
        db.close()


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_password_hashing_and_verification_sec001():
    """
    Verify bcrypt hashing with salt and plain text verification (SEC-001).
    """
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed.startswith("$2b$")
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_register_user_success(client: TestClient, db_session):
    """
    FR-001 / US-011: Register new account in pending state with verification token.
    """
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "nickname": f"nick_{uuid.uuid4().hex[:6]}",
        "password": "validPassword123",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == unique_email
    # The token reaches the user only by email
    assert "verification_token" not in data

    user = db_session.query(User).filter(User.email == unique_email).first()
    assert user is not None
    assert user.status == "pending"
    assert user.email_verified is False
    assert user.password_hash.startswith("$2b$")


def test_register_duplicate_email(client: TestClient):
    """
    FR-001: Reject registration if email is already taken.
    """
    unique_email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "nickname": f"nick_{uuid.uuid4().hex[:6]}",
        "password": "validPassword123",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    payload2 = {
        "email": unique_email,
        "nickname": f"different_{uuid.uuid4().hex[:6]}",
        "password": "anotherPassword123",
    }
    res2 = client.post("/api/v1/auth/register", json=payload2)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_register_duplicate_nickname(client: TestClient):
    """
    FR-001: Reject registration if nickname is already taken.
    """
    unique_nick = f"same_{uuid.uuid4().hex[:6]}"
    res1 = client.post(
        "/api/v1/auth/register",
        json={"email": f"u1_{uuid.uuid4().hex[:6]}@example.com", "nickname": unique_nick, "password": "pass123456"},
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/v1/auth/register",
        json={"email": f"u2_{uuid.uuid4().hex[:6]}@example.com", "nickname": unique_nick, "password": "pass123456"},
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "NICKNAME_ALREADY_EXISTS"


def test_register_invalid_email(client: TestClient):
    """
    Validation: Reject malformed email formats.
    """
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "nickname": "validnick", "password": "validPassword123"},
    )
    assert response.status_code == 422


def test_register_short_password(client: TestClient):
    """
    Validation: Reject passwords shorter than 6 characters.
    """
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "nickname": "validnick", "password": "123"},
    )
    assert response.status_code == 422


def test_verify_email_success(client: TestClient, db_session):
    """
    FR-001 / US-011: Confirm email address with token and activate account.
    """
    email = f"verify_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "nickname": f"nick_{uuid.uuid4().hex[:6]}", "password": "validPassword123"},
    )
    token = emailed_token(email)

    verify_res = client.get(f"/api/v1/auth/verify?token={token}")
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "active"

    user = db_session.query(User).filter(User.email == email).first()
    assert user.email_verified is True
    assert user.status == "active"
    assert user.verification_token is None


def test_verify_email_invalid_token(client: TestClient):
    """
    FR-001: Return 400 for invalid or non-existent token.
    """
    response = client.get("/api/v1/auth/verify?token=non_existent_token_123")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_VERIFICATION_TOKEN"


def test_login_unverified_user_forbidden(client: TestClient):
    """
    FR-001 / US-011: Reject login attempts if email is not yet verified.
    """
    email = f"unverified_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "nickname": f"nick_{uuid.uuid4().hex[:6]}", "password": "validPassword123"},
    )

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "validPassword123"})
    assert login_res.status_code == 403
    assert login_res.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"


def test_login_success_t037(client: TestClient):
    """
    T-037 / US-011 / FR-001: Successful login, JWT token issuance, and HttpOnly cookie set.
    """
    # Trace: T-037
    email = f"login_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "nickname": f"nick_{uuid.uuid4().hex[:6]}", "password": "validPassword123"},
    )
    token = emailed_token(email)
    client.get(f"/api/v1/auth/verify?token={token}")

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "validPassword123"})
    assert login_res.status_code == 200

    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email

    jwt_token = data["access_token"]
    decoded = decode_access_token(jwt_token)
    assert decoded["email"] == email
    assert decoded["role"] == "user"

    assert "access_token" in login_res.cookies


def test_login_invalid_password(client: TestClient):
    """
    SEC-001: Reject login with wrong password.
    """
    email = f"pw_test_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "nickname": f"nick_{uuid.uuid4().hex[:6]}", "password": "correctPassword123"},
    )
    token = emailed_token(email)
    client.get(f"/api/v1/auth/verify?token={token}")

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "wrongPassword123"})
    assert login_res.status_code == 401
    assert login_res.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_banned_user(client: TestClient, db_session):
    """
    FR-009: a banned user can still log in and sees the ban (type and period) in the profile.
    """
    email = f"banned_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "nickname": f"nick_{uuid.uuid4().hex[:6]}", "password": "password123"},
    )
    token = emailed_token(email)
    client.get(f"/api/v1/auth/verify?token={token}")

    user = db_session.query(User).filter(User.email == email).first()
    user.status = "banned"
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert login_res.status_code == 200
    assert login_res.json()["user"]["ban"]["ban_type"] == "permanent"


def test_get_current_user_profile_via_bearer(client: TestClient):
    """
    US-011: Retrieve authenticated profile using Bearer Authorization header.
    """
    email = f"me_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "nickname": f"nick_{uuid.uuid4().hex[:6]}", "password": "password123"},
    )
    client.get(f"/api/v1/auth/verify?token={emailed_token(email)}")
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_res.json()["access_token"]

    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email


def test_get_current_user_profile_via_cookie(client: TestClient):
    """
    US-011: Retrieve authenticated profile using HttpOnly cookie.
    """
    email = f"cookie_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "nickname": f"nick_{uuid.uuid4().hex[:6]}", "password": "password123"},
    )
    client.get(f"/api/v1/auth/verify?token={emailed_token(email)}")
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    cookie_token = login_res.cookies.get("access_token")

    client.cookies.set("access_token", cookie_token)
    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email


def test_get_current_user_unauthorized(client: TestClient):
    """
    US-011: Return 401 when no token or cookie is supplied.
    """
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_get_current_user_invalid_token(client: TestClient):
    """
    US-011: Return 401 when an invalid token is supplied.
    """
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.fake.token"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_logout(client: TestClient):
    """
    US-011: Logout endpoint clears session cookie.
    """
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"


def test_admin_dependency_enforcement(client: TestClient, db_session):
    """
    FR-008, FR-009: Test get_current_admin dependency behavior.
    """
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@example.com"
    admin = User(
        email=admin_email,
        nickname=f"admin_{uuid.uuid4().hex[:4]}",
        password_hash=hash_password("adminpass"),
        role="admin",
        email_verified=True,
        status="active",
    )
    user_email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    user = User(
        email=user_email,
        nickname=f"user_{uuid.uuid4().hex[:4]}",
        password_hash=hash_password("userpass"),
        role="user",
        email_verified=True,
        status="active",
    )
    db_session.add(admin)
    db_session.add(user)
    db_session.commit()

    # Admin passes
    assert get_current_admin(admin) == admin

    # Regular user is forbidden (403)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        get_current_admin(user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "FORBIDDEN"
