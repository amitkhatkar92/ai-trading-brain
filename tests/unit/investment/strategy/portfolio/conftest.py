"""tests/unit/investment/strategy/portfolio/conftest.py
Shared fixtures for portfolio engine tests.
"""
from __future__ import annotations

import pytest
from typing import List

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy


def make_strategy(
    sid: str,
    name: str = "",
    eval_score: float = 70.0,
    sharpe: float = 1.2,
    max_dd: float = 0.12,
    win_rate: float = 0.55,
    profit_factor: float = 1.5,
    robustness: float = 0.70,
    confidence: float = 75.0,
    ann_return: float = 0.18,
    ann_vol: float = 0.12,
    asset_types: List[str] = None,
    sectors: List[str] = None,
    tags: List[str] = None,
    regimes: List[str] = None,
    timeframes: List[str] = None,
    approval: str = "approved",
    min_capital: float = 0.0,
) -> PortfolioStrategy:
    return PortfolioStrategy(
        strategy_id=sid,
        strategy_name=name or f"Strategy-{sid}",
        evaluation_score=eval_score,
        sharpe_ratio=sharpe,
        max_drawdown=max_dd,
        win_rate=win_rate,
        profit_factor=profit_factor,
        robustness_score=robustness,
        confidence_score=confidence,
        annualized_return=ann_return,
        annualized_vol=ann_vol,
        asset_types=asset_types or ["equity"],
        sectors=sectors or ["technology"],
        tags=tags or ["momentum"],
        supported_regimes=regimes or ["trending"],
        supported_timeframes=timeframes or ["daily"],
        approval_status=approval,
        min_capital=min_capital,
    )


@pytest.fixture()
def strat_a() -> PortfolioStrategy:
    return make_strategy(
        "strat-A", tags=["momentum", "trend"],
        sectors=["technology", "finance"], regimes=["trending", "bull"],
    )


@pytest.fixture()
def strat_b() -> PortfolioStrategy:
    return make_strategy(
        "strat-B", tags=["mean_reversion"],
        sectors=["consumer", "healthcare"], regimes=["sideways"],
        sharpe=0.9, eval_score=65.0,
    )


@pytest.fixture()
def strat_c() -> PortfolioStrategy:
    return make_strategy(
        "strat-C", tags=["volatility", "arbitrage"],
        sectors=["energy", "utilities"], regimes=["bear", "volatile"],
        sharpe=1.5, eval_score=80.0,
    )


@pytest.fixture()
def strat_d() -> PortfolioStrategy:
    return make_strategy(
        "strat-D", tags=["momentum", "breakout"],
        sectors=["technology"], regimes=["trending"],
        sharpe=1.1, eval_score=72.0,
    )


@pytest.fixture()
def five_strategies(strat_a, strat_b, strat_c, strat_d) -> List[PortfolioStrategy]:
    strat_e = make_strategy(
        "strat-E", tags=["income", "dividend"],
        sectors=["utilities", "real_estate"], regimes=["stable"],
        sharpe=0.8, eval_score=60.0,
    )
    return [strat_a, strat_b, strat_c, strat_d, strat_e]
