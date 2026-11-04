"""Email confirmation (FR-001): the activation link is emailed; the token is returned only in demo mode."""

import json
import smtplib
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.db.database import Base
from src.api.db.models import User
from src.api.main import app
from src.api.routers import auth as auth_router
from src.api.services import email as email_service

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

EMAIL_VARIABLES = [
    "DEMO_MODE",
    "BREVO_API_KEY",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_SECURITY",
    "EMAIL_FROM",
    "EMAIL_FROM_NAME",
    "APP_BASE_URL",
    "RENDER_EXTERNAL_URL",
]


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    engine_test.dispose()


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in EMAIL_VARIABLES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    db.query(User).delete()
    db.commit()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[auth_router.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sent(monkeypatch):
    """Captures verification emails instead of delivering them."""
    calls = []
    monkeypatch.setattr(auth_router, "send_verification_email", lambda *args: calls.append(args))
    return calls


def register(client, email="new@example.com", nickname="newbie"):
    return client.post("/api/v1/auth/register", json={"email": email, "nickname": nickname, "password": "Password123"})


def test_registration_emails_the_link_and_hides_the_token(client, db_session, sent):
    response = register(client)

    assert response.status_code == 201
    assert response.json()["verification_token"] is None
    user = db_session.query(User).filter(User.email == "new@example.com").one()
    assert sent == [("new@example.com", "newbie", user.verification_token)]
    assert user.email_verified is False


def test_demo_mode_returns_the_token_for_one_click_confirmation(client, db_session, sent, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")

    token = register(client).json()["verification_token"]

    assert token == db_session.query(User).one().verification_token
    assert len(sent) == 1


def test_the_emailed_token_activates_the_account(client, db_session, sent):
    register(client)
    token = sent[0][2]

    response = client.get("/api/v1/auth/verify", params={"token": token})

    assert response.status_code == 200
    user = db_session.query(User).one()
    assert user.email_verified is True and user.status == "active"


def test_resend_issues_a_new_link_for_an_unverified_account(client, db_session, sent):
    register(client)
    first_token = sent[0][2]

    response = client.post("/api/v1/auth/resend-verification", json={"email": " NEW@example.com "})

    assert response.status_code == 202
    new_token = sent[1][2]
    assert new_token != first_token
    assert client.get("/api/v1/auth/verify", params={"token": first_token}).status_code == 400
    assert client.get("/api/v1/auth/verify", params={"token": new_token}).status_code == 200


def test_resend_does_not_reveal_whether_an_account_exists(client, db_session, sent):
    register(client)
    client.get("/api/v1/auth/verify", params={"token": sent[0][2]})

    verified = client.post("/api/v1/auth/resend-verification", json={"email": "new@example.com"})
    unknown = client.post("/api/v1/auth/resend-verification", json={"email": "nobody@example.com"})

    assert verified.status_code == unknown.status_code == 202
    assert verified.json() == unknown.json()
    assert len(sent) == 1


# --- Email transports ---------------------------------------------------------------------------


def test_verification_link_points_to_the_public_site(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "https://pislya-tytriv.example/")

    assert email_service.verification_link("a b&c") == "https://pislya-tytriv.example/verify-email?token=a+b%26c"


def test_render_address_is_used_when_app_base_url_is_not_set(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://pislya-tytriv-4duj.onrender.com")

    assert email_service.verification_link("t").startswith("https://pislya-tytriv-4duj.onrender.com/verify-email?")


def test_without_configuration_the_message_goes_to_the_log(caplog):
    with caplog.at_level("WARNING"):
        backend = email_service.send_verification_email("x@example.com", "Ann", "tok123")

    assert backend == "console"
    assert "http://localhost:5173/verify-email?token=tok123" in caplog.text


def test_brevo_api_receives_the_message(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "test-key")
    monkeypatch.setenv("EMAIL_FROM", "team@example.com")
    captured = {}

    class Response:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        captured.update(url=request.full_url, headers=dict(request.header_items()), body=json.loads(request.data))
        return Response()

    monkeypatch.setattr(email_service.urllib.request, "urlopen", fake_urlopen)

    assert email_service.send_verification_email("x@example.com", "<Ann>", "tok123") == "brevo"
    assert captured["url"] == "https://api.brevo.com/v3/smtp/email"
    assert captured["headers"]["Api-key"] == "test-key"
    assert captured["body"]["to"] == [{"email": "x@example.com"}]
    assert captured["body"]["sender"]["email"] == "team@example.com"
    assert "verify-email?token=tok123" in captured["body"]["textContent"]
    assert "&lt;Ann&gt;" in captured["body"]["htmlContent"]


def test_brevo_failure_is_logged_not_raised(monkeypatch, caplog):
    monkeypatch.setenv("BREVO_API_KEY", "bad-key")

    def failing(request, timeout):
        raise OSError("401 Unauthorized")

    monkeypatch.setattr(email_service.urllib.request, "urlopen", failing)

    with caplog.at_level("ERROR"):
        assert email_service.send_verification_email("x@example.com", "Ann", "t") is None
    assert "was not sent" in caplog.text


@pytest.mark.parametrize("security, port, client_class", [("starttls", 587, "SMTP"), ("ssl", 465, "SMTP_SSL")])
def test_smtp_delivery(monkeypatch, security, port, client_class):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "mailer")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("SMTP_SECURITY", security)
    server = MagicMock()
    server.__enter__.return_value = server
    factory = MagicMock(return_value=server)
    monkeypatch.setattr(email_service.smtplib, client_class, factory)

    assert email_service.send_email("x@example.com", "Subject", "text", "<p>html</p>") == "smtp"
    assert factory.call_args.args[:2] == ("smtp.example.com", port)
    server.login.assert_called_once_with("mailer", "app-password")
    assert server.starttls.called is (security == "starttls")
    message = server.send_message.call_args.args[0]
    assert message["To"] == "x@example.com"


def test_smtp_error_becomes_email_error(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_service.smtplib, "SMTP", MagicMock(side_effect=smtplib.SMTPConnectError(421, "busy")))

    with pytest.raises(email_service.EmailError):
        email_service.send_email("x@example.com", "S", "t", "h")


def test_brevo_non_success_status_is_an_error(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "k")

    class Response:
        status = 302

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(email_service.urllib.request, "urlopen", lambda request, timeout: Response())

    with pytest.raises(email_service.EmailError):
        email_service.send_email("x@example.com", "S", "t", "h")


def test_unique_tokens_are_not_reused(client, db_session, sent):
    register(client, email=f"{uuid.uuid4().hex[:6]}@example.com", nickname="a1")
    register(client, email=f"{uuid.uuid4().hex[:6]}@example.com", nickname="a2")

    assert sent[0][2] != sent[1][2]
