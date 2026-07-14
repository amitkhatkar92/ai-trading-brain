"""test_diversification_engine.py — DiversificationAnalyzer + Quality + Score + Metrics"""
import pytest

from iios.investment.portfolio.diversification.diversification_engine import (
    DiversificationAnalyzer,
)
from iios.investment.portfolio.diversification.diversification_quality import (
    DiversificationQualityAssessor,
)
from iios.investment.portfolio.diversification.diversification_score import (
    DiversificationScoreCalculator,
    DiversificationScoreHistory,
)
from iios.investment.portfolio.diversification.diversification_metrics import (
    DiversificationMetrics,
    compute_diversification_metrics,
)
from iios.investment.portfolio.diversification.diversification_types import DiversificationGrade


class TestDiversificationAnalyzer:
    def test_basic_analysis(self, positions_5_diverse):
        a = DiversificationAnalyzer()
        r = a.analyze(positions_5_diverse, "P1", "plan1")
        assert r.n_positions == 5
        assert r.portfolio_id == "P1"

    def test_hhi_range(self, positions_5_diverse):
        a = DiversificationAnalyzer()
        r = a.analyze(positions_5_diverse)
        assert 0.0 < r.hhi <= 1.0

    def test_entropy_ratio_range(self, positions_5_diverse):
        a = DiversificationAnalyzer()
        r = a.analyze(positions_5_diverse)
        assert 0.0 <= r.entropy_ratio <= 1.0 + 1e-4

    def test_equal_weights_max_entropy(self, positions_5_diverse):
        a = DiversificationAnalyzer()
        r = a.analyze(positions_5_diverse)
        assert r.entropy_ratio == pytest.approx(1.0, abs=0.01)

    def test_effective_n(self, positions_5_diverse):
        a = DiversificationAnalyzer()
        r = a.analyze(positions_5_diverse)
        assert r.effective_n == pytest.approx(5.0, abs=0.1)

    def test_concentrated_lower_effective_n(
        self, positions_5_diverse, positions_3_concentrated
    ):
        a = DiversificationAnalyzer()
        r_div  = a.analyze(positions_5_diverse)
        r_conc = a.analyze(positions_3_concentrated)
        assert r_div.effective_n > r_conc.effective_n

    def test_sector_metrics(self, positions_5_diverse):
        a = DiversificationAnalyzer()
        r = a.analyze(positions_5_diverse)
        assert r.n_sectors == 5
        assert r.top_sector_weight == pytest.approx(0.20, abs=0.01)

    def test_diversification_ratio_positive(self, positions_5_diverse):
        a = DiversificationAnalyzer()
        r = a.analyze(positions_5_diverse)
        assert r.diversification_ratio > 0

    def test_concentration_flags(self, positions_3_concentrated):
        a = DiversificationAnalyzer()
        r = a.analyze(positions_3_concentrated)
        assert r.has_concentration_risk or r.has_correlation_risk

    def test_empty_positions(self):
        a = DiversificationAnalyzer()
        r = a.analyze([])
        assert r.n_positions == 0

    def test_single_position(self, positions_single):
        a = DiversificationAnalyzer()
        r = a.analyze(positions_single)
        assert r.n_positions == 1
        assert r.hhi == pytest.approx(1.0, abs=1e-4)


class TestDiversificationQualityAssessor:
    def test_diverse_portfolio_acceptable(self, positions_10_balanced):
        a = DiversificationAnalyzer()
        q = DiversificationQualityAssessor(acceptable_threshold=0.50)
        analysis = a.analyze(positions_10_balanced)
        report   = q.assess(analysis)
        assert report.is_acceptable

    def test_concentrated_portfolio_lower_score(
        self, positions_5_diverse, positions_3_concentrated
    ):
        a  = DiversificationAnalyzer()
        q  = DiversificationQualityAssessor()
        rd = q.assess(a.analyze(positions_5_diverse))
        rc = q.assess(a.analyze(positions_3_concentrated))
        assert rd.overall_score > rc.overall_score

    def test_five_dimensions(self, positions_5_diverse):
        a = DiversificationAnalyzer()
        q = DiversificationQualityAssessor()
        r = q.assess(a.analyze(positions_5_diverse))
        assert len(r.dimension_scores) == 5

    def test_overall_score_in_range(self, positions_5_diverse):
        a = DiversificationAnalyzer()
        q = DiversificationQualityAssessor()
        r = q.assess(a.analyze(positions_5_diverse))
        assert 0.0 <= r.overall_score <= 1.0

    def test_grade_is_enum(self, positions_5_diverse):
        a = DiversificationAnalyzer()
        q = DiversificationQualityAssessor()
        r = q.assess(a.analyze(positions_5_diverse))
        assert r.grade in DiversificationGrade

    def test_empty_analysis(self):
        a = DiversificationAnalyzer()
        q = DiversificationQualityAssessor()
        r = q.assess(a.analyze([]))
        assert r.overall_score >= 0.0


class TestDiversificationScore:
    def _report(self, positions):
        a  = DiversificationAnalyzer()
        q  = DiversificationQualityAssessor()
        return q.assess(a.analyze(positions))

    def test_score_in_range(self, positions_5_diverse):
        sc = DiversificationScoreCalculator()
        s  = sc.calculate(self._report(positions_5_diverse))
        assert 0.0 <= s.overall <= 1.0

    def test_delta_computed(self, positions_5_diverse):
        sc = DiversificationScoreCalculator()
        r  = self._report(positions_5_diverse)
        s1 = sc.calculate(r)
        s2 = sc.calculate(r, previous_score=s1)
        assert s2.delta_overall is not None

    def test_gate_passed_for_good_portfolio(self, positions_10_balanced):
        sc = DiversificationScoreCalculator(governance_gate=0.40)
        s  = sc.calculate(self._report(positions_10_balanced))
        assert s.gate_passed


class TestDiversificationScoreHistory:
    def _score(self, positions):
        a  = DiversificationAnalyzer()
        q  = DiversificationQualityAssessor()
        sc = DiversificationScoreCalculator()
        return sc.calculate(q.assess(a.analyze(positions)))

    def test_records_and_retrieves(self, positions_5_diverse):
        hist  = DiversificationScoreHistory("P1")
        score = self._score(positions_5_diverse)
        hist.record(score)
        assert hist.latest() == score
        assert hist.count() == 1

    def test_bounded(self, positions_5_diverse):
        hist = DiversificationScoreHistory("P1", max_size=3)
        s    = self._score(positions_5_diverse)
        for _ in range(5):
            hist.record(s)
        assert hist.count() == 3

    def test_trend_insufficient_data(self, positions_5_diverse):
        hist = DiversificationScoreHistory("P1")
        hist.record(self._score(positions_5_diverse))
        assert hist.trend() == "insufficient_data"


class TestDiversificationMetrics:
    def test_metrics_from_analysis(self, positions_5_diverse):
        a   = DiversificationAnalyzer()
        q   = DiversificationQualityAssessor()
        sc  = DiversificationScoreCalculator()
        ana = a.analyze(positions_5_diverse)
        score = sc.calculate(q.assess(ana))
        m = compute_diversification_metrics(ana, score)
        assert m.n_positions == 5
        assert m.grade in ("A","B","C","D","F")
        assert isinstance(m.is_acceptable, bool)

    def test_to_dict(self, positions_5_diverse):
        a   = DiversificationAnalyzer()
        ana = a.analyze(positions_5_diverse)
        m   = compute_diversification_metrics(ana)
        d   = m.to_dict()
        assert "n_positions" in d
        assert "hhi" in d
