"""
rate_limit_engine.py — iios.integration.services
--------------------------------------------------
RateLimitEngine — token-bucket rate limiter for integration connectors.

Supports per-connector and global rate limits. Thread-safe.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_RATE_LIMIT_RPS

_log = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for a token-bucket rate limiter."""
    rps:        float = float(DEFAULT_MAX_RATE_LIMIT_RPS)  # requests per second
    burst:      int   = 10                                  # initial / max tokens

    @property
    def refill_interval_s(self) -> float:
        return 1.0 / self.rps if self.rps > 0 else float("inf")


@dataclass
class RateLimitResult:
    """Result of an acquire() call."""
    allowed:        bool
    bucket_id:      str
    wait_ms:        float    # 0.0 if allowed without waiting
    current_tokens: float
    error:          str = ""


class _TokenBucket:
    """Single token-bucket for one connector/key."""

    def __init__(self, cfg: RateLimitConfig) -> None:
        self._cfg     = cfg
        self._tokens  = float(cfg.burst)
        self._last    = time.monotonic()
        self._lock    = threading.Lock()

    def try_acquire(self, tokens: float = 1.0) -> tuple[bool, float]:
        """
        Attempt to consume tokens without blocking.
        Returns (allowed, current_tokens_after).
        """
        with self._lock:
            now    = time.monotonic()
            elapsed = now - self._last
            refill  = elapsed / self._cfg.refill_interval_s if self._cfg.rps > 0 else 0.0
            self._tokens = min(float(self._cfg.burst), self._tokens + refill)
            self._last   = now
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True, self._tokens
            return False, self._tokens


class RateLimitEngine:
    """
    Manages per-key token-bucket rate limiters.

    Keys typically map to connector_id or service_type. A global
    fallback bucket is applied to all unregistered keys.
    """

    def __init__(self, global_config: Optional[RateLimitConfig] = None) -> None:
        self._lock     = threading.Lock()
        self._buckets: Dict[str, _TokenBucket] = {}
        self._global   = _TokenBucket(global_config or RateLimitConfig())
        self._allowed  = 0
        self._rejected = 0

    # ── Configuration ─────────────────────────────────────────────────────

    def configure(self, key: str, config: RateLimitConfig) -> None:
        with self._lock:
            self._buckets[key] = _TokenBucket(config)

    def remove(self, key: str) -> bool:
        with self._lock:
            if key in self._buckets:
                del self._buckets[key]
                return True
        return False

    # ── Acquire ───────────────────────────────────────────────────────────

    def acquire(
        self,
        key:    str,
        tokens: float = 1.0,
    ) -> RateLimitResult:
        """
        Non-blocking acquire. Returns whether the request is allowed.
        """
        with self._lock:
            bucket = self._buckets.get(key, self._global)

        allowed, current = bucket.try_acquire(tokens)

        with self._lock:
            if allowed:
                self._allowed += 1
            else:
                self._rejected += 1
                _log.debug(f"rate-limit-engine: key={key!r} rejected (tokens={current:.2f})")

        return RateLimitResult(
            allowed        = allowed,
            bucket_id      = key,
            wait_ms        = 0.0,
            current_tokens = current,
            error          = "" if allowed else "Rate limit exceeded",
        )

    def is_limited(self, key: str) -> bool:
        """Return True if the next acquire would be rejected (without consuming)."""
        with self._lock:
            bucket = self._buckets.get(key, self._global)
        _, current = bucket.try_acquire(0)  # 0-token dry run
        return current < 1.0

    # ── Stats ─────────────────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "buckets":  len(self._buckets),
                "allowed":  self._allowed,
                "rejected": self._rejected,
            }
