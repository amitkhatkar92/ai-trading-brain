"""Shared fixtures for Portfolio Performance Engine tests."""
import pytest
from typing import List

from iios.investment.portfolio.performance.performance_types import PerformancePosition


# ---------------------------------------------------------------------------
# Return series fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def nav_series_growing():
    """NAV series with steady growth."""
    base = 100.0
    vals = [base]
    for _ in range(23):  # 24 months
        vals.append(vals[-1] * 1.01)
    return vals


@pytest.fixture
def nav_series_flat():
    return [100.0] * 13


@pytest.fixture
def nav_series_declining():
    base = 100.0
    vals = [base]
    for _ in range(11):
        vals.append(vals[-1] * 0.99)
    return vals


@pytest.fixture
def monthly_returns_positive():
    return [0.012, 0.008, 0.015, 0.010, 0.005, 0.018,
            0.009, 0.011, 0.013, 0.007, 0.014, 0.016]


@pytest.fixture
def monthly_returns_mixed():
    return [0.02, -0.01, 0.03, -0.02, 0.01, 0.04,
            -0.01, 0.02, 0.01, -0.005, 0.025, 0.015]


# ---------------------------------------------------------------------------
# Position fixtures
# ---------------------------------------------------------------------------

def _make_position(symbol, weight, sector="Technology", period_return=0.05,
                   conviction=0.7, risk_score=0.4, strategy_id="s1"):
    return PerformancePosition(
        symbol=symbol, weight=weight, sector=sector,
        industry="Software", asset_class="equity",
        country="IN", currency="INR",
        strategy_id=strategy_id,
        period_return=period_return,
        expected_return_annual=0.15,
        risk_score=risk_score,
        conviction=conviction,
        confidence=0.7,
        liquidity=0.8,
        benchmark_period_return=0.04,
    )


@pytest.fixture
def positions_diverse():
    return [
        _make_position("TCS",    0.20, "Technology",  0.06, 0.75, 0.35, "momentum"),
        _make_position("INFY",   0.15, "Technology",  0.05, 0.70, 0.38, "momentum"),
        _make_position("HDFC",   0.20, "Finance",     0.04, 0.65, 0.45, "value"),
        _make_position("RELIANCE",0.25,"Energy",      0.03, 0.60, 0.50, "value"),
        _make_position("ITC",    0.20, "FMCG",        0.07, 0.72, 0.30, "quality"),
    ]


@pytest.fixture
def positions_concentrated():
    return [
        _make_position("TATASTEEL", 0.70, "Metals", 0.10, 0.80, 0.60, "momentum"),
        _make_position("HINDALCO",  0.30, "Metals", 0.08, 0.75, 0.55, "momentum"),
    ]


@pytest.fixture
def positions_single():
    return [_make_position("NIFTY50", 1.00, "Index", 0.12, 0.60, 0.30, "index")]


@pytest.fixture
def positions_negative_return():
    return [
        _make_position("A", 0.50, "Finance", -0.05, 0.45, 0.65, "value"),
        _make_position("B", 0.50, "Finance", -0.03, 0.50, 0.60, "value"),
    ]


@pytest.fixture
def mock_plan_with_positions(positions_diverse):
    class FakePlan:
        def __init__(self, positions):
            self.positions = positions
    return FakePlan(positions_diverse)
