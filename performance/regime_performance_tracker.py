"""
Performance Evaluation Framework — Regime Performance Tracker
==============================================================
Tracks strategy performance broken down by market regime so the
system can identify WHICH regimes each strategy actually works in.

Maintained buckets per regime:
  bull_trend, bear_trend, range_market, high_volatility

Per bucket tracked:
  • trade count
  • total P&L
  • win rate
  • average R-multiple
  • best / worst trade

Regime awareness is critical: a strategy may be highly profitable
in bull_trend but consistently lose in high_volatility.
"""

from __future__ import annotations
import collections
import statistics
from dataclasses import dataclass, field
from typing import Optional

from utils import get_logger

log = get_logger(__name__)

KNOWN_REGIMES = ("bull_trend", "bear_trend", "range_market",
                 "high_volatility", "unknown")


@dataclass
class RegimeStat:
    regime:       str
    trade_count:  int   = 0
    total_pnl:    float = 0.0
    wins:         int   = 0
    losses:       int   = 0
    pnl_list:     list  = field(default_factory=list)
    r_list:       list  = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        return self.wins / self.trade_count * 100 if self.trade_count else 0.0

    @property
    def avg_r(self) -> float:
        return statistics.mean(self.r_list) if self.r_list else 0.0

    @property
    def best_pnl(self) -> float:
        return max(self.pnl_list) if self.pnl_list else 0.0

    @property
    def worst_pnl(self) -> float:
        return min(self.pnl_list) if self.pnl_list else 0.0

    def summary_row(self) -> str:
        return (f"  {self.regime:<18} Trades={self.trade_count:>4} | "
                f"WinRate={self.win_rate:>5.1f}% | "
                f"PnL=₹{self.total_pnl:>+10,.0f} | "
                f"AvgR={self.avg_r:>+.2f}")


class RegimePerformanceTracker:
    """
    Records trade outcomes segmented by the market regime at trade entry.

    Usage::
        tracker = RegimePerformanceTracker()
        tracker.record("bull_trend",  pnl=2500, r=1.2, won=True)
        tracker.record("high_volatility", pnl=-800, r=-0.8, won=False)
        tracker.print_report()
    """

    def __init__(self) -> None:
        self._stats: dict[str, RegimeStat] = {
            r: RegimeStat(regime=r) for r in KNOWN_REGIMES
        }
        # Per-strategy per-regime matrix
        self._strat_regime: dict[str, dict[str, list[float]]] = \
            collections.defaultdict(lambda: collections.defaultdict(list))
        log.info("[RegimePerformanceTracker] Initialised. Tracking %d regimes.",
                 len(KNOWN_REGIMES))

    # ── Public API ────────────────────────────────────────────────────────
    def record(self, regime: str, pnl: float, r: float,
               won: bool, strategy: str = "unknown") -> None:
        bucket = self._stats.get(regime, self._stats["unknown"])
        bucket.trade_count += 1
        bucket.total_pnl   += pnl
        bucket.pnl_list.append(pnl)
        bucket.r_list.append(r)
        if won:
            bucket.wins += 1
        else:
            bucket.losses += 1
        self._strat_regime[strategy][regime].append(pnl)

    def get_best_regime(self) -> Optional[str]:
        candidates = [s for s in self._stats.values()
                      if s.trade_count >= 3]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s.total_pnl).regime

    def get_worst_regime(self) -> Optional[str]:
        candidates = [s for s in self._stats.values()
                      if s.trade_count >= 3]
        if not candidates:
            return None
        return min(candidates, key=lambda s: s.total_pnl).regime

    def print_report(self) -> None:
        border = "═" * 70
        log.info(border)
        log.info("  REGIME PERFORMANCE BREAKDOWN")
        log.info("─" * 70)
        log.info("  %-18s %-8s %-10s %-14s %-8s",
                 "Regime", "Trades", "WinRate", "PnL", "AvgR")
        log.info("  " + "─" * 66)
        for stat in self._stats.values():
            if stat.trade_count == 0:
                continue
            log.info(stat.summary_row())
        best  = self.get_best_regime()
        worst = self.get_worst_regime()
        log.info("  " + "─" * 66)
        if best:   log.info("  ✅ Best regime:  %s", best)
        if worst:  log.info("  ❌ Worst regime: %s", worst)
        log.info(border)

    def to_dict(self) -> dict:
        return {
            r: {
                "trades":   s.trade_count,
                "pnl":      s.total_pnl,
                "win_rate": s.win_rate,
                "avg_r":    s.avg_r,
            }
            for r, s in self._stats.items() if s.trade_count > 0
        }
