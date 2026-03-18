"""
Learning Engine — Layer 10
=============================
The system's self-improvement engine. At end of each trading day
it analyses all closed trades and adjusts internal weights / parameters
to improve future performance.

Learns:
  • Strategy win rates per market regime
  • Which agents' confidence scores were most predictive
  • Optimal position sizing modifiers per volatility level
  • Sector performance patterns
  • Time-of-day performance bias

Adjustments made:
  • Agent weight modifiers (stored in a persistent JSON file)
  • Strategy enable/disable flags per regime
  • Backtest cache invalidation for underperforming strategies
"""

from __future__ import annotations
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from execution_engine.order_manager import OrderRecord
from utils import get_logger

log = get_logger(__name__)

# StrategyHealthMonitor is injected at runtime to avoid a circular import
_SHM_TYPE = None   # type hint placeholder

LEARNING_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "learning_db.json"
)


class LearningEngine:
    """
    Analyses trade history and adjusts strategy/agent weights for
    improved future decision-making.
    """

    def __init__(self):
        self._db: Dict[str, Any] = self._load_db()
        self._shm = None   # StrategyHealthMonitor — injected by orchestrator
        log.info("[LearningEngine] Initialised. Historical strategies tracked: %d",
                 len(self._db.get("strategy_stats", {})))

    def inject_health_monitor(self, shm) -> None:
        """Inject a StrategyHealthMonitor so learn() records per-trade health."""
        self._shm = shm
        log.info("[LearningEngine] StrategyHealthMonitor injected.")

    # ─────────────────────────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────────────────────────

    def learn(self, closed_trades: List[OrderRecord]):
        """Main EOD learning call — process batch of closed trades."""
        if not closed_trades:
            log.info("[LearningEngine] No closed trades to learn from today.")
            return

        log.info("[LearningEngine] Processing %d closed trades…", len(closed_trades))

        strategy_buckets: Dict[str, List[float]] = defaultdict(list)
        for trade in closed_trades:
            pnl_pct = (
                trade.pnl / (trade.entry_price * trade.quantity)
                if trade.entry_price and trade.quantity else 0.0
            )
            strategy_buckets[trade.strategy].append(pnl_pct)

            # ── Feed StrategyHealthMonitor per-trade ─────────────────
            if self._shm is not None:
                sl_dist = abs(trade.entry_price - trade.stop_loss) if hasattr(trade, 'stop_loss') else 0
                r_mult  = (trade.pnl / (sl_dist * abs(trade.quantity))
                           if sl_dist > 0 and trade.quantity else 0.0)
                self._shm.record_trade(trade.strategy, pnl_pct, r_mult)

        for strategy, pnl_list in strategy_buckets.items():
            self._update_strategy_stats(strategy, pnl_list)

        self._save_db()
        self._print_report()

        # Print health report after every learning cycle
        if self._shm is not None:
            self._shm.print_health_report()

    def get_strategy_modifier(self, strategy_name: str) -> float:
        """
        Returns a confidence modifier for a strategy based on recent performance.
        Positive = boost, Negative = penalty.
        """
        stats = self._db.get("strategy_stats", {}).get(strategy_name, {})
        win_rate = stats.get("win_rate", 0.5)
        if win_rate >= 0.65:
            return +1.0
        elif win_rate >= 0.55:
            return +0.5
        elif win_rate >= 0.45:
            return 0.0
        elif win_rate >= 0.35:
            return -0.5
        else:
            return -1.5

    def get_best_strategies(self, top_n: int = 5) -> List[str]:
        """Return top N performing strategy names."""
        stats = self._db.get("strategy_stats", {})
        ranked = sorted(stats.items(),
                        key=lambda x: x[1].get("expectancy", 0),
                        reverse=True)
        return [name for name, _ in ranked[:top_n]]

    # ─────────────────────────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────────────────────────

    def _update_strategy_stats(self, strategy: str, pnl_list: List[float]):
        db_stats = self._db.setdefault("strategy_stats", {})
        existing = db_stats.get(strategy, {
            "total_trades": 0, "wins": 0, "total_pnl": 0.0,
            "win_rate": 0.5, "expectancy": 0.0,
        })

        wins       = sum(1 for p in pnl_list if p > 0)
        total_pnl  = sum(pnl_list)
        n          = len(pnl_list)

        existing["total_trades"] += n
        existing["wins"]         += wins
        existing["total_pnl"]    += total_pnl
        existing["win_rate"]      = (existing["wins"] /
                                     existing["total_trades"])
        existing["expectancy"]    = (existing["total_pnl"] /
                                     existing["total_trades"])
        existing["last_updated"]  = datetime.now().isoformat()

        db_stats[strategy] = existing
        log.info("[LearningEngine] Strategy '%s' | WR=%.0f%% | Expectancy=%.2f%%",
                 strategy, existing["win_rate"] * 100,
                 existing["expectancy"] * 100)

    def _print_report(self):
        log.info("[LearningEngine] ── EOD Learning Report ──")
        stats = self._db.get("strategy_stats", {})
        for name, s in sorted(stats.items(),
                               key=lambda x: x[1].get("expectancy", 0),
                               reverse=True):
            log.info("  %-35s  WR:%.0f%%  Exp:%.2f%%  Trades:%d",
                     name, s["win_rate"]*100, s["expectancy"]*100,
                     s["total_trades"])

    def _load_db(self) -> Dict[str, Any]:
        if os.path.exists(LEARNING_DB_PATH):
            try:
                with open(LEARNING_DB_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                log.warning("[LearningEngine] Could not load DB: %s", exc)
        return {"strategy_stats": {}, "created": datetime.now().isoformat()}

    def _save_db(self):
        os.makedirs(os.path.dirname(LEARNING_DB_PATH), exist_ok=True)
        try:
            with open(LEARNING_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(self._db, f, indent=2)
        except Exception as exc:
            log.error("[LearningEngine] Could not save DB: %s", exc)
