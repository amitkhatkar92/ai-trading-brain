"""tests/unit/investment/portfolio/construction/conftest.py

Shared fixtures for the construction engine test suite.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.construction.construction_constraints import ConstraintDefinition
from iios.investment.portfolio.construction.construction_types import (
    AssetClass,
    ConstructionDirection,
    ConstructionType,
    ConstraintSeverity,
    ConstraintType,
    MarketCapCategory,
    WeightingMethod,
)
from iios.investment.portfolio.construction.portfolio_blueprint import (
    ConstructionRequest,
    InvestmentRecommendation,
)
from iios.investment.portfolio.construction.portfolio_construction_engine import (
    PortfolioConstructionEngine,
)
from iios.investment.portfolio.construction.security_selector import SecuritySelector
from iios.investment.portfolio.construction.selection_policy import SelectionPolicy


# ---------------------------------------------------------------------------
# Recommendation factories
# ---------------------------------------------------------------------------

def _rec(
    symbol: str,
    *,
    conviction: float = 0.7,
    confidence: float = 0.7,
    risk_score: float = 0.2,
    sector: str = "technology",
    direction: ConstructionDirection = ConstructionDirection.LONG,
    name: str = "",
) -> InvestmentRecommendation:
    return InvestmentRecommendation(
        symbol=symbol,
        name=name or symbol,
        conviction=conviction,
        confidence=confidence,
        risk_score=risk_score,
        sector=sector,
        direction=direction,
        asset_class=AssetClass.EQUITY,
        market_cap_category=MarketCapCategory.LARGE_CAP,
        source_decision_id=f"DEC-{symbol}",
        rationale=f"Buy {symbol}",
    )


def make_recs(
    n: int,
    *,
    sectors: list | None = None,
    conviction: float = 0.7,
    confidence: float = 0.7,
) -> list:
    _sectors = sectors or ["technology", "finance", "healthcare", "energy", "consumer"]
    return [
        _rec(
            f"SYM{i:03d}",
            conviction=conviction,
            confidence=confidence,
            sector=_sectors[i % len(_sectors)],
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def recs_10():
    return make_recs(10)


@pytest.fixture
def recs_5():
    return make_recs(5)


@pytest.fixture
def recs_30():
    return make_recs(30)


@pytest.fixture
def long_only_request():
    return ConstructionRequest(
        portfolio_id      = "TEST-PF",
        construction_type = ConstructionType.LONG_ONLY,
        weighting_method  = WeightingMethod.EQUAL,
        max_holdings      = 20,
        min_holdings      = 3,
        target_cash_pct   = 0.05,
        min_conviction    = 0.3,
        min_confidence    = 0.3,
        max_risk_score    = 0.9,
    )


@pytest.fixture
def engine():
    e = PortfolioConstructionEngine(environment="paper")
    e.start()
    yield e
    e.stop()


@pytest.fixture
def registered_engine():
    e = PortfolioConstructionEngine(environment="paper")
    e.start()
    e.register_portfolio("PF-001")
    yield e
    e.stop()


@pytest.fixture
def max_weight_constraint():
    from iios.investment.portfolio.construction.construction_constraints import (
        MaxSingleWeightConstraint,
    )
    return MaxSingleWeightConstraint(
        name        = "max_single_weight",
        severity    = ConstraintSeverity.HARD,
        description = "Max 20% per holding",
        max_weight  = 0.20,
    )
