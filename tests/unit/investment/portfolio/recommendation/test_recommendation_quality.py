"""tests/unit/investment/portfolio/recommendation/test_recommendation_quality.py

Tests for recommendation_validator.py, recommendation_quality.py,
recommendation_health.py, and recommendation_monitor.py.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.recommendation.portfolio_recommendation import (
    build_recommendation, RecommendationCandidate,
)
from iios.investment.portfolio.recommendation.recommendation_health import (
    RecommendationHealthMonitor,
)
from iios.investment.portfolio.recommendation.recommendation_monitor import (
    RecommendationMonitor,
)
from iios.investment.portfolio.recommendation.recommendation_quality import (
    RecommendationQualityAssessor,
)
from iios.investment.portfolio.recommendation.recommendation_tracker import (
    RecommendationTracker,
)
from iios.investment.portfolio.recommendation.recommendation_types import (
    RecommendationAction,
    RecommendationGrade,
    RecommendationLevel,
    RecommendationPriority,
    RecommendationRisk,
    ValidationStatus,
)
from iios.investment.portfolio.recommendation.recommendation_validator import (
    RecommendationValidator,
)


def _make_rec(confidence=0.75, action=RecommendationAction.REBALANCE_PORTFOLIO,
              priority=RecommendationPriority.HIGH, rationale="Test rationale"):
    candidate = RecommendationCandidate(
        action=action, priority=priority, confidence=confidence,
        rationale=rationale, evidence=("e1",), triggered_rule="r",
        risk_level=RecommendationRisk.MEDIUM, tags=(),
    )
    return build_recommendation(
        candidate, portfolio_id="P-T", policy_id="pid",
        policy_name="balanced", intelligence_id="iid-ok",
        score=0.70, expires_at=None, expiry_hours=24.0,
        requires_approval=False, is_time_sensitive=False,
    )


class TestRecommendationValidator:
    def test_valid_recommendation_passes(self, default_intel, default_policy):
        rec = _make_rec(confidence=0.80)
        validator = RecommendationValidator()
        report = validator.validate(rec, default_policy, default_intel)
        assert report.is_valid

    def test_low_confidence_fails(self, default_intel, default_policy):
        rec = _make_rec(confidence=0.05)
        validator = RecommendationValidator()
        report = validator.validate(rec, default_policy, default_intel)
        assert not report.is_valid
        assert report.n_failed >= 1

    def test_missing_rationale_fails(self, default_intel, default_policy):
        rec = _make_rec(confidence=0.80, rationale="")
        validator = RecommendationValidator()
        report = validator.validate(rec, default_policy, default_intel)
        assert not report.is_valid

    def test_empty_portfolio_warns(self, default_policy):
        from iios.investment.portfolio.recommendation.recommendation_types import PortfolioIntelligence
        empty_intel = PortfolioIntelligence(portfolio_id="P-E", n_positions=0)
        rec = _make_rec(confidence=0.80)
        validator = RecommendationValidator()
        report = validator.validate(rec, default_policy, empty_intel)
        # Warns but does not fail (positions = 0 is WARNING not FAIL)
        assert report.n_warnings >= 1

    def test_report_has_checks(self, default_intel, default_policy):
        rec = _make_rec(confidence=0.75)
        validator = RecommendationValidator()
        report = validator.validate(rec, default_policy, default_intel)
        assert len(report.checks) >= 3

    def test_high_priority_no_action_warns(self, default_intel, default_policy):
        rec = _make_rec(
            confidence=0.80,
            action=RecommendationAction.NO_ACTION,
            priority=RecommendationPriority.IMMEDIATE,
        )
        validator = RecommendationValidator()
        report = validator.validate(rec, default_policy, default_intel)
        assert report.n_warnings >= 1


class TestRecommendationQualityAssessor:
    def test_excellent_score(self):
        assessor = RecommendationQualityAssessor()
        report = assessor.assess(
            overall_score=0.90, confidence_score=0.9, evidence_score=0.9,
            urgency_score=0.8, quality_score_dim=0.8,
        )
        assert report.is_acceptable
        assert report.grade == RecommendationGrade.A

    def test_poor_score_not_acceptable(self):
        assessor = RecommendationQualityAssessor()
        report = assessor.assess(
            overall_score=0.20, confidence_score=0.2, evidence_score=0.2,
            urgency_score=0.1, quality_score_dim=0.1,
        )
        assert not report.is_acceptable
        assert report.grade == RecommendationGrade.F

    def test_has_recommendation_text(self):
        assessor = RecommendationQualityAssessor()
        report = assessor.assess(overall_score=0.70)
        assert len(report.recommendation) > 0

    def test_custom_threshold(self):
        assessor = RecommendationQualityAssessor(acceptable_threshold=0.90)
        report = assessor.assess(overall_score=0.80)
        assert not report.is_acceptable

    def test_to_dict(self):
        assessor = RecommendationQualityAssessor()
        report = assessor.assess(overall_score=0.75)
        d = report.to_dict()
        assert "quality_score" in d
        assert "grade" in d
        assert "is_acceptable" in d


class TestRecommendationHealthMonitor:
    def test_initial_report_is_healthy(self):
        monitor = RecommendationHealthMonitor()
        report = monitor.check()
        assert report.is_healthy

    def test_all_successes(self):
        monitor = RecommendationHealthMonitor()
        for _ in range(10):
            monitor.record_run(True, 50.0, 2)
        report = monitor.check(active_portfolios=3)
        assert report.success_rate == 1.0
        assert report.is_healthy
        assert report.active_portfolios == 3

    def test_below_threshold_unhealthy(self):
        monitor = RecommendationHealthMonitor()
        for _ in range(7):
            monitor.record_run(True, 50.0)
        for _ in range(3):
            monitor.record_run(False, 200.0)
        # 70% < 80% — unhealthy
        report = monitor.check()
        assert not report.is_healthy

    def test_total_runs_counted(self):
        monitor = RecommendationHealthMonitor()
        monitor.record_run(True, 100.0)
        monitor.record_run(True, 80.0)
        report = monitor.check()
        assert report.total_runs == 2

    def test_avg_duration(self):
        monitor = RecommendationHealthMonitor()
        monitor.record_run(True, 100.0)
        monitor.record_run(True, 200.0)
        report = monitor.check()
        assert report.avg_duration_ms == 150.0


class TestRecommendationMonitor:
    def test_empty_active_is_healthy(self):
        monitor = RecommendationMonitor()
        report = monitor.check({})
        assert report.is_healthy
        assert report.n_active == 0

    def test_active_non_expired_recs_counted(self):
        from iios.investment.portfolio.recommendation.recommendation_lifecycle import LifecycleManager
        lm = LifecycleManager()
        rec = lm.publish(_make_rec(confidence=0.80))
        monitor = RecommendationMonitor()
        report = monitor.check({"P-T": [rec]})
        assert report.n_active == 1
        assert report.n_portfolios_checked == 1
