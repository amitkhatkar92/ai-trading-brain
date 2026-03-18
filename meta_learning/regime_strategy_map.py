"""
Regime-Strategy Performance Map — Q3 Learning Mechanism 2
===========================================================
The system learns WHICH strategy performs best in WHICH market regime.

Over time this table evolves:

  ┌──────────────────┬─────────────────────────┬──────────────┬──────────────┐
  │ Market Regime    │ Best Strategy           │ Win Rate     │ Avg R        │
  ├──────────────────┼─────────────────────────┼──────────────┼──────────────┤
  │ BULL_TREND       │ Breakout_Volume         │ 67%          │ +1.8R        │
  │ RANGE_MARKET     │ Iron_Condor_Range       │ 58%          │ +1.1R        │
  │ VOLATILE         │ Short_Straddle_IV_Spike │ 52%          │ +0.9R        │
  │ BEAR_MARKET      │ Hedging_Model           │ 71%          │ +2.1R        │
  └──────────────────┴─────────────────────────┴──────────────┴──────────────┘

How it learns
─────────────
  After each completed trade, record which regime was active at entry.
  The map accumulates regime-tagged performance records and calculates
  best-fit strategy ranking per regime.

  At deep-scan time, MetaStrategyController queries this map to:
    1. Rank candidate strategies by historical regime performance
    2. Boost allocation weight for regime-proven strategies
    3. Reduce weight for strategies with negative regime history

Persistence
───────────
  data/regime_strategy_map.json   (JSON, updated after each trade)

Usage
──────
  rsm = RegimeStrategyMap()
  rsm.record(regime="BULL_TREND", strategy="Breakout_Volume", pnl_r=+1.8)
  best = rsm.best_for_regime("BULL_TREND")   # → "Breakout_Volume"
  ranked = rsm.rank_strategies("BULL_TREND", ["Breakout_Volume", "Mean_Reversion"])
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

MAP_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "regime_strategy_map.json"
)

# Minimum trades in a regime before rankings are trusted
MIN_REGIME_TRADES = 5


@dataclass
class RegimeEntry:
    regime:    str
    strategy:  str
    trades:    int   = 0
    wins:      int   = 0
    total_r:   float = 0.0
    win_r:     float = 0.0
    loss_r:    float = 0.0

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades if self.trades else 0.0

    @property
    def avg_r(self) -> float:
        return self.total_r / self.trades if self.trades else 0.0

    @property
    def avg_win_r(self) -> float:
        return self.win_r / self.wins if self.wins else 0.0

    @property
    def avg_loss_r(self) -> float:
        lr = self.trades - self.wins
        return self.loss_r / lr if lr else 0.0

    @property
    def expectancy(self) -> float:
        wr  = self.win_rate
        lr  = 1.0 - wr
        return round(wr * self.avg_win_r - lr * self.avg_loss_r, 4)

    @property
    def reliable(self) -> bool:
        """True once there's enough data to trust the stats."""
        return self.trades >= MIN_REGIME_TRADES


