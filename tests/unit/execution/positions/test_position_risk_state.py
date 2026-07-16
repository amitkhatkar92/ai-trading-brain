"""tests/unit/execution/positions/test_position_risk_state.py
==================================================
Test suite for C6 Phase 3 M4 — IIOS Position Risk State.

Coverage targets (95%+):
  * Constants, enums: RiskLevel, RiskEventType, RiskOperationType
  * Risk level sets: ACTIVE_RISK_LEVELS, ELEVATED_RISK_LEVELS, TERMINAL_RISK_LEVELS
  * Exceptions — hierarchy, error codes, fields
  * RiskLimits — validation, properties, to_dict
  * RiskThreshold — validation (ordering), to_dict
  * PositionRiskState — PnL update / peak tracking, drawdown, margin, triggers, to_dict
  * RiskContext / make_risk_context
  * RiskEvent + all 8 factory functions
  * RiskHistory — append, extend, clear, filters, eviction, is_empty
  * RiskStatistics — counters, averages, live counts, to_dict
  * RiskSnapshot / RiskBookSnapshot — from_state, factories, properties
  * RiskValidationResult — ok, fail, raise_if_invalid
  * RiskValidator — all 5 checks, validate_all
  * RiskEvaluationResult — fields
  * RiskMonitor — level from drawdown, level from margin, stop-loss, take-profit, events
  * RiskFactory — create, validation failures
  * RiskRegistry — lifecycle guard, register, unregister, require*, all_states, contains
  * PositionRiskManager — full lifecycle, register/update/evaluate/unregister,
      snapshots, statistics, history, validate, concurrency

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from decimal import Decimal
from typing import List

import pytest

from iios.execution.positions.lifecycle import (
    Position,
    PositionDirection,
    PositionFactory,
    PositionProduct,
)

from iios.execution.positions.risk import (
    # constants
    RISK_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    VERSION,
    ACTOR_RISK,
    ACTIVE_RISK_LEVELS,
    ELEVATED_RISK_LEVELS,
    TERMINAL_RISK_LEVELS,
    # enums
    RiskLevel,
    RiskEventType,
    RiskOperationType,
    # exceptions
    PositionRiskError,
    PositionRiskNotRunningError,
    RiskStateNotFoundError,
    DuplicateRiskStateError,
    PositionRiskValidationError,
    PositionRiskCapacityError,
    InvalidRiskLevelError,
    RiskLimitsError,
    RiskEvaluationError,
    RiskSnapshotError,
    # value types
    RiskContext, make_risk_context,
    RiskEvent,
    make_risk_evaluated_event,
    make_risk_updated_event,
    make_risk_warning_event,
    make_risk_critical_event,
    make_stop_loss_triggered_event,
    make_take_profit_triggered_event,
    make_liquidation_warning_event,
    make_risk_recovered_event,
    RiskHistory,
    RiskLimits, DEFAULT_RISK_LIMITS,
    RiskThreshold, DEFAULT_RISK_THRESHOLDS,
    PositionRiskState,
    RiskMonitor, RiskEvaluationResult,
    RiskSnapshot, RiskBookSnapshot,
    make_risk_snapshot, make_risk_book_snapshot,
    RiskStatistics,
    RiskValidationResult, RiskValidator,
    # services
    RiskFactory,
    RiskRegistry,
    PositionRiskManager,
)


# ── Fixtures / helpers ────────────────────────────────────────────────────────

def _make_position(
    instrument:   str = "NIFTY50",
    quantity:     Decimal = Decimal("100"),
    direction:    PositionDirection = PositionDirection.LONG,
    portfolio_id: str = "port-1",
    strategy_id:  str = "strat-1",
) -> Position:
    f = PositionFactory()
    return f.create(
        instrument=instrument,
        exchange="NSE",
        product=PositionProduct.FUTURES,
        direction=direction,
        quantity=quantity,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        decision_id="dec-1",
        workflow_id="wf-1",
        execution_id="exec-1",
    )


def _started_manager(**kwargs) -> PositionRiskManager:
    m = PositionRiskManager(**kwargs)
    m.start()
    return m


def _state(position_id: str = "pos-1") -> PositionRiskState:
    return PositionRiskState(
        position_id=position_id,
        portfolio_id="port-1",
        strategy_id="strat-1",
        instrument="NIFTY50",
    )


# ══════════════════════════════════════════════════════════════════════════════
# 1. Constants & enums
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_system_ids_not_empty(self):
        assert RISK_SYSTEM_ID
        assert MANAGER_SYSTEM_ID
        assert REGISTRY_SYSTEM_ID

    def test_version(self):
        assert VERSION == "1.0.0"

    def test_risk_level_values(self):
        assert RiskLevel.NORMAL.value == "NORMAL"
        assert RiskLevel.WATCH.value  == "WATCH"
        assert RiskLevel.WARNING.value == "WARNING"
        assert RiskLevel.CRITICAL.value == "CRITICAL"
        assert RiskLevel.LIQUIDATION_PENDING.value == "LIQUIDATION_PENDING"
        assert RiskLevel.LIQUIDATED.value == "LIQUIDATED"
        assert RiskLevel.RECOVERING.value == "RECOVERING"
        assert RiskLevel.RECOVERED.value == "RECOVERED"

    def test_risk_event_type_values(self):
        assert RiskEventType.RISK_EVALUATED.value       == "RISK_EVALUATED"
        assert RiskEventType.STOP_LOSS_TRIGGERED.value  == "STOP_LOSS_TRIGGERED"
        assert RiskEventType.TAKE_PROFIT_TRIGGERED.value == "TAKE_PROFIT_TRIGGERED"
        assert RiskEventType.LIQUIDATION_WARNING.value  == "LIQUIDATION_WARNING"
        assert RiskEventType.RISK_RECOVERED.value       == "RISK_RECOVERED"

    def test_risk_operation_type_values(self):
        for op in RiskOperationType:
            assert op.value

    def test_active_risk_levels_contains_normal(self):
        assert RiskLevel.NORMAL in ACTIVE_RISK_LEVELS

    def test_elevated_risk_levels(self):
        assert RiskLevel.WARNING in ELEVATED_RISK_LEVELS
        assert RiskLevel.CRITICAL in ELEVATED_RISK_LEVELS
        assert RiskLevel.NORMAL not in ELEVATED_RISK_LEVELS

    def test_terminal_risk_levels(self):
        assert RiskLevel.LIQUIDATED in TERMINAL_RISK_LEVELS
        assert RiskLevel.NORMAL not in TERMINAL_RISK_LEVELS


# ══════════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_hierarchy(self):
        e = PositionRiskError("base", code="PR4-000")
        assert isinstance(e, Exception)

    def test_not_running(self):
        e = PositionRiskNotRunningError()
        assert "not running" in str(e).lower()
        assert isinstance(e, PositionRiskError)

    def test_state_not_found(self):
        e = RiskStateNotFoundError("pos-99")
        assert e.position_id == "pos-99"
        assert isinstance(e, PositionRiskError)

    def test_duplicate_risk_state(self):
        e = DuplicateRiskStateError("pos-1")
        assert e.position_id == "pos-1"

    def test_validation_error_has_errors_tuple(self):
        e = PositionRiskValidationError("bad", errors=("e1", "e2"))
        assert e.errors == ("e1", "e2")

    def test_capacity_error_has_capacity(self):
        e = PositionRiskCapacityError(500)
        assert e.capacity == 500

    def test_risk_limits_error(self):
        e = RiskLimitsError("bad limits")
        assert isinstance(e, PositionRiskError)

    def test_evaluation_error_has_position_id(self):
        e = RiskEvaluationError("failed", "pos-1")
        assert e.position_id == "pos-1"

    def test_snapshot_error(self):
        e = RiskSnapshotError("snap fail")
        assert isinstance(e, PositionRiskError)


# ══════════════════════════════════════════════════════════════════════════════
# 3. RiskLimits
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskLimits:
    def test_default_construction(self):
        rl = RiskLimits()
        assert rl.max_loss > 0
        assert rl.take_profit is None
        assert rl.max_drawdown_pct == Decimal("0.50")

    def test_default_risk_limits_singleton(self):
        assert DEFAULT_RISK_LIMITS.max_loss > 0

    def test_max_loss_must_be_positive(self):
        with pytest.raises(RiskLimitsError):
            RiskLimits(max_loss=Decimal("0"))
        with pytest.raises(RiskLimitsError):
            RiskLimits(max_loss=Decimal("-1"))

    def test_take_profit_zero_rejected(self):
        with pytest.raises(RiskLimitsError):
            RiskLimits(take_profit=Decimal("0"))

    def test_drawdown_pct_bounds(self):
        with pytest.raises(RiskLimitsError):
            RiskLimits(max_drawdown_pct=Decimal("0"))
        with pytest.raises(RiskLimitsError):
            RiskLimits(max_drawdown_pct=Decimal("1.1"))

    def test_margin_pct_bounds(self):
        with pytest.raises(RiskLimitsError):
            RiskLimits(max_margin_utilization_pct=Decimal("0"))

    def test_has_take_profit_false_by_default(self):
        assert RiskLimits().has_take_profit is False

    def test_has_take_profit_true_when_set(self):
        rl = RiskLimits(take_profit=Decimal("5000"))
        assert rl.has_take_profit is True

    def test_to_dict_keys(self):
        d = RiskLimits().to_dict()
        assert "max_loss" in d
        assert "max_drawdown_pct" in d


# ══════════════════════════════════════════════════════════════════════════════
# 4. RiskThreshold
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskThreshold:
    def test_default_construction(self):
        rt = RiskThreshold()
        assert rt.watch_drawdown_pct < rt.warning_drawdown_pct

    def test_default_thresholds_singleton(self):
        assert DEFAULT_RISK_THRESHOLDS.watch_drawdown_pct > 0

    def test_drawdown_ordering_enforced(self):
        with pytest.raises(RiskLimitsError):
            RiskThreshold(
                watch_drawdown_pct=Decimal("0.50"),
                warning_drawdown_pct=Decimal("0.25"),   # violates watch < warning
                critical_drawdown_pct=Decimal("0.75"),
                liquidation_drawdown_pct=Decimal("0.90"),
            )

    def test_margin_ordering_enforced(self):
        with pytest.raises(RiskLimitsError):
            RiskThreshold(
                watch_margin_pct=Decimal("0.85"),
                warning_margin_pct=Decimal("0.70"),     # violates watch < warning
                critical_margin_pct=Decimal("0.95"),
                liquidation_margin_pct=Decimal("1.00"),
            )

    def test_to_dict(self):
        d = RiskThreshold().to_dict()
        assert "watch_drawdown_pct" in d
        assert "liquidation_margin_pct" in d


# ══════════════════════════════════════════════════════════════════════════════
# 5. PositionRiskState
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionRiskState:
    def test_initial_state(self):
        s = _state()
        assert s.position_id == "pos-1"
        assert s.risk_level  == RiskLevel.NORMAL
        assert s.unrealized_pnl == Decimal("0")
        assert s.peak_pnl       == Decimal("0")
        assert s.execution_drawdown == Decimal("0")
        assert s.execution_drawdown_pct == Decimal("0")
        assert s.stop_loss_triggered  is False
        assert s.take_profit_triggered is False
        assert s.liquidation_warning  is False
        assert s.liquidation_state    is False

    def test_state_id_is_uuid(self):
        s = _state()
        uuid.UUID(s.state_id)   # raises if not valid UUID

    def test_update_pnl_tracks_peak(self):
        s = _state()
        s.update_pnl(Decimal("1000"), Decimal("0"))
        assert s.peak_pnl == Decimal("1000")
        s.update_pnl(Decimal("1200"), Decimal("0"))
        assert s.peak_pnl == Decimal("1200")
        s.update_pnl(Decimal("800"), Decimal("0"))
        assert s.peak_pnl == Decimal("1200")  # peak does not retreat

    def test_update_pnl_computes_drawdown(self):
        s = _state()
        s.update_pnl(Decimal("1000"), Decimal("0"))
        s.update_pnl(Decimal("700"), Decimal("0"))
        assert s.execution_drawdown     == Decimal("300")
        assert s.execution_drawdown_pct == Decimal("0.3")

    def test_drawdown_zero_when_peak_zero(self):
        s = _state()
        s.update_pnl(Decimal("-500"), Decimal("0"))
        assert s.execution_drawdown     == Decimal("0")
        assert s.execution_drawdown_pct == Decimal("0")

    def test_drawdown_clamped_at_zero(self):
        """Drawdown cannot be negative (new high cannot be below peak)."""
        s = _state()
        s.update_pnl(Decimal("1000"), Decimal("0"))
        s.update_pnl(Decimal("1200"), Decimal("0"))
        # After a new peak, drawdown should be 0 (not negative)
        assert s.execution_drawdown >= Decimal("0")

    def test_total_pnl(self):
        s = _state()
        s.update_pnl(Decimal("500"), Decimal("200"))
        assert s.total_pnl == Decimal("700")

    def test_update_exposure(self):
        s = _state()
        s.update_exposure(Decimal("50000"))
        assert s.current_exposure == Decimal("50000")

    def test_update_margin(self):
        s = _state()
        s.update_margin(Decimal("4000"), Decimal("6000"))
        assert s.margin_used      == Decimal("4000")
        assert s.margin_available == Decimal("6000")

    def test_margin_utilization_pct(self):
        s = _state()
        s.update_margin(Decimal("3000"), Decimal("7000"))
        assert s.margin_utilization_pct == Decimal("0.3")

    def test_margin_utilization_zero_when_no_margin(self):
        s = _state()
        assert s.margin_utilization_pct == Decimal("0")

    def test_set_risk_level(self):
        s = _state()
        s.set_risk_level(RiskLevel.WARNING)
        assert s.risk_level == RiskLevel.WARNING

    def test_is_elevated(self):
        s = _state()
        assert s.is_elevated is False
        s.set_risk_level(RiskLevel.CRITICAL)
        assert s.is_elevated is True

    def test_is_liquidated(self):
        s = _state()
        assert s.is_liquidated is False
        s.set_liquidation_state(True)
        assert s.is_liquidated is True

    def test_trigger_stop_loss(self):
        s = _state()
        s.trigger_stop_loss()
        assert s.stop_loss_triggered is True

    def test_trigger_take_profit(self):
        s = _state()
        s.trigger_take_profit()
        assert s.take_profit_triggered is True

    def test_set_liquidation_warning(self):
        s = _state()
        s.set_liquidation_warning(True)
        assert s.liquidation_warning is True

    def test_set_liquidation_state_sets_level(self):
        s = _state()
        s.set_liquidation_state(True)
        assert s.liquidation_state  is True
        assert s.risk_level == RiskLevel.LIQUIDATED

    def test_mark_evaluated(self):
        s = _state()
        before = s.last_evaluated_at
        time.sleep(0.01)
        s.mark_evaluated()
        assert s.last_evaluated_at >= before

    def test_execution_duration_s_positive(self):
        s = _state()
        time.sleep(0.01)
        assert s.execution_duration_s > 0

    def test_to_dict_keys(self):
        s = _state()
        d = s.to_dict()
        expected = {
            "state_id", "position_id", "portfolio_id", "strategy_id",
            "instrument", "risk_level", "unrealized_pnl", "realized_pnl",
            "total_pnl", "peak_pnl", "execution_drawdown", "execution_drawdown_pct",
            "current_exposure", "margin_used", "margin_available",
            "margin_utilization_pct", "stop_loss_triggered", "take_profit_triggered",
            "liquidation_warning", "liquidation_state",
            "created_at", "updated_at", "last_evaluated_at",
            "execution_duration_s", "version",
        }
        assert expected <= d.keys()

    def test_repr(self):
        s = _state("x-pos")
        assert "x-pos" in repr(s)
        assert "NORMAL" in repr(s)

    def test_thread_safety_concurrent_updates(self):
        s = _state()
        errors = []
        def worker(idx):
            try:
                s.update_pnl(Decimal(idx * 100), Decimal("0"))
                s.update_margin(Decimal(idx * 10), Decimal(100 - idx * 10))
                _ = s.total_pnl
                _ = s.margin_utilization_pct
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []


# ══════════════════════════════════════════════════════════════════════════════
# 6. RiskContext
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskContext:
    def test_make_risk_context(self):
        ctx = make_risk_context(
            RiskOperationType.REGISTER,
            position_id="pos-1",
            portfolio_id="port-1",
        )
        assert ctx.operation_type == RiskOperationType.REGISTER
        assert ctx.position_id == "pos-1"
        assert ctx.portfolio_id == "port-1"
        assert ctx.requester == ACTOR_RISK

    def test_context_id_is_uuid(self):
        ctx = make_risk_context(RiskOperationType.EVALUATE)
        uuid.UUID(ctx.context_id)

    def test_age_ms_positive(self):
        ctx = make_risk_context(RiskOperationType.SNAPSHOT)
        time.sleep(0.01)
        assert ctx.age_ms > 0

    def test_to_dict(self):
        ctx = make_risk_context(RiskOperationType.UPDATE)
        d = ctx.to_dict()
        assert "context_id" in d
        assert "operation_type" in d


# ══════════════════════════════════════════════════════════════════════════════
# 7. RiskEvent factories
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskEvents:
    def _kwargs(self):
        return dict(
            drawdown_pct=Decimal("0.2"),
            margin_pct=Decimal("0.5"),
            unrealized_pnl=Decimal("-500"),
            portfolio_id="port-1",
            strategy_id="strat-1",
        )

    def test_make_risk_evaluated_event(self):
        e = make_risk_evaluated_event("pos-1", RiskLevel.NORMAL, **self._kwargs())
        assert e.event_type  == RiskEventType.RISK_EVALUATED
        assert e.position_id == "pos-1"
        uuid.UUID(e.event_id)

    def test_make_risk_updated_event(self):
        e = make_risk_updated_event("pos-1", RiskLevel.WATCH, **self._kwargs())
        assert e.event_type == RiskEventType.RISK_UPDATED

    def test_make_risk_warning_event(self):
        e = make_risk_warning_event("pos-1", **self._kwargs())
        assert e.event_type  == RiskEventType.RISK_WARNING
        assert e.risk_level  == RiskLevel.WARNING

    def test_make_risk_critical_event(self):
        e = make_risk_critical_event("pos-1", **self._kwargs())
        assert e.event_type == RiskEventType.RISK_CRITICAL

    def test_make_stop_loss_triggered_event(self):
        e = make_stop_loss_triggered_event("pos-1", **self._kwargs())
        assert e.event_type == RiskEventType.STOP_LOSS_TRIGGERED

    def test_make_take_profit_triggered_event(self):
        e = make_take_profit_triggered_event("pos-1", **self._kwargs())
        assert e.event_type == RiskEventType.TAKE_PROFIT_TRIGGERED

    def test_make_liquidation_warning_event(self):
        e = make_liquidation_warning_event("pos-1", **self._kwargs())
        assert e.event_type == RiskEventType.LIQUIDATION_WARNING

    def test_make_risk_recovered_event(self):
        e = make_risk_recovered_event("pos-1", **self._kwargs())
        assert e.event_type == RiskEventType.RISK_RECOVERED

    def test_to_dict(self):
        e = make_risk_evaluated_event("pos-1", RiskLevel.NORMAL, **self._kwargs())
        d = e.to_dict()
        assert "event_id" in d
        assert "event_type" in d
        assert d["event_type"] == "RISK_EVALUATED"


# ══════════════════════════════════════════════════════════════════════════════
# 8. RiskHistory
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskHistory:
    def _evt(self, pos="pos-1"):
        return make_risk_evaluated_event(
            pos, RiskLevel.NORMAL,
            drawdown_pct=Decimal("0"),
            margin_pct=Decimal("0"),
            unrealized_pnl=Decimal("0"),
        )

    def test_max_events_lt_1_raises(self):
        with pytest.raises(ValueError):
            RiskHistory(max_events=0)

    def test_append_and_count(self):
        h = RiskHistory()
        h.append(self._evt())
        assert h.count() == 1

    def test_extend(self):
        h = RiskHistory()
        h.extend([self._evt(), self._evt()])
        assert h.count() == 2

    def test_all(self):
        h = RiskHistory()
        h.append(self._evt("p1"))
        h.append(self._evt("p2"))
        assert len(h.all()) == 2

    def test_latest(self):
        h = RiskHistory()
        for i in range(5):
            h.append(self._evt(f"p{i}"))
        latest = h.latest(3)
        assert len(latest) == 3

    def test_for_position(self):
        h = RiskHistory()
        h.append(self._evt("pos-A"))
        h.append(self._evt("pos-B"))
        h.append(self._evt("pos-A"))
        assert len(h.for_position("pos-A")) == 2
        assert len(h.for_position("pos-B")) == 1

    def test_filter(self):
        h = RiskHistory()
        e = make_risk_warning_event(
            "pos-1",
            drawdown_pct=Decimal("0.5"),
            margin_pct=Decimal("0.5"),
            unrealized_pnl=Decimal("-100"),
        )
        h.append(self._evt())
        h.append(e)
        warnings = h.filter(lambda ev: ev.event_type == RiskEventType.RISK_WARNING)
        assert len(warnings) == 1

    def test_eviction_when_full(self):
        h = RiskHistory(max_events=3)
        for i in range(5):
            h.append(self._evt(f"p{i}"))
        assert h.count() == 3

    def test_clear(self):
        h = RiskHistory()
        h.append(self._evt())
        h.clear()
        assert h.is_empty()

    def test_len(self):
        h = RiskHistory()
        h.append(self._evt())
        h.append(self._evt())
        assert len(h) == 2


# ══════════════════════════════════════════════════════════════════════════════
# 9. RiskStatistics
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskStatistics:
    def test_initial_zeroes(self):
        s = RiskStatistics()
        assert s.total_evaluations == 0
        assert s.total_registered  == 0

    def test_record_evaluation(self):
        s = RiskStatistics()
        s.record_evaluation(elapsed_ms=5.0)
        assert s.total_evaluations == 1
        assert s.average_eval_time_ms == 5.0

    def test_record_registered_and_unregistered(self):
        s = RiskStatistics()
        s.record_registered()
        s.record_registered()
        s.record_unregistered()
        assert s.total_registered   == 2
        assert s.total_unregistered == 1

    def test_event_counters(self):
        s = RiskStatistics()
        s.record_warning()
        s.record_critical()
        s.record_liquidation()
        s.record_stop_loss()
        s.record_take_profit()
        s.record_recovery()
        assert s.warning_count      == 1
        assert s.critical_count     == 1
        assert s.liquidation_events == 1
        assert s.stop_loss_events   == 1
        assert s.take_profit_events == 1
        assert s.recovery_events    == 1

    def test_record_sample_averages(self):
        s = RiskStatistics()
        s.record_sample(Decimal("1000"), Decimal("0.5"), Decimal("0.1"))
        s.record_sample(Decimal("2000"), Decimal("0.7"), Decimal("0.3"))
        assert s.average_exposure  == Decimal("1500")
        assert s.average_margin_usage == Decimal("0.6")
        assert s.average_drawdown     == Decimal("0.2")

    def test_update_live_counts(self):
        s = RiskStatistics()
        s.update_live_counts(normal=5, watch=2, warning=1, critical=0, liquidated=0)
        assert s.positions_normal  == 5
        assert s.positions_watch   == 2
        assert s.positions_warning == 1

    def test_average_eval_time_zero_when_no_evals(self):
        s = RiskStatistics()
        assert s.average_eval_time_ms == 0.0

    def test_to_dict_keys(self):
        d = RiskStatistics().to_dict()
        assert "total_evaluations" in d
        assert "average_exposure"  in d


# ══════════════════════════════════════════════════════════════════════════════
# 10. RiskSnapshot & RiskBookSnapshot
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskSnapshot:
    def test_from_state(self):
        s = _state("snap-pos")
        s.update_pnl(Decimal("1000"), Decimal("200"))
        snap = RiskSnapshot.from_state(s)
        assert snap.position_id   == "snap-pos"
        assert snap.risk_level    == "NORMAL"
        assert snap.unrealized_pnl == "1000"

    def test_make_risk_snapshot(self):
        s = _state()
        snap = make_risk_snapshot(s)
        assert isinstance(snap, RiskSnapshot)

    def test_snapshot_id_is_uuid(self):
        snap = make_risk_snapshot(_state())
        uuid.UUID(snap.snapshot_id)

    def test_is_elevated_false_for_normal(self):
        snap = make_risk_snapshot(_state())
        assert snap.is_elevated is False

    def test_to_dict_keys(self):
        snap = make_risk_snapshot(_state())
        d = snap.to_dict()
        assert "snapshot_id"  in d
        assert "position_id"  in d
        assert "risk_level"   in d


class TestRiskBookSnapshot:
    def test_empty_book_snapshot(self):
        snap = make_risk_book_snapshot([], RiskStatistics())
        assert snap.is_empty is True
        assert snap.total_positions == 0
        assert snap.has_elevated is False

    def test_book_snapshot_counts(self):
        states = [
            _state("p1"),   # NORMAL
            _state("p2"),   # will set to WARNING
        ]
        states[1].set_risk_level(RiskLevel.WARNING)
        snap = make_risk_book_snapshot(states, RiskStatistics())
        assert snap.total_positions == 2
        assert snap.normal_count    == 1
        assert snap.warning_count   == 1
        assert snap.has_elevated    is True

    def test_to_dict(self):
        snap = make_risk_book_snapshot([], RiskStatistics())
        d = snap.to_dict()
        assert "total_positions" in d


# ══════════════════════════════════════════════════════════════════════════════
# 11. RiskValidation
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskValidation:
    def test_ok_result(self):
        r = RiskValidationResult.ok()
        assert r.is_valid is True
        assert r.errors   == ()

    def test_fail_result(self):
        r = RiskValidationResult.fail(["err1", "err2"])
        assert r.is_valid is False
        assert "err1" in r.errors

    def test_raise_if_invalid(self):
        r = RiskValidationResult.fail(["bad thing"])
        with pytest.raises(PositionRiskValidationError):
            r.raise_if_invalid()

    def test_raise_if_valid_does_not_raise(self):
        RiskValidationResult.ok().raise_if_invalid()  # no exception


class TestRiskValidator:
    def _validator(self):
        return RiskValidator()

    def test_valid_state(self):
        result = self._validator().validate_state_consistency(_state())
        assert result.is_valid

    def test_empty_position_id_fails(self):
        s = PositionRiskState(position_id="")
        result = self._validator().validate_state_consistency(s)
        assert not result.is_valid

    def test_valid_pnl(self):
        s = _state()
        s.update_pnl(Decimal("1000"), Decimal("0"))
        result = self._validator().validate_pnl_consistency(s)
        assert result.is_valid

    def test_valid_margin(self):
        s = _state()
        s.update_margin(Decimal("3000"), Decimal("7000"))
        result = self._validator().validate_margin_consistency(s)
        assert result.is_valid

    def test_valid_limits(self):
        result = self._validator().validate_limits(RiskLimits())
        assert result.is_valid

    def test_valid_thresholds(self):
        result = self._validator().validate_thresholds(RiskThreshold())
        assert result.is_valid

    def test_validate_all_clean_state(self):
        result = self._validator().validate_all(
            _state(), RiskLimits(), RiskThreshold()
        )
        assert result.is_valid


# ══════════════════════════════════════════════════════════════════════════════
# 12. RiskMonitor
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskMonitor:
    def _monitor(self):
        return RiskMonitor()

    def _eval(self, state, limits=None, thresholds=None):
        return self._monitor().evaluate(
            state,
            limits     or RiskLimits(),
            thresholds or RiskThreshold(),
        )

    def test_normal_state_stays_normal(self):
        s = _state()
        result = self._eval(s)
        assert result.new_risk_level == RiskLevel.NORMAL

    def test_drawdown_watch_threshold(self):
        s = _state()
        # 30% drawdown > 25% WATCH threshold
        s.update_pnl(Decimal("1000"), Decimal("0"))
        s.update_pnl(Decimal("700"), Decimal("0"))   # 30% drawdown
        result = self._eval(s)
        assert result.new_risk_level == RiskLevel.WATCH

    def test_drawdown_warning_threshold(self):
        s = _state()
        s.update_pnl(Decimal("1000"), Decimal("0"))
        s.update_pnl(Decimal("400"), Decimal("0"))   # 60% drawdown > 50% WARNING
        result = self._eval(s)
        assert result.new_risk_level in (RiskLevel.WARNING, RiskLevel.CRITICAL)

    def test_drawdown_critical_threshold(self):
        s = _state()
        s.update_pnl(Decimal("1000"), Decimal("0"))
        s.update_pnl(Decimal("200"), Decimal("0"))   # 80% > 75% CRITICAL
        result = self._eval(s)
        assert result.new_risk_level in (RiskLevel.CRITICAL, RiskLevel.LIQUIDATION_PENDING)

    def test_drawdown_liquidation_threshold(self):
        s = _state()
        s.update_pnl(Decimal("1000"), Decimal("0"))
        s.update_pnl(Decimal("50"), Decimal("0"))    # 95% > 90% LIQUIDATION_PENDING
        result = self._eval(s)
        assert result.new_risk_level == RiskLevel.LIQUIDATION_PENDING

    def test_margin_warning_threshold(self):
        s = _state()
        s.update_margin(Decimal("9000"), Decimal("1000"))  # 90% > 85% WARNING
        result = self._eval(s)
        assert result.new_risk_level in (RiskLevel.WARNING, RiskLevel.CRITICAL)

    def test_stop_loss_by_max_loss(self):
        s = _state()
        limits = RiskLimits(max_loss=Decimal("1000"))
        s.update_pnl(Decimal("-1500"), Decimal("0"))  # loss exceeds max_loss
        result = self._monitor().evaluate(s, limits, RiskThreshold())
        assert result.stop_loss_triggered is True
        assert RiskEventType.STOP_LOSS_TRIGGERED in result.events_to_emit

    def test_take_profit_trigger(self):
        s = _state()
        limits = RiskLimits(take_profit=Decimal("2000"))
        s.update_pnl(Decimal("3000"), Decimal("0"))  # exceeds take_profit
        result = self._monitor().evaluate(s, limits, RiskThreshold())
        assert result.take_profit_triggered is True
        assert RiskEventType.TAKE_PROFIT_TRIGGERED in result.events_to_emit

    def test_liquidation_warning_flag(self):
        s = _state()
        s.update_pnl(Decimal("1000"), Decimal("0"))
        s.update_pnl(Decimal("50"), Decimal("0"))    # 95% drawdown
        result = self._eval(s)
        assert result.liquidation_warning is True

    def test_risk_evaluated_always_in_events(self):
        result = self._eval(_state())
        assert RiskEventType.RISK_EVALUATED in result.events_to_emit

    def test_liquidated_position_stays_liquidated(self):
        s = _state()
        s.set_liquidation_state(True)
        result = self._eval(s)
        assert result.new_risk_level == RiskLevel.LIQUIDATED

    def test_recovery_event_emitted_on_improvement(self):
        s = _state()
        s.set_risk_level(RiskLevel.CRITICAL)   # artificially elevated
        # No drawdown, no margin issues → monitor should see NORMAL
        result = self._eval(s)
        assert RiskEventType.RISK_RECOVERED in result.events_to_emit


# ══════════════════════════════════════════════════════════════════════════════
# 13. RiskFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskFactory:
    def test_create_from_position(self):
        pos = _make_position()
        factory = RiskFactory()
        state = factory.create(pos, RiskLimits(), RiskThreshold())
        assert state.position_id == pos.position_id
        assert state.instrument  == pos.instrument

    def test_create_copies_portfolio_and_strategy(self):
        pos = _make_position(portfolio_id="my-port", strategy_id="my-strat")
        state = RiskFactory().create(pos, RiskLimits(), RiskThreshold())
        assert state.portfolio_id == "my-port"
        assert state.strategy_id  == "my-strat"

    def test_validation_empty_instrument(self):
        factory = RiskFactory()
        pos = _make_position()
        # Monkey-patch instrument to empty (normally not possible via factory)
        object.__setattr__(pos, "_instrument", "")
        with pytest.raises(PositionRiskValidationError):
            factory.create(pos, RiskLimits(), RiskThreshold())

    def test_validation_empty_position_id(self):
        factory = RiskFactory()
        pos = _make_position()
        object.__setattr__(pos, "_position_id", "")
        with pytest.raises(PositionRiskValidationError):
            factory.create(pos, RiskLimits(), RiskThreshold())


# ══════════════════════════════════════════════════════════════════════════════
# 14. RiskRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskRegistry:
    def _started_registry(self, max_positions=100):
        r = RiskRegistry(max_positions=max_positions)
        r.start()
        return r

    def test_start_stop(self):
        r = RiskRegistry()
        r.start()
        assert r.lifecycle_state().value == "running"
        r.stop()
        assert r.lifecycle_state().value != "running"

    def test_register_and_get_state(self):
        r = self._started_registry()
        s = _state("r-pos")
        r.register(s, RiskLimits(), RiskThreshold())
        assert r.get_state("r-pos") is s
        r.stop()

    def test_register_requires_running(self):
        r = RiskRegistry()
        with pytest.raises(PositionRiskNotRunningError):
            r.register(_state(), RiskLimits(), RiskThreshold())

    def test_duplicate_register_raises(self):
        r = self._started_registry()
        s = _state("dup")
        r.register(s, RiskLimits(), RiskThreshold())
        with pytest.raises(DuplicateRiskStateError):
            r.register(_state("dup"), RiskLimits(), RiskThreshold())
        r.stop()

    def test_capacity_enforced(self):
        r = self._started_registry(max_positions=1)
        r.register(_state("p1"), RiskLimits(), RiskThreshold())
        with pytest.raises(PositionRiskCapacityError):
            r.register(_state("p2"), RiskLimits(), RiskThreshold())
        r.stop()

    def test_unregister(self):
        r = self._started_registry()
        s = _state("u-pos")
        r.register(s, RiskLimits(), RiskThreshold())
        returned = r.unregister("u-pos")
        assert returned is s
        assert r.get_state("u-pos") is None
        r.stop()

    def test_unregister_not_found_raises(self):
        r = self._started_registry()
        with pytest.raises(RiskStateNotFoundError):
            r.unregister("ghost")
        r.stop()

    def test_require_state_raises_when_missing(self):
        r = self._started_registry()
        with pytest.raises(RiskStateNotFoundError):
            r.require_state("ghost")
        r.stop()

    def test_all_states(self):
        r = self._started_registry()
        r.register(_state("a"), RiskLimits(), RiskThreshold())
        r.register(_state("b"), RiskLimits(), RiskThreshold())
        assert len(r.all_states()) == 2
        r.stop()

    def test_contains(self):
        r = self._started_registry()
        r.register(_state("c"), RiskLimits(), RiskThreshold())
        assert r.contains("c") is True
        assert r.contains("z") is False
        r.stop()

    def test_count(self):
        r = self._started_registry()
        assert r.count() == 0
        r.register(_state("x"), RiskLimits(), RiskThreshold())
        assert r.count() == 1
        r.stop()

    def test_is_empty(self):
        r = self._started_registry()
        assert r.is_empty() is True
        r.register(_state("y"), RiskLimits(), RiskThreshold())
        assert r.is_empty() is False
        r.stop()

    def test_get_limits(self):
        r = self._started_registry()
        lim = RiskLimits(max_loss=Decimal("999"))
        r.register(_state("lim-pos"), lim, RiskThreshold())
        got = r.get_limits("lim-pos")
        assert got is lim
        r.stop()

    def test_get_thresholds(self):
        r = self._started_registry()
        thr = RiskThreshold()
        r.register(_state("thr-pos"), RiskLimits(), thr)
        got = r.get_thresholds("thr-pos")
        assert got is thr
        r.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 15. PositionRiskManager
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionRiskManager:
    def test_start_stop_lifecycle(self):
        m = PositionRiskManager()
        m.start()
        assert m.lifecycle_state().value == "running"
        m.stop()
        assert m.lifecycle_state().value != "running"

    def test_register_returns_state(self):
        m = _started_manager()
        pos = _make_position()
        state = m.register(pos)
        assert isinstance(state, PositionRiskState)
        assert state.position_id == pos.position_id
        m.stop()

    def test_register_not_running_raises(self):
        m = PositionRiskManager()
        with pytest.raises(PositionRiskNotRunningError):
            m.register(_make_position())

    def test_duplicate_register_raises(self):
        m = _started_manager()
        pos = _make_position()
        m.register(pos)
        with pytest.raises(DuplicateRiskStateError):
            m.register(pos)
        m.stop()

    def test_update_returns_state(self):
        m = _started_manager()
        pos = _make_position()
        m.register(pos)
        state = m.update(
            pos.position_id,
            unrealized_pnl=Decimal("1000"),
            realized_pnl=Decimal("0"),
            exposure=Decimal("50000"),
            margin_used=Decimal("3000"),
            margin_available=Decimal("7000"),
        )
        assert state.unrealized_pnl == Decimal("1000")
        m.stop()

    def test_update_not_found_raises(self):
        m = _started_manager()
        with pytest.raises(RiskStateNotFoundError):
            m.update(
                "ghost",
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                exposure=Decimal("0"),
                margin_used=Decimal("0"),
                margin_available=Decimal("0"),
            )
        m.stop()

    def test_evaluate_updates_risk_level(self):
        m = _started_manager()
        pos = _make_position()
        m.register(pos)
        # Inject a big loss to trigger stop-loss
        state = m.get_state(pos.position_id)
        state.update_pnl(Decimal("-15000"), Decimal("0"))   # exceeds DEFAULT_MAX_LOSS
        evaluated = m.evaluate(pos.position_id)
        assert evaluated.stop_loss_triggered is True
        m.stop()

    def test_evaluate_records_events(self):
        m = _started_manager()
        pos = _make_position()
        m.register(pos)
        m.evaluate(pos.position_id)
        assert m.history().count() >= 1
        m.stop()

    def test_evaluate_not_found_raises(self):
        m = _started_manager()
        with pytest.raises(RiskStateNotFoundError):
            m.evaluate("ghost")
        m.stop()

    def test_unregister(self):
        m = _started_manager()
        pos = _make_position()
        m.register(pos)
        state = m.unregister(pos.position_id)
        assert isinstance(state, PositionRiskState)
        assert m.get_state(pos.position_id) is None
        m.stop()

    def test_unregister_not_found_raises(self):
        m = _started_manager()
        with pytest.raises(RiskStateNotFoundError):
            m.unregister("ghost")
        m.stop()

    def test_get_state_returns_none_when_absent(self):
        m = _started_manager()
        assert m.get_state("absent") is None
        m.stop()

    def test_require_state_raises_when_absent(self):
        m = _started_manager()
        with pytest.raises(RiskStateNotFoundError):
            m.require_state("absent")
        m.stop()

    def test_snapshot(self):
        m = _started_manager()
        pos = _make_position()
        m.register(pos)
        snap = m.snapshot(pos.position_id)
        assert isinstance(snap, RiskSnapshot)
        m.stop()

    def test_snapshot_not_found_raises(self):
        m = _started_manager()
        with pytest.raises(RiskStateNotFoundError):
            m.snapshot("ghost")
        m.stop()

    def test_all_snapshots(self):
        m = _started_manager()
        p1 = _make_position("NIFTY50")
        p2 = _make_position("BANKNIFTY")
        m.register(p1)
        m.register(p2)
        snaps = m.all_snapshots()
        assert len(snaps) == 2
        m.stop()

    def test_book_snapshot(self):
        m = _started_manager()
        m.register(_make_position())
        snap = m.book_snapshot()
        assert isinstance(snap, RiskBookSnapshot)
        assert snap.total_positions == 1
        m.stop()

    def test_statistics_returns_copy(self):
        m = _started_manager()
        s1 = m.statistics()
        s2 = m.statistics()
        assert s1 is not s2
        m.stop()

    def test_statistics_updated_on_register(self):
        m = _started_manager()
        m.register(_make_position())
        stats = m.statistics()
        assert stats.total_registered == 1
        m.stop()

    def test_statistics_updated_on_evaluate(self):
        m = _started_manager()
        pos = _make_position()
        m.register(pos)
        m.evaluate(pos.position_id)
        stats = m.statistics()
        assert stats.total_evaluations >= 1
        m.stop()

    def test_events_list(self):
        m = _started_manager()
        pos = _make_position()
        m.register(pos)
        m.evaluate(pos.position_id)
        events = m.events()
        assert len(events) >= 1
        m.stop()

    def test_validate(self):
        m = _started_manager()
        pos = _make_position()
        m.register(pos)
        result = m.validate(pos.position_id)
        assert result.is_valid is True
        m.stop()

    def test_custom_limits_and_thresholds(self):
        m = _started_manager()
        pos = _make_position()
        limits = RiskLimits(max_loss=Decimal("500"))
        thresholds = RiskThreshold()
        m.register(pos, limits=limits, thresholds=thresholds)
        state = m.get_state(pos.position_id)
        assert state is not None
        m.stop()

    def test_full_lifecycle_cycle(self):
        """Register → update → evaluate → unregister."""
        m = _started_manager()
        pos = _make_position()
        state = m.register(pos)

        m.update(
            pos.position_id,
            unrealized_pnl=Decimal("1000"),
            realized_pnl=Decimal("0"),
            exposure=Decimal("100000"),
            margin_used=Decimal("5000"),
            margin_available=Decimal("5000"),
        )
        m.evaluate(pos.position_id)
        final = m.unregister(pos.position_id)
        assert final.position_id == pos.position_id
        m.stop()

    def test_concurrency_safe_register(self):
        m = _started_manager(max_positions=200)
        errors = []
        positions = [_make_position(f"STOCK{i}") for i in range(20)]

        def worker(pos):
            try:
                m.register(pos)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(p,)) for p in positions]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        assert m.book_snapshot().total_positions == 20
        m.stop()

    def test_live_counts_updated_on_evaluate(self):
        m = _started_manager()
        pos = _make_position()
        state = m.register(pos)
        # Force a big drawdown
        state.update_pnl(Decimal("1000"), Decimal("0"))
        state.update_pnl(Decimal("600"), Decimal("0"))   # 40% > WATCH (25%)
        m.evaluate(pos.position_id)
        stats = m.statistics()
        # Position should be WATCH or WARNING now
        assert (stats.positions_watch + stats.positions_warning) >= 1
        m.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 16. Regression guards
# ══════════════════════════════════════════════════════════════════════════════

class TestRegressionGuards:
    def test_risk_level_is_str_enum(self):
        """RiskLevel values can be compared as strings."""
        assert RiskLevel.NORMAL == "NORMAL"

    def test_manager_registry_is_started_on_manager_start(self):
        m = PositionRiskManager()
        m.start()
        # Internal registry should be running so register works
        pos = _make_position()
        m.register(pos)   # should not raise
        m.stop()

    def test_unregister_decrements_live_count(self):
        m = _started_manager()
        pos = _make_position()
        m.register(pos)
        assert m.statistics().total_registered == 1
        m.unregister(pos.position_id)
        assert m.statistics().total_unregistered == 1
        m.stop()

    def test_default_limits_are_frozen(self):
        """DEFAULT_RISK_LIMITS must not be mutated."""
        import dataclasses
        assert dataclasses.is_dataclass(DEFAULT_RISK_LIMITS)
        with pytest.raises((TypeError, AttributeError)):
            DEFAULT_RISK_LIMITS.max_loss = Decimal("1")  # type: ignore[misc]

    def test_default_thresholds_are_frozen(self):
        import dataclasses
        assert dataclasses.is_dataclass(DEFAULT_RISK_THRESHOLDS)
        with pytest.raises((TypeError, AttributeError)):
            DEFAULT_RISK_THRESHOLDS.watch_drawdown_pct = Decimal("0.1")  # type: ignore[misc]

    def test_position_risk_state_not_lifecycle_aware(self):
        """PositionRiskState must NOT be a LifecycleAwareMixin."""
        from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin
        s = _state()
        assert not isinstance(s, LifecycleAwareMixin)

    def test_risk_monitor_not_lifecycle_aware(self):
        """RiskMonitor must NOT be a LifecycleAwareMixin."""
        from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin
        m = RiskMonitor()
        assert not isinstance(m, LifecycleAwareMixin)

    def test_risk_factory_not_lifecycle_aware(self):
        from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin
        f = RiskFactory()
        assert not isinstance(f, LifecycleAwareMixin)

    def test_peak_pnl_never_decreases(self):
        s = _state()
        s.update_pnl(Decimal("2000"), Decimal("0"))
        s.update_pnl(Decimal("500"),  Decimal("0"))
        s.update_pnl(Decimal("100"),  Decimal("0"))
        assert s.peak_pnl == Decimal("2000")
