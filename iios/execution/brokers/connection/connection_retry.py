"""iios/execution/brokers/connection/connection_retry.py"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from iios.execution.brokers.broker_constants import (
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    CIRCUIT_BREAKER_RECOVERY_SEC,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF_FACTOR,
    DEFAULT_RETRY_DELAY_SEC,
    RetryPolicy,
)
from iios.execution.brokers.broker_exceptions import CircuitOpenError

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED   = "closed"    # Normal — requests pass through
    OPEN     = "open"      # Tripped — requests fail fast
    HALF_OPEN = "half_open" # Testing — one probe allowed


@dataclass
class RetryConfig:
    policy:         RetryPolicy = RetryPolicy.EXPONENTIAL
    max_retries:    int         = DEFAULT_MAX_RETRIES
    base_delay_sec: float       = DEFAULT_RETRY_DELAY_SEC
    backoff_factor: float       = DEFAULT_RETRY_BACKOFF_FACTOR
    max_delay_sec:  float       = 60.0
    jitter:         bool        = True

    def delay_for_attempt(self, attempt: int) -> float:
        """Return wait seconds before *attempt* (1-indexed)."""
        if self.policy == RetryPolicy.NONE:
            return 0.0
        if self.policy == RetryPolicy.LINEAR:
            d = self.base_delay_sec * attempt
        elif self.policy == RetryPolicy.EXPONENTIAL:
            d = self.base_delay_sec * (self.backoff_factor ** (attempt - 1))
        elif self.policy == RetryPolicy.FIBONACCI:
            a, b = 1, 1
            for _ in range(attempt - 1):
                a, b = b, a + b
            d = self.base_delay_sec * a
        else:
            d = self.base_delay_sec
        d = min(d, self.max_delay_sec)
        if self.jitter:
            import random
            d = d * (0.5 + random.random() * 0.5)
        return d


class CircuitBreaker:
    """
    Simple threshold-based circuit breaker.

    States: CLOSED → (too many failures) → OPEN → (recovery period) → HALF_OPEN →
            (success) → CLOSED  |  (failure) → OPEN
    """

    def __init__(
        self,
        failure_threshold: int   = CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_sec:      float = CIRCUIT_BREAKER_RECOVERY_SEC,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_sec      = recovery_sec
        self._state             = CircuitState.CLOSED
        self._failure_count     = 0
        self._last_open_at:  float | None = None
        self._success_count  = 0

    @property
    def state(self) -> CircuitState:
        self._maybe_transition_to_half_open()
        return self._state

    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def allow_request(self) -> bool:
        s = self.state
        if s == CircuitState.CLOSED:
            return True
        if s == CircuitState.HALF_OPEN:
            return True          # one probe attempt
        raise CircuitOpenError(
            f"Circuit breaker is OPEN (failures={self._failure_count}); "
            f"recovery in {self._remaining_recovery_sec():.0f}s",
            "BAF-073",
        )

    def record_success(self) -> None:
        self._failure_count = 0
        self._success_count += 1
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            if self._state != CircuitState.OPEN:
                logger.warning(
                    "Circuit breaker tripped (failures=%d)", self._failure_count
                )
            self._state = CircuitState.OPEN
            self._last_open_at = time.time()

    def reset(self) -> None:
        self._state         = CircuitState.CLOSED
        self._failure_count = 0
        self._last_open_at  = None

    def _maybe_transition_to_half_open(self) -> None:
        if (
            self._state == CircuitState.OPEN
            and self._last_open_at is not None
            and time.time() - self._last_open_at >= self._recovery_sec
        ):
            logger.info("Circuit breaker entering HALF_OPEN")
            self._state = CircuitState.HALF_OPEN

    def _remaining_recovery_sec(self) -> float:
        if self._last_open_at is None:
            return 0.0
        elapsed = time.time() - self._last_open_at
        return max(0.0, self._recovery_sec - elapsed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state":             self._state.value,
            "failure_count":     self._failure_count,
            "success_count":     self._success_count,
            "failure_threshold": self._failure_threshold,
            "recovery_sec":      self._recovery_sec,
            "last_open_at":      self._last_open_at,
        }


class RetryManager:
    """Combines RetryConfig + CircuitBreaker for a single broker endpoint."""

    def __init__(
        self,
        retry_config:    RetryConfig   | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._retry_config    = retry_config    or RetryConfig()
        self._circuit_breaker = circuit_breaker or CircuitBreaker()

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit_breaker

    @property
    def retry_config(self) -> RetryConfig:
        return self._retry_config

    def should_retry(self, attempt: int) -> bool:
        return attempt <= self._retry_config.max_retries

    def delay_for_attempt(self, attempt: int) -> float:
        return self._retry_config.delay_for_attempt(attempt)

    def record_success(self) -> None:
        self._circuit_breaker.record_success()

    def record_failure(self) -> None:
        self._circuit_breaker.record_failure()

    def allow_request(self) -> bool:
        return self._circuit_breaker.allow_request()

    def to_dict(self) -> dict[str, Any]:
        return {
            "retry_config":    {
                "policy":       self._retry_config.policy.value,
                "max_retries":  self._retry_config.max_retries,
                "base_delay":   self._retry_config.base_delay_sec,
            },
            "circuit_breaker": self._circuit_breaker.to_dict(),
        }
