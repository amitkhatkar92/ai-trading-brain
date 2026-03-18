"""
Performance Evaluation Framework — Strategy Attribution
=======================================================
Breaks down total system P&L by strategy so you can see:

  "Iron_Condor_Range generates 60% of our profit
   but Short_Straddle_IV_Spike is consistently losing."

Metrics per strategy:
  • total_pnl           — absolute P&L contribution
  • pnl_contribution_pct — % of total system P&L
  • trade_count
  • win_rate
  • avg_win / avg_loss
  • profit_factor        — gross profit / gross loss
  • expectancy           — expected P&L per trade
  • consecutive_losses   — current streak
  • kelly_fraction       — Kelly criterion sizing suggestion
"""

from __future__ import annotations
import statistics
from dataclasses import dataclass, field
from typing import Optional

from utils import get_logger

log = get_logger(__name__)


@dataclass
class StrategyStats:
    name:            str
    trades:          int   = 0
    total_pnl:       float = 0.0
    gross_profit:    float = 0.0
    gross_loss:      float = 0.0
    wins:            int   = 0
    losses:          int   = 0
    win_pnls:        list  = field(default_factory=list)
    loss_pnls:       list  = field(default_factory=list)
    current_consec_loss: int = 0
    max_consec_loss:     int = 0

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades * 100 if self.trades else 0.0

    @property
    def avg_win(self) -> float:
        return statistics.mean(self.win_pnls) if self.win_pnls else 0.0

    @property
    def avg_loss(self) -> float:
        return statistics.mean(self.loss_pnls) if self.loss_pnls else 0.0

    @property
    def profit_factor(self) -> float:
        if self.gross_loss == 0:
            return float("inf") if self.gross_profit > 0 else 0.0
        return abs(self.gross_profit / self.gross_loss)

    @property
    def expectancy(self) -> float:
        """Expected P&L per trade = (WinRate × AvgWin) – (LossRate × |AvgLoss|)"""
        win_r  = self.wins / self.trades if self.trades else 0.0
        loss_r = 1.0 - win_r
        return win_r * self.avg_win - loss_r * abs(self.avg_loss)

    @property
    def kelly_fraction(self) -> float:
        """Kelly Criterion: f = W - (1-W)/RR, clamped to [0, 0.25]."""
        if not self.win_pnls or not self.loss_pnls:
            return 0.0
        win_r = self.win_rate / 100
        rr    = abs(self.avg_win / self.avg_loss) if self.avg_loss != 0 else 1.0
        k     = win_r - (1 - win_r) / rr if rr > 0 else 0.0
        return round(max(0.0, min(0.25, k)), 4)


class StrategyAttributionEngine:
    """
    Tracks and reports individual strategy performance contribution.

    Usage::
        attribution = StrategyAttributionEngine()
        attribution.record("Iron_Condor_Range", pnl=3200, won=True)
        attribution.record("Short_Straddle",    pnl=-900,  won=False)
        attribution.print_report()
    """

    def __init__(self) -> None:
        self._stats: dict[str, StrategyStats] = {}
        log.info("[StrategyAttribution] Initialised.")

    # ── Public API ────────────────────────────────────────────────────────
    def record(self, strategy: str, pnl: float, won: bool) -> None:
        if strategy not in self._stats:
            self._stats[strategy] = StrategyStats(name=strategy)
        s = self._stats[strategy]
        s.trades    += 1
        s.total_pnl += pnl
        if won:
            s.wins           += 1
            s.gross_profit   += pnl
            s.win_pnls.append(pnl)
            s.current_consec_loss = 0
        else:
            s.losses         += 1
            s.gross_loss     += pnl
            s.loss_pnls.append(pnl)
            s.current_consec_loss += 1
            s.max_consec_loss = max(s.max_consec_loss, s.current_consec_loss)

    def top_strategy(self) -> Optional[str]:
        if not self._stats:
            return None
        return max(self._stats.values(), key=lambda s: s.total_pnl).name

    def worst_strategy(self) -> Optional[str]:
        if not self._stats:
            return None
        return min(self._stats.values(), key=lambda s: s.total_pnl).name

    def print_report(self) -> None:
        if not self._stats:
            log.info("[StrategyAttribution] No attribution data yet.")
            return

        total_system_pnl = sum(s.total_pnl for s in self._stats.values())
        border = "═" * 80
        log.info(border)
        log.info("  STRATEGY ATTRIBUTION REPORT  |  Total System PnL: ₹%+,.0f",
                 total_system_pnl)
        log.info("─" * 80)
        log.info("  %-28s %7s %7s %10s %8s %8s %8s",
                 "Strategy", "Trades", "WinRt%",
                 "PnL(₹)", "PFactor", "Kelly%", "Contrib%")
        log.info("  " + "─" * 76)

        sorted_stats = sorted(self._stats.values(),
                              key=lambda s: s.total_pnl, reverse=True)
        for s in sorted_stats:
            contrib = (s.total_pnl / total_system_pnl * 100
                       if total_system_pnl != 0 else 0.0)
            log.info("  %-28s %7d %7.1f %+10,.0f %8.2f %7.1f%% %+7.1f%%",
                     s.name, s.trades, s.win_rate, s.total_pnl,
                     s.profit_factor, s.kelly_fraction * 100, contrib)
        log.info("  " + "─" * 76)
        top   = self.top_strategy()
        worst = self.worst_strategy()
        if top:   log.info("  🏆 Best:  %s", top)
        if worst: log.info("  📉 Worst: %s", worst)
        log.info(border)

    def to_dict(self) -> dict:
        return {
            name: {
                "trades":     s.trades,
                "pnl":        s.total_pnl,
                "win_rate":   s.win_rate,
                "pf":         s.profit_factor,
                "expectancy": s.expectancy,
                "kelly":      s.kelly_fraction,
            }
            for name, s in self._stats.items()
        }
