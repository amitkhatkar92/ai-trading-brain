"""conftest.py — shared fixtures for rebalancing engine tests."""
from __future__ import annotations

import pytest

from iios.investment.portfolio.rebalancing import (
    CurrentPosition,
    TargetPosition,
)


# ---------------------------------------------------------------------------
# Basic portfolios
# ---------------------------------------------------------------------------

def _cp(symbol: str, weight: float, sector: str = "EQUITY",
        holding_days: int = 400, unrealized_gain: float = 0.05,
        risk_score: float = 0.5, liquidity: float = 0.8) -> CurrentPosition:
    return CurrentPosition(
        symbol=symbol, current_weight=weight, sector=sector,
        holding_days=holding_days, unrealized_gain=unrealized_gain,
        risk_score=risk_score, liquidity=liquidity,
    )


def _tp(symbol: str, weight: float, sector: str = "EQUITY",
        risk_score: float = 0.5, conviction: float = 0.7) -> TargetPosition:
    return TargetPosition(
        symbol=symbol, target_weight=weight, sector=sector,
        risk_score=risk_score, conviction=conviction,
    )


@pytest.fixture
def balanced_current() -> list:
    """5-stock portfolio at target weights."""
    return [
        _cp("RELIANCE",   0.20, "ENERGY"),
        _cp("TCS",        0.20, "IT"),
        _cp("INFY",       0.20, "IT"),
        _cp("HDFCBANK",   0.20, "FINANCIALS"),
        _cp("ICICIBANK",  0.20, "FINANCIALS"),
    ]


@pytest.fixture
def balanced_target() -> list:
    return [
        _tp("RELIANCE",  0.20, "ENERGY"),
        _tp("TCS",       0.20, "IT"),
        _tp("INFY",      0.20, "IT"),
        _tp("HDFCBANK",  0.20, "FINANCIALS"),
        _tp("ICICIBANK", 0.20, "FINANCIALS"),
    ]


@pytest.fixture
def drifted_current() -> list:
    """Portfolio that has drifted significantly from target."""
    return [
        _cp("RELIANCE",  0.35, "ENERGY"),   # overweight by 15%
        _cp("TCS",       0.10, "IT"),        # underweight by 10%
        _cp("INFY",      0.20, "IT"),
        _cp("HDFCBANK",  0.15, "FINANCIALS"),
        _cp("ICICIBANK", 0.20, "FINANCIALS"),
    ]


@pytest.fixture
def drifted_target() -> list:
    return [
        _tp("RELIANCE",  0.20, "ENERGY"),
        _tp("TCS",       0.20, "IT"),
        _tp("INFY",      0.20, "IT"),
        _tp("HDFCBANK",  0.20, "FINANCIALS"),
        _tp("ICICIBANK", 0.20, "FINANCIALS"),
    ]


@pytest.fixture
def diverse_current() -> list:
    """10-stock diverse portfolio with mixed sectors."""
    return [
        _cp("RELIANCE",     0.12, "ENERGY",     holding_days=400),
        _cp("TCS",          0.12, "IT",          holding_days=700),
        _cp("INFY",         0.10, "IT",          holding_days=300),
        _cp("HDFCBANK",     0.12, "FINANCIALS",  holding_days=500),
        _cp("ICICIBANK",    0.08, "FINANCIALS",  holding_days=200, unrealized_gain=-0.02),
        _cp("SUNPHARMA",    0.10, "HEALTHCARE",  holding_days=180),
        _cp("HINDUNILVR",   0.09, "FMCG",        holding_days=600),
        _cp("TATASTEEL",    0.09, "MATERIALS",   holding_days=90, unrealized_gain=-0.05),
        _cp("POWERGRID",    0.09, "UTILITIES",   holding_days=800),
        _cp("DRREDDY",      0.09, "HEALTHCARE",  holding_days=400),
    ]


@pytest.fixture
def diverse_target() -> list:
    return [
        _tp("RELIANCE",     0.10, "ENERGY"),
        _tp("TCS",          0.10, "IT"),
        _tp("INFY",         0.10, "IT"),
        _tp("HDFCBANK",     0.10, "FINANCIALS"),
        _tp("ICICIBANK",    0.10, "FINANCIALS"),
        _tp("SUNPHARMA",    0.10, "HEALTHCARE"),
        _tp("HINDUNILVR",   0.10, "FMCG"),
        _tp("TATASTEEL",    0.10, "MATERIALS"),
        _tp("POWERGRID",    0.10, "UTILITIES"),
        _tp("WIPRO",        0.10, "IT"),         # new position
    ]


@pytest.fixture
def concentrated_current() -> list:
    """Highly concentrated portfolio."""
    return [
        _cp("RELIANCE", 0.60, "ENERGY",    risk_score=0.7, liquidity=0.9),
        _cp("TCS",      0.25, "IT",         risk_score=0.3, liquidity=0.9),
        _cp("TATASTEEL",0.15, "MATERIALS",  risk_score=0.8, liquidity=0.6),
    ]


@pytest.fixture
def concentrated_target() -> list:
    return [
        _tp("RELIANCE", 0.33, "ENERGY"),
        _tp("TCS",      0.34, "IT"),
        _tp("TATASTEEL",0.33, "MATERIALS"),
    ]


@pytest.fixture
def stcg_current() -> list:
    """Portfolio with many short-term positions."""
    return [
        _cp("A", 0.25, holding_days=50, unrealized_gain=0.10),
        _cp("B", 0.25, holding_days=80, unrealized_gain=0.15),
        _cp("C", 0.25, holding_days=400),
        _cp("D", 0.25, holding_days=500),
    ]


@pytest.fixture
def stcg_target() -> list:
    return [
        _tp("A", 0.15),
        _tp("B", 0.15),
        _tp("C", 0.35),
        _tp("D", 0.35),
    ]
