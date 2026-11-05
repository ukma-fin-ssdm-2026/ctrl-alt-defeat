"""
Email delivery for account verification (FR-001).

The transport is chosen from the environment:
    GOOGLE_SCRIPT_URL + GOOGLE_SCRIPT_SECRET
                             Google Apps Script web app (scripts/google-apps-script/mailer.gs) that sends from
                             a Gmail account over HTTPS; needs no own domain and works where SMTP is blocked
                             (Render free web services)
    BREVO_API_KEY            Brevo transactional HTTP API (needs a sender on an own domain)
    SMTP_HOST [+ SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_SECURITY=starttls|ssl|none]
    neither                  the message is only written to the server log (local development)
Common settings: EMAIL_FROM (sender address), EMAIL_FROM_NAME, APP_BASE_URL (public site address for links;
on Render RENDER_EXTERNAL_URL is used when it is not set).
"""

import html as html_lib
import json
import logging
import os
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage
from typing import Optional
from urllib.parse import urlencode, urlparse

logger = logging.getLogger(__name__)

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
GOOGLE_SCRIPT_HOST = "script.google.com"
TIMEOUT_SECONDS = 10


class EmailError(Exception):
    """The message could not be delivered to the email provider."""


def email_backend() -> str:
    if os.getenv("GOOGLE_SCRIPT_URL"):
        return "google_script"
    if os.getenv("BREVO_API_KEY"):
        return "brevo"
    if os.getenv("SMTP_HOST"):
        return "smtp"
    return "console"


def app_base_url() -> str:
    """Public site address for links: APP_BASE_URL, else the address Render sets, else the Vite dev server."""
    return (os.getenv("APP_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL") or "http://localhost:5173").rstrip("/")


def verification_link(token: str) -> str:
    return f"{app_base_url()}/verify-email?{urlencode({'token': token})}"


def _sender() -> tuple:
    return os.getenv("EMAIL_FROM", "no-reply@localhost"), os.getenv("EMAIL_FROM_NAME", "Після титрів")


def _send_brevo(to: str, subject: str, text: str, html: str) -> None:
    sender_email, sender_name = _sender()
    body = json.dumps(
        {
            "sender": {"email": sender_email, "name": sender_name},
            "to": [{"email": to}],
            "subject": subject,
            "textContent": text,
            "htmlContent": html,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        BREVO_URL,
        data=body,
        method="POST",
        headers={
            "api-key": os.environ["BREVO_API_KEY"],
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        # The URL is the fixed https Brevo endpoint above, never user input
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # nosec B310
            if response.status >= 300:
                raise EmailError(f"Brevo answered {response.status}")
    except EmailError:
        raise
    except Exception as error:  # network errors, HTTP 4xx/5xx
        raise EmailError(f"Brevo request failed: {error}") from error


def _google_script_url() -> str:
    url = os.environ["GOOGLE_SCRIPT_URL"].strip()
    parsed = urlparse(url)
    # Only a deployed Apps Script web app: the secret must never be posted anywhere else
    if parsed.scheme != "https" or parsed.hostname != GOOGLE_SCRIPT_HOST or not parsed.path.startswith("/macros/"):
        raise EmailError("GOOGLE_SCRIPT_URL must be https://script.google.com/macros/s/<id>/exec")
    return url


def _send_google_script(to: str, subject: str, text: str, html: str) -> None:
    _, sender_name = _sender()
    body = json.dumps(
        {
            "secret": os.getenv("GOOGLE_SCRIPT_SECRET", ""),
            "to": to,
            "subject": subject,
            "text": text,
            "html": html,
            "name": sender_name,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        _google_script_url(), data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        # Apps Script answers through a redirect to script.googleusercontent.com, which urllib follows
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # nosec B310
            result = json.loads(response.read().decode("utf-8") or "{}")
    except Exception as error:  # network errors, HTTP errors, a non-JSON answer
        raise EmailError(f"Google Apps Script request failed: {error}") from error
    if not result.get("ok"):
        raise EmailError(f"Google Apps Script refused the message: {result.get('error', 'unknown error')}")


def _send_smtp(to: str, subject: str, text: str, html: str) -> None:
    sender_email, sender_name = _sender()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{sender_name} <{sender_email}>"
    message["To"] = to
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    host = os.environ["SMTP_HOST"]
    security = os.getenv("SMTP_SECURITY", "starttls").lower()
    port = int(os.getenv("SMTP_PORT") or (465 if security == "ssl" else 587))
    user, password = os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")
    context = ssl.create_default_context()
    try:
        if security == "ssl":
            server = smtplib.SMTP_SSL(host, port, timeout=TIMEOUT_SECONDS, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=TIMEOUT_SECONDS)
        with server:
            if security == "starttls":
                server.starttls(context=context)
            if user:
                server.login(user, password or "")
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailError(f"SMTP delivery failed: {error}") from error


def send_email(to: str, subject: str, text: str, html: str) -> str:
    """Deliver one message; returns the transport used. Raises EmailError on failure."""
    backend = email_backend()
    if backend == "google_script":
        _send_google_script(to, subject, text, html)
    elif backend == "brevo":
        _send_brevo(to, subject, text, html)
    elif backend == "smtp":
        _send_smtp(to, subject, text, html)
    else:
        logger.warning(
            "Email is not configured (GOOGLE_SCRIPT_URL / BREVO_API_KEY / SMTP_HOST). Message to %s:\n%s", to, text
        )
    return backend


def send_verification_email(to: str, nickname: str, token: str) -> Optional[str]:
    """Send the activation link (FR-001). Errors are logged, not raised: it runs after the response."""
    link = verification_link(token)
    subject = "Підтвердіть пошту — «Після титрів»"
    text = (
        f"Вітаємо, {nickname}!\n\n"
        f"Щоб активувати акаунт на сайті «Після титрів», перейдіть за посиланням:\n{link}\n\n"
        "Якщо ви не реєструвалися, просто проігноруйте цей лист."
    )
    html = (
        f"<p>Вітаємо, {_escape(nickname)}!</p>"
        "<p>Щоб активувати акаунт на сайті «Після титрів», натисніть кнопку:</p>"
        f'<p><a href="{_escape(link)}" style="background:#eab308;color:#111827;padding:10px 18px;'
        'border-radius:8px;text-decoration:none;font-weight:bold">Підтвердити пошту</a></p>'
        f'<p>Або відкрийте посилання: <a href="{_escape(link)}">{_escape(link)}</a></p>'
        "<p>Якщо ви не реєструвалися, просто проігноруйте цей лист.</p>"
    )
    try:
        return send_email(to, subject, text, html)
    except EmailError as error:
        logger.error("Verification email to %s was not sent: %s", to, error)
        return None


def _escape(value: str) -> str:
    return html_lib.escape(value, quote=True)
