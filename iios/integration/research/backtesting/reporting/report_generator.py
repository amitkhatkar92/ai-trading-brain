"""reporting/report_generator.py — Assembles the full institutional backtest report."""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from iios.integration.research.backtesting.backtest_constants import BACKTESTING_ENGINE_VERSION
from iios.integration.research.backtesting.backtest_exceptions import ReportGenerationError
from iios.integration.research.backtesting.core.backtest import Backtest
from iios.integration.research.backtesting.core.backtest_result import BacktestResult
from iios.integration.research.backtesting.core.backtest_statistics import BacktestStatistics
from iios.integration.research.backtesting.reporting.equity_curve import EquityCurveReport
from iios.integration.research.backtesting.reporting.trade_report import TradeReport
from iios.integration.research.backtesting.reporting.benchmark_report import BenchmarkReport


class ReportGenerator:
    """
    Assembles the full institutional-grade backtest report from:
        - BacktestResult (raw artefacts)
        - BacktestStatistics (computed metrics)
        - BacktestConfiguration (run parameters)

    The report is a plain dict — suitable for JSON serialisation, dashboard
    rendering, or storage in the BacktestResult.report field.
    """

    def __init__(self) -> None:
        self._equity_rpt    = EquityCurveReport()
        self._trade_rpt     = TradeReport()
        self._benchmark_rpt = BenchmarkReport()
        self._generated     = 0

    def generate(
        self,
        backtest:          Backtest,
        result:            BacktestResult,
        stats:             BacktestStatistics,
        *,
        benchmark_returns: Optional[list[float]] = None,
        max_equity_points: int = 500,
    ) -> dict[str, Any]:
        """
        Generate the full report dict and attach it to result.report.

        Raises ReportGenerationError on failure.
        """
        try:
            report = self._build(
                backtest,
                result,
                stats,
                benchmark_returns  = benchmark_returns,
                max_equity_points  = max_equity_points,
            )
        except Exception as exc:
            raise ReportGenerationError(f"Report generation failed: {exc}") from exc

        result.report = report
        self._generated += 1
        return report

    def _build(
        self,
        backtest:          Backtest,
        result:            BacktestResult,
        stats:             BacktestStatistics,
        benchmark_returns: Optional[list[float]],
        max_equity_points: int,
    ) -> dict[str, Any]:
        from iios.integration.research.backtesting.metrics.performance_report import PerformanceReport

        perf_rpt = PerformanceReport()

        report: dict[str, Any] = {
            "report_id":       str(uuid.uuid4()),
            "generated_at":    time.time(),
            "engine_version":  BACKTESTING_ENGINE_VERSION,
            "backtest_id":     backtest.backtest_id,
            "strategy_id":     backtest.strategy_id,
            "strategy_name":   backtest.strategy_name,
            "configuration":   backtest.configuration.to_dict(),
            "performance":     perf_rpt.build(
                stats,
                result.equity_curve,
                result.trade_log,
            ),
            "equity_curve":    self._equity_rpt.build(
                result.equity_curve,
                backtest.configuration.initial_capital,
                max_points = max_equity_points,
            ),
            "trade_log":       self._trade_rpt.build(result.trade_log),
            "summary": {
                "is_success":   result.is_success,
                "bar_count":    result.bar_count,
                "trade_count":  result.trade_count,
                "duration_sec": result.duration_sec,
            },
        }

        if benchmark_returns is not None and backtest.configuration.benchmark_symbol:
            from iios.integration.research.backtesting.metrics.return_calculator import (
                calculate_bar_returns,
            )
            strategy_returns = calculate_bar_returns(result.equity_curve)
            report["benchmark"] = self._benchmark_rpt.build(
                strategy_returns  = strategy_returns,
                benchmark_returns = benchmark_returns,
                benchmark_symbol  = backtest.configuration.benchmark_symbol,
                risk_free_rate    = backtest.configuration.risk_free_rate,
            )

        return report

    def stats(self) -> dict[str, Any]:
        return {"generated": self._generated}
