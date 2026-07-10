"""reporting/equity_curve.py — Equity curve analytics and sampling."""
from __future__ import annotations

from typing import Any


def resample_equity_curve(
    equity_curve: list[tuple[float, float]],
    n_points: int = 200,
) -> list[tuple[float, float]]:
    """
    Downsample a long equity curve to at most n_points evenly spaced entries.
    """
    if len(equity_curve) <= n_points:
        return list(equity_curve)
    step   = len(equity_curve) / n_points
    result = [equity_curve[int(i * step)] for i in range(n_points)]
    # Always include the last point
    if result[-1] != equity_curve[-1]:
        result[-1] = equity_curve[-1]
    return result


class EquityCurveReport:
    """
    Builds an equity-curve section for inclusion in the full backtest report.
    """

    def build(
        self,
        equity_curve: list[tuple[float, float]],
        initial_capital: float,
        *,
        max_points: int = 500,
    ) -> dict[str, Any]:
        from iios.integration.research.backtesting.metrics.return_calculator import cumulative_returns
        from iios.integration.research.backtesting.metrics.drawdown_calculator import underwater_curve

        sampled = resample_equity_curve(equity_curve, max_points)

        return {
            "points":            [{"ts": ts, "equity": eq} for ts, eq in sampled],
            "initial_capital":   initial_capital,
            "final_equity":      equity_curve[-1][1] if equity_curve else initial_capital,
            "total_points":      len(equity_curve),
            "sampled_points":    len(sampled),
            "cumulative_returns": [
                {"ts": ts, "return_pct": r}
                for (ts, _), r in zip(sampled, cumulative_returns(sampled))
            ],
            "underwater": [
                {"ts": ts, "dd_pct": dd}
                for ts, dd in underwater_curve(sampled)
            ],
        }
