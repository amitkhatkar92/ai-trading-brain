"""conftest.py — shared fixtures for optimization tests."""
from __future__ import annotations

import pytest

from iios.investment.portfolio.optimization.optimization_engine import AssetProxy
from iios.investment.portfolio.optimization.optimization_plan import (
    OptimizationObjective,
    OptimizationRequest,
)
from iios.investment.portfolio.optimization.optimization_types import (
    ObjectiveType,
    OptimizationMethod,
)


# ---------------------------------------------------------------------------
# Simple mock AllocationPlan (no upstream dependency required)
# ---------------------------------------------------------------------------

class _MockPosition:
    def __init__(self, symbol, conviction, confidence, risk_score, sector, industry, asset_class, capital):
        self.symbol       = symbol
        self.conviction   = conviction
        self.confidence   = confidence
        self.risk_score   = risk_score
        self.sector       = sector
        self.industry     = industry
        self.asset_class  = asset_class
        self.allocated_capital = capital


class _MockAllocationPlan:
    def __init__(self, positions, total_capital=1_000_000.0):
        self.allocations   = positions
        self.total_capital = total_capital
        self.plan_id       = "alloc-plan-001"
        self.blueprint_id  = "blueprint-001"
        self.portfolio_id  = "portfolio-test-001"
        self.version       = 1


@pytest.fixture
def allocation_plan_5():
    positions = [
        _MockPosition("RELIANCE", 0.72, 0.80, 0.25, "energy",    "oil_gas",    "equity", 200_000),
        _MockPosition("TCS",      0.68, 0.75, 0.20, "technology", "it_services","equity", 200_000),
        _MockPosition("INFY",     0.65, 0.70, 0.22, "technology", "it_services","equity", 200_000),
        _MockPosition("HDFC",     0.60, 0.65, 0.30, "finance",    "banking",    "equity", 200_000),
        _MockPosition("AXISBANK", 0.58, 0.62, 0.35, "finance",    "banking",    "equity", 200_000),
    ]
    return _MockAllocationPlan(positions, total_capital=1_000_000.0)


@pytest.fixture
def allocation_plan_3():
    positions = [
        _MockPosition("WIPRO",  0.60, 0.70, 0.30, "technology", "it_services", "equity", 333_333),
        _MockPosition("ITC",    0.55, 0.65, 0.28, "consumer",   "fmcg",        "equity", 333_333),
        _MockPosition("MARUTI", 0.50, 0.60, 0.40, "auto",       "passenger_vehicles", "equity", 333_334),
    ]
    return _MockAllocationPlan(positions, total_capital=1_000_000.0)


@pytest.fixture
def allocation_plan_single():
    positions = [
        _MockPosition("TATASTEEL", 0.65, 0.70, 0.45, "materials", "steel", "equity", 1_000_000),
    ]
    return _MockAllocationPlan(positions, total_capital=1_000_000.0)


@pytest.fixture
def standard_request():
    return OptimizationRequest(
        portfolio_id       = "portfolio-test-001",
        allocation_plan_id = "alloc-plan-001",
        total_capital      = 1_000_000.0,
        method             = OptimizationMethod.MAXIMUM_SHARPE,
        objective          = OptimizationObjective(primary=ObjectiveType.MAXIMIZE_SHARPE),
        min_weight         = 0.0,
        max_weight         = 0.40,
        max_sector_weight  = 0.60,
        risk_aversion      = 2.0,
        max_iterations     = 500,
    )


@pytest.fixture
def five_assets():
    return [
        AssetProxy("A", expected_return=0.72, risk=0.25, confidence=0.80, prior_weight=0.20, sector="tech"),
        AssetProxy("B", expected_return=0.68, risk=0.20, confidence=0.75, prior_weight=0.20, sector="tech"),
        AssetProxy("C", expected_return=0.65, risk=0.22, confidence=0.70, prior_weight=0.20, sector="energy"),
        AssetProxy("D", expected_return=0.60, risk=0.30, confidence=0.65, prior_weight=0.20, sector="finance"),
        AssetProxy("E", expected_return=0.58, risk=0.35, confidence=0.62, prior_weight=0.20, sector="finance"),
    ]
