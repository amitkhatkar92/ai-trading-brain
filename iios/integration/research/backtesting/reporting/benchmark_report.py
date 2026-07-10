"""reporting/benchmark_report.py — Benchmark comparison section."""
from __future__ import annotations

from typing import Any, Optional


class BenchmarkReport:
    """
    Builds a benchmark comparison section for the full backtest report.

    benchmark_returns – list of bar-by-bar fractional returns for the benchmark.
    """

    def build(
        self,
        strategy_returns:  list[float],
        benchmark_returns: list[float],
        benchmark_symbol:  str = "BENCHMARK",
        risk_free_rate:    float = 0.06,
    ) -> dict[str, Any]:
        from iios.integration.research.backtesting.metrics.risk_metrics import (
            compute_beta, information_ratio,
        )
        from iios.integration.research.backtesting.metrics.return_calculator import (
            annualized_return, total_return,
        )

        n       = min(len(strategy_returns), len(benchmark_returns))
        s_ret   = strategy_returns[:n]
        b_ret   = benchmark_returns[:n]

        # Cumulative returns
        s_total = 1.0
        b_total = 1.0
        for s, b in zip(s_ret, b_ret):
            s_total *= (1 + s)
            b_total *= (1 + b)
        s_total -= 1.0
        b_total -= 1.0

        beta  = compute_beta(s_ret, b_ret)
        ir    = information_ratio(s_ret, b_ret)
        ann_s = annualized_return(s_total, n)
        ann_b = annualized_return(b_total, n)
        alpha = ann_s - (risk_free_rate + beta * (ann_b - risk_free_rate))

        return {
            "benchmark_symbol":           benchmark_symbol,
            "strategy_total_return_pct":  round(s_total * 100, 4),
            "benchmark_total_return_pct": round(b_total * 100, 4),
            "active_return_pct":          round((s_total - b_total) * 100, 4),
            "alpha":                      round(alpha, 4),
            "beta":                       round(beta, 4),
            "information_ratio":          round(ir, 4),
            "bar_count":                  n,
        }
