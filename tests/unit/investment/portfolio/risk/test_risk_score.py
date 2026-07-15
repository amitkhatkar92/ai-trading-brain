"""tests/unit/investment/portfolio/risk/test_risk_score.py"""
import pytest
from iios.investment.portfolio.risk.portfolio_risk_score import (
    RiskScore, RiskDimensionScore, RiskScoreCalculator, RiskScoreHistory,
)
from iios.investment.portfolio.risk.risk_health import RiskHealthMonitor, RiskHealthReport
from iios.investment.portfolio.risk.risk_quality import RiskQualityAssessor, RiskQualityReport
from iios.investment.portfolio.risk.risk_confidence import compute_risk_confidence
from iios.investment.portfolio.risk.risk_types import RiskGrade, RiskLevel


# ── RiskScoreCalculator ───────────────────────────────────────────────────

def test_calculator_creates_score():
    calc = RiskScoreCalculator()
    s = calc.calculate(0.4, 0.3, 0.2, 0.5, 0.4, 0.1, 0.1)
    assert isinstance(s, RiskScore)


def test_calculator_overall_in_range():
    calc = RiskScoreCalculator()
    s = calc.calculate(0.4, 0.3, 0.2, 0.5, 0.4, 0.1, 0.1)
    assert 0.0 <= s.overall <= 1.0


def test_calculator_weights_sum():
    calc = RiskScoreCalculator()
    s = calc.calculate(0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
    assert abs(s.overall - 0.5) < 1e-6


def test_calculator_grade_valid():
    calc = RiskScoreCalculator()
    s = calc.calculate(0.4, 0.3, 0.2, 0.5, 0.4, 0.1, 0.1)
    assert s.grade in list(RiskGrade)


def test_calculator_risk_level_valid():
    calc = RiskScoreCalculator()
    s = calc.calculate(0.4, 0.3, 0.2, 0.5, 0.4, 0.1, 0.1)
    assert s.risk_level in list(RiskLevel)


def test_calculator_is_acceptable_high_risk():
    calc = RiskScoreCalculator(quality_gate=0.55)
    s = calc.calculate(0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9)
    assert s.is_acceptable is False


def test_calculator_is_acceptable_low_risk():
    calc = RiskScoreCalculator(quality_gate=0.55)
    s = calc.calculate(0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
    assert s.is_acceptable is True


def test_calculator_delta_overall():
    calc = RiskScoreCalculator()
    s1 = calc.calculate(0.4, 0.3, 0.2, 0.5, 0.4, 0.1, 0.1)
    s2 = calc.calculate(0.6, 0.5, 0.3, 0.6, 0.5, 0.2, 0.2, previous_overall=s1.overall)
    assert abs(s2.delta_overall - (s2.overall - s1.overall)) < 1e-6


def test_calculator_dimension_scores_count():
    calc = RiskScoreCalculator()
    s = calc.calculate(0.4, 0.3, 0.2, 0.5, 0.4, 0.1, 0.1)
    assert len(s.dimension_scores) == 7


def test_score_to_dict():
    calc = RiskScoreCalculator()
    d = calc.calculate(0.4, 0.3, 0.2, 0.5, 0.4, 0.1, 0.1).to_dict()
    assert "overall" in d
    assert "grade" in d


# ── RiskScoreHistory ─────────────────────────────────────────────────────

def test_score_history_empty():
    h = RiskScoreHistory("p1")
    assert h.latest() is None


def test_score_history_record_and_retrieve():
    calc = RiskScoreCalculator()
    s = calc.calculate(0.4, 0.3, 0.2, 0.5, 0.4, 0.1, 0.1)
    h = RiskScoreHistory("p1")
    h.record(s)
    assert h.latest() is s


def test_score_history_bounded():
    calc = RiskScoreCalculator()
    h = RiskScoreHistory("p1", max_size=3)
    for _ in range(5):
        h.record(calc.calculate(0.4, 0.3, 0.2, 0.5, 0.4, 0.1, 0.1))
    assert len(h.all()) == 3


# ── RiskHealthMonitor ─────────────────────────────────────────────────────

def test_health_initial():
    m = RiskHealthMonitor()
    r = m.check(active_portfolios=0)
    assert r.is_healthy is True
    assert r.total_runs == 0


def test_health_record_success():
    m = RiskHealthMonitor()
    m.record_run(succeeded=True, duration_ms=100.0)
    r = m.check()
    assert r.total_runs == 1
    assert r.success_rate == 1.0


def test_health_record_failure():
    m = RiskHealthMonitor()
    for _ in range(10):
        m.record_run(succeeded=False, duration_ms=50.0)
    r = m.check()
    assert r.is_healthy is False


def test_health_to_dict():
    m = RiskHealthMonitor()
    d = m.check().to_dict()
    assert "is_healthy" in d
    assert "success_rate" in d


# ── RiskQualityAssessor ───────────────────────────────────────────────────

def test_quality_assessor_acceptable():
    calc = RiskScoreCalculator(quality_gate=0.55)
    s = calc.calculate(0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
    assessor = RiskQualityAssessor(acceptable_threshold=0.55)
    r = assessor.assess(s)
    assert isinstance(r, RiskQualityReport)
    assert r.is_acceptable is True


def test_quality_assessor_not_acceptable():
    calc = RiskScoreCalculator(quality_gate=0.55)
    s = calc.calculate(0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9)
    assessor = RiskQualityAssessor(acceptable_threshold=0.55)
    r = assessor.assess(s)
    assert r.is_acceptable is False


def test_quality_assessor_primary_driver():
    calc = RiskScoreCalculator()
    s = calc.calculate(0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1)  # market is highest
    assessor = RiskQualityAssessor()
    r = assessor.assess(s)
    assert r.primary_risk_driver == "market"


def test_quality_to_dict():
    calc = RiskScoreCalculator()
    s = calc.calculate(0.4, 0.3, 0.2, 0.5, 0.4, 0.1, 0.1)
    d = RiskQualityAssessor().assess(s).to_dict()
    assert "is_acceptable" in d


# ── Risk Confidence ───────────────────────────────────────────────────────

def test_confidence_empty():
    r = compute_risk_confidence([])
    assert r.insufficient_data is True


def test_confidence_positive(positions_5_diverse):
    r = compute_risk_confidence(positions_5_diverse)
    assert 0.0 <= r.confidence_score <= 1.0


def test_confidence_level_valid(positions_5_diverse):
    r = compute_risk_confidence(positions_5_diverse)
    assert r.confidence_level in ("low", "moderate", "high", "very_high")


def test_confidence_no_sector_metadata():
    from iios.investment.portfolio.risk.risk_types import RiskPosition
    no_sector = [
        RiskPosition(
            symbol="X", weight=0.5, sector="unknown", industry="unknown",
            asset_class="equity", country="IN", currency="INR",
            risk_score=0.5, conviction=0.5, confidence=0.5,
            liquidity=0.8, credit_quality=0.7,
        ),
        RiskPosition(
            symbol="Y", weight=0.5, sector="unknown", industry="unknown",
            asset_class="equity", country="IN", currency="INR",
            risk_score=0.5, conviction=0.5, confidence=0.5,
            liquidity=0.8, credit_quality=0.7,
        ),
    ]
    r = compute_risk_confidence(no_sector)
    assert "many_positions_missing_sector_metadata" in r.model_limitations


def test_confidence_to_dict(positions_5_diverse):
    d = compute_risk_confidence(positions_5_diverse).to_dict()
    assert "confidence_score" in d
    assert "confidence_level" in d
