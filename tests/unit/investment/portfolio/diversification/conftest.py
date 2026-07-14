"""conftest.py — shared fixtures for diversification tests."""
from __future__ import annotations

import pytest

from iios.investment.portfolio.diversification.diversification_types import PositionData


# ---------------------------------------------------------------------------
# PositionData fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def positions_5_diverse():
    """5 well-diversified positions across 4 sectors."""
    return [
        PositionData("RELIANCE",  0.20, "energy",     "oil_gas",      "equity", risk_score=0.28, conviction=0.72, confidence=0.80),
        PositionData("TCS",       0.20, "technology", "it_services",  "equity", risk_score=0.22, conviction=0.68, confidence=0.75),
        PositionData("HDFC",      0.20, "finance",    "banking",      "equity", risk_score=0.30, conviction=0.65, confidence=0.70),
        PositionData("ITC",       0.20, "consumer",   "fmcg",         "equity", risk_score=0.25, conviction=0.60, confidence=0.68),
        PositionData("MARUTI",    0.20, "auto",       "passenger_vehicles", "equity", risk_score=0.35, conviction=0.55, confidence=0.65),
    ]


@pytest.fixture
def positions_3_concentrated():
    """3 positions: one dominant, all in 2 sectors."""
    return [
        PositionData("TCS",   0.60, "technology", "it_services", "equity", risk_score=0.20, conviction=0.75, confidence=0.80),
        PositionData("INFY",  0.25, "technology", "it_services", "equity", risk_score=0.22, conviction=0.70, confidence=0.75),
        PositionData("HDFC",  0.15, "finance",    "banking",     "equity", risk_score=0.28, conviction=0.62, confidence=0.70),
    ]


@pytest.fixture
def positions_10_balanced():
    """10 equal-weight positions across 5 sectors."""
    sectors = ["energy","technology","finance","consumer","auto",
               "pharma","materials","utilities","realty","telecom"]
    return [
        PositionData(f"SYM{i}", 0.10, sectors[i], f"ind_{i}", "equity",
                     risk_score=0.20+i*0.02, conviction=0.75-i*0.02, confidence=0.80-i*0.01)
        for i in range(10)
    ]


@pytest.fixture
def positions_single():
    return [PositionData("ONLY", 1.0, "equity", "equity", "equity", risk_score=0.30)]


# ---------------------------------------------------------------------------
# Mock plan objects
# ---------------------------------------------------------------------------

class _MockPosition:
    def __init__(self, p: PositionData):
        self.symbol              = p.symbol
        self.optimized_weight    = p.weight
        self.sector              = p.sector
        self.industry            = p.industry
        self.asset_class         = p.asset_class
        self.risk_proxy          = p.risk_score
        self.expected_return_proxy = p.conviction
        self.confidence_proxy    = p.confidence


class _MockPlan:
    def __init__(self, positions, total_capital=1_000_000.0, plan_id="plan-001"):
        self.positions     = [_MockPosition(p) for p in positions]
        self.total_capital = total_capital
        self.plan_id       = plan_id
        self.blueprint_id  = "blueprint-001"
        self.allocation_plan_id = "alloc-001"


@pytest.fixture
def plan_5_diverse(positions_5_diverse):
    return _MockPlan(positions_5_diverse)


@pytest.fixture
def plan_3_concentrated(positions_3_concentrated):
    return _MockPlan(positions_3_concentrated)


@pytest.fixture
def plan_10_balanced(positions_10_balanced):
    return _MockPlan(positions_10_balanced)


@pytest.fixture
def plan_single(positions_single):
    return _MockPlan(positions_single)
