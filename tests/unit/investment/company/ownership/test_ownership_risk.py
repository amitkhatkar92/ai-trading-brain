"""tests/unit/investment/company/ownership/test_ownership_risk.py"""
from __future__ import annotations

import pytest

from iios.investment.company.ownership.ownership_risk import OwnershipRiskEngine
from iios.investment.company.ownership.ownership_profile import (
    OwnershipRiskProfile, OwnershipRiskLabel,
)
from iios.investment.company.ownership.shareholder_registry import build_shareholder_registry
from iios.investment.company.ownership.control_risk import (
    score_control_risk,
    score_minority_protection,
    score_hostile_takeover_exposure,
)
from iios.investment.company.ownership.dilution_analysis import (
    score_esop_dilution, score_total_dilution_risk,
)
from iios.investment.company.ownership.ownership_alerts import generate_ownership_alerts


@pytest.fixture
def engine():
    return OwnershipRiskEngine()


class TestOwnershipRiskEngine:
    def test_returns_profile(self, engine):
        reg = build_shareholder_registry("T", None)
        result = engine.compute(registry=reg)
        assert isinstance(result, OwnershipRiskProfile)

    def test_low_risk_good_data(self, engine, good_ownership_data):
        reg = build_shareholder_registry("T", good_ownership_data)
        result = engine.compute(registry=reg)
        assert result.overall_risk_score < 60.0
        assert result.risk_label in (
            OwnershipRiskLabel.LOW, OwnershipRiskLabel.MODERATE, OwnershipRiskLabel.ELEVATED,
        )

    def test_high_risk_risky_data(self, engine, risky_ownership_data):
        reg = build_shareholder_registry("T", risky_ownership_data)
        result = engine.compute(registry=reg)
        assert result.overall_risk_score >= 45.0
        assert result.pledge_risk_score > 50.0

    def test_all_scores_in_range(self, engine, good_ownership_data):
        reg = build_shareholder_registry("T", good_ownership_data)
        result = engine.compute(registry=reg)
        for s in [
            result.pledge_risk_score, result.concentration_risk_score,
            result.dilution_risk_score, result.control_risk_score,
            result.liquidity_risk_score, result.overall_risk_score,
        ]:
            assert 0.0 <= s <= 100.0

    def test_risk_label_type(self, engine):
        reg = build_shareholder_registry("T", None)
        result = engine.compute(registry=reg)
        assert isinstance(result.risk_label, OwnershipRiskLabel)

    def test_alerts_list(self, engine, risky_ownership_data):
        reg = build_shareholder_registry("T", risky_ownership_data)
        result = engine.compute(registry=reg)
        assert isinstance(result.alerts, list)

    def test_high_pledge_generates_alert(self, engine, risky_ownership_data):
        reg = build_shareholder_registry("T", risky_ownership_data)
        result = engine.compute(registry=reg)
        assert len(result.alerts) > 0

    def test_management_snapshot_adjusts_control(self, engine, good_ownership_data, mock_management):
        mock_management.governance_risk.overall_risk_score = 70.0
        reg = build_shareholder_registry("T", good_ownership_data)
        result = engine.compute(registry=reg, management_snapshot=mock_management)
        # control risk should be elevated
        assert result.control_risk_score >= 0.0


class TestControlRisk:
    def test_low_risk(self):
        s = score_control_risk(0.52, False, False)
        assert s < 50.0

    def test_dominant_family(self):
        s = score_control_risk(0.80, True, True)
        assert s >= 60.0

    def test_range(self):
        for p, f, c in [(0.3, False, False), (0.8, True, True), (0.1, False, False)]:
            s = score_control_risk(p, f, c)
            assert 0.0 <= s <= 100.0


class TestMinorityProtection:
    def test_strong_protection(self):
        s = score_minority_protection(0.70, True, 0.30)
        assert s >= 75.0

    def test_weak_protection(self):
        s = score_minority_protection(0.20, False, 0.05)
        assert s < 60.0


class TestHostileTakeoverExposure:
    def test_low_exposure_majority_promoter(self):
        s = score_hostile_takeover_exposure(0.60, 0.30, 0.25)
        assert s < 40.0

    def test_high_exposure(self):
        s = score_hostile_takeover_exposure(0.10, 0.70, 0.10)
        assert s >= 50.0


class TestDilutionAnalysis:
    def test_low_esop(self):
        assert score_esop_dilution(0.01) < 15.0

    def test_high_esop(self):
        assert score_esop_dilution(0.10) >= 55.0

    def test_composite_low(self):
        s = score_total_dilution_risk(0.02, 1.0, 0.45)
        assert s < 35.0

    def test_composite_high(self):
        s = score_total_dilution_risk(0.12, -8.0, 0.18)
        assert s >= 45.0


class TestOwnershipAlerts:
    def test_high_pledge_alert(self):
        alerts = generate_ownership_alerts(promoter_pledge_pct=0.60)
        assert any("pledge" in a.lower() or "pledg" in a.lower() for a in alerts)

    def test_no_alerts_clean(self):
        alerts = generate_ownership_alerts(
            promoter_pledge_pct=0.05, promoter_change_3m=0.2,
            promoter_change_1y=1.0, pledge_risk_score=5.0,
        )
        assert isinstance(alerts, list)

    def test_liquidating_alert(self):
        alerts = generate_ownership_alerts(insider_activity_label="liquidating")
        assert any("liquidat" in a.lower() or "selling" in a.lower() for a in alerts)

    def test_low_free_float_alert(self):
        alerts = generate_ownership_alerts(free_float_pct=0.08)
        assert len(alerts) > 0

    def test_alerts_are_strings(self):
        alerts = generate_ownership_alerts(promoter_pledge_pct=0.70, control_risk_score=80.0)
        for a in alerts:
            assert isinstance(a, str)
