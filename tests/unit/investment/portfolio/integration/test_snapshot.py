"""tests/unit/investment/portfolio/integration/test_snapshot.py

Tests for portfolio_snapshot.py, portfolio_summary.py,
portfolio_quality.py, portfolio_confidence.py.
"""
from __future__ import annotations

import dataclasses
import pytest

from iios.investment.portfolio.integration.portfolio_confidence import (
    PortfolioConfidenceCalculator,
)
from iios.investment.portfolio.integration.portfolio_quality import (
    PortfolioQualityAssessor,
)
from iios.investment.portfolio.integration.portfolio_snapshot import (
    PortfolioIntelligenceSnapshot,
)
from iios.investment.portfolio.integration.portfolio_summary import (
    PortfolioState, PortfolioSummary, build_state, build_summary,
)
from iios.investment.portfolio.integration.integration_types import (
    AggregationStatus, EngineId, QualityGrade, REQUIRED_ENGINES, SnapshotStatus,
)


def _make_snap(**kw) -> PortfolioIntelligenceSnapshot:
    defaults = dict(
        portfolio_id             = "P-T",
        status                   = SnapshotStatus.VALIDATED,
        aggregation_status       = AggregationStatus.COMPLETE,
        n_engines_contributed    = 9,
        completeness             = 1.0,
        freshness_score          = 1.0,
        construction_quality     = 0.80,
        equity_weight            = 0.60,
        bond_weight              = 0.25,
        cash_weight              = 0.10,
        alternative_weight       = 0.05,
        hhi                      = 0.06,
        effective_positions      = 16.0,
        risk_budget_utilization  = 0.55,
        is_risk_within_budget    = True,
        max_drawdown             = 0.08,
        sharpe_ratio             = 0.90,
        optimization_quality     = 0.78,
        rebalance_recommended    = False,
        primary_action           = "no_action",
        quality_score            = 0.82,
        quality_grade            = QualityGrade.B,
        consistency_score        = 0.90,
        confidence_score         = 0.85,
        n_conflicts              = 0,
        n_unresolved_conflicts   = 0,
        is_consistent            = True,
        is_ready                 = True,
    )
    defaults.update(kw)
    return PortfolioIntelligenceSnapshot(**defaults)


class TestPortfolioIntelligenceSnapshot:
    def test_default_snapshot(self):
        snap = PortfolioIntelligenceSnapshot(portfolio_id="P-1")
        assert snap.portfolio_id == "P-1"
        assert snap.status == SnapshotStatus.DRAFT

    def test_frozen(self):
        snap = _make_snap()
        with pytest.raises((AttributeError, TypeError)):
            snap.quality_score = 0.0  # type: ignore

    def test_to_dict_keys(self):
        snap = _make_snap()
        d    = snap.to_dict()
        assert "snapshot_id" in d
        assert "quality_score" in d
        assert "is_ready" in d
        assert "primary_action" in d

    def test_replace_with_published(self):
        snap      = _make_snap()
        published = dataclasses.replace(snap, status=SnapshotStatus.PUBLISHED)
        assert published.status == SnapshotStatus.PUBLISHED
        assert snap.status == SnapshotStatus.VALIDATED  # original unchanged

    def test_snapshot_id_uuid(self):
        snap = _make_snap()
        assert len(snap.snapshot_id) == 36


class TestBuildState:
    def test_healthy_state(self):
        snap  = _make_snap()
        state = build_state(snap)
        assert state.is_risk_within_budget
        assert state.is_construction_sound
        assert state.is_optimized
        assert state.is_ready
        assert not state.is_rebalance_needed
        assert not state.has_active_recommendation

    def test_diversified_state(self):
        snap  = _make_snap(hhi=0.06, effective_positions=16.0)
        state = build_state(snap)
        assert state.is_diversified

    def test_concentrated_not_diversified(self):
        snap  = _make_snap(hhi=0.40, effective_positions=4.0)
        state = build_state(snap)
        assert not state.is_diversified

    def test_rebalance_needed_flag(self):
        snap  = _make_snap(rebalance_recommended=True)
        state = build_state(snap)
        assert state.is_rebalance_needed

    def test_active_recommendation_flag(self):
        snap  = _make_snap(primary_action="rebalance_portfolio")
        state = build_state(snap)
        assert state.has_active_recommendation

    def test_to_dict(self):
        snap  = _make_snap()
        state = build_state(snap)
        d     = state.to_dict()
        assert "is_ready" in d
        assert "health_status" in d


