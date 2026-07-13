"""tests/unit/investment/company/growth/test_growth_sustainability.py"""
from __future__ import annotations

import pytest

from iios.investment.company.growth.growth_sustainability import GrowthSustainabilityEngine
from iios.investment.company.growth.growth_consistency import compute_consistency_score
from iios.investment.company.growth.growth_resilience import compute_resilience_score
from iios.investment.company.growth.growth_risk import assess_growth_risk
from iios.investment.company.growth.growth_profile import GrowthSustainabilityProfile


@pytest.fixture
def engine():
    return GrowthSustainabilityEngine()


# ── Consistency ────────────────────────────────────────────────────────────────

class TestGrowthConsistency:
    def test_high_quality_data(self):
        score = compute_consistency_score(
            eps_volatility=0.10,
            revenue_volatility=0.08,
            margin_volatility=0.05,
            consistency_score=85.0,
            loss_rate=0.0,
            history_depth=10,
        )
        assert score > 70.0

    def test_low_quality_data(self):
        score = compute_consistency_score(
            eps_volatility=1.5,
            revenue_volatility=1.0,
            margin_volatility=0.8,
            consistency_score=None,
            loss_rate=0.30,
            history_depth=2,
        )
        assert score < 40.0

    def test_score_in_range(self):
        for cv in [0.0, 0.3, 0.6, 1.2, 2.0]:
            s = compute_consistency_score(eps_volatility=cv)
            assert 0.0 <= s <= 100.0

    def test_thin_history_penalty(self):
        s_thick = compute_consistency_score(history_depth=10, consistency_score=70.0)
        s_thin  = compute_consistency_score(history_depth=1, consistency_score=70.0)
        assert s_thick > s_thin


# ── Resilience ─────────────────────────────────────────────────────────────────

class TestGrowthResilience:
    def test_high_resilience(self):
        score = compute_resilience_score(
            resilience_score=80.0,
            is_cyclical=False,
            loss_rate=0.0,
            avg_fcf_margin=0.15,
            earnings_stability=80.0,
            moat_score=75.0,
        )
        assert score > 70.0

    def test_cyclical_penalty(self):
        s_non_cyclical = compute_resilience_score(is_cyclical=False)
        s_cyclical     = compute_resilience_score(is_cyclical=True)
        assert s_cyclical < s_non_cyclical

    def test_negative_fcf_penalty(self):
        s_pos = compute_resilience_score(avg_fcf_margin=0.10)
        s_neg = compute_resilience_score(avg_fcf_margin=-0.05)
        assert s_pos > s_neg

    def test_range(self):
        for loss in [0.0, 0.10, 0.25, 0.50]:
            s = compute_resilience_score(loss_rate=loss)
            assert 0.0 <= s <= 100.0


# ── Risk ───────────────────────────────────────────────────────────────────────

class TestGrowthRisk:
    def test_low_risk_healthy(self):
        result = assess_growth_risk(
            eps_volatility=0.10,
            revenue_volatility=0.08,
            loss_rate=0.0,
            is_cyclical=False,
            avg_fcf_margin=0.12,
            net_margin=0.12,
            avg_net_margin=0.10,
            history_depth=8,
        )
        assert result.risk_score < 30.0
        assert not result.risk_factors

    def test_high_risk_distressed(self):
        result = assess_growth_risk(
            eps_volatility=1.5,
            revenue_volatility=0.9,
            loss_rate=0.40,
            is_cyclical=True,
            avg_fcf_margin=-0.05,
            net_margin=0.02,
            avg_net_margin=0.10,
            history_depth=2,
        )
        assert result.risk_score > 60.0
        assert len(result.risk_factors) > 0

    def test_risk_factors_populated(self):
        result = assess_growth_risk(eps_volatility=1.0, loss_rate=0.20)
        assert "high_earnings_volatility" in result.risk_factors
        assert "loss_periods_in_history" in result.risk_factors

    def test_negative_fcf_flagged(self):
        result = assess_growth_risk(avg_fcf_margin=-0.10)
        assert "negative_fcf" in result.risk_factors

    def test_range(self):
        result = assess_growth_risk()
        assert 0.0 <= result.risk_score <= 100.0


# ── SustainabilityEngine ───────────────────────────────────────────────────────

class TestGrowthSustainabilityEngine:
    def test_healthy_company(self, engine):
        result = engine.compute(
            eps_volatility=0.10,
            revenue_volatility=0.08,
            margin_volatility=0.05,
            consistency_score=80.0,
            loss_rate=0.0,
            is_cyclical=False,
            avg_fcf_margin=0.12,
            net_margin=0.13,
            avg_net_margin=0.10,
            earnings_stability=78.0,
            moat_score=70.0,
            resilience_score=68.0,
            history_depth=8,
        )
        assert isinstance(result, GrowthSustainabilityProfile)
        assert result.sustainability_score > 55.0
        assert result.is_sustainable is True

    def test_distressed_company(self, engine):
        result = engine.compute(
            eps_volatility=1.5,
            loss_rate=0.30,
            is_cyclical=True,
            avg_fcf_margin=-0.05,
            history_depth=2,
        )
        assert result.sustainability_score < 50.0

    def test_range(self, engine):
        result = engine.compute()
        assert 0.0 <= result.sustainability_score <= 100.0
        assert 0.0 <= result.consistency_score  <= 100.0
        assert 0.0 <= result.resilience_score   <= 100.0
        assert 0.0 <= result.cyclicality        <= 100.0

    def test_no_data(self, engine):
        result = engine.compute()
        assert isinstance(result, GrowthSustainabilityProfile)
        assert result.is_sustainable is False or result.is_sustainable is True  # not crash

    def test_sustainable_threshold(self, engine):
        result_high = engine.compute(
            consistency_score=90.0, resilience_score=85.0, loss_rate=0.0,
            avg_fcf_margin=0.15, moat_score=80.0, history_depth=10,
        )
        result_low = engine.compute(
            eps_volatility=1.0, loss_rate=0.30, is_cyclical=True,
            avg_fcf_margin=-0.10, history_depth=1,
        )
        assert result_high.sustainability_score > result_low.sustainability_score
