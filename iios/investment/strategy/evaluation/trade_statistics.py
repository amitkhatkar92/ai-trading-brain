"""iios/investment/strategy/evaluation/trade_statistics.py
Aggregate trade-level statistics from a list of Trade records.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.strategy.evaluation.trade import Trade
from iios.investment.strategy.evaluation.performance_statistics import (
    safe_mean, safe_std, percentile
)


@dataclass(frozen=True)
class TradeStatistics:
    total_trades:       int   = 0
    winning_trades:     int   = 0
    losing_trades:      int   = 0
    breakeven_trades:   int   = 0
    win_rate:           float = 0.0
    loss_rate:          float = 0.0
    avg_winner:         float = 0.0   # mean net PnL of winners
    avg_loser:          float = 0.0   # mean net PnL of losers (negative)
    largest_winner:     float = 0.0
    largest_loser:      float = 0.0
    risk_reward_ratio:  float = 0.0   # avg_winner / abs(avg_loser)
    avg_holding_days:   float = 0.0
    median_holding_days:float = 0.0
    max_holding_days:   float = 0.0
    min_holding_days:   float = 0.0
    avg_winner_holding: float = 0.0   # avg holding for winners
    avg_loser_holding:  float = 0.0   # avg holding for losers
    gross_profit:       float = 0.0
    gross_loss:         float = 0.0   # negative number
    net_pnl:            float = 0.0
    std_pnl:            float = 0.0   # std of per-trade PnL
    trade_consistency:  float = 0.0   # 1 - CoV of abs(PnL); higher = consistent
    max_consecutive_wins:  int = 0
    max_consecutive_losses: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}  # type: ignore[attr-defined]


class TradeStatisticsCalculator:

    def compute(self, trades: List[Trade]) -> TradeStatistics:
        if not trades:
            return TradeStatistics()

        n = len(trades)
        winners = [t for t in trades if t.is_winner]
        losers = [t for t in trades if t.is_loser]
        be = [t for t in trades if t.is_breakeven]

        win_rate = len(winners) / n
        loss_rate = len(losers) / n

        pnls = [t.net_pnl for t in trades]
        win_pnls = [t.net_pnl for t in winners]
        lose_pnls = [t.net_pnl for t in losers]

        avg_winner = safe_mean(win_pnls) if win_pnls else 0.0
        avg_loser = safe_mean(lose_pnls) if lose_pnls else 0.0

        gross_profit = sum(p for p in pnls if p > 0.0)
        gross_loss = sum(p for p in pnls if p < 0.0)
        net = sum(pnls)

        rr = avg_winner / abs(avg_loser) if avg_loser != 0.0 else 0.0

        holding = [t.holding_days for t in trades]
        avg_hold = safe_mean(holding)
        med_hold = percentile(holding, 50.0)

        win_hold = safe_mean([t.holding_days for t in winners]) if winners else 0.0
        lose_hold = safe_mean([t.holding_days for t in losers]) if losers else 0.0

        std_pnl = safe_std(pnls)

        # Trade consistency: 1 - CoV of absolute PnL values
        abs_pnls = [abs(p) for p in pnls]
        mean_abs = safe_mean(abs_pnls)
        std_abs = safe_std(abs_pnls) if len(abs_pnls) > 1 else 0.0
        cov = std_abs / mean_abs if mean_abs > 0.0 else 0.0
        consistency = max(0.0, 1.0 - cov)

        # Consecutive runs
        max_cw = max_cl = cw = cl = 0
        for t in trades:
            if t.is_winner:
                cw += 1
                cl = 0
                max_cw = max(max_cw, cw)
            elif t.is_loser:
                cl += 1
                cw = 0
                max_cl = max(max_cl, cl)
            else:
                cw = cl = 0

        return TradeStatistics(
            total_trades=n,
            winning_trades=len(winners),
            losing_trades=len(losers),
            breakeven_trades=len(be),
            win_rate=win_rate,
            loss_rate=loss_rate,
            avg_winner=avg_winner,
            avg_loser=avg_loser,
            largest_winner=max(win_pnls) if win_pnls else 0.0,
            largest_loser=min(lose_pnls) if lose_pnls else 0.0,
            risk_reward_ratio=rr,
            avg_holding_days=avg_hold,
            median_holding_days=med_hold,
            max_holding_days=max(holding),
            min_holding_days=min(holding),
            avg_winner_holding=win_hold,
            avg_loser_holding=lose_hold,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_pnl=net,
            std_pnl=std_pnl,
            trade_consistency=consistency,
            max_consecutive_wins=max_cw,
            max_consecutive_losses=max_cl,
        )
