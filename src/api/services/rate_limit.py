"""
Limit of failed login attempts (brute-force protection of /auth/login).

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

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = AttemptLimiter(LOGIN_MAX_FAILURES, LOGIN_WINDOW_SECONDS)
