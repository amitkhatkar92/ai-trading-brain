"""iios/execution/risk/lifecycle/execution_risk_registry.py
==================================================
RiskRegistry — LifecycleAwareMixin registry of ExecutionRisk objects.

Thread-safe storage and retrieval with filtering helpers.
Aggregates statistics across all registered evaluations.

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

import copy
import threading
from typing import List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTIVE_STATES,
    BLOCKING_STATES,
    DEFAULT_MAX_EVALUATIONS,
    ENDED_STATES,
    OUTCOME_STATES,
    PASS_STATES,
    REGISTRY_SYSTEM_ID,
    TERMINAL_STATES,
    VERSION,
    RiskCategory,
    RiskState,
)
from .exceptions import (
    DuplicateRiskError,
    RiskNotFoundError,
    RiskRegistryCapacityError,
    RiskRegistryNotRunningError,
)
from .execution_risk import ExecutionRisk
from .execution_risk_statistics import RiskStatistics

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)


class RiskRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry for ``ExecutionRisk`` objects.

    The registry must be started before any write operations.
    Read operations are permitted regardless of lifecycle state
    to allow inspection after shutdown.

    Evaluations are keyed by ``risk_id``.
    """

    def __init__(self, max_evaluations: int = DEFAULT_MAX_EVALUATIONS) -> None:
        super().__init__()
        self._max    = max(1, max_evaluations)
        self._store: dict[str, ExecutionRisk] = {}
        self._stats  = RiskStatistics()
        self._lock   = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RiskRegistryNotRunningError()

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("RiskRegistry started.", max_evaluations=self._max)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info("RiskRegistry stopped.", evaluation_count=len(self._store))

    # ── Write ─────────────────────────────────────────────────────────────────

    def register(self, risk: ExecutionRisk) -> None:
        """
        Register *risk* in the registry.

        Raises
        ------
        RiskRegistryNotRunningError
            If the registry has not been started.
        RiskRegistryCapacityError
            If the registry is at maximum capacity.
        DuplicateRiskError
            If an evaluation with the same ``risk_id`` already exists.
        """
        self._assert_running()
        with self._lock:
            if len(self._store) >= self._max:
                raise RiskRegistryCapacityError(self._max)
            rid = risk.risk_id
            if rid in self._store:
                raise DuplicateRiskError(rid)
            self._store[rid] = risk
            self._stats.record_created()

        _log.info(
            "Risk evaluation registered.",
            risk_id=risk.risk_id,
            category=risk.risk_category.value,
            state=risk.state.value,
        )

    def deregister(self, risk_id: str) -> None:
        """
        Remove an evaluation from the registry.

        Raises ``RiskNotFoundError`` if not present.
        """
        self._assert_running()
        with self._lock:
            if risk_id not in self._store:
                raise RiskNotFoundError(risk_id)
            del self._store[risk_id]
        _log.info("Risk evaluation deregistered.", risk_id=risk_id)

    def notify_transition(
        self,
        risk:               ExecutionRisk,
        to_state:           RiskState,
        evaluation_time_ms: float = 0.0,
    ) -> None:
        """
        Update statistics when a risk evaluation transitions state.

        Should be called by the owner after every successful ``transition_to()``.
        """
        self._assert_running()
        with self._lock:
            self._stats.record_transition(is_override=(to_state == RiskState.OVERRIDDEN))
            if to_state == RiskState.PASSED:
                self._stats.record_passed(evaluation_time_ms)
            elif to_state == RiskState.WARNING:
                self._stats.record_warned(evaluation_time_ms)
            elif to_state == RiskState.BLOCKED:
                self._stats.record_blocked(evaluation_time_ms)
            elif to_state == RiskState.OVERRIDDEN:
                self._stats.record_overridden()
            elif to_state == RiskState.EXPIRED:
                self._stats.record_expired()
            elif to_state == RiskState.FAILED:
                self._stats.record_failed()
            elif to_state == RiskState.ARCHIVED:
                self._stats.record_archived()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, risk_id: str) -> Optional[ExecutionRisk]:
        """Return the evaluation or ``None`` if not found."""
        with self._lock:
            return self._store.get(risk_id)

    def require(self, risk_id: str) -> ExecutionRisk:
        """Return the evaluation or raise ``RiskNotFoundError``."""
        with self._lock:
            risk = self._store.get(risk_id)
        if risk is None:
            raise RiskNotFoundError(risk_id)
        return risk

    def contains(self, risk_id: str) -> bool:
        """True if the evaluation is registered."""
        with self._lock:
            return risk_id in self._store

    # ── Filtering ─────────────────────────────────────────────────────────────

    def all(self) -> List[ExecutionRisk]:
        """All registered evaluations."""
        with self._lock:
            return list(self._store.values())

    def by_state(self, state: RiskState) -> List[ExecutionRisk]:
        """Evaluations in the given *state*."""
        with self._lock:
            return [r for r in self._store.values() if r.state == state]

    def by_category(self, category: RiskCategory) -> List[ExecutionRisk]:
        """Evaluations of the given *category*."""
        with self._lock:
            return [r for r in self._store.values() if r.risk_category == category]

    def by_portfolio(self, portfolio_id: str) -> List[ExecutionRisk]:
        """Evaluations belonging to *portfolio_id*."""
        with self._lock:
            return [r for r in self._store.values() if r.portfolio_id == portfolio_id]

    def by_strategy(self, strategy_id: str) -> List[ExecutionRisk]:
        """Evaluations belonging to *strategy_id*."""
        with self._lock:
            return [r for r in self._store.values() if r.strategy_id == strategy_id]

    def by_execution(self, execution_id: str) -> List[ExecutionRisk]:
        """Evaluations for a given *execution_id*."""
        with self._lock:
            return [r for r in self._store.values() if r.execution_id == execution_id]

    def active(self) -> List[ExecutionRisk]:
        """Evaluations in PENDING_EVALUATION or EVALUATING state."""
        with self._lock:
            return [r for r in self._store.values() if r.state in ACTIVE_STATES]

    def passed(self) -> List[ExecutionRisk]:
        """Evaluations in PASSED, WARNING, or OVERRIDDEN state."""
        with self._lock:
            return [r for r in self._store.values() if r.state in PASS_STATES]

    def blocked(self) -> List[ExecutionRisk]:
        """Evaluations in BLOCKED state."""
        with self._lock:
            return [r for r in self._store.values() if r.state in BLOCKING_STATES]

    def archived(self) -> List[ExecutionRisk]:
        """Evaluations in the terminal ARCHIVED state."""
        with self._lock:
            return [r for r in self._store.values() if r.state in TERMINAL_STATES]

    def ended(self) -> List[ExecutionRisk]:
        """Evaluations in EXPIRED, FAILED, or ARCHIVED state."""
        with self._lock:
            return [r for r in self._store.values() if r.state in ENDED_STATES]

    # ── Counters ──────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        """Total number of registered evaluations."""
        with self._lock:
            return len(self._store)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._store) == 0

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> RiskStatistics:
        """Return a shallow copy of the current statistics snapshot."""
        with self._lock:
            return copy.copy(self._stats)
