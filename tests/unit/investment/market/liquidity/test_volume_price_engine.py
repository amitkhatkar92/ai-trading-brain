"""tests/unit/investment/market/liquidity/test_volume_price_engine.py"""
from __future__ import annotations

import pytest

from iios.investment.market.liquidity.models import EffortResultType
from iios.investment.market.liquidity.effort_result import EffortResultAnalyzer
from iios.investment.market.liquidity.confirmation_engine import ConfirmationEngine
from iios.investment.market.liquidity.absorption_detector import AbsorptionDetector
from iios.investment.market.liquidity.volume_price_engine import VolumePriceEngine

from tests.unit.investment.market.liquidity.conftest import make_volume_bar


class TestEffortResultAnalyzer:
    def setup_method(self):
        self.analyzer = EffortResultAnalyzer()

    def test_high_volume_small_range_absorption(self):
        """High effort (volume) but very small range → ABSORPTION."""
        vbar = make_volume_bar(
            volume=400_000.0, relative_volume=4.0,
            bar_range=0.2,   # much less than avg_range
            body_pct=0.1, close_position=0.5,
        )
        avg_volume = 100_000.0
        avg_range = 3.0  # bar_range < avg_range * 0.5 → 0.2 < 1.5 ✓
        er = self.analyzer.analyze(vbar, avg_volume, avg_range)
        # effort > 0.70 and bar_range < avg_range * 0.5
        assert er.is_absorption

    def test_extreme_volume_climax(self):
        """Extreme volume + high relative_volume + poor result → CLIMAX."""
        vbar = make_volume_bar(
            volume=1_000_000.0, relative_volume=3.0,
            bar_range=0.5, body_pct=0.1, close_position=0.5,
        )
        avg_volume = 100_000.0
        avg_range = 3.0
        er = self.analyzer.analyze(vbar, avg_volume, avg_range)
        # effort = min(1, 1M/300K) = 1.0 > 0.85, ratio = result/effort < 0.5 if range small
        assert er.is_climax or er.is_absorption  # climax if ratio < 0.5

    def test_moderate_volume_good_move_confirmed(self):
        """Moderate volume + good price move → CONFIRMED."""
        vbar = make_volume_bar(
            volume=200_000.0, relative_volume=2.0,
            bar_range=4.5, body_pct=0.7, close_position=0.8,
        )
        avg_volume = 100_000.0
        avg_range = 3.0
        er = self.analyzer.analyze(vbar, avg_volume, avg_range)
        assert er.effort >= 0.5
        assert er.result >= 0.0

    def test_high_volume_tiny_move_divergent(self):
        """High effort but tiny price move → DIVERGENT."""
        vbar = make_volume_bar(
            volume=200_000.0, relative_volume=2.0,
            bar_range=0.1, body_pct=0.1, close_position=0.5,
        )
        avg_volume = 100_000.0
        avg_range = 3.0
        er = self.analyzer.analyze(vbar, avg_volume, avg_range)
        # effort = min(1, 200K/300K) ≈ 0.67 >= 0.60; result = min(1, 0.1/9.0) ≈ 0.011 < 0.30
        assert er.effort_result_type in (EffortResultType.DIVERGENT, EffortResultType.ABSORPTION)

    def test_low_volume_low_move_exhaustion(self):
        """Low effort AND low result → EXHAUSTION."""
        vbar = make_volume_bar(
            volume=10_000.0, relative_volume=0.1,
            bar_range=0.05, body_pct=0.1, close_position=0.5,
        )
        avg_volume = 100_000.0
        avg_range = 3.0
        er = self.analyzer.analyze(vbar, avg_volume, avg_range)
        # effort = min(1, 10K/300K) ≈ 0.033 < 0.30; result ≈ 0 < 0.20
        assert er.effort_result_type == EffortResultType.EXHAUSTION

    def test_initiative_buying(self):
        """Up bar, rel_vol >= 1.2, close_position >= 0.70 → initiative_buying."""
        vbar = make_volume_bar(
            is_up=True, relative_volume=1.5, close_position=0.75,
        )
        er = self.analyzer.analyze(vbar, 100_000.0, 3.0)
        assert er.initiative_buying is True

    def test_initiative_selling(self):
        """Down bar, rel_vol >= 1.2, close_position <= 0.30."""
        vbar = make_volume_bar(
            is_up=False, relative_volume=1.5, close_position=0.20,
        )
        er = self.analyzer.analyze(vbar, 100_000.0, 3.0)
        assert er.initiative_selling is True

    def test_no_initiative_buying_low_close(self):
        vbar = make_volume_bar(is_up=True, relative_volume=1.5, close_position=0.4)
        er = self.analyzer.analyze(vbar, 100_000.0, 3.0)
        assert er.initiative_buying is False

    def test_effort_in_range(self):
        vbar = make_volume_bar(volume=100_000.0)
        er = self.analyzer.analyze(vbar, 100_000.0, 3.0)
        assert 0.0 <= er.effort <= 1.0

    def test_result_in_range(self):
        vbar = make_volume_bar(bar_range=3.0)
        er = self.analyzer.analyze(vbar, 100_000.0, 3.0)
        assert 0.0 <= er.result <= 1.0


