"""iios/investment/strategy/lifecycle/failure_handler.py
Strategy failure detection, retry scheduling, and circuit-breaker pattern.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FailurePolicy:
    """
    Per-strategy failure and retry policy.

    Defaults are production-conservative.
    """

    max_retries: int = 3
    initial_retry_delay_s: float = 1.0
    backoff_factor: float = 2.0          # exponential backoff multiplier
    max_retry_delay_s: float = 60.0
    circuit_breaker_threshold: int = 5   # consecutive failures to open circuit
    circuit_reset_delay_s: float = 300.0  # seconds until circuit tries half-open

    # Error types that skip retry entirely (permanent errors)
    non_retryable_errors: List[str] = field(default_factory=list)


class CircuitState(str, Enum):
    CLOSED    = "closed"     # normal — requests pass through
    OPEN      = "open"       # failing — all requests blocked
    HALF_OPEN = "half_open"  # trial — one request probes recovery


@dataclass
class FailureRecord:
    """Record of a single failure event."""

    strategy_id: str
    error_type: str
    error_message: str
    attempt_number: int
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    was_retried: bool = False


class StrategyCircuit:
    """Per-strategy circuit breaker implementation."""

    def __init__(self, policy: FailurePolicy) -> None:
        self._policy = policy
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: Optional[datetime] = None

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state

    @property
    def is_open(self) -> bool:
        """True if requests should be blocked (OPEN or HALF_OPEN probe failed)."""
        with self._lock:
            if self._state != CircuitState.OPEN:
                return False
            # Check if the reset delay has elapsed → transition to HALF_OPEN
            if self._opened_at is not None:
                elapsed = (
                    datetime.now(timezone.utc) - self._opened_at
                ).total_seconds()
                if elapsed >= self._policy.circuit_reset_delay_s:
                    self._state = CircuitState.HALF_OPEN
                    return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._state = CircuitState.CLOSED
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if (
                self._state == CircuitState.CLOSED
                and self._consecutive_failures
                >= self._policy.circuit_breaker_threshold
            ):
                self._state = CircuitState.OPEN
                self._opened_at = datetime.now(timezone.utc)
                logger.warning(
                    "Circuit OPENED after %d consecutive failures",
                    self._consecutive_failures,
                )
            elif self._state == CircuitState.HALF_OPEN:
                # Trial request failed — reopen
                self._state = CircuitState.OPEN
                self._opened_at = datetime.now(timezone.utc)


class FailureHandler:
    """
    Per-strategy failure policy enforcement, retry scheduling, and circuit
    breaker management.

    Usage:
        handler.should_retry(strategy_id, error_type, attempt) → bool
        handler.retry_delay(strategy_id, attempt) → float  (seconds)
        handler.record_success(strategy_id)
        handler.record_failure(strategy_id, error_type, error_message, attempt)
    """

    def __init__(
        self, default_policy: Optional[FailurePolicy] = None
    ) -> None:
        self._default_policy = default_policy or FailurePolicy()
        self._lock = threading.RLock()
        self._policies: Dict[str, FailurePolicy] = {}
        self._circuits: Dict[str, StrategyCircuit] = {}
        self._failure_records: Dict[str, List[FailureRecord]] = {}

    # ── Configuration ─────────────────────────────────────────────────────────

    def set_policy(self, strategy_id: str, policy: FailurePolicy) -> None:
        with self._lock:
            self._policies[strategy_id] = policy
            # Reset circuit on policy change
            self._circuits[strategy_id] = StrategyCircuit(policy)

    def get_policy(self, strategy_id: str) -> FailurePolicy:
        with self._lock:
            return self._policies.get(strategy_id, self._default_policy)

    # ── Circuit breaker ───────────────────────────────────────────────────────

    def is_circuit_open(self, strategy_id: str) -> bool:
        return self._get_circuit(strategy_id).is_open

    def circuit_state(self, strategy_id: str) -> CircuitState:
        return self._get_circuit(strategy_id).state

    # ── Retry logic ───────────────────────────────────────────────────────────

    def should_retry(
        self, strategy_id: str, error_type: str, attempt: int
    ) -> bool:
        """
        True if the failed execution should be retried.

        Returns False when:
          - Max retries exceeded
          - Circuit is OPEN
          - Error type is in non_retryable_errors
        """
        policy = self.get_policy(strategy_id)

        if attempt >= policy.max_retries:
            return False
        if self.is_circuit_open(strategy_id):
            return False
        if error_type in policy.non_retryable_errors:
            return False
        return True

    def retry_delay(self, strategy_id: str, attempt: int) -> float:
        """Exponential backoff delay for the given attempt number (0-based)."""
        policy = self.get_policy(strategy_id)
        delay = policy.initial_retry_delay_s * (policy.backoff_factor ** attempt)
        return min(delay, policy.max_retry_delay_s)

    # ── Event recording ───────────────────────────────────────────────────────

    def record_success(self, strategy_id: str) -> None:
        self._get_circuit(strategy_id).record_success()

    def record_failure(
        self,
        strategy_id: str,
        error_type: str,
        error_message: str,
        attempt: int,
    ) -> FailureRecord:
        circuit = self._get_circuit(strategy_id)
        circuit.record_failure()

        will_retry = self.should_retry(strategy_id, error_type, attempt)
        record = FailureRecord(
            strategy_id=strategy_id,
            error_type=error_type,
            error_message=error_message,
            attempt_number=attempt,
            was_retried=will_retry,
        )
        with self._lock:
            recs = self._failure_records.setdefault(strategy_id, [])
            recs.append(record)
            if len(recs) > 100:
                self._failure_records[strategy_id] = recs[-100:]
        return record

    def get_failure_history(self, strategy_id: str) -> List[FailureRecord]:
        with self._lock:
            return list(self._failure_records.get(strategy_id, []))

    def reset_strategy(self, strategy_id: str) -> None:
        """Clear failure history and reset the circuit for a strategy."""
        with self._lock:
            self._failure_records.pop(strategy_id, None)
            policy = self._policies.get(strategy_id, self._default_policy)
            self._circuits[strategy_id] = StrategyCircuit(policy)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_circuit(self, strategy_id: str) -> StrategyCircuit:
        with self._lock:
            if strategy_id not in self._circuits:
                policy = self._policies.get(strategy_id, self._default_policy)
                self._circuits[strategy_id] = StrategyCircuit(policy)
            return self._circuits[strategy_id]
