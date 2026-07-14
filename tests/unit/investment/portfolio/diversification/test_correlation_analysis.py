"""test_correlation_analysis.py"""
import pytest

from iios.investment.portfolio.diversification.correlation_matrix import (
    build_correlation_matrix, diversification_ratio, portfolio_risk_from_matrix,
)
from iios.investment.portfolio.diversification.correlation_analysis import analyze_correlations
from iios.investment.portfolio.diversification.correlation_engine import CorrelationEngine
from iios.investment.portfolio.diversification.dependency_analysis import analyze_dependencies
from iios.investment.portfolio.diversification.relationship_graph import build_relationship_graph
from iios.investment.portfolio.diversification.overlap_analysis import analyze_overlap
from iios.investment.portfolio.diversification.diversification_types import (
    CORR_SAME_INDUSTRY, CORR_SAME_SECTOR, CORR_DIFFERENT, PositionData,
)


class TestCorrelationMatrix:
    def test_same_symbol_is_one(self, positions_5_diverse):
        m = build_correlation_matrix(positions_5_diverse)
        assert m.get("RELIANCE", "RELIANCE") == 1.0

    def test_same_industry_high_corr(self, positions_3_concentrated):
        # TCS and INFY are both in it_services
        m = build_correlation_matrix(positions_3_concentrated)
        assert m.get("TCS", "INFY") == pytest.approx(CORR_SAME_INDUSTRY, abs=1e-6)

    def test_different_sector_low_corr(self, positions_5_diverse):
        m = build_correlation_matrix(positions_5_diverse)
        corr = m.get("RELIANCE", "TCS")
        assert corr <= CORR_SAME_SECTOR

    def test_matrix_symmetric(self, positions_5_diverse):
        m = build_correlation_matrix(positions_5_diverse)
        assert m.get("RELIANCE", "TCS") == m.get("TCS", "RELIANCE")

    def test_n_pairs(self, positions_5_diverse):
        m = build_correlation_matrix(positions_5_diverse)
        # n*(n-1)/2 = 10 pairs for 5 positions
        assert len(m.data) == 10

    def test_avg_off_diagonal_in_range(self, positions_5_diverse):
        m = build_correlation_matrix(positions_5_diverse)
        assert 0.0 <= m.avg_off_diagonal <= 1.0

    def test_empty_positions(self):
        m = build_correlation_matrix([])
        assert m.n == 0


class TestPortfolioRiskAndDR:
    def test_portfolio_risk_positive(self, positions_5_diverse):
        m = build_correlation_matrix(positions_5_diverse)
        risk = portfolio_risk_from_matrix(positions_5_diverse, m)
        assert risk > 0

    def test_dr_at_least_one_for_diverse(self, positions_5_diverse):
        m = build_correlation_matrix(positions_5_diverse)
        dr = diversification_ratio(positions_5_diverse, m)
        assert dr >= 1.0

    def test_dr_higher_for_diversified_vs_concentrated(
        self, positions_5_diverse, positions_3_concentrated
    ):
        md = build_correlation_matrix(positions_5_diverse)
        mc = build_correlation_matrix(positions_3_concentrated)
        dr_div  = diversification_ratio(positions_5_diverse, md)
        dr_conc = diversification_ratio(positions_3_concentrated, mc)
        assert dr_div >= dr_conc - 0.01  # diverse should be at least as good


class TestCorrelationAnalysis:
    def test_high_pairs_in_concentrated(self, positions_3_concentrated):
        m = build_correlation_matrix(positions_3_concentrated)
        r = analyze_correlations(positions_3_concentrated, m)
        assert r.n_high_pairs > 0

    def test_avg_correlation_in_range(self, positions_5_diverse):
        m = build_correlation_matrix(positions_5_diverse)
        r = analyze_correlations(positions_5_diverse, m)
        assert 0.0 <= r.avg_correlation <= 1.0

    def test_dr_in_report(self, positions_5_diverse):
        m = build_correlation_matrix(positions_5_diverse)
        r = analyze_correlations(positions_5_diverse, m)
        assert r.diversification_ratio >= 1.0


class TestDependencyAnalysis:
    def test_sector_clusters_exist(self, positions_5_diverse):
        r = analyze_dependencies(positions_5_diverse)
        assert r.n_sector_clusters == 5

    def test_concentrated_has_large_cluster(self, positions_3_concentrated):
        r = analyze_dependencies(positions_3_concentrated)
        assert r.max_sector_cluster_weight >= 0.85

    def test_systemic_score_in_range(self, positions_5_diverse):
        r = analyze_dependencies(positions_5_diverse)
        assert 0.0 <= r.systemic_exposure_score <= 1.0

    def test_empty_positions(self):
        r = analyze_dependencies([])
        assert r.n_sector_clusters == 0


class TestRelationshipGraph:
    def test_graph_built(self, positions_3_concentrated):
        m = build_correlation_matrix(positions_3_concentrated)
        g = build_relationship_graph(positions_3_concentrated, m, threshold=0.50)
        assert g.n_nodes == 3
        assert g.n_edges > 0

    def test_high_threshold_fewer_edges(self, positions_5_diverse):
        m = build_correlation_matrix(positions_5_diverse)
        g_low  = build_relationship_graph(positions_5_diverse, m, threshold=0.10)
        g_high = build_relationship_graph(positions_5_diverse, m, threshold=0.90)
        assert g_low.n_edges >= g_high.n_edges


class TestOverlapAnalysis:
    def test_same_sector_high_overlap(self, positions_3_concentrated):
        r = analyze_overlap(positions_3_concentrated)
        assert r.sector_overlap > 0.30

    def test_diverse_low_overlap(self, positions_5_diverse):
        r = analyze_overlap(positions_5_diverse)
        assert r.sector_overlap < 0.30

    def test_overlap_risk_label(self, positions_3_concentrated):
        r = analyze_overlap(positions_3_concentrated)
        assert r.overlap_risk in ("low", "moderate", "high")


class TestCorrelationEngine:
    def test_full_report(self, positions_5_diverse):
        e = CorrelationEngine()
        r = e.evaluate(positions_5_diverse, "P1", "plan1")
        assert r.portfolio_id == "P1"
        assert r.analysis.n_pairs == 10

    def test_concentrated_has_extreme_pair_warning(self, positions_3_concentrated):
        # TCS+INFY share industry → extreme pair warning, but avg across 3 pairs is ~0.33
        e = CorrelationEngine()
        r = e.evaluate(positions_3_concentrated)
        # At least one warning about extreme correlation pairs
        assert any("extreme" in w.lower() for w in r.warnings)

    def test_diverse_not_high_corr(self, positions_5_diverse):
        e = CorrelationEngine()
        r = e.evaluate(positions_5_diverse)
        # Diverse positions should have low avg correlation
        assert not r.is_high_correlation

    def test_warnings_for_concentrated(self, positions_3_concentrated):
        e = CorrelationEngine()
        r = e.evaluate(positions_3_concentrated)
        assert len(r.warnings) > 0
