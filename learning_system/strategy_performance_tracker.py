"""
Strategy Performance Tracker — Q3 Learning Mechanism 1
========================================================
Tracks every trade outcome and maintains running statistics per strategy.

What it tracks (per strategy)
──────────────────────────────
  • total trades
  • wins / losses
  • win rate (%)
  • average R-multiple (return in R units)
  • expectancy (win_rate × avg_win_R - loss_rate × avg_loss_R)
  • consecutive losses
  • last 20 trades (rolling)

Auto-disable rules
──────────────────
  A strategy is AUTO-DISABLED when ANY of these trigger:
    1. win_rate  < 35%   AND  trades >= MIN_SAMPLE
    2. expectancy < -0.3R AND  trades >= MIN_SAMPLE
    3. consecutive_losses >= 5

  Auto-enable (recovery) rules:
    • Disabled strategy may be re-tested after COOLDOWN_TRADES new trades
      by the system (paper mode, 2-trade micro-test batch)

Persistence
───────────
  Stats are stored in  data/strategy_performance.json
  and reloaded on startup so learning survives restarts.

Usage
──────
  tracker = StrategyPerformanceTracker()
  tracker.record_trade("Breakout_Volume", pnl_r=+1.8)
  tracker.record_trade("Mean_Reversion",  pnl_r=-1.0)
  print(tracker.get_table())              # full leaderboard
  active = tracker.get_active_strategies(["Breakout_Volume", "Mean_Reversion"])
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

# ── Tuning ────────────────────────────────────────────────────────────────────
MIN_SAMPLE          = 10      # need at least this many trades to auto-disable
WIN_RATE_FLOOR      = 0.35    # below 35% win rate → disable
EXPECTANCY_FLOOR    = -0.30   # below -0.3R expectancy → disable
MAX_CONSEC_LOSSES   = 5       # 5 consecutive losses → disable

PERF_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "strategy_performance.json"
)


@dataclass
class StrategyStats:
    name:             str
    total_trades:     int   = 0
    wins:             int   = 0
    losses:           int   = 0
    total_r:          float = 0.0    # sum of R multiples
    win_r:            float = 0.0    # sum of positive R
    loss_r:           float = 0.0    # sum of negative R (stored positive)
    consec_losses:    int   = 0
    enabled:          bool  = True
    disabled_reason:  str   = ""
    last_trades:      List[float] = field(default_factory=list)   # last 20 R values
    last_updated:     str   = ""

    @property
    def win_rate(self) -> float:
        return self.wins / self.total_trades if self.total_trades else 0.0

    @property
    def avg_r(self) -> float:
        return self.total_r / self.total_trades if self.total_trades else 0.0

    @property
    def avg_win_r(self) -> float:
        return self.win_r / self.wins if self.wins else 0.0

    @property
    def avg_loss_r(self) -> float:
        return self.loss_r / self.losses if self.losses else 0.0

    @property
    def expectancy(self) -> float:
        """Expected R per trade = win_rate × avg_win - loss_rate × avg_loss."""
        wr = self.win_rate
        lr = 1.0 - wr
        return round(wr * self.avg_win_r - lr * self.avg_loss_r, 4)

    def to_row(self) -> dict:
        return {
            "Strategy":        self.name,
            "Trades":          self.total_trades,
            "Win%":            f"{self.win_rate * 100:.1f}%",
            "Avg R":           f"{self.avg_r:+.2f}R",
            "Expectancy":      f"{self.expectancy:+.3f}R",
            "Consec Losses":   self.consec_losses,
            "Status":          "✅ ACTIVE" if self.enabled else f"⛔ DISABLED ({self.disabled_reason})",
        }


class StrategyPerformanceTracker:
    """
    Per-strategy P&L ledger with automatic disable/enable logic.
    """

    def __init__(self) -> None:
        self._stats: Dict[str, StrategyStats] = {}
        self._load()
        log.info("[StrategyPerformanceTracker] Loaded %d strategy records.", len(self._stats))

    # ── Public API ────────────────────────────────────────────────────────────

    def record_trade(self, strategy: str, pnl_r: float) -> StrategyStats:
        """
        Record a completed trade for a strategy.

        Parameters
        ----------
        strategy : strategy name, e.g. "Breakout_Volume"
        pnl_r    : trade P&L in R multiples (+1.5 = win, -1.0 = loss)

        Returns the updated StrategyStats.
        """
        s = self._get_or_create(strategy)
        s.total_trades += 1
        s.total_r      += pnl_r
        s.last_trades   = (s.last_trades + [pnl_r])[-20:]  # keep last 20
        s.last_updated  = datetime.now().strftime("%Y-%m-%d %H:%M")

        if pnl_r >= 0:
            s.wins      += 1
            s.win_r     += pnl_r
            s.consec_losses = 0
        else:
            s.losses    += 1
            s.loss_r    += abs(pnl_r)
            s.consec_losses += 1

        # ── Auto-disable checks ────────────────────────────────────────────
        if s.enabled:
            self._check_disable(s)

        self._save()
        log.info("[PerfTracker] %s | trade=%+.2fR | winrate=%.0f%% | E=%.3fR | status=%s",
                 strategy, pnl_r, s.win_rate * 100, s.expectancy,
                 "ACTIVE" if s.enabled else "DISABLED")
        return s

    def get_active_strategies(self, candidates: List[str]) -> List[str]:
        """Filter a list of strategy names to only those currently enabled."""
        result = []
        for name in candidates:
            s = self._stats.get(name)
            if s is None or s.enabled:
                result.append(name)   # unknown = assume active (no data yet)
        return result

    def get_disabled_set(self) -> set:
        """
        Return the set of strategy names that have been auto-disabled.
        Used by the orchestrator to subtract from the MSC passing_set.
        """
        return {name for name, s in self._stats.items() if not s.enabled}

    def get_performance_weight(self, strategy: str) -> float:
        """
        Return a capital-size multiplier (0.5 – 2.0) based on the strategy's
        live expectancy.  Used by PortfolioAllocationAI to tilt capital toward
        high-expectancy strategies and away from struggling ones.

        Formula  :  weight = clamp(1.0 + expectancy, 0.5, 2.0)
        Examples :
          E = +0.50R  →  1.5×  (strong — allocate more)
          E =  0.00R  →  1.0×  (neutral)
          E = −0.20R  →  0.8×  (weak but not retired)
          No data yet  →  1.0×  (prior = neutral)
        """
        s = self._stats.get(strategy)
        if s is None or s.total_trades == 0:
            return 1.0   # prior: neutral until we have data
        return max(0.5, min(2.0, 1.0 + s.expectancy))

    def get_table(self) -> str:
        """Return a formatted leaderboard string (for logging / Telegram)."""
        if not self._stats:
            return "No strategy performance data yet."
        rows = sorted(self._stats.values(),
                      key=lambda s: s.expectancy, reverse=True)
        lines = [
            "📊 <b>Strategy Leaderboard</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        for r in rows:
            row = r.to_row()
            lines.append(
                f"  <b>{row['Strategy']}</b>  "
                f"W:{row['Win%']}  AvgR:{row['Avg R']}  E:{row['Expectancy']}  "
                f"{row['Status']}"
            )
        return "\n".join(lines)

    def get_stats(self, strategy: str) -> Optional[StrategyStats]:
        return self._stats.get(strategy)

    def get_all_stats(self) -> Dict[str, StrategyStats]:
        return dict(self._stats)

    def re_enable(self, strategy: str) -> None:
        """Manually re-enable a disabled strategy (e.g. after regime change)."""
        if strategy in self._stats:
            self._stats[strategy].enabled        = True
            self._stats[strategy].disabled_reason = ""
            self._stats[strategy].consec_losses   = 0
            log.info("[PerfTracker] %s manually re-enabled.", strategy)
            self._save()

    # ── Auto-disable logic ────────────────────────────────────────────────────

    def _check_disable(self, s: StrategyStats) -> None:
        if s.total_trades < MIN_SAMPLE:
            return   # not enough data yet

        reason = ""
        if s.win_rate < WIN_RATE_FLOOR:
            reason = f"win_rate={s.win_rate:.0%}<{WIN_RATE_FLOOR:.0%}"
        elif s.expectancy < EXPECTANCY_FLOOR:
            reason = f"expectancy={s.expectancy:.3f}R<{EXPECTANCY_FLOOR}R"
        elif s.consec_losses >= MAX_CONSEC_LOSSES:
            reason = f"{s.consec_losses} consecutive_losses"

        if reason:
            s.enabled        = False
            s.disabled_reason = reason
            log.warning("[PerfTracker] ⛔ AUTO-DISABLED: %s — %s", s.name, reason)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _get_or_create(self, strategy: str) -> StrategyStats:
        if strategy not in self._stats:
            self._stats[strategy] = StrategyStats(name=strategy)
        return self._stats[strategy]

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(PERF_FILE), exist_ok=True)
            data = {k: asdict(v) for k, v in self._stats.items()}
            with open(PERF_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            log.warning("[PerfTracker] Save failed: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(PERF_FILE):
            return
        try:
            with open(PERF_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, raw in data.items():
                # Drop computed properties if they were accidentally serialised
                for computed in ("win_rate", "avg_r", "avg_win_r", "avg_loss_r", "expectancy"):
                    raw.pop(computed, None)
                self._stats[name] = StrategyStats(**raw)
        except Exception as exc:
            log.warning("[PerfTracker] Load failed: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────
_TRACKER: Optional[StrategyPerformanceTracker] = None


def get_performance_tracker() -> StrategyPerformanceTracker:
    global _TRACKER
    if _TRACKER is None:
        _TRACKER = StrategyPerformanceTracker()
    return _TRACKER
