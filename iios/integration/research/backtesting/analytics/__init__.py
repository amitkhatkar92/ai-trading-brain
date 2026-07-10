"""analytics/__init__.py — Analytics subpackage (re-exports from metrics)."""
from iios.integration.research.backtesting.metrics import (
    calculate_bar_returns,
    total_return,
    annualized_return,
    monthly_returns,
    annual_returns,
    drawdown_series,
    max_drawdown,
    max_drawdown_duration_bars,
    sharpe_ratio,
    sortino_ratio,
    calmar_ratio,
    volatility,
    win_rate,
    profit_factor,
    expectancy,
)

__all__ = [
    "calculate_bar_returns", "total_return", "annualized_return",
    "monthly_returns", "annual_returns",
    "drawdown_series", "max_drawdown", "max_drawdown_duration_bars",
    "sharpe_ratio", "sortino_ratio", "calmar_ratio", "volatility",
    "win_rate", "profit_factor", "expectancy",
]
