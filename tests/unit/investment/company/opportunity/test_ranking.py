"""tests/unit/investment/company/opportunity/test_ranking.py
Tests for ranking engine, ranking scores, and ranking statistics.
"""
from __future__ import annotations

import pytest

from iios.investment.company.opportunity.ranking_engine import RankingEngine
from iios.investment.company.opportunity.ranking_score import RankingChange, RankingResult
from iios.investment.company.opportunity.ranking_statistics import (
    compute_score_percentile, normalise_scores, rank_tickers, score_distribution_summary,
    score_momentum, top_n_tickers,
)


class TestRankingStatistics:
    def test_rank_tickers(self):
        scores = {"A": 80.0, "B": 60.0, "C": 70.0}
        ranks = rank_tickers(scores)
        assert ranks["A"] == 1
        assert ranks["C"] == 2
        assert ranks["B"] == 3

    def test_rank_ties(self):
        scores = {"A": 70.0, "B": 70.0, "C": 50.0}
        ranks = rank_tickers(scores)
        assert ranks["A"] == ranks["B"] == 1
        assert ranks["C"] == 3

    def test_top_n(self):
        scores = {"A": 80.0, "B": 60.0, "C": 70.0, "D": 90.0}
        top = top_n_tickers(scores, 2)
        assert top[0] == "D"
        assert top[1] == "A"

    def test_percentile_100(self):
        pop = [10.0, 20.0, 30.0, 40.0, 50.0]
        # value = 50 is the max
        p = compute_score_percentile(50.0, pop)
        assert p > 80.0

    def test_percentile_empty(self):
        assert compute_score_percentile(50.0, []) == 50.0

    def test_normalise_scores(self):
        scores = {"A": 0.0, "B": 50.0, "C": 100.0}
        norm = normalise_scores(scores)
        assert norm["A"] == pytest.approx(0.0)
        assert norm["C"] == pytest.approx(100.0)
        assert norm["B"] == pytest.approx(50.0)

    def test_normalise_all_same(self):
        scores = {"A": 60.0, "B": 60.0}
        norm = normalise_scores(scores)
        assert norm["A"] == 50.0 and norm["B"] == 50.0

    def test_score_momentum_improving(self):
        mom = score_momentum(80.0, [60.0, 62.0, 65.0], lookback=3)
        assert mom > 0

    def test_score_momentum_deteriorating(self):
        mom = score_momentum(50.0, [70.0, 68.0, 65.0])
        assert mom < 0

    def test_distribution_summary(self):
        scores = {"A": 70.0, "B": 80.0, "C": 60.0}
        summary = score_distribution_summary(scores)
        assert summary["count"] == 3
        assert summary["min"] == 60.0
        assert summary["max"] == 80.0


class TestRankingResult:
    def test_global_percentile_rank1(self):
        r = RankingResult(ticker="T", global_rank=1, score=80.0, population_size=100)
        assert r.global_percentile == pytest.approx(100.0)

    def test_global_percentile_last(self):
        r = RankingResult(ticker="T", global_rank=100, score=20.0, population_size=100)
        assert r.global_percentile == pytest.approx(1.0)

    def test_global_percentile_none(self):
        r = RankingResult(ticker="T", global_rank=None, score=50.0, population_size=0)
        assert r.global_percentile is None

    def test_to_dict(self):
        r = RankingResult(ticker="X", global_rank=5, score=72.0, population_size=50)
        d = r.to_dict()
        assert d["global_rank"] == 5
        assert d["score"] == 72.0


class TestRankingChange:
    def test_rank_delta_improvement(self):
        from datetime import datetime, timezone
        c = RankingChange("T", 10, 5, 3.0, datetime.now(timezone.utc))
        assert c.rank_delta == 5

    def test_rank_delta_decline(self):
        from datetime import datetime, timezone
        c = RankingChange("T", 3, 7, -2.0, datetime.now(timezone.utc))
        assert c.rank_delta == -4


class TestRankingEngine:
    @pytest.fixture
    def engine(self):
        return RankingEngine()

    def test_update_returns_result(self, engine):
        result = engine.update("INFY", 75.0, sector="IT", industry="Software")
        assert isinstance(result, RankingResult)
        assert result.ticker == "INFY"

    def test_single_ticker_rank1(self, engine):
        result = engine.update("X", 70.0)
        assert result.global_rank == 1

    def test_ranking_order(self, engine):
        engine.update("A", 80.0)
        engine.update("B", 60.0)
        r = engine.get_ranking("A")
        assert r.global_rank == 1
        r2 = engine.get_ranking("B")
        assert r2.global_rank == 2

    def test_update_improves_rank(self, engine):
        engine.update("A", 80.0)
        engine.update("B", 60.0)
        r_before = engine.get_ranking("B")
        assert r_before.global_rank == 2
        # Improve B's score
        engine.update("B", 90.0)
        r_after = engine.get_ranking("B")
        assert r_after.global_rank == 1

    def test_sector_rank(self, engine):
        engine.update("A", 80.0, sector="IT")
        engine.update("B", 60.0, sector="IT")
        engine.update("C", 90.0, sector="Finance")
        top_it = engine.get_top(n=5, sector="IT")
        assert "A" in top_it
        assert "C" not in top_it

    def test_top_global(self, engine):
        for i, t in enumerate(["A", "B", "C", "D", "E"]):
            engine.update(t, float(i * 10 + 30))
        top = engine.get_top(3)
        assert len(top) == 3
        assert "E" in top

    def test_unknown_ticker_returns_none(self, engine):
        assert engine.get_ranking("UNKNOWN") is None

    def test_population_size(self, engine):
        engine.update("X", 60.0)
        engine.update("Y", 70.0)
        assert engine.population_size() == 2

    def test_score_distribution(self, engine):
        engine.update("A", 60.0)
        engine.update("B", 80.0)
        dist = engine.score_distribution()
        assert dist["count"] == 2
        assert dist["min"] == 60.0
        assert dist["max"] == 80.0
