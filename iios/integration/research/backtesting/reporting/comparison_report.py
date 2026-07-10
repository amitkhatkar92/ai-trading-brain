"""reporting/comparison_report.py — Side-by-side multi-backtest comparison."""
from __future__ import annotations

from typing import Any

from iios.integration.research.backtesting.core.backtest_result import BacktestResult


class ComparisonReport:
    """
    Produces a side-by-side comparison of multiple BacktestResult objects.
    """

    # Metrics shown in comparison table
    COMPARISON_KEYS = (
        "total_return_pct",
        "annualized_return_pct",
        "volatility_pct",
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "max_drawdown_pct",
        "win_rate",
        "profit_factor",
        "expectancy",
        "total_trades",
    )

    def build(
        self,
        results: list[BacktestResult],
        names:   list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Build a comparison dict.

        names – optional list of labels for each result (defaults to result_id).
        """
        labels = names if names and len(names) == len(results) else [
            r.result_id for r in results
        ]

        rows: dict[str, dict[str, Any]] = {}
        for label, r in zip(labels, results):
            rows[label] = {k: r.metrics.get(k) for k in self.COMPARISON_KEYS}

        # Rank by Sharpe
        ranked = sorted(
            labels,
            key=lambda lbl: rows[lbl].get("sharpe_ratio") or 0.0,
            reverse=True,
        )

        return {
            "count":     len(results),
            "labels":    labels,
            "metrics":   rows,
            "ranked_by_sharpe": ranked,
        }
