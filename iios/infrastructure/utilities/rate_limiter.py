"""
iios/infrastructure/utilities/rate_limiter.py
=============================================
Sliding-window rate limiter.
"""

from __future__ import annotations

import collections
import threading
import time
from typing import Optional

__all__ = ["RateLimiter", "RateLimitExceeded"]


class RateLimitExceeded(Exception):
    """Raised when the rate limit is exceeded and wait=False."""


class RateLimiter:
    """Thread-safe sliding-window rate limiter.

    Usage::

        limiter = RateLimiter(limit=100, window=1.0)   # 100 calls/sec
        limiter.acquire()          # blocks if limit reached
        allowed = limiter.try_acquire()   # returns False if limit reached
    """

    def __init__(self, limit: int = 100, window: float = 1.0) -> None:
        self._limit = limit
        self._window = window
        self._calls: collections.deque[float] = collections.deque()
        self._lock = threading.Lock()

    def acquire(self, timeout: Optional[float] = None) -> None:
        """Block until a token is available (or timeout expires)."""
        deadline = time.monotonic() + timeout if timeout is not None else None
        while True:
            with self._lock:
                now = time.monotonic()
                # Remove expired entries
                cutoff = now - self._window
                while self._calls and self._calls[0] < cutoff:
                    self._calls.popleft()
                if len(self._calls) < self._limit:
                    self._calls.append(now)
                    return
                # Calculate wait time
                oldest = self._calls[0]
                wait = self._window - (now - oldest) + 0.001

            if deadline is not None and time.monotonic() + wait > deadline:
                raise RateLimitExceeded(
                    f"Rate limit of {self._limit}/{self._window}s exceeded"
                )
            time.sleep(min(wait, 0.05))

    def try_acquire(self) -> bool:
        """Non-blocking acquire. Returns True if token obtained."""
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._window
            while self._calls and self._calls[0] < cutoff:
                self._calls.popleft()
            if len(self._calls) < self._limit:
                self._calls.append(now)
                return True
        return False

    @property
    def current_count(self) -> int:
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._window
            while self._calls and self._calls[0] < cutoff:
                self._calls.popleft()
            return len(self._calls)

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def window(self) -> float:
        return self._window
