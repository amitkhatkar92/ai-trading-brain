"""test_models.py — unit tests for all correlation models."""
from __future__ import annotations

import time

import pytest

from iios.investment.market.correlation.models import (
    AssetClass,
    CorrelationConfidenceScore,
    CorrelationEvent,
    CorrelationEventType,
    CorrelationMatrix,
    CorrelationMethod,
    CorrelationPair,
    CorrelationRegimeSnapshot,
    CorrelationRegimeType,
    DependencyEdge,
    DependencyGraph,
    DependencyType,
    DiversificationLevel,
    DiversificationMetrics,
    IntermarketAnalysis,
    IntermarketRelationship,
    MultiAssetSnapshot,
    PriceObservation,
    RelationshipType,
    RiskLevel,
    SystemicRiskMetrics,
)


# ── PriceObservation ──────────────────────────────────────────────────────

class TestPriceObservation:
    def test_defaults(self):
        obs = PriceObservation("AAPL", 0.01)
        assert obs.symbol == "AAPL"
        assert obs.return_pct == 0.01
        assert obs.asset_class == AssetClass.UNKNOWN.value
        assert obs.sector == "unknown"
        assert obs.volume == 0.0

    def test_with_all_fields(self):
        obs = PriceObservation(
            "SPY", 0.005, asset_class=AssetClass.INDEX.value,
            sector="Broad Market", price=450.0, volume=1e6,
        )
        assert obs.asset_class == "index"
        assert obs.price == 450.0


# ── MultiAssetSnapshot ────────────────────────────────────────────────────

class TestMultiAssetSnapshot:
    def _make(self):
        obs = [
            PriceObservation("A", 0.01, asset_class="equity", sector="Tech"),
            PriceObservation("B", -0.005, asset_class="bond",  sector="Rates"),
            PriceObservation("C", 0.003, asset_class="equity", sector="Finance"),
        ]
        return MultiAssetSnapshot(bar_index=5, timestamp=1.0, observations=obs)

    def test_total(self):
        snap = self._make()
        assert snap.total == 3

    def test_symbols(self):
        snap = self._make()
        assert set(snap.symbols) == {"A", "B", "C"}

    def test_returns(self):
        snap = self._make()
        r = snap.returns()
        assert r["A"] == pytest.approx(0.01)
        assert r["B"] == pytest.approx(-0.005)

    def test_by_asset_class(self):
        snap = self._make()
        by_ac = snap.by_asset_class()
        assert "equity" in by_ac
        assert len(by_ac["equity"]) == 2

    def test_by_sector(self):
        snap = self._make()
        by_sec = snap.by_sector()
        assert "Tech" in by_sec

    def test_get(self):
        snap = self._make()
        assert snap.get("A") is not None
        assert snap.get("X") is None

    def test_empty_snapshot(self):
        snap = MultiAssetSnapshot(0, 0.0, [])
        assert snap.total == 0
        assert snap.symbols == []


# ── CorrelationMatrix ─────────────────────────────────────────────────────

class TestCorrelationMatrix:
    def _make(self, syms=("A", "B", "C"), avg_corr=0.60) -> CorrelationMatrix:
        data = {}
        for s in syms:
            data[s] = {}
            for t in syms:
                data[s][t] = 1.0 if s == t else avg_corr
        return CorrelationMatrix(
            symbols=list(syms),
            data=data,
            method=CorrelationMethod.PEARSON,
            window=60,
            n_observations=50,
            bar_index=10,
            timestamp=1.0,
            confidence=0.85,
        )

    def test_get_symmetric(self):
        m = self._make()
        assert m.get("A", "B") == pytest.approx(0.60)
        assert m.get("B", "A") == pytest.approx(0.60)

    def test_get_self(self):
        m = self._make()
        assert m.get("A", "A") == pytest.approx(1.0)

    def test_get_missing(self):
        m = self._make()
        assert m.get("X", "Y") is None

    def test_avg_correlation(self):
        m = self._make(avg_corr=0.60)
        assert m.avg_correlation() == pytest.approx(0.60)

    def test_avg_abs_correlation(self):
        data = {"A": {"A": 1.0, "B": -0.50}, "B": {"A": -0.50, "B": 1.0}}
        m = CorrelationMatrix(
            symbols=["A", "B"], data=data, method=CorrelationMethod.PEARSON,
            window=60, n_observations=30, bar_index=0, timestamp=0.0, confidence=0.8,
        )
        assert m.avg_abs_correlation() == pytest.approx(0.50)

    def test_max_pair(self):
        m = self._make()
        res = m.max_pair()
        assert res is not None
        assert res[2] == pytest.approx(0.60)

    def test_min_pair(self):
        m = self._make()
        res = m.min_pair()
        assert res is not None
        assert res[2] == pytest.approx(0.60)

    def test_highly_correlated_pairs(self):
        m = self._make(avg_corr=0.80)
        pairs = m.highly_correlated_pairs(threshold=0.70)
        assert len(pairs) == 3  # A-B, A-C, B-C

    def test_inversely_correlated_pairs(self):
        data = {"A": {"A": 1.0, "B": -0.80}, "B": {"A": -0.80, "B": 1.0}}
        m = CorrelationMatrix(
            symbols=["A", "B"], data=data, method=CorrelationMethod.PEARSON,
            window=60, n_observations=30, bar_index=0, timestamp=0.0, confidence=0.9,
        )
        pairs = m.inversely_correlated_pairs(threshold=-0.70)
        assert len(pairs) == 1
        assert pairs[0][2] == pytest.approx(-0.80)

    def test_n_pairs(self):
        m = self._make(syms=("A", "B", "C", "D"))
        assert m.n_pairs() == 6

    def test_to_dict(self):
        m = self._make()
        d = m.to_dict()
        assert "method" in d
        assert "avg_correlation" in d
        assert d["n_pairs"] == 3

    def test_empty_matrix(self):
        m = CorrelationMatrix([], {}, CorrelationMethod.PEARSON, 60, 0, 0, 0.0, 0.0)
        assert m.avg_correlation() == 0.0
        assert m.max_pair() is None


