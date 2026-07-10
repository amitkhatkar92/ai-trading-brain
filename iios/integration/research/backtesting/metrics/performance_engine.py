"""metrics/performance_engine.py — Computes all metrics from BacktestResult."""
from __future__ import annotations

import logging
from typing import Any, Optional

from iios.integration.research.backtesting.backtest_exceptions import MetricsCalculationError
from iios.integration.research.backtesting.core.backtest_result import BacktestResult
from iios.integration.research.backtesting.core.backtest_statistics import BacktestStatistics

_log = logging.getLogger(__name__)


class PerformanceEngine:
    """
    Computes BacktestStatistics from a completed BacktestResult.

    Stateless — one instance can be reused for many results.
    """

    def compute(
        self,
        result:            BacktestResult,
        risk_free_rate:    float = 0.06,
        benchmark_returns: Optional[list[float]] = None,
    ) -> BacktestStatistics:
        """
        Compute and attach performance statistics to result.

        Also populates result.metrics with the flat dict.
        Raises MetricsCalculationError on unrecoverable computation failure.
        """
        try:
            stats = BacktestStatistics.compute(
                equity_curve       = result.equity_curve,
                trades             = result.trade_log,
                risk_free_rate     = risk_free_rate,
                benchmark_returns  = benchmark_returns,
            )
        except Exception as exc:
            raise MetricsCalculationError(
                f"Failed to compute performance metrics: {exc}"
            ) from exc

        result.metrics.update(stats.to_dict())
        _log.debug(
            "[PerformanceEngine] computed metrics for backtest=%s  "
            "return=%.2f%%  sharpe=%.2f  maxdd=%.2f%%",
            result.backtest_id,
            stats.total_return_pct * 100,
            stats.sharpe_ratio,
            stats.max_drawdown_pct * 100,
        )
        return stats

    def compare(
        self,
        results: list[BacktestResult],
        risk_free_rate: float = 0.06,
    ) -> dict[str, Any]:
        """
        Compare multiple backtest results side-by-side.

        Returns a dict of result_id → statistics dict.
        """
        comparison: dict[str, Any] = {}
        for r in results:
            try:
                s = self.compute(r, risk_free_rate)
                comparison[r.result_id] = s.to_dict()
            except MetricsCalculationError as exc:
                comparison[r.result_id] = {"error": str(exc)}
        return comparison
