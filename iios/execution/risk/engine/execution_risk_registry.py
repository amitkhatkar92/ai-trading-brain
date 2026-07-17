"""iios/execution/risk/engine/execution_risk_registry.py
==================================================
EngineRiskRegistry — LifecycleAwareMixin wrapper around the M1
RiskRegistry, exposing engine-level read and notify APIs.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import threading
from typing import List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.risk.lifecycle import (
    ExecutionRisk,
    RiskCategory,
    RiskRegistry as LifecycleRegistry,
    RiskState,
    RiskStatistics as LifecycleStatistics,
    DEFAULT_MAX_EVALUATIONS,
)

from .constants import DEFAULT_MAX_EVALUATIONS as ENGINE_MAX_EVALS, REGISTRY_SYSTEM_ID, VERSION
from .exceptions import RiskEngineNotRunningError

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)


class EngineRiskRegistry(LifecycleAwareMixin):
    """
    Engine-layer wrapper around ``iios.execution.risk.lifecycle.RiskRegistry``.

    Owns and manages the lifecycle of the underlying M1 registry.
    Delegates all storage operations to it while providing engine-level
    lifecycle control and logging.
    """

    def __init__(self, max_evaluations: int = ENGINE_MAX_EVALS) -> None:
        super().__init__()
        self._inner = LifecycleRegistry(max_evaluations=max_evaluations)

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RiskEngineNotRunningError()

    def _on_start(self) -> None:
        self._inner.start()
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("EngineRiskRegistry started.", max_evaluations=self._inner._max)

    def _on_stop(self) -> None:
        self._inner.stop()
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("EngineRiskRegistry stopped.", evaluation_count=self._inner.count)

    # ── Write ─────────────────────────────────────────────────────────────────

    def register(self, risk: ExecutionRisk) -> None:
        """Register *risk*; delegates to the M1 registry."""
        self._assert_running()
        self._inner.register(risk)

    def deregister(self, risk_id: str) -> None:
        """Deregister *risk_id*; delegates to the M1 registry."""
        self._assert_running()
        self._inner.deregister(risk_id)

    def notify_transition(
        self,
        risk:               ExecutionRisk,
        to_state:           RiskState,
        evaluation_time_ms: float = 0.0,
    ) -> None:
        """Update M1 statistics when a risk evaluation transitions state."""
        self._assert_running()
        self._inner.notify_transition(risk, to_state, evaluation_time_ms=evaluation_time_ms)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, risk_id: str) -> Optional[ExecutionRisk]:
        return self._inner.get(risk_id)

    def require(self, risk_id: str) -> ExecutionRisk:
        return self._inner.require(risk_id)

    def contains(self, risk_id: str) -> bool:
        return self._inner.contains(risk_id)

    # ── Filters ───────────────────────────────────────────────────────────────

    def all(self) -> List[ExecutionRisk]:
        return self._inner.all()

    def by_state(self, state: RiskState) -> List[ExecutionRisk]:
        return self._inner.by_state(state)

    def by_category(self, category: RiskCategory) -> List[ExecutionRisk]:
        return self._inner.by_category(category)

    def by_portfolio(self, portfolio_id: str) -> List[ExecutionRisk]:
        return self._inner.by_portfolio(portfolio_id)

    def by_strategy(self, strategy_id: str) -> List[ExecutionRisk]:
        return self._inner.by_strategy(strategy_id)

    def by_execution(self, execution_id: str) -> List[ExecutionRisk]:
        return self._inner.by_execution(execution_id)

    def active(self) -> List[ExecutionRisk]:
        return self._inner.active()

    def passed(self) -> List[ExecutionRisk]:
        return self._inner.passed()

    def blocked(self) -> List[ExecutionRisk]:
        return self._inner.blocked()

    def archived(self) -> List[ExecutionRisk]:
        return self._inner.archived()

    def ended(self) -> List[ExecutionRisk]:
        return self._inner.ended()

    # ── Counters ──────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return self._inner.count

    @property
    def is_empty(self) -> bool:
        return self._inner.is_empty

    # ── Statistics ────────────────────────────────────────────────────────────

    def lifecycle_statistics(self) -> LifecycleStatistics:
        """Return the M1 RiskRegistry statistics snapshot."""
        return self._inner.statistics()