class RegimeStrategyMap:
    """
    Learns and stores per-regime strategy performance.
    Used by MetaStrategyController to rank strategies dynamically.
    """

    def __init__(self) -> None:
        # key: (regime, strategy) → RegimeEntry
        self._map: Dict[Tuple[str, str], RegimeEntry] = {}
        self._load()
        log.info("[RegimeStrategyMap] Loaded %d regime-strategy pairs.", len(self._map))

    # ── Public API ────────────────────────────────────────────────────────────

    def record(self, regime: str, strategy: str, pnl_r: float) -> None:
        """
        Record the outcome of a trade tagged with the active regime.

        Parameters
        ----------
        regime   : "BULL_TREND" | "RANGE_MARKET" | "BEAR_MARKET" | "VOLATILE"
        strategy : strategy name, e.g. "Breakout_Volume"
        pnl_r    : trade P&L in R multiples
        """
        key = (regime, strategy)
        if key not in self._map:
            self._map[key] = RegimeEntry(regime=regime, strategy=strategy)

        e = self._map[key]
        e.trades  += 1
        e.total_r += pnl_r
        if pnl_r >= 0:
            e.wins   += 1
            e.win_r  += pnl_r
        else:
            e.loss_r += abs(pnl_r)

        log.debug("[RegimeStrategyMap] %s|%s → %+.2fR  (total=%d  E=%.3fR)",
                  regime, strategy, pnl_r, e.trades, e.expectancy)
        self._save()

    def best_for_regime(self, regime: str) -> Optional[str]:
        """
        Return the name of the best-performing strategy in a given regime.
        Only considers strategies with enough sample data.
        Returns None if no reliable data exists yet.
        """
        candidates = [e for (r, _), e in self._map.items()
                      if r == regime and e.reliable]
        if not candidates:
            return None
        best = max(candidates, key=lambda e: e.expectancy)
        return best.strategy

    def rank_strategies(
        self, regime: str, candidates: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Rank candidate strategies by their expectancy in the given regime.

        Returns list of (strategy_name, score) sorted best-first.
        Strategies with no regime data get a neutral score of 0.0.
        """
        result = []
        for s in candidates:
            key = (regime, s)
            e = self._map.get(key)
            if e and e.reliable:
                score = e.expectancy
            else:
                score = 0.0   # no data → neutral
            result.append((s, score))
        result.sort(key=lambda x: x[1], reverse=True)
        return result

    def get_regime_table(self, regime: Optional[str] = None) -> str:
        """
        Return a formatted table string (for logging / Telegram /edges command).
        If regime is None, show all regimes.
        """
        rows = [e for (r, _), e in self._map.items()
                if (regime is None or r == regime)]
        if not rows:
            return "No regime-strategy performance data yet."

        lines = ["🔬 <b>Regime → Strategy Performance</b>",
                 "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
        prev_regime = None
        rows_sorted = sorted(rows, key=lambda e: (e.regime, -e.expectancy))
        for e in rows_sorted:
            if e.regime != prev_regime:
                lines.append(f"\n<b>{e.regime}</b>")
                prev_regime = e.regime
            reliable_tag = "" if e.reliable else " ⚠️ (low sample)"
            lines.append(
                f"  {e.strategy:30}  "
                f"W:{e.win_rate*100:.0f}%  "
                f"AvgR:{e.avg_r:+.2f}  "
                f"E:{e.expectancy:+.3f}R  "
                f"n={e.trades}{reliable_tag}"
            )
        return "\n".join(lines)

    # ── Learning timeline helper ───────────────────────────────────────────────

    @property
    def total_trades(self) -> int:
        return sum(e.trades for e in self._map.values())

    def learning_stage(self) -> str:
        """Return a human-readable learning stage based on trade count."""
        n = self.total_trades
        if n < 30:
            return f"🌱 Learning execution ({n} trades — target 30 for first insights)"
        elif n < 100:
            return f"📈 Building patterns ({n} trades — target 100 for strategy ranking)"
        elif n < 250:
            return f"🧠 Strategy optimization ({n} trades — reliable regime mapping forming)"
        else:
            return f"⚡ Adaptive intelligence active ({n} trades)"

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(MAP_FILE), exist_ok=True)
            data = {
                f"{r}|{s}": asdict(e)
                for (r, s), e in self._map.items()
            }
            with open(MAP_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            log.warning("[RegimeStrategyMap] Save failed: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(MAP_FILE):
            return
        try:
            with open(MAP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key_str, raw in data.items():
                regime, strategy = key_str.split("|", 1)
                for computed in ("win_rate", "avg_r", "avg_win_r", "avg_loss_r",
                                 "expectancy", "reliable"):
                    raw.pop(computed, None)
                self._map[(regime, strategy)] = RegimeEntry(**raw)
        except Exception as exc:
            log.warning("[RegimeStrategyMap] Load failed: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────
_RSM: Optional[RegimeStrategyMap] = None


def get_regime_strategy_map() -> RegimeStrategyMap:
    global _RSM
    if _RSM is None:
        _RSM = RegimeStrategyMap()
    return _RSM
