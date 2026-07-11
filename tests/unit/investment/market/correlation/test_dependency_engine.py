"""test_dependency_engine.py — tests for DependencyEngine and DependencyGraph."""
from __future__ import annotations

import pytest

from iios.investment.market.correlation.models import (
    AssetClass,
    CorrelationMatrix,
    CorrelationMethod,
    DependencyGraph,
    DependencyType,
)
from iios.investment.market.correlation.rolling_correlation import RollingCorrelationCalculator
from iios.investment.market.correlation.pearson_estimator import PearsonEstimator
from iios.investment.market.correlation.dependency_engine import DependencyEngine
from iios.investment.market.correlation.dependency_graph import build_dependency_graph

from tests.unit.investment.market.correlation.conftest import (
    make_snapshot,
    make_correlated_snapshots,
)


def _make_matrix(syms, data):
    return CorrelationMatrix(
        symbols=syms, data=data, method=CorrelationMethod.PEARSON,
        window=60, n_observations=60, bar_index=0, timestamp=0.0, confidence=0.9,
    )


def _make_dep_engine():
    calc = RollingCorrelationCalculator(
        window=20, estimator=PearsonEstimator(), min_observations=10
    )
    return DependencyEngine(primary_calc=calc, window=20, max_lag=3, min_corr=0.20)


# ── DependencyGraph ────────────────────────────────────────────────────────

class TestDependencyGraph:
    def test_empty_graph(self):
        g = DependencyGraph(edges=[], bar_index=0, timestamp=0.0)
        assert g.leading_assets() == []
        assert g.lagging_assets() == []
        assert g.n_edges if hasattr(g, "n_edges") else len(g.edges) == 0

    def test_leading_assets(self):
        from iios.investment.market.correlation.models import DependencyEdge
        e = DependencyEdge(
            source="SPY", target="QQQ", lag_bars=1,
            correlation=0.85, dependency_type=DependencyType.LEADING, confidence=0.8,
        )
        g = DependencyGraph(edges=[e], bar_index=0, timestamp=0.0)
        assert "SPY" in g.leading_assets()
        assert "QQQ" in g.lagging_assets()

    def test_influence_score_zero_without_followers(self):
        g = DependencyGraph(edges=[], bar_index=0, timestamp=0.0)
        assert g.influence_score("SPY") == 0.0

    def test_get_leaders_of(self):
        from iios.investment.market.correlation.models import DependencyEdge
        e = DependencyEdge("SPY", "QQQ", 1, 0.80, DependencyType.LEADING, 0.9)
        g = DependencyGraph(edges=[e], bar_index=0, timestamp=0.0)
        leaders = g.get_leaders_of("QQQ")
        assert len(leaders) == 1
        assert leaders[0].source == "SPY"

    def test_to_dict(self):
        g = DependencyGraph(edges=[], bar_index=5, timestamp=0.0)
        d = g.to_dict()
        assert isinstance(d, dict)
        assert "bar_index" in d


# ── DependencyEngine ───────────────────────────────────────────────────────

class TestDependencyEngine:
    def test_returns_empty_graph_with_insufficient_data(self):
        engine = _make_dep_engine()
        snap = make_snapshot({"SPY": 0.01, "QQQ": 0.008})
        matrix = _make_matrix(
            ["SPY", "QQQ"],
            {"SPY": {"SPY": 1.0, "QQQ": 0.80}, "QQQ": {"SPY": 0.80, "QQQ": 1.0}},
        )
        result = engine.update(snap, matrix)
        assert isinstance(result, DependencyGraph)
        assert result.bar_index == snap.bar_index

    def test_graph_populates_after_enough_history(self):
        engine = _make_dep_engine()
        snapshots = make_correlated_snapshots(30, ["SPY", "QQQ"], target_corr=0.80)
        matrix = _make_matrix(
            ["SPY", "QQQ"],
            {"SPY": {"SPY": 1.0, "QQQ": 0.80}, "QQQ": {"SPY": 0.80, "QQQ": 1.0}},
        )
        result = None
        for snap in snapshots:
            result = engine.update(snap, matrix)
        assert isinstance(result, DependencyGraph)

    def test_current_property(self):
        engine = _make_dep_engine()
        snap = make_snapshot({"A": 0.01, "B": 0.005})
        matrix = _make_matrix(
            ["A", "B"],
            {"A": {"A": 1.0, "B": 0.70}, "B": {"A": 0.70, "B": 1.0}},
        )
        engine.update(snap, matrix)
        assert engine.current is not None

    def test_history_grows(self):
        engine = _make_dep_engine()
        matrix = _make_matrix(
            ["A", "B"],
            {"A": {"A": 1.0, "B": 0.60}, "B": {"A": 0.60, "B": 1.0}},
        )
        for i, snap in enumerate(make_correlated_snapshots(5, ["A", "B"])):
            engine.update(snap, matrix)
        assert len(engine.recent(100)) >= 1  # at least one update stored

    def test_single_asset_returns_empty(self):
        engine = _make_dep_engine()
        snap = make_snapshot({"SPY": 0.01})
        matrix = _make_matrix(["SPY"], {"SPY": {"SPY": 1.0}})
        result = engine.update(snap, matrix)
        assert len(result.edges) == 0


# ── build_dependency_graph ────────────────────────────────────────────────

class TestBuildDependencyGraph:
    def test_no_symbols_returns_empty(self):
        g = build_dependency_graph(
            symbol_returns={},
            window=10, max_lag=3, min_corr=0.30,
            bar_index=0, timestamp=0.0
        )
        assert isinstance(g, DependencyGraph)
        assert len(g.edges) == 0

    def test_returns_dependency_graph(self):
        import numpy as np
        rng = np.random.default_rng(42)
        f   = rng.normal(0, 0.01, 30)
        # SPY leads QQQ by 1 bar
        arrays = {
            "SPY": f,
            "QQQ": np.concatenate([[0.0], f[:-1]]) + rng.normal(0, 0.001, 30),
        }
        g = build_dependency_graph(
            symbol_returns=arrays,
            window=10,
            max_lag=3,
            min_corr=0.10,
            bar_index=0,
            timestamp=0.0,
        )
        assert isinstance(g, DependencyGraph)
