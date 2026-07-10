"""iios/integration/providers/provider_health.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from iios.integration.integration_constants import (
    CircuitBreakerState,
    HealthStatus,
    DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
    DEFAULT_CIRCUIT_BREAKER_RESET_SEC,
    DEFAULT_MIN_AVAILABILITY_PCT,
)


@dataclass
class ProviderHealth:
    """
    Real-time health snapshot of a provider.

    Produced by health_check() and tracked by HealthMonitor.
    """

    provider_id:        str               = ""
    status:             HealthStatus      = HealthStatus.UNKNOWN
    circuit_state:      CircuitBreakerState = CircuitBreakerState.CLOSED
    availability_pct:   float             = 1.0
    avg_latency_ms:     float             = 0.0
    p95_latency_ms:     float             = 0.0
    failure_rate:       float             = 0.0
    consecutive_failures: int             = 0
    last_success_at:    float | None      = None
    last_failure_at:    float | None      = None
    error_message:      str | None        = None
    checked_at:         float             = field(default_factory=time.time)
    metadata:           dict[str, Any]    = field(default_factory=dict)

    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    def is_circuit_open(self) -> bool:
        return self.circuit_state == CircuitBreakerState.OPEN

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id":         self.provider_id,
            "status":              self.status.value,
            "circuit_state":       self.circuit_state.value,
            "availability_pct":    round(self.availability_pct, 4),
            "avg_latency_ms":      round(self.avg_latency_ms, 2),
            "p95_latency_ms":      round(self.p95_latency_ms, 2),
            "failure_rate":        round(self.failure_rate, 4),
            "consecutive_failures": self.consecutive_failures,
            "last_success_at":     self.last_success_at,
            "last_failure_at":     self.last_failure_at,
            "error_message":       self.error_message,
            "checked_at":          self.checked_at,
        }


class CircuitBreaker:
    """
    Simple circuit breaker implementation.

    States:
      CLOSED   → normal operation, passes requests through
      OPEN     → blocking requests after too many failures
      HALF_OPEN → one test request allowed to probe recovery
    """

    def __init__(
        self,
        failure_threshold: int   = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
        reset_sec:         float = DEFAULT_CIRCUIT_BREAKER_RESET_SEC,
    ) -> None:
        self._threshold         = failure_threshold
        self._reset_sec         = reset_sec
        self._state             = CircuitBreakerState.CLOSED
        self._failure_count     = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitBreakerState:
        if self._state == CircuitBreakerState.OPEN and self._opened_at is not None:
            if time.time() - self._opened_at >= self._reset_sec:
                self._state = CircuitBreakerState.HALF_OPEN
        return self._state

    def allow_request(self) -> bool:
        s = self.state
        return s in (CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN)

    def record_success(self) -> None:
        self._failure_count = 0
        self._state         = CircuitBreakerState.CLOSED
        self._opened_at     = None

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self._threshold:
            self._state     = CircuitBreakerState.OPEN
            self._opened_at = time.time()

    def reset(self) -> None:
        self._failure_count = 0
        self._state         = CircuitBreakerState.CLOSED
        self._opened_at     = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "state":          self.state.value,
            "failure_count":  self._failure_count,
            "threshold":      self._threshold,
            "reset_sec":      self._reset_sec,
            "opened_at":      self._opened_at,
        }
