"""tests/unit/investment/company/governance/test_transparency.py"""
from __future__ import annotations

import pytest

from iios.investment.company.governance.transparency_engine import TransparencyEngine
from iios.investment.company.governance.governance_events import classify_events
from iios.investment.company.governance.management_profile import (
    TransparencyProfile, TransparencyLabel,
)


@pytest.fixture
def engine():
    return TransparencyEngine()


class TestTransparencyEngine:
    def test_returns_profile(self, engine):
        result = engine.compute()
        assert isinstance(result, TransparencyProfile)

    def test_high_transparency(self, engine):
        result = engine.compute(
            earnings_quality_score=82.0,
            consistency_score=80.0,
            avg_accruals_ratio=0.03,
            avg_ocf_to_ni=1.12,
            restatement_count=0,
            regulatory_actions=[],
        )
        assert result.overall_transparency_score >= 60.0

    def test_low_transparency(self, engine):
        events = classify_events(["accounting_fraud", "regulatory_penalty"])
        result = engine.compute(
            earnings_quality_score=25.0,
            consistency_score=20.0,
            avg_accruals_ratio=0.25,
            avg_ocf_to_ni=0.5,
            restatement_count=3,
            event_log=events,
            regulatory_actions=["sebi_action_2020", "sebi_action_2021"],
        )
        assert result.overall_transparency_score < 45.0

    def test_restatement_penalty(self, engine):
        clean    = engine.compute(restatement_count=0)
        restate2 = engine.compute(restatement_count=2)
        assert clean.overall_transparency_score > restate2.overall_transparency_score

    def test_accruals_impact(self, engine):
        clean    = engine.compute(avg_accruals_ratio=0.02)
        high_acc = engine.compute(avg_accruals_ratio=0.30)
        assert clean.accounting_integrity_score > high_acc.accounting_integrity_score

    def test_all_scores_in_range(self, engine):
        result = engine.compute(earnings_quality_score=70.0, avg_ocf_to_ni=1.0)
        for score in [
            result.disclosure_quality_score, result.reporting_transparency_score,
            result.compliance_score, result.accounting_integrity_score,
            result.overall_transparency_score,
        ]:
            assert 0.0 <= score <= 100.0

    def test_label_type(self, engine):
        result = engine.compute()
        assert isinstance(result.transparency_label, TransparencyLabel)

    def test_governance_standard_sebi(self, engine):
        result = engine.compute(governance_standard="sebi", restatement_count=0)
        assert isinstance(result, TransparencyProfile)

    def test_event_log_impact(self, engine):
        events_bad = classify_events(["accounting_irregularity", "regulatory_inquiry"])
        result_bad = engine.compute(event_log=events_bad)
        result_clean = engine.compute()
        assert result_clean.overall_transparency_score >= result_bad.overall_transparency_score
