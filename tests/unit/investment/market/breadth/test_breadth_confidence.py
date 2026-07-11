"""test_breadth_confidence.py — tests for BreadthHistory and BreadthStatistics."""
from __future__ import annotations

import time

import pytest

from iios.investment.market.breadth.models import (
    BreadthData,
    BreadthTrend,
)
from iios.investment.market.breadth.breadth_statistics import BreadthStatistics
from iios.investment.market.breadth.breadth_history import BreadthHistory

from tests.unit.investment.market.breadth.conftest import make_bull_universe


# ── BreadthStatistics ─────────────────────────────────────────────────────

def _bd(pct: float, stability: float = 0.7) -> BreadthData:
    return BreadthData(
        advancing=int(100 * pct), declining=int(100 * (1 - pct)),
        unchanged=0, total=100, breadth_pct=pct,
        ad_ratio=pct / max(1 - pct, 0.01),
        ad_line=0.0, ad_momentum=0.0,
        breadth_trend=BreadthTrend.RISING if pct > 0.5 else BreadthTrend.FALLING,
        breadth_stability=stability, metric_values={},
    )


class TestBreadthStatistics:
    def test_trend_stable_on_constant_input(self):
        stats = BreadthStatistics(window=20)
        for i in range(25):
            stats.update(0.60, 1.5, 0.60, 65.0)
        from iios.investment.market.breadth.models import BreadthTrend
        trend = stats.breadth_trend()
        assert trend in (BreadthTrend.STABLE, BreadthTrend.RISING)

    def test_trend_rising_on_improving_breadth(self):
        stats = BreadthStatistics(window=20)
        for i in range(25):
            stats.update(0.40 + i * 0.02, 1.0 + i * 0.05, 0.40 + i * 0.02, 50.0)
        from iios.investment.market.breadth.models import BreadthTrend
        trend = stats.breadth_trend()
        assert trend in (BreadthTrend.RISING, BreadthTrend.SURGING)

    def test_trend_falling_on_deteriorating_breadth(self):
        stats = BreadthStatistics(window=20)
        for i in range(25):
            stats.update(0.80 - i * 0.02, 4.0 - i * 0.05, 0.80 - i * 0.02, 80.0)
        from iios.investment.market.breadth.models import BreadthTrend
        trend = stats.breadth_trend()
        assert trend in (BreadthTrend.FALLING, BreadthTrend.COLLAPSING)

    def test_stability_after_many_stable_bars(self):
        stats = BreadthStatistics(window=20)
        for _ in range(30):
            stats.update(0.65, 1.8, 0.65, 70.0)
        s = stats.breadth_stability()
        assert s > 0.5   # stable input → high stability

    def test_momentum_positive_when_improving(self):
        stats = BreadthStatistics(window=10)
        for i in range(15):
            stats.update(0.40 + i * 0.03, 1.0, 0.40 + i * 0.03, 50.0)
        mom = stats.breadth_momentum()
        assert mom > 0

    def test_avg_breadth_pct(self):
        stats = BreadthStatistics(window=10)
        for _ in range(10):
            stats.update(0.60, 1.5, 0.60, 65.0)
        avg = stats.avg_breadth_pct()
        assert avg == pytest.approx(0.60, abs=0.05)

    def test_avg_above_ma20(self):
        stats = BreadthStatistics(window=10)
        for _ in range(10):
            stats.update(0.60, 1.5, 0.65, 65.0)
        avg = stats.avg_above_ma20()
        assert avg == pytest.approx(0.65, abs=0.05)

    def test_empty_returns_defaults(self):
        stats = BreadthStatistics(window=20)
        assert stats.breadth_momentum() == 0.0
        assert stats.breadth_stability() == 0.5


# ── BreadthHistory ────────────────────────────────────────────────────────

class TestBreadthHistory:
    def _snap(self, bar_index: int):
        from iios.investment.market.breadth.models import (
            BreadthConfidenceScore, BreadthIntelligenceSnapshot,
            BreadthRegimeSnapshot, BreadthRegimeType, HealthTrend,
            MarketHealthSnapshot, ParticipationSnapshot,
        )
        import uuid
        bd = _bd(0.65)
        ps = ParticipationSnapshot(
            large_cap_pct=0.65, mid_cap_pct=0.60, small_cap_pct=0.55,
            sector_participation={}, above_ma20_pct=0.60, above_ma50_pct=0.55,
            new_highs=10, new_lows=5, nh_nl_ratio=2.0,
            market_participation_score=65.0, participation_breadth=0.70,
        )
        # Note: metric_values is a Dict[str, BreadthMetricValue] in BreadthData
        mh = MarketHealthSnapshot(
            health_score=65.0, internal_strength=0.65, leadership_breadth=0.60,
            lagging_breadth=0.40, participation_quality=0.65, internal_momentum=0.0,
            health_trend=HealthTrend.STABLE, leading_sectors=[], lagging_sectors=[],
        )
        rs = BreadthRegimeSnapshot(
            regime=BreadthRegimeType.HEALTHY_PARTICIPATION, confidence=0.80,
            duration_bars=3, previous_regime=None, transition_probability=0.10,
            regime_score=60.0,
        )
        conf = BreadthConfidenceScore(
            breadth_confidence=0.80, participation_confidence=0.75,
            leadership_confidence=0.70, internal_strength_score=65.0, overall_score=75.0,
        )
        return BreadthIntelligenceSnapshot(
            snapshot_id=str(uuid.uuid4()), universe_id="TEST", bar_index=bar_index,
            timestamp=time.time(), breadth_data=bd, participation=ps,
            market_health=mh, regime_snapshot=rs, active_divergences=[],
            confidence=conf, active_events=[], last_event=None,
        )

    def test_append_and_recent(self):
        h = BreadthHistory(maxlen=10)
        for i in range(5):
            h.append(self._snap(i))
        assert len(h.recent(10)) == 5

    def test_maxlen_cap(self):
        h = BreadthHistory(maxlen=3)
        for i in range(10):
            h.append(self._snap(i))
        assert len(h.recent(100)) == 3

    def test_latest(self):
        h = BreadthHistory(maxlen=10)
        assert h.latest() is None
        snap = self._snap(0)
        h.append(snap)
        assert h.latest().bar_index == 0

    def test_len(self):
        h = BreadthHistory(maxlen=10)
        for i in range(4):
            h.append(self._snap(i))
        assert len(h) == 4