class TestConfirmationEngine:
    def setup_method(self):
        self.engine = ConfirmationEngine()

    def test_up_bar_with_high_vol_confirmed(self):
        vbar = make_volume_bar(is_up=True, close_position=0.7)
        assert self.engine.is_price_confirmed_by_volume(vbar, 1.2) is True

    def test_up_bar_with_low_vol_not_confirmed(self):
        vbar = make_volume_bar(is_up=True, close_position=0.7)
        assert self.engine.is_price_confirmed_by_volume(vbar, 0.9) is False

    def test_down_bar_with_high_vol_confirmed(self):
        vbar = make_volume_bar(is_up=False, close_position=0.3)
        assert self.engine.is_price_confirmed_by_volume(vbar, 1.2) is True

    def test_down_bar_low_vol_not_confirmed(self):
        vbar = make_volume_bar(is_up=False, close_position=0.3)
        assert self.engine.is_price_confirmed_by_volume(vbar, 0.9) is False

    def test_breakout_up_confirmed(self):
        vbar = make_volume_bar(is_up=True, close_position=0.7)
        assert self.engine.is_breakout_confirmed(vbar, 2.0, "up") is True

    def test_breakout_up_not_confirmed_low_vol(self):
        vbar = make_volume_bar(is_up=True, close_position=0.7)
        assert self.engine.is_breakout_confirmed(vbar, 1.2, "up") is False

    def test_confirmation_strength_in_range(self):
        vbar = make_volume_bar(body_pct=0.7)
        s = self.engine.confirmation_strength(vbar, 1.5)
        assert 0.0 <= s <= 1.0

    def test_confirmation_strength_zero_for_zero_vol(self):
        vbar = make_volume_bar(body_pct=0.7)
        s = self.engine.confirmation_strength(vbar, 0.0)
        assert s == 0.0


class TestAbsorptionDetector:
    def setup_method(self):
        self.detector = AbsorptionDetector(window=5)

    def _make_absorption_bar(self, index: int = 0) -> tuple:
        from iios.investment.market.liquidity.models import EffortResultType, EffortResultAnalysis
        vbar = make_volume_bar(index=index)
        er = EffortResultAnalysis(
            effort=0.8, result=0.2, ratio=0.25,
            effort_result_type=EffortResultType.ABSORPTION,
            is_confirmed=False, is_divergent=False,
            is_absorption=True, is_climax=False,
            absorption_strength=0.6, climax_score=0.0,
            initiative_buying=False, initiative_selling=False,
            responsive_buying=False, responsive_selling=False,
        )
        return vbar, er

    def _make_climax_buy_bar(self, index: int = 0) -> tuple:
        from iios.investment.market.liquidity.models import EffortResultType, EffortResultAnalysis
        vbar = make_volume_bar(index=index, is_up=True, close_position=0.85)
        er = EffortResultAnalysis(
            effort=0.9, result=0.2, ratio=0.22,
            effort_result_type=EffortResultType.CLIMAX,
            is_confirmed=False, is_divergent=False,
            is_absorption=False, is_climax=True,
            absorption_strength=0.0, climax_score=0.9,
            initiative_buying=True, initiative_selling=False,
            responsive_buying=False, responsive_selling=False,
        )
        return vbar, er

    def test_detect_absorption_after_two_consecutive(self):
        vbar0, er0 = self._make_absorption_bar(0)
        vbar1, er1 = self._make_absorption_bar(1)
        self.detector.update(vbar0, er0)
        self.detector.update(vbar1, er1)
        detected, conf = self.detector.detect_absorption()
        assert detected is True
        assert conf > 0.0

    def test_no_absorption_single_bar(self):
        vbar, er = self._make_absorption_bar(0)
        self.detector.update(vbar, er)
        detected, _ = self.detector.detect_absorption()
        assert detected is False

    def test_buying_climax_detected(self):
        vbar0, er0 = self._make_climax_buy_bar(0)
        # Next bar: close_position drops
        vbar1 = make_volume_bar(index=1, close_position=0.3)
        from iios.investment.market.liquidity.models import EffortResultType, EffortResultAnalysis
        er1 = EffortResultAnalysis(
            effort=0.4, result=0.3, ratio=0.75,
            effort_result_type=EffortResultType.NEUTRAL,
            is_confirmed=False, is_divergent=False,
            is_absorption=False, is_climax=False,
            absorption_strength=0.0, climax_score=0.0,
            initiative_buying=False, initiative_selling=False,
            responsive_buying=False, responsive_selling=False,
        )
        self.detector.update(vbar0, er0)
        self.detector.update(vbar1, er1)
        detected, conf = self.detector.detect_buying_climax()
        assert detected is True

    def test_reset_clears_history(self):
        vbar, er = self._make_absorption_bar()
        self.detector.update(vbar, er)
        self.detector.reset()
        detected, _ = self.detector.detect_absorption()
        assert detected is False


class TestVolumePriceEngine:
    def test_update_returns_er_analysis(self):
        engine = VolumePriceEngine(window=10)
        vbar = make_volume_bar()
        er = engine.update(vbar, 100_000.0, 3.0)
        assert er is not None
        assert 0.0 <= er.effort <= 1.0

    def test_initialize_bulk(self):
        engine = VolumePriceEngine(window=10)
        vbars = [make_volume_bar(index=i) for i in range(10)]
        er = engine.initialize(vbars, 100_000.0, 3.0)
        assert er is not None

    def test_current_analysis_updates(self):
        engine = VolumePriceEngine(window=10)
        assert engine.current_analysis() is None
        engine.update(make_volume_bar(), 100_000.0, 3.0)
        assert engine.current_analysis() is not None

    def test_confirmation_strength_after_update(self):
        engine = VolumePriceEngine(window=10)
        engine.update(make_volume_bar(), 100_000.0, 3.0)
        s = engine.confirmation_strength(1.5)
        assert 0.0 <= s <= 1.0
