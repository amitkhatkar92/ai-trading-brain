"""iios/investment/strategy/evaluation/performance_engine.py
Computes PerformanceMetrics from EvaluationInput.
All calculations delegated to performance_statistics (pure functions).
"""
from __future__ import annotations

import math
import logging

from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput
from iios.investment.strategy.evaluation.performance_metrics import PerformanceMetrics
from iios.investment.strategy.evaluation.performance_statistics import (
    annualized_return,
    alpha,
    beta,
    calmar_ratio,
    expectancy,
    information_ratio,
    profit_factor,
    recovery_factor,
    safe_mean,
    sharpe_ratio,
    sortino_ratio,
    treynor_ratio,
)

logger = logging.getLogger(__name__)

# minimum data required to compute meaningful metrics
_MIN_PERIODS = 5
_MIN_TRADES = 1


class PerformanceEngine:
    """Stateless performance metric calculator."""

    def compute(self, inp: EvaluationInput) -> PerformanceMetrics:
        """Compute all performance metrics from EvaluationInput."""
        curve = inp.equity_curve
        trades = inp.trades
        rf = inp.risk_free_rate
        ppy = inp.periods_per_year
        rf_per_period = inp.rf_per_period

        if curve.is_empty():
            logger.warning("PerformanceEngine: empty equity curve for %s", inp.strategy_id)
            return PerformanceMetrics(n_trades=len(trades), risk_free_rate=rf)

        returns = curve.period_returns
        total_ret = curve.total_return
        dur_years = curve.duration_years
        ann_ret = annualized_return(total_ret, dur_years) if dur_years > 0 else 0.0

        # Drawdown needed for Calmar / recovery factor
        dd_series = curve.drawdown_series()
        max_dd = max(dd_series) if dd_series else 0.0
        # Max drawdown in currency units (for recovery factor denominator)
        peaks = curve.running_peak()
        max_dd_currency = max(
            (pk - pt.value) for pk, pt in zip(peaks, curve.points)
        ) if peaks else 0.0

        # Trade aggregates
        pnls = [t.net_pnl for t in trades]
        winners = [t for t in trades if t.is_winner]
        losers = [t for t in trades if t.is_loser]
        avg_winner = safe_mean([t.net_pnl for t in winners]) if winners else 0.0
        avg_loser = safe_mean([abs(t.net_pnl) for t in losers]) if losers else 0.0
        win_rate = len(winners) / len(trades) if trades else 0.0
        pf = profit_factor(pnls)
        exp = expectancy(win_rate, avg_winner, avg_loser)
        rf_val = recovery_factor(sum(pnls), max_dd_currency) if pnls else 0.0

        # Ratios
        sr = sharpe_ratio(returns, rf_per_period, ppy) if len(returns) >= _MIN_PERIODS else 0.0
        srt = sortino_ratio(returns, rf_per_period, ppy) if len(returns) >= _MIN_PERIODS else 0.0
        cr = calmar_ratio(ann_ret, max_dd)

        # Benchmark-dependent
        beta_val, alpha_val, ir, tr = 0.0, 0.0, 0.0, 0.0
        ann_bench = 0.0
        if inp.has_benchmark:
            bench = inp.benchmark_curve
            b_returns = bench.period_returns
            n = min(len(returns), len(b_returns))
            if n >= _MIN_PERIODS:
                s_r = returns[:n]
                b_r = b_returns[:n]
                beta_val = beta(s_r, b_r)
                ann_bench = annualized_return(bench.total_return, bench.duration_years)
                alpha_val = alpha(ann_ret, ann_bench, beta_val, rf)
                ir = information_ratio(s_r, b_r, ppy)
                tr = treynor_ratio(ann_ret, beta_val, rf)

        # Clamp infinities for storage
        def _safe(v: float) -> float:
            if not math.isfinite(v):
                return 0.0
            return v

        return PerformanceMetrics(
            total_return=total_ret,
            annualized_return=ann_ret,
            alpha=_safe(alpha_val),
            beta=beta_val,
            information_ratio=_safe(ir),
            sharpe_ratio=_safe(sr),
            sortino_ratio=_safe(srt),
            calmar_ratio=_safe(cr),
            treynor_ratio=_safe(tr),
            profit_factor=_safe(pf),
            recovery_factor=_safe(rf_val),
            expectancy=exp,
            n_periods=curve.length,
            duration_years=dur_years,
            n_trades=len(trades),
            risk_free_rate=rf,
        )
