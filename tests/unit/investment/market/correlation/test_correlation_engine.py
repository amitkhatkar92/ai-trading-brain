"""test_correlation_engine.py — estimators, rolling calc, core engine."""
from __future__ import annotations

import numpy as np
import pytest

from iios.investment.market.correlation.pearson_estimator import PearsonEstimator
from iios.investment.market.correlation.spearman_estimator import SpearmanEstimator
from iios.investment.market.correlation.kendall_estimator import KendallEstimator
from iios.investment.market.correlation.estimator_registry import EstimatorRegistry
from iios.investment.market.correlation.correlation_engine import CorrelationEngine
from iios.investment.market.correlation.models import CorrelationMethod

from tests.unit.investment.market.correlation.conftest import (
    make_correlated_snapshots,
    make_anti_correlated_snapshots,
    make_independent_snapshots,
)


# ── Pearson Estimator ─────────────────────────────────────────────────────

class TestPearsonEstimator:
    def _est(self):
        return PearsonEstimator()

    def test_perfect_positive_correlation(self):
        x = np.linspace(0, 1, 50)
        assert self._est().estimate(x, x) == pytest.approx(1.0, abs=1e-6)

    def test_perfect_negative_correlation(self):
        x = np.linspace(0, 1, 50)
        assert self._est().estimate(x, -x) == pytest.approx(-1.0, abs=1e-6)

    def test_uncorrelated(self):
        rng = np.random.default_rng(99)
        x = rng.normal(0, 1, 1000)
        y = rng.normal(0, 1, 1000)
        r = self._est().estimate(x, y)
        assert abs(r) < 0.15

    def test_partial_correlation(self):
        rng = np.random.default_rng(1)
        F = rng.normal(0, 1, 100)
        x = 0.8 * F + 0.6 * rng.normal(0, 1, 100)
        y = 0.8 * F + 0.6 * rng.normal(0, 1, 100)
        r = self._est().estimate(x, y)
        assert r > 0.40  # should be noticeably positive

    def test_too_few_observations(self):
        x = np.array([1.0, 2.0])
        assert self._est().estimate(x, x) == 0.0

    def test_constant_returns_zero(self):
        x = np.ones(30)
        y = np.linspace(0, 1, 30)
        assert self._est().estimate(x, y) == 0.0

    def test_output_range(self):
        rng = np.random.default_rng(42)
        for _ in range(20):
            x = rng.normal(0, 1, 50)
            y = rng.normal(0, 1, 50)
            r = PearsonEstimator().estimate(x, y)
            assert -1.0 <= r <= 1.0

    def test_name_and_method(self):
        est = PearsonEstimator()
        assert est.name == "pearson"
        assert est.method == CorrelationMethod.PEARSON


# ── Spearman Estimator ────────────────────────────────────────────────────

class TestSpearmanEstimator:
    def _est(self):
        return SpearmanEstimator()

    def test_monotone_increasing(self):
        x = np.arange(1, 21, dtype=float)
        y = x ** 2
        r = self._est().estimate(x, y)
        assert r == pytest.approx(1.0, abs=1e-6)

    def test_monotone_decreasing(self):
        x = np.arange(1, 21, dtype=float)
        r = self._est().estimate(x, -x)
        assert r == pytest.approx(-1.0, abs=1e-6)

    def test_output_range(self):
        rng = np.random.default_rng(7)
        for _ in range(20):
            x = rng.normal(0, 1, 50)
            y = rng.normal(0, 1, 50)
            r = self._est().estimate(x, y)
            assert -1.0 <= r <= 1.0

    def test_name_and_method(self):
        est = SpearmanEstimator()
        assert est.name == "spearman"
        assert est.method == CorrelationMethod.SPEARMAN


# ── Kendall Estimator ──────────────────────────────────────────────────────

