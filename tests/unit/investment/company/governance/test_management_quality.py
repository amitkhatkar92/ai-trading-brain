"""tests/unit/investment/company/governance/test_management_quality.py"""
from __future__ import annotations

import pytest

from iios.investment.company.governance.management_quality import ManagementQualityEngine
from iios.investment.company.governance.management_profile import (
    ManagementQualityProfile, LeadershipStability,
)


@pytest.fixture
def engine():
    return ManagementQualityEngine()


class TestManagementQualityEngine:
    def test_returns_profile(self, engine):
        result = engine.compute()
        assert isinstance(result, ManagementQualityProfile)

    def test_high_quality(self, engine):
        result = engine.compute(
            ceo_tenure_years=8.0,
            leadership_changes_3y=0,
            earnings_stability_score=80.0,
            consistency_score=82.0,
            operational_quality_score=75.0,
            avg_roic=0.20,
            moat_score=70.0,
            earnings_quality_score=80.0,
            avg_ocf_to_ni=1.10,
            restatement_count=0,
            governance_incidents=0,
        )
        assert result.overall_quality_score >= 60.0
        assert result.quality_label in ("exceptional", "strong", "adequate")
        assert result.stability in (LeadershipStability.STABLE, LeadershipStability.MODERATELY_STABLE)

    def test_poor_quality(self, engine):
        result = engine.compute(
            ceo_tenure_years=0.5,
            leadership_changes_3y=4,
            earnings_stability_score=20.0,
            consistency_score=15.0,
            avg_roic=0.02,
            earnings_quality_score=20.0,
            avg_ocf_to_ni=0.5,
            restatement_count=2,
            governance_incidents=2,
        )
        assert result.overall_quality_score < 50.0
        assert result.stability == LeadershipStability.UNSTABLE

    def test_founder_premium(self, engine):
        s_non_founder = engine.compute(avg_roic=0.20, is_founder_led=False)
        s_founder     = engine.compute(avg_roic=0.20, is_founder_led=True)
        assert s_founder.long_term_orientation_score >= s_non_founder.long_term_orientation_score

    def test_restatement_penalty(self, engine):
        s_clean      = engine.compute(restatement_count=0)
        s_restatement = engine.compute(restatement_count=2)
        assert s_clean.management_credibility_score > s_restatement.management_credibility_score

    def test_score_ranges(self, engine):
        result = engine.compute(
            ceo_tenure_years=6.0, avg_roic=0.15, consistency_score=70.0,
        )
        for score in [
            result.leadership_stability_score, result.execution_quality_score,
            result.strategic_consistency_score, result.long_term_orientation_score,
            result.management_credibility_score, result.overall_quality_score,
        ]:
            assert 0.0 <= score <= 100.0

    def test_explanation_populated(self, engine):
        result = engine.compute(ceo_tenure_years=8.0, avg_roic=0.18)
        assert len(result.explanation) > 0

    def test_stability_classification(self, engine):
        # Many leadership changes → unstable
        result = engine.compute(leadership_changes_3y=3)
        assert result.stability == LeadershipStability.UNSTABLE

        # Stable tenure → stable
        result = engine.compute(ceo_tenure_years=8.0, leadership_changes_3y=0)
        assert result.stability in (LeadershipStability.STABLE, LeadershipStability.MODERATELY_STABLE)
