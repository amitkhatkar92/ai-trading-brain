"""tests/unit/investment/market/sector_rotation/test_relative_strength.py"""
from __future__ import annotations

import pytest

from iios.investment.market.sector_rotation.models import SectorPerformance
from iios.investment.market.sector_rotation.relative_strength_engine import (
    RelativeStrengthEngine,
)
from iios.investment.market.sector_rotation.relative_strength_ranker import (
    rank_sectors_by_rs,
)
from iios.investment.market.sector_rotation.relative_strength_score import (
    compute_rs_score,
)


def _make_perf(sector: str, rel20: float, rel1: float = 0.0) -> SectorPerformance:
    return SectorPerformance(
        sector=sector, bar_index=1,
        return_1bar=rel1, return_5bar=0.0, return_20bar=rel20, return_60bar=0.0,
        rel_return_1bar=rel1, rel_return_5bar=0.0, rel_return_20bar=rel20,
        breadth_pct=0.6, avg_volume_ratio=1.2,
        momentum_score=55.0, strength_score=60.0, n_securities=5,
    )


class TestComputeRsScore:
    def test_top_ranked(self):
        rs = compute_rs_score("IT", vs_benchmark=0.05, vs_group=0.03, rank=1, total=5)
        assert rs.composite > 50.0
        assert rs.rank == 1
        assert rs.percentile == pytest.approx(1.0)

    def test_bottom_ranked(self):
        rs = compute_rs_score("Utilities", vs_benchmark=-0.05, vs_group=-0.03, rank=5, total=5)
        assert rs.composite < 50.0
        assert rs.rank == 5
        assert rs.percentile == pytest.approx(0.0)

    def test_neutral(self):
        rs = compute_rs_score("FIN", vs_benchmark=0.0, vs_group=0.0, rank=3, total=5)
        assert rs.composite == pytest.approx(50.0, abs=1.0)

    def test_composite_range(self):
        for vb in (-0.2, 0.0, 0.2):
            rs = compute_rs_score("X", vs_benchmark=vb, vs_group=0.0, rank=1, total=1)
            assert 0.0 <= rs.composite <= 100.0


class TestRankSectorsByRs:
    def test_empty(self):
        result = rank_sectors_by_rs({})
        assert result == {}

    def test_ranking_order(self):
        perfs = {
            "IT":         _make_perf("IT",         0.10),
            "Financials": _make_perf("Financials", 0.0),
            "Utilities":  _make_perf("Utilities",  -0.10),
        }
        rs = rank_sectors_by_rs(perfs)
        assert rs["IT"].rank < rs["Financials"].rank < rs["Utilities"].rank

    def test_all_sectors_present(self):
        perfs = {s: _make_perf(s, i * 0.01) for i, s in enumerate(["A", "B", "C"])}
        rs = rank_sectors_by_rs(perfs)
        assert set(rs.keys()) == {"A", "B", "C"}

    def test_composites_in_range(self):
        perfs = {s: _make_perf(s, i * 0.02) for i, s in enumerate(["A", "B", "C", "D"])}
        rs = rank_sectors_by_rs(perfs)
        for r in rs.values():
            assert 0.0 <= r.composite <= 100.0

    def test_percentile_top_sector(self):
        perfs = {
            "IT":         _make_perf("IT",         0.05),
            "Financials": _make_perf("Financials", -0.05),
        }
        rs = rank_sectors_by_rs(perfs)
        assert rs["IT"].percentile > rs["Financials"].percentile


class TestRelativeStrengthEngine:
    def test_update_and_query(self):
        engine = RelativeStrengthEngine()
        perfs = {
            "IT":         _make_perf("IT",         0.05),
            "Financials": _make_perf("Financials", -0.02),
            "Utilities":  _make_perf("Utilities",  -0.05),
        }
        engine.update(perfs, {})
        it_rs = engine.get_sector("IT")
        assert it_rs is not None
        assert it_rs.composite > 50.0

    def test_sector_leaders(self):
        engine = RelativeStrengthEngine()
        perfs = {s: _make_perf(s, i * 0.01) for i, s in enumerate(["A", "B", "C", "D"])}
        engine.update(perfs, {})
        leaders = engine.sector_leaders(2)
        assert len(leaders) == 2

    def test_sector_laggards(self):
        engine = RelativeStrengthEngine()
        perfs = {s: _make_perf(s, i * 0.01) for i, s in enumerate(["A", "B", "C", "D"])}
        engine.update(perfs, {})
        laggards = engine.sector_laggards(2)
        assert len(laggards) == 2
        assert laggards[0] == "A"   # lowest rel20 = 0.0

    def test_missing_sector_returns_none(self):
        engine = RelativeStrengthEngine()
        assert engine.get_sector("NonExistent") is None

    def test_sector_rs_dict(self):
        engine = RelativeStrengthEngine()
        perfs = {"X": _make_perf("X", 0.01), "Y": _make_perf("Y", -0.01)}
        engine.update(perfs, {})
        rs_dict = engine.sector_rs()
        assert "X" in rs_dict
        assert "Y" in rs_dict
