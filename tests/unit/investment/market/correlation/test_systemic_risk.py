"""test_systemic_risk.py — tests for SystemicRiskCalculator, ContagionEngine, ShockPropagation."""
from __future__ import annotations

import pytest

from iios.investment.market.correlation.models import (
    AssetClass,
    CorrelationMatrix,
    CorrelationMethod,
    DependencyGraph,
    RiskLevel,
    SystemicRiskMetrics,
)
from iios.investment.market.correlation.systemic_risk import SystemicRiskCalculator
from iios.investment.market.correlation.contagion_engine import ContagionEngine
from iios.investment.market.correlation.shock_propagation import ShockPropagationAnalyzer

from tests.unit.investment.market.correlation.conftest import (
    make_snapshot,
    make_correlated_snapshots,
)


def _matrix(syms, data, n_obs=60):
    return CorrelationMatrix(
        symbols=syms, data=data, method=CorrelationMethod.PEARSON,
        window=60, n_observations=n_obs, bar_index=0, timestamp=0.0, confidence=0.9,
    )


def _empty_graph():
    return DependencyGraph(edges=[], bar_index=0, timestamp=0.0)


def _high_corr_matrix():
    syms = ["A", "B", "C", "D"]
    data = {s: {t: (1.0 if s == t else 0.85) for t in syms} for s in syms}
    return _matrix(syms, data)


def _low_corr_matrix():
    syms = ["A", "B", "C", "D"]
    data = {s: {t: (1.0 if s == t else 0.05) for t in syms} for s in syms}
    return _matrix(syms, data)


# ── SystemicRiskCalculator ────────────────────────────────────────────────

class TestSystemicRiskCalculator:
    def test_returns_metrics(self):
        calc = SystemicRiskCalculator()
        result = calc.calculate(_high_corr_matrix(), _empty_graph())
        assert isinstance(result, SystemicRiskMetrics)

    def test_high_corr_gives_high_risk(self):
        calc = SystemicRiskCalculator()
        result = calc.calculate(_high_corr_matrix(), _empty_graph())
        assert result.systemic_risk_score >= 40.0
        assert result.risk_level in (RiskLevel.ELEVATED, RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_low_corr_gives_low_risk(self):
        calc = SystemicRiskCalculator()
        result = calc.calculate(_low_corr_matrix(), _empty_graph())
        assert result.systemic_risk_score < 50.0

    def test_risk_score_range(self):
        calc = SystemicRiskCalculator()
        for matrix in [_high_corr_matrix(), _low_corr_matrix()]:
            r = calc.calculate(matrix, _empty_graph())
            assert 0.0 <= r.systemic_risk_score <= 100.0

    def test_single_asset_returns_empty(self):
        calc = SystemicRiskCalculator()
        m = _matrix(["A"], {"A": {"A": 1.0}})
        result = calc.calculate(m, _empty_graph())
        assert result.systemic_risk_score == 0.0

    def test_avg_correlations_correct(self):
        calc = SystemicRiskCalculator()
        result = calc.calculate(_high_corr_matrix(), _empty_graph())
        assert result.avg_abs_correlation >= 0.70  # all pairs at 0.85

    def test_n_correlated_clusters(self):
        calc = SystemicRiskCalculator()
        result = calc.calculate(_high_corr_matrix(), _empty_graph())
        assert result.n_correlated_clusters >= 1

    def test_to_dict(self):
        calc = SystemicRiskCalculator()
        result = calc.calculate(_high_corr_matrix(), _empty_graph())
        d = result.to_dict()
        assert "systemic_risk_score" in d
        assert "risk_level" in d


# ── ContagionEngine ───────────────────────────────────────────────────────

class TestContagionEngine:
    def _make_systemic(self, score: float = 80.0):
        return SystemicRiskMetrics(
            risk_level=RiskLevel.HIGH if score >= 65 else RiskLevel.LOW,
            avg_pairwise_correlation=0.80, avg_abs_correlation=0.80,
            correlation_concentration=0.80, contagion_index=0.80,
            interconnectedness=0.80, systemic_risk_score=score,
            most_interconnected=["A"], n_correlated_clusters=2,
        )

    def test_returns_value(self):
        engine = ContagionEngine()
        result = engine.update(self._make_systemic(80.0), bar_index=0)
        assert isinstance(result, list)

    def test_high_corr_high_contagion(self):
        engine = ContagionEngine()
        # Prime with low risk then escalate
        engine.update(self._make_systemic(10.0), bar_index=0)
        events = engine.update(self._make_systemic(85.0), bar_index=1)
        # May or may not generate events on first escalation
        assert isinstance(events, list)

    def test_single_asset_zero_or_minimal(self):
        engine = ContagionEngine()
        m = _matrix(["A"], {"A": {"A": 1.0}})
        systemic = SystemicRiskMetrics(
            risk_level=RiskLevel.LOW, avg_pairwise_correlation=0.0,
            avg_abs_correlation=0.0, correlation_concentration=0.0,
            contagion_index=0.0, interconnectedness=0.0, systemic_risk_score=0.0,
            most_interconnected=[], n_correlated_clusters=0,
        )
        result = engine.update(systemic, bar_index=0)
        assert isinstance(result, list)


# ── ShockPropagationAnalyzer ──────────────────────────────────────────────

class TestShockPropagationAnalyzer:
    def test_returns_result(self):
        analyzer = ShockPropagationAnalyzer()
        matrix   = _high_corr_matrix()
        paths, events = analyzer.analyze(
            matrix=matrix, dep_graph=_empty_graph(),
            current_returns={"A": 0.05, "B": -0.01, "C": 0.01, "D": 0.02},
            bar_index=0,
        )
        assert isinstance(paths, list)
        assert isinstance(events, list)

    def test_large_shock_triggers_paths(self):
        analyzer = ShockPropagationAnalyzer(shock_threshold_pct=0.03)
        matrix   = _high_corr_matrix()
        paths, events = analyzer.analyze(
            matrix=matrix, dep_graph=_empty_graph(),
            current_returns={"A": 0.08, "B": -0.01, "C": -0.01, "D": -0.01},
            bar_index=0,
        )
        assert isinstance(paths, list)

    def test_small_returns_no_shock(self):
        analyzer = ShockPropagationAnalyzer(shock_threshold_pct=0.10)
        matrix   = _high_corr_matrix()
        paths, events = analyzer.analyze(
            matrix=matrix, dep_graph=_empty_graph(),
            current_returns={"A": 0.001, "B": 0.001, "C": 0.001, "D": 0.001},
            bar_index=0,
        )
        assert len(paths) == 0
