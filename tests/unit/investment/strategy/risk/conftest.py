"""tests/unit/investment/strategy/risk/conftest.py
Shared fixtures for the Strategy Risk Engine test suite.
"""
import pytest

from iios.investment.strategy.risk.risk_input import StrategyRiskInput


def make_risk_input(
    sid: str = "s1",
    name: str = "TestStrategy",
    evaluation_score: float = 70.0,
    sharpe_ratio: float = 1.2,
    max_drawdown: float = 0.12,
    win_rate: float = 0.55,
    profit_factor: float = 1.5,
    robustness_score: float = 0.70,
    confidence_score: float = 75.0,
    annualized_return: float = 0.18,
    annualized_vol: float = 0.14,
    opportunity_score: float = 65.0,
    asset_types: tuple = ("equity",),
    sectors: tuple = ("technology",),
    tags: tuple = ("momentum",),
    supported_regimes: tuple = ("trending",),
    supported_timeframes: tuple = ("daily",),
    current_regime: str = "trending",
    current_volatility_level: str = "normal",
    market_liquidity: str = "high",
    portfolio_weight: float = 0.10,
    portfolio_size: int = 10,
) -> StrategyRiskInput:
    return StrategyRiskInput(
        strategy_id=sid,
        strategy_name=name,
        evaluation_score=evaluation_score,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        profit_factor=profit_factor,
        robustness_score=robustness_score,
        confidence_score=confidence_score,
        annualized_return=annualized_return,
        annualized_vol=annualized_vol,
        opportunity_score=opportunity_score,
        asset_types=asset_types,
        sectors=sectors,
        tags=tags,
        supported_regimes=supported_regimes,
        supported_timeframes=supported_timeframes,
        current_regime=current_regime,
        current_volatility_level=current_volatility_level,
        market_liquidity=market_liquidity,
        portfolio_weight=portfolio_weight,
        portfolio_size=portfolio_size,
    )


@pytest.fixture()
def risk_input():
    return make_risk_input()


@pytest.fixture()
def high_risk_input():
    return make_risk_input(
        sid="s_high",
        name="HighRisk",
        evaluation_score=30.0,
        sharpe_ratio=0.2,
        max_drawdown=0.45,
        win_rate=0.38,
        robustness_score=0.25,
        confidence_score=30.0,
        annualized_vol=0.50,
        current_regime="ranging",
        supported_regimes=("trending",),   # mismatch
        current_volatility_level="extreme",
        market_liquidity="low",
        portfolio_weight=0.30,
    )


@pytest.fixture()
def low_risk_input():
    return make_risk_input(
        sid="s_low",
        name="LowRisk",
        evaluation_score=90.0,
        sharpe_ratio=2.5,
        max_drawdown=0.05,
        win_rate=0.70,
        robustness_score=0.92,
        confidence_score=92.0,
        annualized_vol=0.08,
        current_regime="trending",
        supported_regimes=("trending",),
        current_volatility_level="low",
        market_liquidity="high",
        portfolio_weight=0.05,
    )
