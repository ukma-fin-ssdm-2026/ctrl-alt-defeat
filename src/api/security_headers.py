"""
HTTP security headers of every response (threat model: clickjacking, MIME sniffing, injected scripts).

The Content-Security-Policy allows only this site's own scripts, styles and requests, posters and photos
from image.tmdb.org and the YouTube player (youtube-nocookie.com) for trailers. The interactive API docs
(/api-docs, /redoc) load Swagger UI / ReDoc from a CDN with inline scripts, so they get every header
except the CSP.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "img-src 'self' data: https://image.tmdb.org",
        # React and Tailwind set inline style attributes
        "style-src 'self' 'unsafe-inline'",
        "script-src 'self'",
        "connect-src 'self'",
        # Trailers on the page of a title (US-013): the YouTube player without tracking cookies
        "frame-src https://www.youtube-nocookie.com",
        "font-src 'self' data:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

DOCS_PATHS = ("/api-docs", "/redoc")


class SecurityHeadersMiddleware:
    """Pure ASGI middleware: adds the headers without buffering the response body."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        with_csp = not scope.get("path", "").startswith(DOCS_PATHS)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                extra = dict(SECURITY_HEADERS)
                if with_csp:
                    extra["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
                for name, value in extra.items():
                    if name.lower().encode() not in present:
                        headers.append((name.lower().encode(), value.encode()))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
