"""tests/unit/investment/portfolio/integration/conftest.py

Shared fixtures for the Portfolio Intelligence Integration Engine test suite.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.integration.integration_types import (
    EngineId, IntegrationParameters,
)
from iios.investment.portfolio.integration.portfolio_intelligence_integration_engine import (
    PortfolioIntelligenceIntegrationEngine,
)


# ---------------------------------------------------------------------------
# Engine data fixtures (simulate contributions from upstream engines)
# ---------------------------------------------------------------------------

@pytest.fixture()
def healthy_contributions():
    """A complete set of consistent, healthy engine contributions."""
    return {
        EngineId.FRAMEWORK: {
            "portfolio_name": "Test Portfolio",
            "portfolio_type": "balanced",
        },
        EngineId.CONSTRUCTION: {
            "portfolio_name":     "Test Portfolio",
            "portfolio_value":    1_000_000.0,
            "n_positions":        20,
            "construction_quality": 0.82,
        },
        EngineId.ALLOCATION: {
            "equity_weight":       0.60,
            "bond_weight":         0.25,
            "cash_weight":         0.10,
            "alternative_weight":  0.05,
            "international_weight": 0.20,
            "equity_drift":        0.02,
            "n_positions":         20,
        },
        EngineId.OPTIMIZATION: {
            "optimization_quality":    0.78,
            "is_at_efficient_frontier": True,
            "optimization_score":      0.80,
        },
        EngineId.DIVERSIFICATION: {
            "hhi":                  0.06,
            "effective_positions":  16.5,
            "sector_concentration": 0.18,
            "country_concentration": 0.30,
            "n_sectors":            8,
        },
        EngineId.RISK: {
            "portfolio_risk_score":    0.42,
            "risk_budget_utilization": 0.55,
            "var_utilization":         0.60,
            "cvar_utilization":        0.65,
            "is_risk_within_budget":   True,
            "max_position_risk":       0.08,
            "max_drawdown":            0.08,
        },
        EngineId.PERFORMANCE: {
            "sharpe_ratio":      0.90,
            "alpha":             0.02,
            "information_ratio": 0.45,
            "max_drawdown":      0.08,
            "ytd_return":        0.12,
            "tracking_error":    0.04,
            "calmar_ratio":      1.50,
        },
        EngineId.REBALANCING: {
            "drift_level":          "minor",
            "rebalance_recommended": False,
            "rebalance_score":      0.30,
            "days_since_rebalance": 45,
        },
        EngineId.RECOMMENDATION: {
            "primary_action":     "no_action",
            "priority":           "informational",
            "recommendation_score": 0.75,
            "confidence":         0.85,
        },
    }


@pytest.fixture()
def conflicted_contributions():
    """Contributions that contain deliberate cross-engine conflicts."""
    return {
        EngineId.CONSTRUCTION: {
            "portfolio_name":       "Stressed Portfolio",
            "portfolio_value":      500_000.0,
            "n_positions":          10,
            "construction_quality": 0.30,   # low
        },
        EngineId.ALLOCATION: {
            "equity_weight":        0.85,   # overweight
            "bond_weight":          0.10,
            "cash_weight":          0.03,
            "alternative_weight":   0.02,
            "international_weight": 0.05,
            "equity_drift":         0.25,
            "n_positions":          10,
        },
        EngineId.OPTIMIZATION: {
            "optimization_quality":     0.78,
            "is_at_efficient_frontier": True,   # conflicts with low construction quality
            "optimization_score":       0.78,
        },
        EngineId.DIVERSIFICATION: {
            "hhi":                  0.35,
            "effective_positions":  3.5,
            "sector_concentration": 0.45,
            "n_sectors":            3,
        },
        EngineId.RISK: {
            "portfolio_risk_score":    0.80,
            "risk_budget_utilization": 0.92,
            "var_utilization":         0.88,
            "is_risk_within_budget":   False,
            "max_drawdown":            0.20,
        },
        EngineId.PERFORMANCE: {
            "sharpe_ratio":      0.20,
            "alpha":            -0.01,
            "information_ratio": 0.05,
            "max_drawdown":      0.22,   # slightly different from risk.max_drawdown
            "ytd_return":       -0.05,
            "calmar_ratio":      0.20,
        },
        EngineId.REBALANCING: {
            "drift_level":           "critical",
            "rebalance_recommended":  True,
            "rebalance_score":        0.85,
        },
        EngineId.RECOMMENDATION: {
            "primary_action":      "aggressive_positioning",   # conflicts with high risk
            "priority":            "high",
            "recommendation_score": 0.40,
            "confidence":           0.65,
        },
    }


@pytest.fixture()
def engine():
    e = PortfolioIntelligenceIntegrationEngine()
    e.start()
    return e


@pytest.fixture()
def loaded_engine(engine, healthy_contributions):
    """Engine pre-loaded with healthy contributions for P-HEALTH."""
    for eid, data in healthy_contributions.items():
        engine.receive("P-HEALTH", eid, data)
    return engine
