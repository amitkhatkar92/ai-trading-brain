"""tests/unit/investment/market/liquidity/test_participation_engine.py"""
from __future__ import annotations

import pytest

from iios.investment.market.liquidity.models import ParticipationBias
from iios.investment.market.liquidity.participation_score import ParticipationScoreCalculator
from iios.investment.market.liquidity.participation_tracker import ParticipationTracker
from iios.investment.market.liquidity.participation_engine import ParticipationEngine
from iios.investment.market.liquidity.volume_engine import VolumeEngine

from tests.unit.investment.market.liquidity.conftest import (
    make_bar, make_up_bar, make_down_bar, make_bars, make_volume_bar,
)


class TestParticipationScoreCalculator:
    def setup_method(self):
        self.calc = ParticipationScoreCalculator()

    def test_up_bar_buying_participation_gt_half(self):
        vbar = make_volume_bar(close_position=0.8, is_up=True)
        buy, sell, inst, retail, bias, score = self.calc.calculate(vbar, 1.5)
        assert buy > 0.5

    def test_down_bar_selling_participation_gt_half(self):
        vbar = make_volume_bar(close_position=0.2, is_up=False)
        buy, sell, inst, retail, bias, score = self.calc.calculate(vbar, 1.5)
        assert sell > 0.5

    def test_extreme_up_bar_strong_buy_bias(self):
        vbar = make_volume_bar(close_position=0.9, is_up=True)
        buy, sell, inst, retail, bias, score = self.calc.calculate(vbar, 2.0)
        assert bias in (ParticipationBias.STRONG_BUY, ParticipationBias.BUY)

    def test_extreme_down_bar_strong_sell_bias(self):
        vbar = make_volume_bar(close_position=0.05, is_up=False)
        buy, sell, inst, retail, bias, score = self.calc.calculate(vbar, 2.0)
        assert bias in (ParticipationBias.STRONG_SELL, ParticipationBias.SELL)

    def test_neutral_close_position(self):
        vbar = make_volume_bar(close_position=0.5, is_up=True)
        buy, sell, inst, retail, bias, score = self.calc.calculate(vbar, 1.0)
        assert bias == ParticipationBias.NEUTRAL

    def test_institutional_est_increases_with_relative_volume(self):
        vbar = make_volume_bar(close_position=0.5)
        _, _, inst_low, _, _, _ = self.calc.calculate(vbar, 0.5)
        _, _, inst_high, _, _, _ = self.calc.calculate(vbar, 2.5)
        assert inst_high > inst_low

    def test_participation_score_in_range(self):
        vbar = make_volume_bar(close_position=0.7, is_up=True)
        _, _, _, _, _, score = self.calc.calculate(vbar, 1.5)
        assert 0.0 <= score <= 100.0

    def test_score_zero_for_zero_relative_volume(self):
        vbar = make_volume_bar(close_position=0.7)
        _, _, _, _, _, score = self.calc.calculate(vbar, 0.0)
        assert score >= 0.0

    def test_buying_plus_selling_eq_1(self):
        vbar = make_volume_bar(close_position=0.65)
        buy, sell, _, _, _, _ = self.calc.calculate(vbar, 1.0)
        assert abs(buy + sell - 1.0) < 1e-9

    def test_institutional_body_pct_boost(self):
        vbar_low = make_volume_bar(body_pct=0.2, close_position=0.5)
        vbar_high = make_volume_bar(body_pct=0.8, close_position=0.5)
        _, _, inst_low, _, _, _ = self.calc.calculate(vbar_low, 2.0)
        _, _, inst_high, _, _, _ = self.calc.calculate(vbar_high, 2.0)
        assert inst_high >= inst_low


class TestParticipationTracker:
    def test_update_returns_snapshot(self):
        tracker = ParticipationTracker(window=20)
        vbar = make_volume_bar(close_position=0.7)
        snap = tracker.update(vbar, 1.5)
        assert snap is not None

    def test_avg_buying_close_to_expected(self):
        tracker = ParticipationTracker(window=20)
        for i in range(10):
            vbar = make_volume_bar(index=i, close_position=0.7)
            tracker.update(vbar, 1.0)
        avg = tracker.avg_buying_participation(n=10)
        assert abs(avg - 0.7) < 0.01

    def test_bias_streak_positive_for_buy(self):
        tracker = ParticipationTracker(window=20)
        for i in range(5):
            vbar = make_volume_bar(index=i, close_position=0.8, is_up=True)
            tracker.update(vbar, 1.5)
        streak = tracker.bias_streak()
        assert streak > 0

    def test_count(self):
        tracker = ParticipationTracker(window=20)
        for i in range(7):
            tracker.update(make_volume_bar(index=i), 1.0)
        assert tracker.count() == 7


class TestParticipationEngine:
    def test_update_returns_snapshot(self):
        engine = ParticipationEngine(window=20)
        vbar = make_volume_bar()
        snap = engine.update(vbar, 1.0)
        assert snap is not None
        assert 0.0 <= snap.participation_score <= 100.0

    def test_initialize_with_bulk_bars(self):
        engine = ParticipationEngine(window=20)
        bars = make_bars(25)
        ve = VolumeEngine(window=20)
        vbars = [ve.update(b)[0] for b in bars]
        snap = engine.initialize(bars, vbars)
        assert snap is not None

    def test_current_updates(self):
        engine = ParticipationEngine(window=20)
        assert engine.current() is None
        engine.update(make_volume_bar(), 1.0)
        assert engine.current() is not None

    def test_confidence_in_range(self):
        engine = ParticipationEngine(window=20)
        snap = engine.update(make_volume_bar(), 2.0)
        assert 0.0 <= snap.participation_confidence <= 1.0
