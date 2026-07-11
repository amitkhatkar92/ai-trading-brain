"""test_breadth_transition.py — tests for BreadthQualityScorer and BreadthConfidenceCalculator."""
from __future__ import annotations

import time

import pytest

from iios.investment.market.breadth.models import (
    BreadthData,
    BreadthRegimeSnapshot,
    BreadthRegimeType,
    BreadthTrend,
    HealthTrend,
    MarketHealthSnapshot,
    ParticipationSnapshot,
    SecurityObservation,
    UniverseSnapshot,
)
from iios.investment.market.breadth.breadth_quality import BreadthQualityScorer
from iios.investment.market.breadth.breadth_confidence import BreadthConfidenceCalculator
from iios.investment.market.breadth.breadth_regime import build_regime_snapshot

from tests.unit.investment.market.breadth.conftest import (
    make_bull_universe,
    make_universe,
    make_multi_sector_universe,
)


# ── BreadthQualityScorer ──────────────────────────────────────────────────

class TestBreadthQualityScorer:
    def test_empty_universe_zero(self):
        scorer = BreadthQualityScorer()
        u = UniverseSnapshot("EMPTY", 0, time.time(), [])
        assert scorer.score(u) == 0.0

    def test_large_well_covered_universe(self):
        scorer = BreadthQualityScorer()
        sectors = ["Tech", "Finance", "Healthcare", "Energy", "Consumer"]
        u = make_multi_sector_universe(sectors, [0.70] * 5, n_per_sector=20)
        score = scorer.score(u)
        assert score >= 0.70

    def test_small_unknown_universe_penalised(self):
        scorer = BreadthQualityScorer()
        obs = [SecurityObservation(f"X{i}", 0.5) for i in range(5)]  # 5 only, sector unknown
        u = UniverseSnapshot("SMALL", 0, time.time(), obs)
        score = scorer.score(u)
        assert score < 0.50

    def test_score_range(self):
        scorer = BreadthQualityScorer()
        for n in [1, 10, 30, 60, 100]:
            u = make_universe(int(n * 0.6), int(n * 0.4))
            s = scorer.score(u)
            assert 0.0 <= s <= 1.0


# ── BreadthConfidenceCalculator ───────────────────────────────────────────

def _make_test_objects(breadth_pct: float = 0.70, above_ma20: float = 0.65):
    bd = BreadthData(
        advancing=int(100 * breadth_pct), declining=int(100 * (1 - breadth_pct)),
        unchanged=0, total=100, breadth_pct=breadth_pct,
        ad_ratio=breadth_pct / max(1 - breadth_pct, 0.01),
        ad_line=0.0, ad_momentum=0.0,
        breadth_trend=BreadthTrend.RISING, breadth_stability=0.75,
        metric_values={},
    )
    ps = ParticipationSnapshot(
        large_cap_pct=0.70, mid_cap_pct=0.60, small_cap_pct=0.55,
        sector_participation={"Tech": 0.80, "Finance": 0.70, "Healthcare": 0.65,
                               "Energy": 0.60, "Consumer": 0.55},
        above_ma20_pct=above_ma20, above_ma50_pct=above_ma20 * 0.90,
        new_highs=15, new_lows=5, nh_nl_ratio=3.0,
        market_participation_score=72.0, participation_breadth=0.80,
    )
    health = MarketHealthSnapshot(
        health_score=70.0, internal_strength=0.70, leadership_breadth=0.65,
        lagging_breadth=0.35, participation_quality=0.70, internal_momentum=0.05,
        health_trend=HealthTrend.IMPROVING, leading_sectors=[], lagging_sectors=[],
    )
    regime_snap = build_regime_snapshot(
        BreadthRegimeType.STRONG_PARTICIPATION, 0.85, 5, None, 0.10, 75.0
    )
    return bd, ps, health, regime_snap


class TestBreadthConfidenceCalculator:
    def test_all_fields_in_range(self):
        calc = BreadthConfidenceCalculator()
        sectors = ["Tech", "Finance", "Healthcare", "Energy", "Consumer"]
        u = make_multi_sector_universe(sectors, [0.70] * 5, n_per_sector=20)
        bd, ps, health, rs = _make_test_objects()
        conf = calc.calculate(u, bd, ps, health, rs)
        assert 0.0 <= conf.breadth_confidence <= 1.0
        assert 0.0 <= conf.participation_confidence <= 1.0
        assert 0.0 <= conf.leadership_confidence <= 1.0
        assert 0.0 <= conf.internal_strength_score <= 100.0
        assert 0.0 <= conf.overall_score <= 100.0

    def test_small_universe_lower_confidence(self):
        calc = BreadthConfidenceCalculator()
        small_u = make_universe(6, 4)
        large_u = make_multi_sector_universe(
            ["Tech", "Finance", "Healthcare", "Energy", "Consumer"],
            [0.70] * 5, n_per_sector=20
        )
        bd, ps, health, rs = _make_test_objects()
        small_conf = calc.calculate(small_u, bd, ps, health, rs)
        large_conf = calc.calculate(large_u, bd, ps, health, rs)
        assert small_conf.breadth_confidence <= large_conf.breadth_confidence

    def test_overall_monotone_with_quality(self):
        calc = BreadthConfidenceCalculator()
        bd, ps, health, rs = _make_test_objects()
        u_tiny  = make_universe(6, 4)
        u_large = make_multi_sector_universe(
            ["Tech", "Finance", "Healthcare", "Energy", "Consumer"],
            [0.70] * 5, n_per_sector=20
        )
        c_tiny  = calc.calculate(u_tiny, bd, ps, health, rs)
        c_large = calc.calculate(u_large, bd, ps, health, rs)
        assert c_large.overall_score >= c_tiny.overall_score
