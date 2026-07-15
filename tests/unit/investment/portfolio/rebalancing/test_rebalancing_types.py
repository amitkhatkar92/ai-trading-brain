"""test_rebalancing_types.py — types, enums, constants, utilities."""
from __future__ import annotations

import pytest

from iios.investment.portfolio.rebalancing import (
    DRIFT_THRESHOLD_CRITICAL,
    DRIFT_THRESHOLD_MINOR,
    DRIFT_THRESHOLD_MODERATE,
    DRIFT_THRESHOLD_SIGNIFICANT,
    LTCG_HOLDING_DAYS,
    REBAL_SCORE_EXCELLENT,
    REBAL_SCORE_GOOD,
    CurrentPosition,
    DriftLevel,
    RebalanceGrade,
    RebalanceLevel,
    RebalanceStatus,
    RebalanceTrigger,
    TradePriority,
    TradeSide,
    TargetPosition,
    ValidationStatus,
    aggregate_drift_level,
    classify_drift_level,
    current_positions_from_any,
    now_utc,
    portfolio_weighted_liquidity,
    portfolio_weighted_risk,
    rebalance_score_to_grade,
    rebalance_score_to_level,
    target_positions_from_any,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_drift_thresholds_ordered(self):
        assert DRIFT_THRESHOLD_MINOR < DRIFT_THRESHOLD_MODERATE
        assert DRIFT_THRESHOLD_MODERATE < DRIFT_THRESHOLD_SIGNIFICANT
        assert DRIFT_THRESHOLD_SIGNIFICANT < DRIFT_THRESHOLD_CRITICAL

    def test_score_thresholds_ordered(self):
        from iios.investment.portfolio.rebalancing import (
            REBAL_SCORE_AVERAGE, REBAL_SCORE_BELOW_AVERAGE,
        )
        assert REBAL_SCORE_BELOW_AVERAGE < REBAL_SCORE_AVERAGE
        assert REBAL_SCORE_AVERAGE < REBAL_SCORE_GOOD
        assert REBAL_SCORE_GOOD < REBAL_SCORE_EXCELLENT

    def test_ltcg_is_365(self):
        assert LTCG_HOLDING_DAYS == 365


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_trigger_values(self):
        assert RebalanceTrigger.CALENDAR.value == "calendar"
        assert RebalanceTrigger.NONE.value == "none"

    def test_status_values(self):
        assert RebalanceStatus.COMPLETED.value == "completed"
        assert RebalanceStatus.FAILED.value == "failed"

    def test_drift_level_values(self):
        assert DriftLevel.NONE.value == "none"
        assert DriftLevel.CRITICAL.value == "critical"

    def test_trade_priority_values(self):
        assert TradePriority.IMMEDIATE.value == "immediate"
        assert TradePriority.LOW.value == "low"

    def test_trade_side_values(self):
        assert TradeSide.BUY.value == "buy"
        assert TradeSide.SELL.value == "sell"
        assert TradeSide.HOLD.value == "hold"

    def test_validation_status(self):
        assert ValidationStatus.PASSED.value == "passed"
        assert ValidationStatus.FAILED.value == "failed"


# ---------------------------------------------------------------------------
# CurrentPosition
# ---------------------------------------------------------------------------

class TestCurrentPosition:
    def test_ltcg_eligible(self):
        p = CurrentPosition(symbol="X", current_weight=0.10, holding_days=400)
        assert p.is_ltcg_eligible is True

    def test_not_ltcg_eligible(self):
        p = CurrentPosition(symbol="X", current_weight=0.10, holding_days=200)
        assert p.is_ltcg_eligible is False

    def test_applicable_tax_rate_ltcg(self):
        p = CurrentPosition(symbol="X", current_weight=0.10, holding_days=400)
        assert p.applicable_tax_rate == 0.125

    def test_applicable_tax_rate_stcg(self):
        p = CurrentPosition(symbol="X", current_weight=0.10, holding_days=100)
        assert p.applicable_tax_rate == 0.20

    def test_frozen(self):
        p = CurrentPosition(symbol="X", current_weight=0.10)
        with pytest.raises((TypeError, AttributeError)):
            p.symbol = "Y"  # type: ignore

    def test_to_dict(self):
        p = CurrentPosition(symbol="RELIANCE", current_weight=0.20, sector="ENERGY")
        d = p.to_dict()
        assert d["symbol"] == "RELIANCE"
        assert d["sector"] == "ENERGY"


# ---------------------------------------------------------------------------
# TargetPosition
# ---------------------------------------------------------------------------

class TestTargetPosition:
    def test_frozen(self):
        p = TargetPosition(symbol="X", target_weight=0.10)
        with pytest.raises((TypeError, AttributeError)):
            p.symbol = "Y"  # type: ignore

    def test_to_dict(self):
        p = TargetPosition(symbol="TCS", target_weight=0.15)
        d = p.to_dict()
        assert d["symbol"] == "TCS"


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

class TestFactories:
    def test_current_from_list(self):
        items = [
            CurrentPosition("A", 0.5),
            CurrentPosition("B", 0.5),
        ]
        result = current_positions_from_any(items)
        assert len(result) == 2
        assert result[0].symbol == "A"

    def test_target_from_list(self):
        items = [TargetPosition("A", 0.5), TargetPosition("B", 0.5)]
        result = target_positions_from_any(items)
        assert len(result) == 2

    def test_current_duck_typed(self):
        class DuckPos:
            symbol = "X"
            current_weight = 0.5
        result = current_positions_from_any([DuckPos()])
        assert result[0].symbol == "X"
        assert result[0].current_weight == 0.5

    def test_target_duck_typed(self):
        class DuckPos:
            symbol = "X"
            target_weight = 0.5
        result = target_positions_from_any([DuckPos()])
        assert result[0].symbol == "X"

    def test_empty_list(self):
        assert current_positions_from_any([]) == []
        assert target_positions_from_any([]) == []


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

class TestUtilities:
    def test_classify_drift_none(self):
        assert classify_drift_level(0.01) == DriftLevel.NONE

    def test_classify_drift_minor(self):
        assert classify_drift_level(0.03) == DriftLevel.MINOR

    def test_classify_drift_moderate(self):
        assert classify_drift_level(0.06) == DriftLevel.MODERATE

    def test_classify_drift_significant(self):
        assert classify_drift_level(0.09) == DriftLevel.SIGNIFICANT

    def test_classify_drift_critical(self):
        assert classify_drift_level(0.12) == DriftLevel.CRITICAL

    def test_score_to_grade(self):
        assert rebalance_score_to_grade(0.80) == RebalanceGrade.A
        assert rebalance_score_to_grade(0.65) == RebalanceGrade.B
        assert rebalance_score_to_grade(0.10) == RebalanceGrade.F

    def test_score_to_level(self):
        assert rebalance_score_to_level(0.80) == RebalanceLevel.EXCELLENT
        assert rebalance_score_to_level(0.10) == RebalanceLevel.POOR

    def test_aggregate_drift_level_highest(self):
        levels = [DriftLevel.MINOR, DriftLevel.CRITICAL, DriftLevel.MODERATE]
        assert aggregate_drift_level(levels) == DriftLevel.CRITICAL

    def test_aggregate_drift_empty(self):
        assert aggregate_drift_level([]) == DriftLevel.NONE

    def test_portfolio_weighted_risk(self):
        positions = [
            CurrentPosition("A", 0.5, risk_score=0.4),
            CurrentPosition("B", 0.5, risk_score=0.6),
        ]
        assert abs(portfolio_weighted_risk(positions) - 0.5) < 1e-9

    def test_portfolio_weighted_liquidity(self):
        positions = [
            CurrentPosition("A", 0.5, liquidity=0.8),
            CurrentPosition("B", 0.5, liquidity=0.6),
        ]
        assert abs(portfolio_weighted_liquidity(positions) - 0.7) < 1e-9

    def test_now_utc_format(self):
        ts = now_utc()
        assert "T" in ts or " " in ts or len(ts) > 15
