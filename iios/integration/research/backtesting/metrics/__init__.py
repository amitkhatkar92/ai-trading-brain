"""metrics/__init__.py"""
from iios.integration.research.backtesting.metrics.return_calculator   import (
    calculate_bar_returns, total_return, annualized_return, monthly_returns, annual_returns,
)
from iios.integration.research.backtesting.metrics.drawdown_calculator import (
    drawdown_series, max_drawdown, max_drawdown_duration_bars, drawdown_periods,
)
from iios.integration.research.backtesting.metrics.risk_metrics        import (
    volatility, sharpe_ratio, sortino_ratio, calmar_ratio,
    omega_ratio, value_at_risk, compute_beta, information_ratio,
)
from iios.integration.research.backtesting.metrics.trade_statistics    import (
    win_rate, profit_factor, expectancy, avg_win, avg_loss,
    largest_win, largest_loss, avg_trade_duration, max_consecutive_wins,
    max_consecutive_losses, trade_return_distribution,
)
from iios.integration.research.backtesting.metrics.performance_engine  import PerformanceEngine
from iios.integration.research.backtesting.metrics.performance_report  import PerformanceReport

__all__ = [
    "calculate_bar_returns", "total_return", "annualized_return",
    "monthly_returns", "annual_returns",
    "drawdown_series", "max_drawdown", "max_drawdown_duration_bars", "drawdown_periods",
    "volatility", "sharpe_ratio", "sortino_ratio", "calmar_ratio",
    "omega_ratio", "value_at_risk", "compute_beta", "information_ratio",
    "win_rate", "profit_factor", "expectancy", "avg_win", "avg_loss",
    "largest_win", "largest_loss", "avg_trade_duration",
    "max_consecutive_wins", "max_consecutive_losses", "trade_return_distribution",
    "PerformanceEngine", "PerformanceReport",
]