class TestKendallEstimator:
    def _est(self):
        return KendallEstimator()

    def test_concordant_pairs(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        r = self._est().estimate(x, x)
        assert r == pytest.approx(1.0, abs=1e-6)

    def test_discordant_pairs(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        r = self._est().estimate(x, -x)
        assert r == pytest.approx(-1.0, abs=1e-6)

    def test_too_few_observations(self):
        x = np.array([1.0, 2.0, 3.0])
        assert self._est().estimate(x, x) == 0.0

    def test_output_range(self):
        rng = np.random.default_rng(3)
        for _ in range(10):
            x = rng.normal(0, 1, 20)
            y = rng.normal(0, 1, 20)
            r = self._est().estimate(x, y)
            assert -1.0 <= r <= 1.0

    def test_name_and_method(self):
        est = KendallEstimator()
        assert est.name == "kendall"
        assert est.method == CorrelationMethod.KENDALL


# ── EstimatorRegistry ─────────────────────────────────────────────────────

class TestEstimatorRegistry:
    def test_register_and_get(self):
        reg = EstimatorRegistry()
        p = PearsonEstimator()
        reg.register(p)
        assert reg.get("pearson") is p

    def test_unregister(self):
        reg = EstimatorRegistry()
        reg.register(PearsonEstimator())
        reg.unregister("pearson")
        assert reg.get("pearson") is None

    def test_names(self):
        reg = EstimatorRegistry()
        reg.register(PearsonEstimator())
        reg.register(SpearmanEstimator())
        assert "pearson" in reg.names()
        assert "spearman" in reg.names()

    def test_all(self):
        reg = EstimatorRegistry()
        reg.register(PearsonEstimator())
        reg.register(KendallEstimator())
        assert len(reg.all()) == 2

    def test_default_is_first(self):
        reg = EstimatorRegistry()
        p = PearsonEstimator()
        reg.register(p)
        assert reg.default() is p

    def test_len(self):
        reg = EstimatorRegistry()
        assert len(reg) == 0
        reg.register(PearsonEstimator())
        assert len(reg) == 1


# ── CorrelationEngine ──────────────────────────────────────────────────────

class TestCorrelationEngine:
    def test_returns_none_before_min_obs(self):
        engine = CorrelationEngine(window=60, min_observations=10)
        snaps = make_correlated_snapshots(5, ["A", "B"])
        for s in snaps:
            result = engine.update(s)
        assert result is None

    def test_returns_matrix_after_min_obs(self):
        engine = CorrelationEngine(window=60, min_observations=5)
        snaps = make_correlated_snapshots(20, ["A", "B", "C"])
        matrix = None
        for s in snaps:
            matrix = engine.update(s)
        assert matrix is not None
        assert "A" in matrix.symbols

    def test_correlated_assets_show_positive_corr(self):
        engine = CorrelationEngine(window=60, min_observations=5)
        snaps = make_correlated_snapshots(80, ["A", "B"], target_corr=0.85)
        matrix = None
        for s in snaps:
            matrix = engine.update(s)
        assert matrix is not None
        corr = matrix.get("A", "B")
        assert corr is not None
        assert corr > 0.40  # should be reasonably positive

    def test_anti_correlated_assets_show_negative_corr(self):
        engine = CorrelationEngine(window=60, min_observations=5)
        snaps = make_anti_correlated_snapshots(80)
        matrix = None
        for s in snaps:
            matrix = engine.update(s)
        assert matrix is not None
        corr = matrix.get("A", "B")
        assert corr is not None
        assert corr < 0.0

    def test_matrix_diagonal_is_one(self):
        engine = CorrelationEngine(window=30, min_observations=5)
        snaps = make_correlated_snapshots(40, ["A", "B", "C"])
        matrix = None
        for s in snaps:
            matrix = engine.update(s)
        assert matrix is not None
        for sym in matrix.symbols:
            assert matrix.get(sym, sym) == pytest.approx(1.0, abs=1e-9)

    def test_all_symbols_populated(self):
        engine = CorrelationEngine(window=30, min_observations=5)
        snaps = make_correlated_snapshots(40, ["X", "Y", "Z", "W"])
        matrix = None
        for s in snaps:
            matrix = engine.update(s)
        assert matrix is not None
        assert set(matrix.symbols) >= {"X", "Y", "Z", "W"}

    def test_register_unregister_estimator(self):
        engine = CorrelationEngine()
        engine.register_estimator(SpearmanEstimator())
        assert "spearman" in engine._registry.names()
        engine.unregister_estimator("spearman")
        assert "spearman" not in engine._registry.names()

    def test_statistics_updated(self):
        engine = CorrelationEngine(window=30, min_observations=5)
        snaps = make_correlated_snapshots(40, ["A", "B"])
        for s in snaps:
            engine.update(s)
        stats = engine.statistics()
        assert len(stats) > 0

    def test_get_returns_array(self):
        engine = CorrelationEngine(window=30, min_observations=5)
        snaps = make_correlated_snapshots(20, ["A", "B"])
        for s in snaps:
            engine.update(s)
        arr = engine.get_returns("A")
        assert len(arr) > 0
