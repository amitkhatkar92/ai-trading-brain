"""tests/unit/investment/market/sector_rotation/test_sector_performance.py"""
from __future__ import annotations

import pytest

from iios.investment.market.sector_rotation.models import MarketSnapshot, SecurityData
from iios.investment.market.sector_rotation.sector_performance import (
    _avg_volume_ratio,
    _breadth,
    _momentum_score,
    _rolling_return,
    _strength_score,
    _weighted_avg_return,
    compute_sector_performance,
)
from iios.investment.market.sector_rotation.sector_snapshot import SectorSnapshotBuilder
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy
from iios.investment.market.sector_rotation.sector_tracker import SectorTracker
from collections import deque


class TestWeightedAvgReturn:
    def test_equal_weight_fallback(self):
        securities = [
            SecurityData("A", 0.02, "IT", "S", market_cap=0.0),
            SecurityData("B", 0.04, "IT", "S", market_cap=0.0),
        ]
        assert _weighted_avg_return(securities) == pytest.approx(0.03)

    def test_market_cap_weighted(self):
        securities = [
            SecurityData("A", 0.10, "IT", "S", market_cap=10.0),
            SecurityData("B", 0.0,  "IT", "S", market_cap=90.0),
        ]
        assert _weighted_avg_return(securities) == pytest.approx(0.01)

    def test_empty(self):
        assert _weighted_avg_return([]) == 0.0


class TestBreadth:
    def test_all_advancing(self):
        secs = [SecurityData("A", 0.01, "X", "Y"), SecurityData("B", 0.02, "X", "Y")]
        assert _breadth(secs) == pytest.approx(1.0)

    def test_half(self):
        secs = [
            SecurityData("A",  0.01, "X", "Y"),
            SecurityData("B", -0.01, "X", "Y"),
        ]
        assert _breadth(secs) == pytest.approx(0.5)

    def test_empty(self):
        assert _breadth([]) == pytest.approx(0.5)


class TestRollingReturn:
    def test_empty(self):
        assert _rolling_return(deque(), 5) == 0.0

    def test_sum_of_window(self):
        h = deque([0.01, 0.02, 0.03, 0.04, 0.05], maxlen=10)
        assert _rolling_return(h, 3) == pytest.approx(0.03 + 0.04 + 0.05)

    def test_full_window(self):
        h = deque([0.01] * 20, maxlen=20)
        assert _rolling_return(h, 5) == pytest.approx(0.05)


class TestMomentumScore:
    def test_neutral_returns_midpoint(self):
        score = _momentum_score(0.0, 0.0, 0.0)
        assert score == pytest.approx(50.0)

    def test_positive_returns_above_50(self):
        score = _momentum_score(0.02, 0.10, 0.20)
        assert score > 50.0

    def test_negative_returns_below_50(self):
        score = _momentum_score(-0.02, -0.10, -0.20)
        assert score < 50.0

    def test_clamped_to_0_100(self):
        score = _momentum_score(1.0, 5.0, 10.0)
        assert 0.0 <= score <= 100.0
        score2 = _momentum_score(-1.0, -5.0, -10.0)
        assert 0.0 <= score2 <= 100.0


class TestStrengthScore:
    def test_all_positive_factors(self):
        score = _strength_score(70.0, 0.9, 2.0)
        assert score > 60.0

    def test_range(self):
        for mom in (20.0, 50.0, 80.0):
            for breadth in (0.2, 0.5, 0.8):
                for vol in (0.5, 1.0, 2.0):
                    score = _strength_score(mom, breadth, vol)
                    assert 0.0 <= score <= 100.0


class TestComputeSectorPerformance:
    def test_empty_securities(self):
        taxonomy = SectorTaxonomy()
        perf = compute_sector_performance(
            sector="IT",
            securities=[],
            benchmark_return=0.005,
            bar_index=1,
            return_history=deque(),
            taxonomy=taxonomy,
        )
        assert perf.n_securities == 0
        assert perf.sector == "IT"
        assert 0 <= perf.momentum_score <= 100

    def test_returns_sector_perf_object(self, single_snapshot, taxonomy):
        by_sector = single_snapshot.by_sector()
        perf = compute_sector_performance(
            sector="Information Technology",
            securities=by_sector["Information Technology"],
            benchmark_return=0.005,
            bar_index=1,
            return_history=deque([0.01, 0.02]),
            taxonomy=taxonomy,
        )
        assert perf.sector == "Information Technology"
        assert perf.n_securities == 3
        assert 0.0 <= perf.momentum_score <= 100.0
        assert 0.0 <= perf.breadth_pct <= 1.0


class TestSectorTracker:
    def test_update_returns_performance(self, single_snapshot, taxonomy):
        tracker = SectorTracker("Information Technology", taxonomy)
        perf = tracker.update(single_snapshot)
        assert perf.sector == "Information Technology"
        assert perf.n_securities == 3

    def test_rolling_history_grows(self, multi_snapshot_series, taxonomy):
        tracker = SectorTracker("Information Technology", taxonomy)
        for snap in multi_snapshot_series:
            tracker.update(snap)
        assert tracker.history_length == len(multi_snapshot_series)

    def test_current_is_latest(self, multi_snapshot_series, taxonomy):
        tracker = SectorTracker("Financials", taxonomy)
        for snap in multi_snapshot_series:
            perf = tracker.update(snap)
        assert tracker.current is perf


class TestSectorSnapshotBuilder:
    def test_all_sectors_present(self, single_snapshot, taxonomy):
        builder = SectorSnapshotBuilder(taxonomy)
        result  = builder.update(single_snapshot)
        for sector in single_snapshot.sectors():
            assert sector in result

    def test_second_update_cumulates_history(self, multi_snapshot_series, taxonomy):
        builder = SectorSnapshotBuilder(taxonomy)
        for snap in multi_snapshot_series:
            result = builder.update(snap)
        assert "Information Technology" in result
