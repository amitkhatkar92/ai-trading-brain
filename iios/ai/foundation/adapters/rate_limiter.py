"""
rate_limiter.py — iios.ai.foundation.adapters
=============================================
:class:`RateLimiter` — sliding-window token-per-minute and
request-per-minute rate enforcement for AI provider calls.

A1 AI Foundation — Phase 3, Module 4
"""
from __future__ import annotations

import collections
import threading
import time
from dataclasses import dataclass
from typing import Any, Deque, Dict

from .constants import DEFAULT_RATE_LIMIT_RPM, DEFAULT_RATE_LIMIT_TPM, SCHEMA_VERSION


@dataclass(frozen=True)
class RateLimitSnapshot:
    """Immutable point-in-time rate-limit status."""
    provider_id:      str
    tokens_per_min:   int
    requests_per_min: int
    tokens_used_1m:   int
    requests_used_1m: int
    token_headroom:   int
    request_headroom: int
    is_token_limited: bool
    is_req_limited:   bool
    schema:           str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id":      self.provider_id,
            "tokens_per_min":   self.tokens_per_min,
            "requests_per_min": self.requests_per_min,
            "tokens_used_1m":   self.tokens_used_1m,
            "requests_used_1m": self.requests_used_1m,
            "token_headroom":   self.token_headroom,
            "request_headroom": self.request_headroom,
            "is_token_limited": self.is_token_limited,
            "is_req_limited":   self.is_req_limited,
        }


class RateLimiter:
    """
    Thread-safe sliding-window rate limiter (1-minute window).

    Tracks two independent budgets:
    * Token-per-minute (TPM) — based on token counts.
    * Request-per-minute (RPM) — based on request counts.

    ``check()`` returns immediately with a boolean and an optional wait
    duration.  ``record()`` registers a completed call.

    Usage::

        limiter = RateLimiter(provider_id="openai", tpm=100_000, rpm=500)
        ok, wait_s = limiter.check(tokens=512)
        if not ok:
            time.sleep(wait_s)
        # perform the API call
        limiter.record(tokens=512)
    """

    _WINDOW_S: float = 60.0

    def __init__(
        self,
        provider_id: str,
        tpm:         int = DEFAULT_RATE_LIMIT_TPM,
        rpm:         int = DEFAULT_RATE_LIMIT_RPM,
    ) -> None:
        self._provider_id  = provider_id
        self._tpm          = tpm
        self._rpm          = rpm
        self._lock         = threading.Lock()
        self._token_log:   Deque[tuple[float, int]] = collections.deque()  # (ts, tokens)
        self._request_log: Deque[float]             = collections.deque()  # ts

    # ── Public interface ───────────────────────────────────────────────────────

    def check(self, tokens: int = 0) -> tuple[bool, float]:
        """
        Check whether a request with the given token count is within rate limits.

        Returns
        -------
        (allowed, wait_seconds)
            ``allowed`` is ``True`` iff the call can proceed now.
            ``wait_seconds`` is the suggested wait if not allowed.
        """
        with self._lock:
            now = time.monotonic()
            self._prune(now)
            token_sum = sum(t for _, t in self._token_log)
            req_count = len(self._request_log)

            token_ok = (token_sum + tokens) <= self._tpm
            req_ok   = (req_count + 1) <= self._rpm

            if token_ok and req_ok:
                return True, 0.0

            # Estimate wait until oldest entry ages out
            wait = self._WINDOW_S  # default: retry after full window
            if self._token_log:
                wait = min(wait, self._WINDOW_S - (now - self._token_log[0][0]))
            if self._request_log:
                wait = min(wait, self._WINDOW_S - (now - self._request_log[0]))
            return False, max(0.0, wait)

    def record(self, tokens: int = 0) -> None:
        """Register a completed API call that consumed ``tokens`` tokens."""
        now = time.monotonic()
        with self._lock:
            if tokens > 0:
                self._token_log.append((now, tokens))
            self._request_log.append(now)
            self._prune(now)

    def snapshot(self) -> RateLimitSnapshot:
        """Return an immutable status snapshot."""
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            token_used = sum(t for _, t in self._token_log)
            req_used   = len(self._request_log)
        return RateLimitSnapshot(
            provider_id      = self._provider_id,
            tokens_per_min   = self._tpm,
            requests_per_min = self._rpm,
            tokens_used_1m   = token_used,
            requests_used_1m = req_used,
            token_headroom   = max(0, self._tpm - token_used),
            request_headroom = max(0, self._rpm - req_used),
            is_token_limited = token_used >= self._tpm,
            is_req_limited   = req_used   >= self._rpm,
        )

    # ── Internals ──────────────────────────────────────────────────────────────

    def _prune(self, now: float) -> None:
        """Discard entries older than the sliding window."""
        cutoff = now - self._WINDOW_S
        while self._token_log   and self._token_log[0][0]   < cutoff:
            self._token_log.popleft()
        while self._request_log and self._request_log[0]    < cutoff:
            self._request_log.popleft()

    def __repr__(self) -> str:
        snap = self.snapshot()
        return (
            f"<RateLimiter provider={self._provider_id!r} "
            f"tpm={snap.tokens_used_1m}/{self._tpm} "
            f"rpm={snap.requests_used_1m}/{self._rpm}>"
        )
