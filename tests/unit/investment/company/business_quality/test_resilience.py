"""tests/unit/investment/company/business_quality/test_resilience.py"""
import pytest

from iios.investment.company.business_quality.cyclicality import CyclicalityDetector
from iios.investment.company.business_quality.business_risk import BusinessRiskAnalyzer
from iios.investment.company.business_quality.stress_resilience import StressResilienceAnalyzer
from iios.investment.company.business_quality.resilience_engine import ResilienceEngine
from iios.investment.company.business_quality.business_resilience import CyclicalityLabel
from tests.unit.investment.company.business_quality.conftest import make_ctx


def make_cyclical_ctx():
    from tests.unit.investment.company.business_quality.conftest import (
        make_financial_snapshot, make_earnings_snapshot,
    )
    from iios.investment.company.business_quality.assessment_context import AssessmentContext
    fs = make_financial_snapshot(gross_margin=12.0)
    es = make_earnings_snapshot(
        revenue_volatility=0.6, margin_volatility=5.0, is_cyclical=True, loss_rate=0.2,
    )
    return AssessmentContext(ticker="CYCL", financial_snapshot=fs, earnings_snapshot=es)


class TestCyclicalityDetector:
    def test_defensive_business_low_score(self, ctx_high_quality):
        p = CyclicalityDetector().analyze(ctx_high_quality)
        assert p.cyclicality_score < 70.0

    def test_cyclical_business_high_score(self):
        ctx = make_cyclical_ctx()
        p = CyclicalityDetector().analyze(ctx)
        assert p.cyclicality_score > 40.0

    def test_label_classified(self, ctx_high_quality):
        p = CyclicalityDetector().analyze(ctx_high_quality)
        assert isinstance(p.label, CyclicalityLabel)

    def test_thin_margin_adds_flag(self, ctx_commodity):
        p = CyclicalityDetector().analyze(ctx_commodity)
        assert "thin_margins_cyclical_risk" in p.flags

    def test_score_in_range(self, ctx_high_quality):
        p = CyclicalityDetector().analyze(ctx_high_quality)
        assert 0.0 <= p.cyclicality_score <= 100.0

    def test_minimal_context_no_crash(self, ctx_minimal):
        p = CyclicalityDetector().analyze(ctx_minimal)
        assert isinstance(p.label, CyclicalityLabel)

    def test_to_dict_keys(self, ctx_high_quality):
        d = CyclicalityDetector().analyze(ctx_high_quality).to_dict()
        assert "label" in d
        assert "cyclicality_score" in d


class TestBusinessRiskAnalyzer:
    def test_debt_to_equity_populated(self, ctx_high_quality):
        p = BusinessRiskAnalyzer().analyze(ctx_high_quality)
        assert p.debt_to_equity is not None

    def test_high_leverage_flagged(self, ctx_asset_heavy):
        p = BusinessRiskAnalyzer().analyze(ctx_asset_heavy)
        assert p.is_over_leveraged is True
        assert any("leverage" in f for f in p.flags)

    def test_good_leverage_not_flagged(self, ctx_high_quality):
        p = BusinessRiskAnalyzer().analyze(ctx_high_quality)
        assert p.is_over_leveraged is False

    def test_financial_risk_score_range(self, ctx_high_quality):
        p = BusinessRiskAnalyzer().analyze(ctx_high_quality)
        assert 0.0 <= p.financial_risk_score <= 100.0

    def test_high_risk_for_heavy_leverage(self, ctx_asset_heavy):
        p = BusinessRiskAnalyzer().analyze(ctx_asset_heavy)
        assert p.financial_risk_score > 40.0

    def test_earnings_quality_from_snapshot(self, ctx_high_quality):
        p = BusinessRiskAnalyzer().analyze(ctx_high_quality)
        assert p.earnings_quality_score > 0.0

    def test_minimal_context_no_crash(self, ctx_minimal):
        p = BusinessRiskAnalyzer().analyze(ctx_minimal)
        assert 0.0 <= p.financial_risk_score <= 100.0

    def test_to_dict_keys(self, ctx_high_quality):
        d = BusinessRiskAnalyzer().analyze(ctx_high_quality).to_dict()
        assert "financial_risk_score" in d
        assert "debt_to_equity" in d


class TestStressResilienceAnalyzer:
    def test_strong_fcf_high_resilience(self, ctx_high_quality):
        p = StressResilienceAnalyzer().analyze(ctx_high_quality)
        assert p.stress_resilience_score > 50.0
        assert p.is_stress_resilient is True

    def test_negative_fcf_low_resilience(self):
        ctx = make_ctx(fcf_margin=-8.0)
        p = StressResilienceAnalyzer().analyze(ctx)
        assert p.stress_resilience_score < 50.0

    def test_score_in_range(self, ctx_high_quality):
        p = StressResilienceAnalyzer().analyze(ctx_high_quality)
        assert 0.0 <= p.stress_resilience_score <= 100.0

    def test_fcf_negative_flag(self):
        ctx = make_ctx(fcf_margin=-5.0)
        p = StressResilienceAnalyzer().analyze(ctx)
        assert "fcf_negative" in p.flags

    def test_to_dict_keys(self, ctx_high_quality):
        d = StressResilienceAnalyzer().analyze(ctx_high_quality).to_dict()
        assert "stress_resilience_score" in d
        assert "is_stress_resilient" in d


class TestResilienceEngine:
    def test_returns_profile(self, ctx_high_quality):
        p = ResilienceEngine().analyze(ctx_high_quality)
        assert p.cyclicality is not None
        assert p.business_risk is not None
        assert p.stress_resilience is not None

    def test_score_in_range(self, ctx_high_quality):
        p = ResilienceEngine().analyze(ctx_high_quality)
        assert 0.0 <= p.resilience_score <= 100.0

    def test_resilient_high_quality(self, ctx_high_quality):
        p = ResilienceEngine().analyze(ctx_high_quality)
        assert p.resilience_score > 40.0

    def test_higher_resilience_for_quality(self, ctx_high_quality, ctx_commodity):
        e = ResilienceEngine()
        hq = e.analyze(ctx_high_quality).resilience_score
        cm = e.analyze(ctx_commodity).resilience_score
        assert hq > cm

    def test_pricing_power_set(self, ctx_high_quality):
        from iios.investment.company.business_quality.business_resilience import PricingPowerLabel
        p = ResilienceEngine().analyze(ctx_high_quality)
        assert isinstance(p.pricing_power, PricingPowerLabel)

    def test_pricing_power_strong_for_high_gm(self, ctx_high_quality):
        from iios.investment.company.business_quality.business_resilience import PricingPowerLabel
        p = ResilienceEngine().analyze(ctx_high_quality)
        assert p.pricing_power in [PricingPowerLabel.STRONG, PricingPowerLabel.MODERATE]

    def test_to_dict_keys(self, ctx_high_quality):
        d = ResilienceEngine().analyze(ctx_high_quality).to_dict()
        assert "resilience_score" in d
        assert "pricing_power" in d
        assert "cyclicality" in d
