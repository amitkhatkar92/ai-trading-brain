"""tests/unit/investment/market/liquidity/test_liquidity_confidence.py
Tests for LiquidityConfidenceCalculator, VolumeQualityScorer, LiquidityStatistics.
"""
from __future__ import annotations

import pytest

from iios.investment.market.liquidity.liquidity_confidence import LiquidityConfidenceCalculator
from iios.investment.market.liquidity.volume_quality import VolumeQualityScorer
from iios.investment.market.liquidity.liquidity_statistics import LiquidityStatistics, VolumeLiquidityStats
from iios.investment.market.liquidity.models import (
    LiquidityProfile, ParticipationSnapshot, OrderFlowSnapshot, ParticipationBias,
    LiquidityEventType, LiquidityEvent, VolumeLiquiditySnapshot,
    VolumeBar, VolumeProfile, EffortResultAnalysis, EffortResultType,
    VolumeLevel, VolumeTrend,
)
from iios.investment.market.liquidity.volume_statistics import VolumeStatistics
from tests.unit.investment.market.liquidity.conftest import (
    make_bar, make_volume_bar, make_bars,
)


def _make_liquidity_profile(
    availability: float = 0.7,
    stability: float = 0.75,
    depth: float = 0.6,
    concentration: float = 0.3,
    fragmentation: float = 0.7,
    quality: float = 65.0,
    confidence: float = 0.70,
) -> LiquidityProfile:
    return LiquidityProfile(
        availability=availability,
        stability=stability,
        depth=depth,
        concentration=concentration,
        fragmentation=fragmentation,
        quality=quality,
        liquidity_confidence=confidence,
    )


def _make_participation(
    buying: float = 0.60,
    selling: float = 0.40,
    institutional: float = 0.50,
    retail: float = 0.50,
    balance: float = 0.20,
    bias: ParticipationBias = ParticipationBias.BUY,
    confidence: float = 0.70,
    score: float = 65.0,
) -> ParticipationSnapshot:
    return ParticipationSnapshot(
        buying_participation=buying,
        selling_participation=selling,
        institutional_participation=institutional,
        retail_participation=retail,
        participation_balance=balance,
        participation_bias=bias,
        participation_confidence=confidence,
        participation_score=score,
    )


def _make_order_flow() -> OrderFlowSnapshot:
    return OrderFlowSnapshot(
        estimated_buy_volume=60_000.0,
        estimated_sell_volume=40_000.0,
        estimated_delta=20_000.0,
        cumulative_delta=20_000.0,
        buy_imbalance=0.60,
        sell_imbalance=0.40,
        net_imbalance=0.20,
        aggressive_buying=False,
        aggressive_selling=False,
        has_l2_data=False,
    )


