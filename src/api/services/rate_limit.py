"""
Limits per client address: failed logins (brute-force protection of /auth/login), new accounts
(/auth/register), activation and password reset emails; and per user: comments (spam protection).

A client (IP address) that gets the password wrong LOGIN_MAX_FAILURES times within LOGIN_WINDOW_SECONDS
has to wait until the oldest of those failures leaves the window; a successful login clears its record.
The record is kept in memory of the server process: the site runs as one process, so this is enough,
and a restart only forgets the counters.
"""

import math
import threading
import time
from collections import deque
from typing import Callable, Deque, Dict, Optional

from src.api.settings import env_int

LOGIN_MAX_FAILURES = env_int("LOGIN_MAX_FAILURES", 5, minimum=1, maximum=100)
LOGIN_WINDOW_SECONDS = env_int("LOGIN_WINDOW_SECONDS", 60, minimum=1, maximum=3600)
# Mass registration and email bombing: accounts and activation emails per address and hour
REGISTER_MAX_PER_HOUR = env_int("REGISTER_MAX_PER_HOUR", 5, minimum=1, maximum=1000)
RESEND_MAX_PER_HOUR = env_int("RESEND_MAX_PER_HOUR", 5, minimum=1, maximum=1000)
PASSWORD_RESET_MAX_PER_HOUR = env_int("PASSWORD_RESET_MAX_PER_HOUR", 5, minimum=1, maximum=1000)
# Comment spam: comments per user and minute / hour
COMMENTS_MAX_PER_MINUTE = env_int("COMMENTS_MAX_PER_MINUTE", 5, minimum=1, maximum=1000)
COMMENTS_MAX_PER_HOUR = env_int("COMMENTS_MAX_PER_HOUR", 60, minimum=1, maximum=10000)
HOUR_SECONDS = 3600


class AttemptLimiter:
    """Sliding window of failures per key (for logins: the client IP address)."""

    def __init__(self, max_failures: int, window_seconds: float, clock: Callable[[], float] = time.monotonic):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.clock = clock
        self._failures: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> Deque[float]:
        failures = self._failures.get(key, deque())
        while failures and now - failures[0] >= self.window_seconds:
            failures.popleft()
        if not failures:
            self._failures.pop(key, None)
        return failures

    def retry_after(self, key: str) -> Optional[int]:
        """Seconds to wait before the next attempt, or None if attempts are allowed."""
        with self._lock:
            now = self.clock()
            failures = self._recent(key, now)
            if len(failures) < self.max_failures:
                return None
            return max(1, math.ceil(self.window_seconds - (now - failures[0])))

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = self.clock()
            failures = self._recent(key, now)
            failures.append(now)
            self._failures[key] = failures

    def record(self, key: str) -> None:
        """Count an action that is limited whether or not it succeeds (a new account, a sent email)."""
        self.record_failure(key)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = AttemptLimiter(LOGIN_MAX_FAILURES, LOGIN_WINDOW_SECONDS)
register_limiter = AttemptLimiter(REGISTER_MAX_PER_HOUR, HOUR_SECONDS)
resend_limiter = AttemptLimiter(RESEND_MAX_PER_HOUR, HOUR_SECONDS)
password_reset_limiter = AttemptLimiter(PASSWORD_RESET_MAX_PER_HOUR, HOUR_SECONDS)
comment_minute_limiter = AttemptLimiter(COMMENTS_MAX_PER_MINUTE, 60)
comment_hour_limiter = AttemptLimiter(COMMENTS_MAX_PER_HOUR, HOUR_SECONDS)
ALL_LIMITERS = (
    login_limiter,
    register_limiter,
    resend_limiter,
    password_reset_limiter,
    comment_minute_limiter,
    comment_hour_limiter,
)
