"""tests/unit/investment/portfolio/recommendation/conftest.py

Shared fixtures for the Portfolio Recommendation Engine test suite.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.recommendation.recommendation_policies import (
    PolicyParameters,
    InstitutionalPolicy,
)
from iios.investment.portfolio.recommendation.recommendation_registry import (
    RecommendationPolicyRegistry,
)
from iios.investment.portfolio.recommendation.recommendation_types import (
    PolicyType,
    PortfolioIntelligence,
)


@pytest.fixture()
def default_intel():
    """A healthy, well-formed PortfolioIntelligence snapshot."""
    return PortfolioIntelligence(
        portfolio_id            = "P-TEST-01",
        portfolio_name          = "Test Portfolio",
        portfolio_value         = 1_000_000.0,
        n_positions             = 20,
        construction_quality    = 0.80,
        equity_weight           = 0.60,
        bond_weight             = 0.25,
        cash_weight             = 0.10,
        alternative_weight      = 0.05,
        international_weight    = 0.20,
        target_equity_weight    = 0.60,
        target_bond_weight      = 0.25,
        target_cash_weight      = 0.10,
        equity_drift            = 0.01,
        optimization_quality    = 0.78,
        is_at_efficient_frontier= True,
        optimization_score      = 0.80,
        hhi                     = 0.06,
        effective_positions     = 16.5,
        sector_concentration    = 0.18,
        country_concentration   = 0.30,
        n_sectors               = 8,
        portfolio_risk_score    = 0.42,
        risk_budget_utilization = 0.55,
        var_utilization         = 0.60,
        cvar_utilization        = 0.65,
        is_risk_within_budget   = True,
        max_position_risk       = 0.08,
        sharpe_ratio            = 0.90,
        alpha                   = 0.02,
        information_ratio       = 0.45,
        max_drawdown            = 0.08,
        ytd_return              = 0.12,
        tracking_error          = 0.04,
        calmar_ratio            = 1.50,
        drift_level             = 0.03,
        rebalance_recommended   = False,
        rebalance_score         = 0.30,
        days_since_rebalance    = 45,
        market_regime           = "normal",
        macro_signal            = "neutral",
        signal_confidence       = 0.85,
    )


@pytest.fixture()
def stressed_intel():
    """Portfolio under multiple stress conditions — should trigger many rules."""
    return PortfolioIntelligence(
        portfolio_id            = "P-STRESS-01",
        portfolio_name          = "Stressed Portfolio",
        portfolio_value         = 500_000.0,
        n_positions             = 12,
        construction_quality    = 0.30,
        equity_weight           = 0.85,   # overweight
        bond_weight             = 0.10,
        cash_weight             = 0.03,
        alternative_weight      = 0.02,
        international_weight    = 0.05,   # under threshold
        target_equity_weight    = 0.60,
        target_bond_weight      = 0.25,
        target_cash_weight      = 0.10,
        equity_drift            = 0.25,   # well above EQUITY_OVERWEIGHT_THRESHOLD (0.10)
        optimization_quality    = 0.30,
        is_at_efficient_frontier= False,
        optimization_score      = 0.30,
        hhi                     = 0.35,   # concentrated
        effective_positions     = 3.5,    # too few
        sector_concentration    = 0.45,   # over threshold
        country_concentration   = 0.70,
        n_sectors               = 3,
        portfolio_risk_score    = 0.80,
        risk_budget_utilization = 0.92,   # over budget
        var_utilization         = 0.95,   # breach
        cvar_utilization        = 0.95,
        is_risk_within_budget   = False,
        max_position_risk       = 0.25,
        sharpe_ratio            = 0.15,   # poor
        alpha                   = -0.01,
        information_ratio       = 0.05,
        max_drawdown            = 0.20,   # severe
        ytd_return              = -0.05,
        tracking_error          = 0.12,
        calmar_ratio            = 0.20,
        drift_level             = 0.10,
        rebalance_recommended   = True,
        rebalance_score         = 0.85,
        days_since_rebalance    = 180,
        market_regime           = "crisis",
        macro_signal            = "bearish",
        signal_confidence       = 0.70,
    )


@pytest.fixture()
def default_policy():
    """The default balanced policy from the registry."""
    registry = RecommendationPolicyRegistry()
    return registry.default_policy()


@pytest.fixture()
def registry():
    return RecommendationPolicyRegistry()
