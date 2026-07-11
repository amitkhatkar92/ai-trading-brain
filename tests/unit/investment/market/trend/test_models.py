"""tests/unit/investment/market/trend/test_models.py
Tests for all enums and dataclasses in trend/models.py.
"""
from __future__ import annotations

import pytest
from iios.investment.market.trend.models import (
    TrendStage,
    TrendEventType,
    TrendTransitionType,
    ImpulseQuality,
    CorrectionQuality,
    TrendQualityMetrics,
    TrendScore,
    StrategyReadiness,
    TrendIntelligenceSnapshot,
    TrendEventRecord,
    TrendMomentumState,
)
from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.regime.models import RegimeType


class TestEnums:
    def test_trend_stage_has_8_values(self):
        assert len(TrendStage) == 8

    def test_trend_event_type_has_9_values(self):
        assert len(TrendEventType) == 9

    def test_trend_transition_type_has_4_values(self):
        assert len(TrendTransitionType) == 4

    def test_impulse_quality_has_3_values(self):
        assert len(ImpulseQuality) == 3

    def test_correction_quality_has_4_values(self):
        assert len(CorrectionQuality) == 4

    def test_trend_stage_values(self):
        expected = {"emerging", "developing", "established", "mature",
                    "exhausting", "failing", "reversing", "completed"}
        assert {s.value for s in TrendStage} == expected


class TestTrendQualityMetrics:
    def _make(self, overall: float) -> TrendQualityMetrics:
        return TrendQualityMetrics(
            smoothness=0.5, reliability=0.5, efficiency=0.5,
            consistency=0.5, stability=0.5, persistence=0.5,
            overall=overall,
        )

    def test_grade_A(self):
        assert self._make(85.0).grade == "A"

    def test_grade_B(self):
        assert self._make(70.0).grade == "B"

    def test_grade_C(self):
        assert self._make(55.0).grade == "C"

    def test_grade_D(self):
        assert self._make(40.0).grade == "D"

    def test_grade_F(self):
        assert self._make(20.0).grade == "F"

    def test_to_dict_has_correct_keys(self):
        d = self._make(60.0).to_dict()
        expected_keys = {
            "smoothness", "reliability", "efficiency",
            "consistency", "stability", "persistence", "overall", "grade",
        }
        assert set(d.keys()) == expected_keys


class TestTrendScore:
    def _make(self, overall: float) -> TrendScore:
        return TrendScore(
            overall=overall, quality_score=50.0,
            momentum_score=50.0, lifecycle_score=60.0,
            regime_alignment_score=50.0,
        )

    def test_grade_A(self):
        assert self._make(82.0).grade == "A"

    def test_grade_F(self):
        assert self._make(10.0).grade == "F"

    def test_to_dict_keys(self):
        d = self._make(60.0).to_dict()
        assert "overall" in d
        assert "grade" in d
        assert "quality_score" in d
        assert "momentum_score" in d
        assert "lifecycle_score" in d
        assert "regime_alignment_score" in d


class TestStrategyReadiness:
    def test_to_dict_has_correct_keys(self):
        sr = StrategyReadiness(
            momentum_suitability=0.8,
            breakout_suitability=0.7,
            retest_suitability=0.6,
            mean_reversion_suitability=0.2,
            swing_trading_suitability=0.75,
            position_trading_suitability=0.65,
            best_approach="momentum",
            notes="test",
        )
        d = sr.to_dict()
        expected = {
            "momentum_suitability", "breakout_suitability", "retest_suitability",
            "mean_reversion_suitability", "swing_trading_suitability",
            "position_trading_suitability", "best_approach", "notes",
        }
        assert set(d.keys()) == expected


class TestTrendIntelligenceSnapshot:
    def test_to_dict_has_all_top_level_keys(self):
        snap = TrendIntelligenceSnapshot(symbol="NIFTY", timeframe="1d")
        d = snap.to_dict()
        expected = {
            "snapshot_id", "symbol", "timeframe", "bar_index", "timestamp",
            "direction", "confirmed", "leg_count", "structure_phase", "trend_phase",
            "stage", "stage_confidence", "quality", "momentum", "confidence",
            "continuation_probability", "failure_probability", "reversal_probability",
            "expected_remaining_legs", "strategy_readiness", "regime",
            "regime_aligned", "last_event", "score",
        }
        assert set(d.keys()) == expected

    def test_default_direction_undefined(self):
        snap = TrendIntelligenceSnapshot()
        assert snap.direction == TrendDirection.UNDEFINED

    def test_default_regime_unknown(self):
        snap = TrendIntelligenceSnapshot()
        assert snap.regime == RegimeType.UNKNOWN


class TestTrendEventRecord:
    def test_to_dict_round_trips_correctly(self):
        rec = TrendEventRecord(
            event_type=TrendEventType.TREND_START,
            symbol="NIFTY",
            timeframe="1d",
            bar_index=42,
            stage_before=TrendStage.EMERGING,
            stage_after=TrendStage.DEVELOPING,
            description="test event",
        )
        d = rec.to_dict()
        assert d["event_type"] == "trend_start"
        assert d["symbol"] == "NIFTY"
        assert d["bar_index"] == 42
        assert d["stage_before"] == "emerging"
        assert d["stage_after"] == "developing"
        assert "event_id" in d

    def test_auto_uuid(self):
        r1 = TrendEventRecord()
        r2 = TrendEventRecord()
        assert r1.event_id != r2.event_id


class TestTrendMomentumState:
    def test_to_dict_has_correct_keys(self):
        ms = TrendMomentumState(
            velocity=1.0, acceleration=0.2,
            impulse_quality=ImpulseQuality.STRONG,
            correction_quality=CorrectionQuality.SHALLOW,
            is_accelerating=True, is_decelerating=False,
            momentum_score=75.0,
        )
        d = ms.to_dict()
        expected = {
            "velocity", "acceleration", "impulse_quality", "correction_quality",
            "is_accelerating", "is_decelerating", "momentum_score",
        }
        assert set(d.keys()) == expected

    def test_values_serialized_as_strings(self):
        ms = TrendMomentumState(
            velocity=1.0, acceleration=0.0,
            impulse_quality=ImpulseQuality.MODERATE,
            correction_quality=CorrectionQuality.NORMAL,
            is_accelerating=False, is_decelerating=False,
            momentum_score=50.0,
        )
        d = ms.to_dict()
        assert d["impulse_quality"] == "moderate"
        assert d["correction_quality"] == "normal"