# ── DependencyGraph ───────────────────────────────────────────────────────

class TestDependencyGraph:
    def _make(self) -> DependencyGraph:
        edges = [
            DependencyEdge("A", "B", 1, 0.70, DependencyType.LEADING, 0.8),
            DependencyEdge("A", "C", 2, 0.60, DependencyType.LEADING, 0.7),
            DependencyEdge("B", "D", 1, 0.50, DependencyType.LEADING, 0.6),
        ]
        return DependencyGraph(edges=edges, bar_index=5, timestamp=1.0)

    def test_leading_assets(self):
        g = self._make()
        leaders = g.leading_assets()
        assert "A" in leaders

    def test_lagging_assets(self):
        g = self._make()
        laggers = g.lagging_assets()
        assert "B" in laggers

    def test_get_leaders_of(self):
        g = self._make()
        leaders_of_b = g.get_leaders_of("B")
        assert len(leaders_of_b) == 1
        assert leaders_of_b[0].source == "A"

    def test_get_followers_of(self):
        g = self._make()
        followers_of_a = g.get_followers_of("A")
        assert len(followers_of_a) == 2

    def test_influence_score(self):
        g = self._make()
        score_a = g.influence_score("A")
        score_d = g.influence_score("D")
        assert score_a > score_d

    def test_empty_graph(self):
        g = DependencyGraph([], 0, 0.0)
        assert g.leading_assets() == []
        assert g.lagging_assets() == []
        assert g.influence_score("X") == 0.0


# ── SystemicRiskMetrics ────────────────────────────────────────────────────

class TestSystemicRiskMetrics:
    def test_construction(self):
        m = SystemicRiskMetrics(
            risk_level=RiskLevel.ELEVATED,
            avg_pairwise_correlation=0.65,
            avg_abs_correlation=0.65,
            correlation_concentration=0.70,
            contagion_index=0.60,
            interconnectedness=0.50,
            systemic_risk_score=62.0,
            most_interconnected=["A", "B"],
            n_correlated_clusters=2,
        )
        assert m.risk_level == RiskLevel.ELEVATED
        assert m.systemic_risk_score == 62.0

    def test_to_dict(self):
        m = SystemicRiskMetrics(
            risk_level=RiskLevel.LOW, avg_pairwise_correlation=0.10,
            avg_abs_correlation=0.10, correlation_concentration=0.05,
            contagion_index=0.10, interconnectedness=0.05,
            systemic_risk_score=8.0, most_interconnected=[], n_correlated_clusters=0,
        )
        d = m.to_dict()
        assert "risk_level" in d
        assert d["risk_level"] == "low"


# ── DiversificationMetrics ─────────────────────────────────────────────────

class TestDiversificationMetrics:
    def test_construction(self):
        m = DiversificationMetrics(
            diversification_score=72.0,
            diversification_level=DiversificationLevel.GOOD,
            effective_n_assets=8.5,
            correlation_clusters=[["A", "B"], ["C", "D"]],
            redundant_pairs=[],
            hedging_pairs=[("A", "E", -0.75)],
            portfolio_correlation=0.25,
            cluster_count=2,
        )
        assert m.diversification_score == 72.0
        assert m.cluster_count == 2


# ── CorrelationEvent ──────────────────────────────────────────────────────

class TestCorrelationEvent:
    def test_defaults(self):
        ev = CorrelationEvent(
            event_type=CorrelationEventType.REGIME_CHANGE,
            bar_index=10,
            severity=0.7,
        )
        assert ev.from_regime is None
        assert ev.to_regime is None
        assert ev.affected_assets == []

    def test_with_regime_transition(self):
        ev = CorrelationEvent(
            event_type=CorrelationEventType.REGIME_CHANGE,
            bar_index=10,
            severity=0.5,
            from_regime=CorrelationRegimeType.WEAKLY_CORRELATED,
            to_regime=CorrelationRegimeType.HIGHLY_CORRELATED,
        )
        d = ev.to_dict()
        assert d["from_regime"] == "weakly_correlated"
        assert d["to_regime"] == "highly_correlated"


# ── Enums ─────────────────────────────────────────────────────────────────

class TestEnums:
    def test_asset_class_values(self):
        assert AssetClass.EQUITY.value == "equity"
        assert AssetClass.BOND.value == "bond"
        assert AssetClass.VOLATILITY.value == "volatility"

    def test_correlation_regime_all_exist(self):
        expected = {
            "HIGHLY_CORRELATED", "MODERATELY_CORRELATED", "WEAKLY_CORRELATED",
            "INDEPENDENT", "INVERSE_CORRELATION", "CORRELATION_BREAKDOWN",
            "FLIGHT_TO_SAFETY", "RISK_ON", "RISK_OFF", "UNKNOWN",
        }
        assert {r.name for r in CorrelationRegimeType} == expected

    def test_dependency_type(self):
        assert DependencyType.LEADING.value == "leading"
        assert DependencyType.LAGGING.value == "lagging"
