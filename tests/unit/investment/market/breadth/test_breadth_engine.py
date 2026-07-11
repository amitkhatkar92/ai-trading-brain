"""test_breadth_engine.py — tests for the BreadthEngine and metrics."""
from __future__ import annotations

import time

import pytest

from iios.investment.market.breadth.models import SecurityObservation, UniverseSnapshot
from iios.investment.market.breadth.advance_decline_metric import AdvanceDeclineMetric
from iios.investment.market.breadth.participation_rate_metric import ParticipationRateMetric
from iios.investment.market.breadth.new_high_low_metric import NewHighLowMetric
from iios.investment.market.breadth.above_ma_metric import AboveMa20Metric, AboveMa50Metric
from iios.investment.market.breadth.metric_registry import MetricRegistry
from iios.investment.market.breadth.breadth_engine import BreadthEngine

from tests.unit.investment.market.breadth.conftest import (
    make_universe,
    make_bull_universe,
    make_bear_universe,
)


# ── Metrics ───────────────────────────────────────────────────────────────

class TestAdvanceDeclineMetric:
    def test_bullish_ratio(self):
        obs = [SecurityObservation(f"A{i}", 0.5) for i in range(70)]
        obs += [SecurityObservation(f"D{i}", -0.5) for i in range(30)]
        m = AdvanceDeclineMetric()
        result = m.compute(obs)
        assert result is not None
        assert result.value > 1.0
        assert result.signal == "bullish"

    def test_bearish_ratio(self):
        obs = [SecurityObservation(f"A{i}", 0.5) for i in range(20)]
        obs += [SecurityObservation(f"D{i}", -0.5) for i in range(80)]
        m = AdvanceDeclineMetric()
        result = m.compute(obs)
        assert result is not None
        assert result.value < 1.0
        assert result.signal == "bearish"

    def test_neutral_equal(self):
        obs = [SecurityObservation(f"A{i}", 0.5) for i in range(50)]
        obs += [SecurityObservation(f"D{i}", -0.5) for i in range(50)]
        m = AdvanceDeclineMetric()
        result = m.compute(obs)
        assert result is not None
        assert result.signal == "neutral"

    def test_empty_returns_none(self):
        assert AdvanceDeclineMetric().compute([]) is None

    def test_name(self):
        assert AdvanceDeclineMetric().name == "advance_decline"


class TestParticipationRateMetric:
    def test_bull_market(self):
        obs = [SecurityObservation(f"A{i}", 0.5) for i in range(60)]
        obs += [SecurityObservation(f"D{i}", -0.5) for i in range(40)]
        m = ParticipationRateMetric()
        result = m.compute(obs)
        assert result is not None
        assert result.value == pytest.approx(0.60)
        assert result.signal == "bullish"

    def test_name(self):
        assert ParticipationRateMetric().name == "participation_rate"


class TestNewHighLowMetric:
    def test_with_highs(self):
        obs = [
            SecurityObservation(f"A{i}", 0.5, is_new_52w_high=True) for i in range(20)
        ]
        obs += [SecurityObservation(f"D{i}", -0.5) for i in range(80)]
        m = NewHighLowMetric()
        result = m.compute(obs)
        assert result is not None
        assert result.value >= 1.0   # highs > lows

    def test_name(self):
        assert NewHighLowMetric().name == "new_high_low"


class TestAboveMaMetrics:
    def test_above_ma20(self):
        obs = [
            SecurityObservation(f"A{i}", 0.5, is_above_ma20=True) for i in range(65)
        ]
        obs += [SecurityObservation(f"D{i}", -0.5) for i in range(35)]
        m = AboveMa20Metric()
        result = m.compute(obs)
        assert result is not None
        assert result.value == pytest.approx(0.65)
        assert result.signal == "bullish"

    def test_above_ma50(self):
        obs = [
            SecurityObservation(f"A{i}", 0.5, is_above_ma50=True) for i in range(35)
        ]
        obs += [SecurityObservation(f"D{i}", -0.5) for i in range(65)]
        m = AboveMa50Metric()
        result = m.compute(obs)
        assert result is not None
        assert result.value == pytest.approx(0.35)
        assert result.signal == "bearish"


# ── MetricRegistry ────────────────────────────────────────────────────────

class TestMetricRegistry:
    def test_register_and_get(self):
        reg = MetricRegistry()
        m = AdvanceDeclineMetric()
        reg.register(m)
        assert reg.get("advance_decline") is m

    def test_unregister(self):
        reg = MetricRegistry()
        reg.register(AdvanceDeclineMetric())
        reg.unregister("advance_decline")
        assert reg.get("advance_decline") is None

    def test_all_returns_all(self):
        reg = MetricRegistry()
        reg.register(AdvanceDeclineMetric())
        reg.register(ParticipationRateMetric())
        assert len(reg.all()) == 2

    def test_names(self):
        reg = MetricRegistry()
        reg.register(AdvanceDeclineMetric())
        assert "advance_decline" in reg.names()

    def test_duplicate_registration_replaces(self):
        reg = MetricRegistry()
        m1 = AdvanceDeclineMetric()
        m2 = AdvanceDeclineMetric()
        reg.register(m1)
        reg.register(m2)  # silent replacement
        assert len(reg.all()) == 1
        assert reg.get("advance_decline") is m2


# ── BreadthEngine ─────────────────────────────────────────────────────────

class TestBreadthEngine:
    def _make_engine(self):
        reg = MetricRegistry()
        reg.register(AdvanceDeclineMetric())
        reg.register(ParticipationRateMetric())
        return BreadthEngine(registry=reg)

    def test_bull_breadth_pct(self):
        engine = self._make_engine()
        u = make_bull_universe()
        bd = engine.update(u, above_ma20_pct=0.65, health_score=0.65)
        assert bd.breadth_pct >= 0.60

    def test_bear_breadth_pct(self):
        engine = self._make_engine()
        u = make_bear_universe()
        bd = engine.update(u, above_ma20_pct=0.25, health_score=0.25)
        assert bd.breadth_pct <= 0.30

    def test_ad_ratio_bull(self):
        engine = self._make_engine()
        u = make_bull_universe()
        bd = engine.update(u, above_ma20_pct=0.65, health_score=0.65)
        assert bd.ad_ratio > 1.0

    def test_ad_line_cumulative(self):
        engine = self._make_engine()
        for i in range(5):
            u = make_bull_universe(bar_index=i)
            bd = engine.update(u, above_ma20_pct=0.65, health_score=0.65)
        # A/D line should be positive after 5 bull bars
        assert bd.ad_line > 0

    def test_metric_values_populated(self):
        engine = self._make_engine()
        u = make_bull_universe()
        bd = engine.update(u, above_ma20_pct=0.65, health_score=0.65)
        assert len(bd.metric_values) >= 2
        # metric_values is a dict keyed by metric name
        assert all(isinstance(k, str) for k in bd.metric_values.keys())

    def test_empty_universe(self):
        engine = self._make_engine()
        u = UniverseSnapshot("EMPTY", 0, time.time(), [])
        bd = engine.update(u, above_ma20_pct=0.0, health_score=0.0)
        assert bd.total == 0
        assert bd.breadth_pct == 0.0

    def test_breadth_trend_after_consistent_bull(self):
        engine = self._make_engine()
        bd = None
        for i in range(25):
            bd = engine.update(make_bull_universe(bar_index=i),
                               above_ma20_pct=0.65, health_score=0.65)
        from iios.investment.market.breadth.models import BreadthTrend
        assert bd.breadth_trend in (BreadthTrend.RISING, BreadthTrend.STABLE, BreadthTrend.SURGING)