class TestLiquidityConfidenceCalculator:
    def setup_method(self):
        self.calc = LiquidityConfidenceCalculator()
        self.lp = _make_liquidity_profile()
        self.part = _make_participation()
        self.of = _make_order_flow()

    def test_calculate_confidence_in_range(self):
        conf = self.calc.calculate_confidence(self.lp, self.part, 70.0, False, False)
        assert 0.05 <= conf <= 0.95

    def test_shock_event_reduces_confidence(self):
        normal = self.calc.calculate_confidence(self.lp, self.part, 70.0, False, False)
        shocked = self.calc.calculate_confidence(self.lp, self.part, 70.0, False, True)
        assert shocked < normal

    def test_active_events_reduce_confidence(self):
        no_events = self.calc.calculate_confidence(self.lp, self.part, 70.0, False, False)
        with_events = self.calc.calculate_confidence(self.lp, self.part, 70.0, True, False)
        assert with_events < no_events

    def test_low_volume_quality_reduces_confidence(self):
        high_q = self.calc.calculate_confidence(self.lp, self.part, 80.0, False, False)
        low_q = self.calc.calculate_confidence(self.lp, self.part, 20.0, False, False)
        assert low_q < high_q

    def test_high_participation_confidence_boost(self):
        normal_part = _make_participation(confidence=0.50)
        high_part = _make_participation(confidence=0.80)
        normal = self.calc.calculate_confidence(self.lp, normal_part, 60.0, False, False)
        boosted = self.calc.calculate_confidence(self.lp, high_part, 60.0, False, False)
        assert boosted >= normal

    def test_execution_readiness_in_range(self):
        er = self.calc.execution_readiness(self.lp, self.of, 70.0, False)
        assert 0.05 <= er <= 0.95

    def test_shock_reduces_execution_readiness(self):
        normal = self.calc.execution_readiness(self.lp, self.of, 70.0, False)
        shocked = self.calc.execution_readiness(self.lp, self.of, 70.0, True)
        assert shocked < normal

    def test_low_availability_reduces_readiness(self):
        low_avail = _make_liquidity_profile(availability=0.15)
        normal = self.calc.execution_readiness(self.lp, self.of, 60.0, False)
        low = self.calc.execution_readiness(low_avail, self.of, 60.0, False)
        assert low < normal

    def test_execution_readiness_not_nan(self):
        zero_lp = _make_liquidity_profile(availability=0.0, stability=0.0)
        er = self.calc.execution_readiness(zero_lp, self.of, 0.0, True)
        assert er == er  # not NaN
        assert 0.05 <= er <= 0.95


class TestVolumeQualityScorer:
    def setup_method(self):
        self.scorer = VolumeQualityScorer()

    def _populated_stats(self, n: int = 20, base_vol: float = 100_000.0) -> VolumeStatistics:
        s = VolumeStatistics(window=20)
        for i in range(n):
            s.update(base_vol * (1 + i * 0.01))
        return s

    def test_zero_volume_scores_low(self):
        vbar = make_volume_bar(index=0, volume=0.0, relative_volume=0.0)
        stats = self._populated_stats()
        score = self.scorer.score(vbar, stats)
        assert score == 0.0 or score < 10.0

    def test_normal_volume_with_history_scores_high(self):
        stats = self._populated_stats(20)
        vbar = make_volume_bar(index=20, volume=100_000.0, relative_volume=1.0, normalized_volume=0.5)
        score = self.scorer.score(vbar, stats)
        assert score > 50.0

    def test_extreme_volume_scores_lower(self):
        stats = self._populated_stats(20)
        # relative_volume > 5.0 = extreme outlier
        normal_vbar = make_volume_bar(relative_volume=1.0, normalized_volume=0.5)
        extreme_vbar = make_volume_bar(relative_volume=6.0, normalized_volume=1.0, volume=600_000.0)
        normal_score = self.scorer.score(normal_vbar, stats)
        extreme_score = self.scorer.score(extreme_vbar, stats)
        assert extreme_score < normal_score

    def test_insufficient_history_scores_lower(self):
        few_stats = VolumeStatistics(window=20)
        for _ in range(3):
            few_stats.update(100_000.0)
        full_stats = self._populated_stats(20)
        vbar = make_volume_bar(relative_volume=1.0, normalized_volume=0.5)
        few_score = self.scorer.score(vbar, few_stats)
        full_score = self.scorer.score(vbar, full_stats)
        assert few_score <= full_score

    def test_score_in_range(self):
        stats = self._populated_stats(20)
        vbar = make_volume_bar(relative_volume=1.2, normalized_volume=0.6)
        score = self.scorer.score(vbar, stats)
        assert 0.0 <= score <= 100.0

    def test_zero_range_bar_penalized(self):
        stats = self._populated_stats(20)
        zero_range = make_volume_bar(relative_volume=1.0, bar_range=0.0)
        normal = make_volume_bar(relative_volume=1.0, bar_range=3.0)
        z_score = self.scorer.score(zero_range, stats)
        n_score = self.scorer.score(normal, stats)
        assert z_score <= n_score


