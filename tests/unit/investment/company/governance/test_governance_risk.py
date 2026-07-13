"""tests/unit/investment/company/governance/test_governance_risk.py"""
from __future__ import annotations

import pytest

from iios.investment.company.governance.governance_risk import GovernanceRiskEngine
from iios.investment.company.governance.governance_events import classify_events
from iios.investment.company.governance.management_profile import GovernanceRiskProfile, RiskLabel
from iios.investment.company.governance.key_person_risk import score_key_person_risk
from iios.investment.company.governance.succession_analysis import score_succession_quality
from iios.investment.company.governance.governance_alerts import generate_alerts


@pytest.fixture
def engine():
    return GovernanceRiskEngine()


class TestGovernanceRiskEngine:
    def test_returns_profile(self, engine):
        result = engine.compute()
        assert isinstance(result, GovernanceRiskProfile)

    def test_low_risk_profile(self, engine):
        result = engine.compute(
            ceo_tenure_years=8.0,
            cfo_tenure_years=5.0,
            is_founder_led=False,
            executive_team_size=8,
            leadership_changes_3y=0,
            has_nomination_committee=True,
            avg_director_tenure=6.0,
            independence_ratio=0.70,
            ceo_chairman_same=False,
            is_family_controlled=False,
            regulatory_actions=[],
            restatement_count=0,
        )
        assert result.overall_risk_score <= 50.0

    def test_high_risk_profile(self, engine):
        events = classify_events(["accounting_fraud", "regulatory_penalty"])
        result = engine.compute(
            ceo_tenure_years=30.0,
            cfo_tenure_years=1.0,
            is_founder_led=True,
            executive_team_size=2,
            leadership_changes_3y=4,
            has_nomination_committee=False,
            avg_director_tenure=18.0,
            independence_ratio=0.10,
            ceo_chairman_same=True,
            is_family_controlled=True,
            event_log=events,
            regulatory_actions=["sebi_penalty_2022"],
            restatement_count=2,
        )
        assert result.overall_risk_score >= 55.0

    def test_risk_score_in_range(self, engine):
        result = engine.compute()
        assert 0.0 <= result.overall_risk_score <= 100.0

    def test_risk_label_type(self, engine):
        result = engine.compute()
        assert isinstance(result.risk_label, RiskLabel)

    def test_ceo_chairman_same_risk(self, engine):
        r1 = engine.compute(ceo_chairman_same=False)
        r2 = engine.compute(ceo_chairman_same=True)
        assert r2.overall_risk_score >= r1.overall_risk_score

    def test_regulatory_actions_raise_risk(self, engine):
        r_clean = engine.compute(regulatory_actions=[])
        r_penalised = engine.compute(regulatory_actions=["sebi_action_2020"])
        assert r_penalised.overall_risk_score > r_clean.overall_risk_score

    def test_alerts_emitted(self, engine):
        events = classify_events(["accounting_fraud"])
        result = engine.compute(
            event_log=events, ceo_chairman_same=True, restatement_count=2,
        )
        assert len(result.alerts) > 0

    def test_alerts_are_strings(self, engine):
        events = classify_events(["accounting_fraud"])
        result = engine.compute(event_log=events)
        for alert in result.alerts:
            assert isinstance(alert, str)


class TestKeyPersonRisk:
    def test_low_kpr(self):
        s = score_key_person_risk(
            ceo_tenure_years=8.0, is_founder_led=False,
            executive_team_size=8, leadership_changes_3y=0,
        )
        assert s <= 50.0
        assert 0.0 <= s <= 100.0

    def test_high_kpr(self):
        s = score_key_person_risk(
            ceo_tenure_years=30.0, is_founder_led=True,
            executive_team_size=2, leadership_changes_3y=3,
        )
        assert s >= 60.0

    def test_none_inputs(self):
        s = score_key_person_risk()
        assert 0.0 <= s <= 100.0


class TestSuccessionAnalysis:
    def test_good_succession(self):
        s = score_succession_quality(
            has_nomination_committee=True,
            avg_director_tenure=6.0,
            executive_team_size=8,
            leadership_changes_3y=0,
        )
        assert s >= 55.0

    def test_poor_succession(self):
        s = score_succession_quality(
            has_nomination_committee=False,
            avg_director_tenure=20.0,
            executive_team_size=2,
            leadership_changes_3y=4,
        )
        assert s <= 40.0


class TestGovernanceAlerts:
    def test_no_alerts_clean(self):
        alerts = generate_alerts(
            event_log=classify_events([]),
            restatement_count=0,
            regulatory_actions=[],
            ceo_chairman_same=False,
        )
        assert isinstance(alerts, list)

    def test_fraud_alert(self):
        alerts = generate_alerts(
            event_log=classify_events(["accounting_fraud"]),
            restatement_count=0,
            regulatory_actions=[],
        )
        # High-severity event should produce at least one alert
        assert len(alerts) > 0

    def test_restatement_alert(self):
        alerts = generate_alerts(
            event_log=classify_events([]),
            restatement_count=2,
            regulatory_actions=[],
        )
        assert any("restatement" in a.lower() or "restat" in a.lower() for a in alerts)

    def test_combined_alerts(self):
        alerts = generate_alerts(
            event_log=classify_events(["accounting_fraud"]),
            restatement_count=2,
            regulatory_actions=["sebi_action"],
            ceo_chairman_same=True,
        )
        assert len(alerts) >= 2
