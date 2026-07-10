"""tests/unit/investment/market/structure/test_structure_quality.py"""
from __future__ import annotations

import pytest

from iios.investment.market.market_constants import MarketStrength, TrendDirection
from iios.investment.market.structure.confidence_calculator import ConfidenceCalculator
from iios.investment.market.structure.models import (
    StructurePhase,
    StructureQualityScore,
    SwingPoint,
    SwingSequence,
    SwingStrength,
    SwingType,
    TrendPhase,
    TrendState,
    Zone,
    ZoneStrength,
    ZoneType,
)
from iios.investment.market.structure.structure_quality import StructureQualityAssessor
from iios.investment.market.structure.structure_score import StructureScorer
from tests.unit.investment.market.structure.conftest import (
    make_uptrend_bars,
)


def _make_swing(idx: int, price: float, sw_type: SwingType) -> SwingPoint:
    return SwingPoint(
        index=idx, timestamp=float(idx),
        price=price, swing_type=sw_type,
        strength=SwingStrength.MAJOR,
        volume=150_000.0, bar_range=1.5,
        left_bars=5, right_bars=5,
    )


def _make_zone(level: float) -> Zone:
    return Zone(
        zone_id=f"R_{level:.2f}_0",
        zone_type=ZoneType.RESISTANCE,
        upper=level + 1, lower=level - 1,
        strength=ZoneStrength.MODERATE,
        touch_count=3, first_touch_index=0, last_touch_index=20,
        first_touch_price=level, origin_swing_count=3,
    )


def _make_trend(direction=TrendDirection.UP, leg_count=3) -> TrendState:
    return TrendState(
        direction=direction, strength=MarketStrength.STRONG,
        phase=TrendPhase.IMPULSE, leg_count=leg_count,
        current_leg_height=5.0, total_displacement=15.0,
        correction_depth=0.3, start_index=0, start_price=100.0,
        last_swing_index=40, last_swing_price=115.0, confirmed=True,
    )


class TestConfidenceCalculator:
    def setup_method(self):
        self.calc = ConfidenceCalculator()

    def test_swing_confidence_range(self):
        bars = make_uptrend_bars(n=30)
        sw = _make_swing(10, 105.0, SwingType.HIGH)
        score = self.calc.swing_confidence(sw, bars)
        assert 0.0 <= score <= 100.0

    def test_swing_confidence_high_volume_scores_high(self):
        bars = make_uptrend_bars(n=30)
        avg_vol = sum(b.volume for b in bars) / len(bars)
        sw_high = _make_swing(10, 105.0, SwingType.HIGH)
        sw_high.volume = avg_vol * 5  # 5× average volume
        # Use object directly since SwingPoint is not frozen
        score = self.calc.swing_confidence(sw_high, bars)
        assert score > 30.0

    def test_trend_confidence_more_legs_higher(self):
        t_few = _make_trend(leg_count=1)
        t_many = _make_trend(leg_count=5)
        s_few = self.calc.trend_confidence(t_few)
        s_many = self.calc.trend_confidence(t_many)
        assert s_many >= s_few

    def test_trend_confidence_confirmed_bonus(self):
        t_unconfirmed = _make_trend(leg_count=2)
        t_unconfirmed.confirmed = False
        t_confirmed = _make_trend(leg_count=2)
        t_confirmed.confirmed = True
        s_u = self.calc.trend_confidence(t_unconfirmed)
        s_c = self.calc.trend_confidence(t_confirmed)
        assert s_c > s_u

    def test_zone_confidence_range(self):
        zone = _make_zone(100.0)
        score = self.calc.zone_confidence(zone, 95.0)
        assert 0.0 <= score <= 100.0

    def test_data_quality_clean_bars(self):
        bars = make_uptrend_bars(n=30)
        score = self.calc.data_quality(bars)
        assert score >= 80.0  # Clean synthetic bars should score well

    def test_data_quality_zero_volume_penalty(self):
        bars = make_uptrend_bars(n=10)
        import dataclasses
        bad_bars = [dataclasses.replace(b, volume=0.0) for b in bars]
        score = self.calc.data_quality(bad_bars)
        assert score < 80.0


class TestStructureScorer:
    def test_overall_in_range(self):
        scorer = StructureScorer()
        result = scorer.score(
            swing_conf=80.0, trend_conf=70.0, zone_conf=60.0,
            breakout_conf=50.0, data_quality=90.0,
            bar_count=50, valid_swing_count=8,
        )
        assert 0.0 <= result.overall <= 100.0

    def test_grade_a_for_high_score(self):
        scorer = StructureScorer()
        result = scorer.score(
            swing_conf=90.0, trend_conf=90.0, zone_conf=90.0,
            breakout_conf=90.0, data_quality=90.0,
            bar_count=100, valid_swing_count=20,
        )
        assert result.grade == "A"

    def test_grade_f_for_low_score(self):
        scorer = StructureScorer()
        result = scorer.score(
            swing_conf=10.0, trend_conf=10.0, zone_conf=10.0,
            breakout_conf=10.0, data_quality=10.0,
            bar_count=5, valid_swing_count=0,
        )
        assert result.grade == "F"

    def test_weights_sum_to_one(self):
        from iios.investment.market.structure.structure_score import (
            _W_SWING, _W_TREND, _W_ZONE, _W_BREAKOUT, _W_DATA
        )
        total = _W_SWING + _W_TREND + _W_ZONE + _W_BREAKOUT + _W_DATA
        assert abs(total - 1.0) < 1e-9


class TestStructureQualityAssessor:
    def test_assess_returns_score(self):
        bars = make_uptrend_bars(n=50)
        trend = _make_trend()
        seq = SwingSequence(
            highs=[_make_swing(40, 115.0, SwingType.HIGH),
                   _make_swing(25, 108.0, SwingType.HIGH)],
            lows=[_make_swing(35, 110.0, SwingType.LOW),
                  _make_swing(20, 103.0, SwingType.LOW)],
        )
        zones = [_make_zone(120.0), _make_zone(95.0)]
        assessor = StructureQualityAssessor(ConfidenceCalculator(), StructureScorer())
        score = assessor.assess(bars, trend, seq, zones, None)
        assert isinstance(score, StructureQualityScore)
        assert 0.0 <= score.overall <= 100.0
        assert score.bar_count == 50
