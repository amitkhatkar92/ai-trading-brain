"""iios/execution/positions/risk/position_risk_manager.py
==================================================
PositionRiskManager — primary facade for the Position Risk module.

Orchestrates the registry, factory, monitor, validator, statistics,
and history to provide a unified API for execution-time risk tracking.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

import copy
import threading
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.positions.lifecycle import Position

from .constants import (
    ACTOR_RISK,
    MANAGER_SYSTEM_ID,
    VERSION,
    RiskLevel,
)
from .exceptions import (
    PositionRiskNotRunningError,
    RiskEvaluationError,
    RiskSnapshotError,
    RiskStateNotFoundError,
)
from .position_risk_events import (
    RiskEvent,
    make_liquidation_warning_event,
    make_risk_critical_event,
    make_risk_evaluated_event,
    make_risk_recovered_event,
    make_risk_updated_event,
    make_risk_warning_event,
    make_stop_loss_triggered_event,
    make_take_profit_triggered_event,
)
from .position_risk_factory import RiskFactory
from .position_risk_history import RiskHistory
from .position_risk_limits import DEFAULT_RISK_LIMITS, RiskLimits
from .position_risk_monitor import RiskMonitor
from .position_risk_registry import RiskRegistry
from .position_risk_snapshot import (
    RiskBookSnapshot,
    RiskSnapshot,
    make_risk_book_snapshot,
    make_risk_snapshot,
)
from .position_risk_state import PositionRiskState
from .position_risk_statistics import RiskStatistics
from .position_risk_threshold import DEFAULT_RISK_THRESHOLDS, RiskThreshold
from .position_risk_validation import RiskValidationResult, RiskValidator
from .constants import RiskEventType

_log   = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID)

_DEFAULT_MAX_HISTORY  = 5_000
_DEFAULT_MAX_POSITIONS = 10_000


class PositionRiskManager(LifecycleAwareMixin):
    """
    Primary facade for the IIOS Position Risk subsystem.

    Responsibilities
    ----------------
    * Register and unregister positions for risk tracking.
    * Accept PnL / exposure / margin updates and persist them.
    * Evaluate risk levels via ``RiskMonitor`` and apply results.
    * Emit risk domain events to history.
    * Produce immutable snapshots and statistics.

    Non-responsibilities
    --------------------
    * No position state-machine.
    * No broker connectivity.
    * No portfolio-level aggregation.
    * No order management.
    """

    def __init__(
        self,
        max_positions: int = _DEFAULT_MAX_POSITIONS,
        max_history:   int = _DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._registry   = RiskRegistry(max_positions=max_positions)
        self._factory    = RiskFactory()
        self._monitor    = RiskMonitor()
        self._validator  = RiskValidator()
        self._statistics = RiskStatistics()
        self._history    = RiskHistory(max_events=max_history)
        self._lock       = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("PositionRiskManager started.")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        _log.info(
            "PositionRiskManager stopped.",
            tracked_positions=self._registry.count(),
            total_evaluations=self._statistics.total_evaluations,
        )
        self._registry.stop()

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionRiskNotRunningError()

    # ── Public API ────────────────────────────────────────────────────────────

    def register(
        self,
        position:   Position,
        limits:     Optional[RiskLimits]    = None,
        thresholds: Optional[RiskThreshold] = None,
    ) -> PositionRiskState:
        """
        Register a position for risk tracking.

        Returns the freshly created ``PositionRiskState``.

        Raises
        ------
        PositionRiskNotRunningError
        PositionRiskValidationError
        DuplicateRiskStateError
        PositionRiskCapacityError
        """
        self._assert_running()
        eff_limits     = limits     or DEFAULT_RISK_LIMITS
        eff_thresholds = thresholds or DEFAULT_RISK_THRESHOLDS

        state = self._factory.create(position, eff_limits, eff_thresholds)
        self._registry.register(state, eff_limits, eff_thresholds)

        with self._lock:
            self._statistics.record_registered()
            self._refresh_live_counts()

        _log.info(
            "Position registered for risk tracking.",
            position_id=position.position_id,
        )
        return state

    def update(
        self,
        position_id:    str,
        *,
        unrealized_pnl: Decimal,
        realized_pnl:   Decimal,
        exposure:       Decimal,
        margin_used:    Decimal,
        margin_available: Decimal,
    ) -> PositionRiskState:
        """
        Update metrics for a tracked position.

        Does NOT run a risk evaluation — call ``evaluate()`` separately
        to advance the risk level.

        Raises
        ------
        PositionRiskNotRunningError
        RiskStateNotFoundError
        """
        self._assert_running()
        state = self._registry.require_state(position_id)
        state.update_pnl(unrealized_pnl, realized_pnl)
        state.update_exposure(exposure)
        state.update_margin(margin_used, margin_available)

        with self._lock:
            self._statistics.record_update()

        _log.debug("Risk state updated.", position_id=position_id)
        return state

    def evaluate(self, position_id: str) -> PositionRiskState:
        """
        Run ``RiskMonitor`` for *position_id* and apply the results.

        Updates risk level and trigger flags in the state, records
        events to history, and updates statistics.

        Raises
        ------
        PositionRiskNotRunningError
        RiskStateNotFoundError
        RiskEvaluationError
        """
        self._assert_running()
        try:
            state      = self._registry.require_state(position_id)
            limits     = self._registry.require_limits(position_id)
            thresholds = self._registry.require_thresholds(position_id)

            t0 = time.perf_counter()
            result = self._monitor.evaluate(state, limits, thresholds)
            elapsed_ms = (time.perf_counter() - t0) * 1_000

            # Apply result back to state
            state.set_risk_level(result.new_risk_level)
            if result.stop_loss_triggered and not state.stop_loss_triggered:
                state.trigger_stop_loss()
            if result.take_profit_triggered and not state.take_profit_triggered:
                state.trigger_take_profit()
            state.set_liquidation_warning(result.liquidation_warning)
            if result.liquidation_warning:
                state.set_liquidation_state(True)
            state.mark_evaluated()

            # Build and store events
            events = self._build_events(
                result.events_to_emit,
                position_id=position_id,
                portfolio_id=state.portfolio_id,
                strategy_id=state.strategy_id,
                risk_level=result.new_risk_level,
                drawdown_pct=result.drawdown_pct,
                margin_pct=result.margin_utilization_pct,
                unrealized_pnl=state.unrealized_pnl,
            )
            self._history.extend(events)

            with self._lock:
                self._statistics.record_evaluation(elapsed_ms)
                if result.new_risk_level == RiskLevel.WARNING:
                    self._statistics.record_warning()
                if result.new_risk_level == RiskLevel.CRITICAL:
                    self._statistics.record_critical()
                if result.liquidation_warning:
                    self._statistics.record_liquidation()
                if result.stop_loss_triggered and not state.stop_loss_triggered:
                    self._statistics.record_stop_loss()
                if result.take_profit_triggered and not state.take_profit_triggered:
                    self._statistics.record_take_profit()
                if RiskEventType.RISK_RECOVERED in result.events_to_emit:
                    self._statistics.record_recovery()
                self._statistics.record_sample(
                    exposure=state.current_exposure,
                    margin_usage=result.margin_utilization_pct,
                    drawdown=result.drawdown_pct,
                )
                self._refresh_live_counts()

        except RiskStateNotFoundError:
            raise
        except Exception as exc:
            raise RiskEvaluationError(
                f"Evaluation failed for position {position_id!r}: {exc}",
                position_id=position_id,
            ) from exc

        return state

    def unregister(self, position_id: str) -> PositionRiskState:
        """
        Remove a position from risk tracking and return its final state.

        Raises
        ------
        PositionRiskNotRunningError
        RiskStateNotFoundError
        """
        self._assert_running()
        state = self._registry.unregister(position_id)
        with self._lock:
            self._statistics.record_unregistered()
            self._refresh_live_counts()
        _log.info("Position unregistered from risk tracking.", position_id=position_id)
        return state

    def get_state(self, position_id: str) -> Optional[PositionRiskState]:
        return self._registry.get_state(position_id)

    def require_state(self, position_id: str) -> PositionRiskState:
        return self._registry.require_state(position_id)

    def snapshot(self, position_id: str) -> RiskSnapshot:
        """
        Produce an immutable snapshot of a single position's risk state.

        Raises
        ------
        RiskStateNotFoundError
        RiskSnapshotError
        """
        try:
            state = self._registry.require_state(position_id)
            return make_risk_snapshot(state)
        except RiskStateNotFoundError:
            raise
        except Exception as exc:
            raise RiskSnapshotError(
                f"Snapshot failed for position {position_id!r}: {exc}"
            ) from exc

    def all_snapshots(self) -> List[RiskSnapshot]:
        return [make_risk_snapshot(s) for s in self._registry.all_states()]

    def book_snapshot(self) -> RiskBookSnapshot:
        states = self._registry.all_states()
        with self._lock:
            stats = copy.copy(self._statistics)
        return make_risk_book_snapshot(states, stats)

    def statistics(self) -> RiskStatistics:
        with self._lock:
            return copy.copy(self._statistics)

    def history(self) -> RiskHistory:
        return self._history

    def events(self) -> List[RiskEvent]:
        return self._history.all()

    def validate(self, position_id: str) -> RiskValidationResult:
        state      = self._registry.require_state(position_id)
        limits     = self._registry.require_limits(position_id)
        thresholds = self._registry.require_thresholds(position_id)
        return self._validator.validate_all(state, limits, thresholds)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _refresh_live_counts(self) -> None:
        """Must be called under self._lock."""
        states = self._registry.all_states()
        self._statistics.update_live_counts(
            normal=sum(1 for s in states if s.risk_level == RiskLevel.NORMAL),
            watch=sum(1 for s in states if s.risk_level == RiskLevel.WATCH),
            warning=sum(1 for s in states if s.risk_level == RiskLevel.WARNING),
            critical=sum(1 for s in states if s.risk_level == RiskLevel.CRITICAL),
            liquidated=sum(1 for s in states if s.risk_level in (
                RiskLevel.LIQUIDATION_PENDING, RiskLevel.LIQUIDATED
            )),
        )

    def _build_events(
        self,
        event_types:    List[RiskEventType],
        *,
        position_id:    str,
        portfolio_id:   str,
        strategy_id:    str,
        risk_level:     RiskLevel,
        drawdown_pct:   Decimal,
        margin_pct:     Decimal,
        unrealized_pnl: Decimal,
    ) -> List[RiskEvent]:
        events: List[RiskEvent] = []
        kw: Dict[str, Any] = dict(
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            emitted_by=ACTOR_RISK,
        )
        for et in event_types:
            if et == RiskEventType.RISK_EVALUATED:
                events.append(make_risk_evaluated_event(
                    position_id, risk_level, drawdown_pct, margin_pct, unrealized_pnl, **kw
                ))
            elif et == RiskEventType.RISK_UPDATED:
                events.append(make_risk_updated_event(
                    position_id, risk_level, drawdown_pct, margin_pct, unrealized_pnl, **kw
                ))
            elif et == RiskEventType.RISK_WARNING:
                events.append(make_risk_warning_event(
                    position_id, drawdown_pct, margin_pct, unrealized_pnl, **kw
                ))
            elif et == RiskEventType.RISK_CRITICAL:
                events.append(make_risk_critical_event(
                    position_id, drawdown_pct, margin_pct, unrealized_pnl, **kw
                ))
            elif et == RiskEventType.STOP_LOSS_TRIGGERED:
                events.append(make_stop_loss_triggered_event(
                    position_id, drawdown_pct, margin_pct, unrealized_pnl, **kw
                ))
            elif et == RiskEventType.TAKE_PROFIT_TRIGGERED:
                events.append(make_take_profit_triggered_event(
                    position_id, drawdown_pct, margin_pct, unrealized_pnl, **kw
                ))
            elif et == RiskEventType.LIQUIDATION_WARNING:
                events.append(make_liquidation_warning_event(
                    position_id, drawdown_pct, margin_pct, unrealized_pnl, **kw
                ))
            elif et == RiskEventType.RISK_RECOVERED:
                events.append(make_risk_recovered_event(
                    position_id, drawdown_pct, margin_pct, unrealized_pnl, **kw
                ))
        return events