class TestBuildSummary:
    def test_ready_headline(self):
        snap    = _make_snap()
        summary = build_summary(snap)
        assert "ready" in summary.headline.lower()

    def test_not_ready_headline(self):
        snap    = _make_snap(completeness=0.30, is_ready=False)
        summary = build_summary(snap)
        assert "not ready" in summary.headline.lower()

    def test_high_quality_narrative(self):
        snap    = _make_snap(quality_score=0.90)
        summary = build_summary(snap)
        assert "high" in summary.quality_narrative.lower()

    def test_risk_near_limit_warning(self):
        snap    = _make_snap(risk_budget_utilization=0.95)
        summary = build_summary(snap)
        assert len(summary.warnings) >= 1

    def test_conflict_warning(self):
        snap    = _make_snap(n_unresolved_conflicts=2)
        summary = build_summary(snap)
        warns   = " ".join(summary.warnings)
        assert "conflict" in warns.lower()

    def test_to_dict(self):
        snap    = _make_snap()
        summary = build_summary(snap)
        d       = summary.to_dict()
        assert "headline" in d
        assert "warnings" in d


class TestPortfolioQualityAssessor:
    def test_all_perfect_scores(self):
        assessor = PortfolioQualityAssessor()
        report   = assessor.assess(1.0, 1.0, 1.0, 1.0, 1.0)
        assert report.overall_score == 1.0
        assert report.grade == QualityGrade.A
        assert report.is_publishable

    def test_all_zero_scores(self):
        assessor = PortfolioQualityAssessor()
        report   = assessor.assess(0.0, 0.0, 0.0, 0.0, 0.0)
        assert report.overall_score == 0.0
        assert report.grade == QualityGrade.F
        assert not report.is_publishable

    def test_partial_scores_publishable(self):
        assessor = PortfolioQualityAssessor()
        report   = assessor.assess(0.80, 0.85, 0.90, 0.80, 0.80)
        assert report.is_publishable

    def test_primary_weakness_identified(self):
        assessor = PortfolioQualityAssessor()
        report   = assessor.assess(0.90, 0.90, 0.10, 0.90, 0.90)
        assert report.primary_weakness == "freshness"

    def test_warns_low_completeness(self):
        assessor = PortfolioQualityAssessor()
        report   = assessor.assess(0.50, 0.90, 0.90, 0.90, 0.90)
        assert any("completeness" in w.lower() for w in report.warnings)

    def test_to_dict(self):
        assessor = PortfolioQualityAssessor()
        report   = assessor.assess(0.80, 0.85, 0.90, 0.80, 0.80)
        d        = report.to_dict()
        assert "overall_score" in d
        assert "grade" in d
        assert "is_publishable" in d


class TestPortfolioConfidenceCalculator:
    def test_full_engines_no_conflicts(self):
        calc   = PortfolioConfidenceCalculator()
        score  = calc.calculate(list(REQUIRED_ENGINES), 1.0, 0)
        assert score.penalized_score > 0.80

    def test_partial_engines_lower_confidence(self):
        calc  = PortfolioConfidenceCalculator()
        half  = list(REQUIRED_ENGINES)[:5]
        score = calc.calculate(half, 0.55, 0)
        assert score.penalized_score < 1.0

    def test_unresolved_conflicts_penalize(self):
        calc   = PortfolioConfidenceCalculator()
        full   = calc.calculate(list(REQUIRED_ENGINES), 1.0, 0)
        penalized = calc.calculate(list(REQUIRED_ENGINES), 1.0, 5)
        assert penalized.penalized_score < full.penalized_score

    def test_penalty_floor_zero(self):
        calc  = PortfolioConfidenceCalculator()
        score = calc.calculate([], 0.0, 100)
        assert score.penalized_score >= 0.0

    def test_to_dict(self):
        calc  = PortfolioConfidenceCalculator()
        score = calc.calculate(list(REQUIRED_ENGINES), 0.80, 0)
        d     = score.to_dict()
        assert "penalized_score" in d
        assert "completeness" in d
