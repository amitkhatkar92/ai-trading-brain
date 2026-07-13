"""iios/investment/strategy/evaluation/execution_quality.py
Execution quality metrics: slippage, fill efficiency, timing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.strategy.evaluation.trade import Trade
from iios.investment.strategy.evaluation.performance_statistics import (
    safe_mean, safe_std, percentile
)


@dataclass(frozen=True)
class ExecutionMetrics:
    avg_entry_slippage:  float = 0.0   # mean entry slippage in price units
    avg_exit_slippage:   float = 0.0
    avg_total_slippage:  float = 0.0
    slippage_pct:        float = 0.0   # avg total slippage as % of notional
    avg_commission:      float = 0.0
    commission_drag:     float = 0.0   # commission / gross profit (0 = free)
    execution_efficiency: float = 0.0  # 1 - slippage_pct (capped at 1)
    fill_rate:           float = 1.0   # assumed 100 % unless metadata differs
    p95_slippage:        float = 0.0   # 95th pct total slippage
    total_commission:    float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}  # type: ignore[attr-defined]


class ExecutionQualityAnalyzer:

    def analyze(self, trades: List[Trade]) -> ExecutionMetrics:
        if not trades:
            return ExecutionMetrics()

        entry_slips = [t.entry_slippage for t in trades]
        exit_slips = [t.exit_slippage for t in trades]
        total_slips = [t.total_slippage_pts for t in trades]
        slip_pcts = [t.slippage_pct for t in trades]
        commissions = [t.commission for t in trades]

        avg_slip_pct = safe_mean(slip_pcts)
        exec_eff = max(0.0, min(1.0, 1.0 - avg_slip_pct))

        gross_profit = sum(t.gross_pnl for t in trades if t.gross_pnl > 0.0)
        total_commission = sum(commissions)
        commission_drag = (
            total_commission / gross_profit if gross_profit > 0.0 else 0.0
        )

        return ExecutionMetrics(
            avg_entry_slippage=safe_mean([abs(s) for s in entry_slips]),
            avg_exit_slippage=safe_mean([abs(s) for s in exit_slips]),
            avg_total_slippage=safe_mean([abs(s) for s in total_slips]),
            slippage_pct=avg_slip_pct,
            avg_commission=safe_mean(commissions),
            commission_drag=commission_drag,
            execution_efficiency=exec_eff,
            fill_rate=1.0,
            p95_slippage=percentile(sorted(total_slips), 95.0),
            total_commission=total_commission,
        )
