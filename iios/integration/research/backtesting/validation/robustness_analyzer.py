"""validation/robustness_analyzer.py — Sensitivity and parameter stability analysis."""
from __future__ import annotations

import statistics
from typing import Any, Callable


class RobustnessAnalyzer:
    """
    Analyses strategy sensitivity to small data perturbations.

    Perturbation-based robustness: run the strategy multiple times with
    slightly noisy price data and measure consistency of key metrics.
    """

    def analyse(
        self,
        metric_samples: list[dict[str, float]],
        metric_key: str = "sharpe_ratio",
    ) -> dict[str, Any]:
        """
        Analyse robustness from a set of metric samples.

        metric_samples – list of metric dicts (one per perturbation run)
        metric_key     – the metric to focus on

        Returns a robustness summary.
        """
        values = [s.get(metric_key, 0.0) for s in metric_samples]
        if not values:
            return {"status": "no_data"}

        mean_val   = statistics.mean(values)
        stdev_val  = statistics.stdev(values) if len(values) > 1 else 0.0
        cv         = stdev_val / abs(mean_val) if mean_val != 0 else 0.0
        pct_positive = sum(1 for v in values if v > 0) / len(values)

        status = (
            "robust"     if cv < 0.20 and pct_positive >= 0.70 else
            "marginal"   if cv < 0.40 and pct_positive >= 0.55 else
            "fragile"
        )

        return {
            "metric":       metric_key,
            "n_samples":    len(values),
            "mean":         round(mean_val,  4),
            "stdev":        round(stdev_val, 4),
            "cv":           round(cv,         4),
            "min":          round(min(values), 4),
            "max":          round(max(values), 4),
            "pct_positive": round(pct_positive, 4),
            "status":       status,
        }

    def perturbation_test(
        self,
        equity_curves: list[list[tuple[float, float]]],
    ) -> dict[str, Any]:
        """
        Compare equity curves across multiple perturbation runs.

        Returns consistency metrics (how similar the curves are to each other).
        """
        from iios.integration.research.backtesting.metrics.return_calculator import total_return

        if not equity_curves:
            return {}

        returns = []
        for curve in equity_curves:
            if len(curve) >= 2:
                returns.append(total_return(curve[0][1], curve[-1][1]))

        if not returns:
            return {}

        mean_ret   = statistics.mean(returns)
        stdev_ret  = statistics.stdev(returns) if len(returns) > 1 else 0.0
        consistency = 1.0 - min(1.0, abs(stdev_ret / mean_ret) if mean_ret != 0 else 1.0)

        return {
            "n_curves":    len(equity_curves),
            "mean_return": round(mean_ret,  4),
            "stdev_return": round(stdev_ret, 4),
            "consistency": round(consistency, 4),
        }
