"""test_diversification_engine.py — tests for DiversificationScorer, PortfolioCorrelation, HedgingAnalysis."""
from __future__ import annotations

import pytest

from iios.investment.market.correlation.models import (
    CorrelationMatrix,
    CorrelationMethod,
    DiversificationLevel,
    DiversificationMetrics,
)
from iios.investment.market.correlation.diversification_engine import DiversificationScorer
from iios.investment.market.correlation import portfolio_correlation as pc
from iios.investment.market.correlation import hedging_analysis as ha


def _matrix(syms, data):
    return CorrelationMatrix(
        symbols=syms, data=data, method=CorrelationMethod.PEARSON,
        window=60, n_observations=60, bar_index=0, timestamp=0.0, confidence=0.9,
    )


def _highly_correlated():
    syms = ["A", "B", "C", "D"]
    data = {s: {t: (1.0 if s == t else 0.90) for t in syms} for s in syms}
    return _matrix(syms, data)


def _well_diversified():
    """Near-zero correlation = ideal diversification."""
    syms = ["A", "B", "C", "D"]
    data = {s: {t: (1.0 if s == t else 0.05) for t in syms} for s in syms}
    return _matrix(syms, data)


def _with_hedge():
    """A and B strongly negative = hedging pair."""
    return _matrix(
        ["A", "B"],
        {"A": {"A": 1.0, "B": -0.80}, "B": {"A": -0.80, "B": 1.0}},
    )


def _with_redundant():
    """A and B highly positive = redundant pair."""
    return _matrix(
        ["A", "B"],
        {"A": {"A": 1.0, "B": 0.95}, "B": {"A": 0.95, "B": 1.0}},
    )


# ── DiversificationScorer ─────────────────────────────────────────────────

class TestDiversificationScorer:
    def test_returns_metrics(self):
        scorer = DiversificationScorer()
        result = scorer.score(_well_diversified())
        assert isinstance(result, DiversificationMetrics)

    def test_score_range(self):
        scorer = DiversificationScorer()
        for m in [_highly_correlated(), _well_diversified()]:
            result = scorer.score(m)
            assert 0.0 <= result.diversification_score <= 100.0

    def test_high_corr_poor_diversification(self):
        scorer = DiversificationScorer()
        result = scorer.score(_highly_correlated())
        assert result.diversification_score < 50.0
        assert result.diversification_level in (
            DiversificationLevel.POOR, DiversificationLevel.CRITICAL, DiversificationLevel.FAIR
        )

    def test_low_corr_good_diversification(self):
        scorer = DiversificationScorer()
        result = scorer.score(_well_diversified())
        assert result.diversification_score >= 50.0

    def test_effective_n_high_for_low_corr(self):
        scorer = DiversificationScorer()
        result = scorer.score(_well_diversified())
        assert result.effective_n_assets > 1.0

    def test_effective_n_low_for_high_corr(self):
        scorer = DiversificationScorer()
        result = scorer.score(_highly_correlated())
        assert result.effective_n_assets <= result.diversification_score / 10 + 2

    def test_redundant_pairs_detected(self):
        scorer = DiversificationScorer()
        result = scorer.score(_with_redundant())
        assert len(result.redundant_pairs) >= 1

    def test_hedging_pairs_detected(self):
        scorer = DiversificationScorer()
        result = scorer.score(_with_hedge())
        assert len(result.hedging_pairs) >= 1

    def test_single_asset_returns_result(self):
        scorer = DiversificationScorer()
        m = _matrix(["A"], {"A": {"A": 1.0}})
        result = scorer.score(m)
        assert isinstance(result, DiversificationMetrics)

    def test_cluster_count_positive(self):
        scorer = DiversificationScorer()
        result = scorer.score(_highly_correlated())
        assert result.cluster_count >= 1

    def test_to_dict(self):
        scorer = DiversificationScorer()
        result = scorer.score(_well_diversified())
        d = result.to_dict()
        assert "diversification_score" in d
        assert "effective_n_assets" in d


# ── PortfolioCorrelation ──────────────────────────────────────────────────

class TestPortfolioCorrelation:
    def test_equal_weight(self):
        m = _well_diversified()
        corr = pc.equal_weight_portfolio_correlation(m)
        assert isinstance(corr, float)
        assert -1.0 <= corr <= 1.0

    def test_high_matrix_high_portfolio_corr(self):
        high_corr = pc.equal_weight_portfolio_correlation(_highly_correlated())
        low_corr  = pc.equal_weight_portfolio_correlation(_well_diversified())
        assert high_corr > low_corr


# ── HedgingAnalysis ───────────────────────────────────────────────────────

class TestHedgingAnalysis:
    def test_find_hedging_pairs_inverse(self):
        m      = _with_hedge()
        pairs  = ha.find_hedging_pairs(m, threshold=-0.40)
        assert len(pairs) >= 1
        a, b, corr = pairs[0]
        assert corr <= -0.40

    def test_no_hedging_in_positive_matrix(self):
        m     = _well_diversified()
        pairs = ha.find_hedging_pairs(m, threshold=-0.40)
        assert len(pairs) == 0

    def test_hedging_effectiveness_inverse_pair(self):
        # ha.hedging_effectiveness(correlation) → fraction of variance eliminated
        eff = ha.hedging_effectiveness(-0.80)
        assert eff >= 0.50  # strong negative corr → good hedge
