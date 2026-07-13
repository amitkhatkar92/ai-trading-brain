"""iios/investment/strategy/evaluation/trade_distribution.py
Distribution analysis of trade PnL, holding times, and symbol concentration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from iios.investment.strategy.evaluation.trade import Trade
from iios.investment.strategy.evaluation.performance_statistics import (
    safe_mean, safe_std, percentile
)


@dataclass(frozen=True)
class TradeDistribution:
    # PnL distribution
    pnl_mean:      float = 0.0
    pnl_std:       float = 0.0
    pnl_skewness:  float = 0.0  # positive = right-skewed (wins bigger)
    pnl_kurtosis:  float = 0.0  # excess kurtosis
    pnl_p5:        float = 0.0
    pnl_p25:       float = 0.0
    pnl_p50:       float = 0.0
    pnl_p75:       float = 0.0
    pnl_p95:       float = 0.0

    # Holding-time distribution
    hold_mean_days: float = 0.0
    hold_std_days:  float = 0.0
    hold_p50_days:  float = 0.0

    # Concentration
    symbol_count:  int   = 0
    top_symbol_pct: float = 0.0  # fraction of trades in most-traded symbol

    # Temporal clustering
    trades_per_day: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}  # type: ignore[attr-defined]


class TradeDistributionAnalyzer:

    def analyze(self, trades: List[Trade]) -> TradeDistribution:
        if not trades:
            return TradeDistribution()

        pnls = [t.net_pnl for t in trades]
        n = len(pnls)

        pnl_mean = safe_mean(pnls)
        pnl_std = safe_std(pnls)

        # Skewness and excess kurtosis
        if pnl_std > 0.0 and n >= 3:
            skew = sum(((p - pnl_mean) / pnl_std) ** 3 for p in pnls) / n
        else:
            skew = 0.0

        if pnl_std > 0.0 and n >= 4:
            kurt = sum(((p - pnl_mean) / pnl_std) ** 4 for p in pnls) / n - 3.0
        else:
            kurt = 0.0

        sorted_pnls = sorted(pnls)
        pnl_p5 = percentile(sorted_pnls, 5.0)
        pnl_p25 = percentile(sorted_pnls, 25.0)
        pnl_p50 = percentile(sorted_pnls, 50.0)
        pnl_p75 = percentile(sorted_pnls, 75.0)
        pnl_p95 = percentile(sorted_pnls, 95.0)

        holding = [t.holding_days for t in trades]
        hold_mean = safe_mean(holding)
        hold_std = safe_std(holding)
        hold_p50 = percentile(sorted(holding), 50.0)

        # Symbol concentration
        sym_counts: Dict[str, int] = {}
        for t in trades:
            sym_counts[t.symbol] = sym_counts.get(t.symbol, 0) + 1
        n_symbols = len(sym_counts)
        top_pct = max(sym_counts.values()) / n if sym_counts else 0.0

        # Trades per calendar day
        if len(trades) >= 2:
            first = min(t.entry_time for t in trades)
            last = max(t.exit_time for t in trades)
            days = (last - first).total_seconds() / 86_400.0
            tpd = n / days if days > 0.0 else 0.0
        else:
            tpd = 0.0

        return TradeDistribution(
            pnl_mean=pnl_mean,
            pnl_std=pnl_std,
            pnl_skewness=skew,
            pnl_kurtosis=kurt,
            pnl_p5=pnl_p5,
            pnl_p25=pnl_p25,
            pnl_p50=pnl_p50,
            pnl_p75=pnl_p75,
            pnl_p95=pnl_p95,
            hold_mean_days=hold_mean,
            hold_std_days=hold_std,
            hold_p50_days=hold_p50,
            symbol_count=n_symbols,
            top_symbol_pct=top_pct,
            trades_per_day=tpd,
        )