class TestLiquidityStatistics:
    def _make_snapshot_with_events(self, event_types=None) -> VolumeLiquiditySnapshot:
        """Minimal VolumeLiquiditySnapshot for recording."""
        vbar = make_volume_bar(relative_volume=1.0, volume=100_000.0)
        events = []
        if event_types:
            for et in event_types:
                events.append(LiquidityEvent(
                    event_type=et,
                    symbol="TEST",
                    timeframe="1d",
                    bar_index=0,
                    severity=0.5,
                ))
        part = _make_participation()
        lp = _make_liquidity_profile()
        of = _make_order_flow()
        er = EffortResultAnalysis(
            effort=0.5, result=0.5, ratio=1.0,
            effort_result_type=EffortResultType.CONFIRMED,
            is_confirmed=True, is_divergent=False,
            is_absorption=False, is_climax=False,
            absorption_strength=0.0, climax_score=0.0,
            initiative_buying=False, initiative_selling=False,
            responsive_buying=False, responsive_selling=False,
        )
        vp = VolumeProfile(
            period_bars=20, avg_volume=100_000.0, std_volume=5_000.0,
            median_volume=100_000.0, peak_volume=150_000.0, min_volume=80_000.0,
            recent_avg=100_000.0, volume_trend=VolumeTrend.STABLE,
            up_volume=50_000.0, down_volume=50_000.0, up_down_ratio=1.0,
        )
        from iios.investment.market.regime.models import RegimeType
        return VolumeLiquiditySnapshot(
            symbol="TEST", timeframe="1d", bar_index=0,
            volume_bar=vbar, volume_profile=vp,
            volume_level=VolumeLevel.AVERAGE,
            volume_trend=VolumeTrend.STABLE, volume_quality=65.0,
            participation=part, liquidity=lp,
            effort_result=er, order_flow=of,
            active_events=events, last_event=events[-1] if events else None,
            overall_confidence=0.70, execution_readiness=0.65,
            liquidity_score=65.0, regime=RegimeType.UNKNOWN, trend_stage="unknown",
        )

    def test_initial_stats(self):
        stats = LiquidityStatistics()
        s = stats.stats()
        assert s.total_bars == 0
        assert s.volume_spike_count == 0

    def test_record_increments_total_bars(self):
        stats = LiquidityStatistics()
        for _ in range(5):
            stats.record(self._make_snapshot_with_events())
        assert stats.stats().total_bars == 5

    def test_volume_spike_counted(self):
        stats = LiquidityStatistics()
        stats.record(self._make_snapshot_with_events([LiquidityEventType.VOLUME_SPIKE]))
        assert stats.stats().volume_spike_count == 1

    def test_climax_counted(self):
        stats = LiquidityStatistics()
        stats.record(self._make_snapshot_with_events([LiquidityEventType.BUYING_CLIMAX]))
        assert stats.stats().climax_count == 1

    def test_absorption_counted(self):
        stats = LiquidityStatistics()
        stats.record(self._make_snapshot_with_events([LiquidityEventType.ABSORPTION_DETECTED]))
        assert stats.stats().absorption_count == 1

    def test_shock_counted(self):
        stats = LiquidityStatistics()
        stats.record(self._make_snapshot_with_events([LiquidityEventType.SHOCK]))
        assert stats.stats().shock_count == 1

    def test_dry_up_counted(self):
        stats = LiquidityStatistics()
        stats.record(self._make_snapshot_with_events([LiquidityEventType.DRY_UP]))
        assert stats.stats().dry_up_count == 1

    def test_no_events_no_counts(self):
        stats = LiquidityStatistics()
        stats.record(self._make_snapshot_with_events([]))
        s = stats.stats()
        assert s.volume_spike_count == 0
        assert s.climax_count == 0

    def test_reset(self):
        stats = LiquidityStatistics()
        stats.record(self._make_snapshot_with_events([LiquidityEventType.VOLUME_SPIKE]))
        stats.reset()
        assert stats.stats().total_bars == 0
        assert stats.stats().volume_spike_count == 0

    def test_stats_returns_correct_type(self):
        stats = LiquidityStatistics()
        assert isinstance(stats.stats(), VolumeLiquidityStats)
