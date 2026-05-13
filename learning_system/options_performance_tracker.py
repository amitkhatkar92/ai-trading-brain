"""
Options Performance Tracker  (Self-Learning Engine)
=====================================================
Records every closed options trade and learns which strategies work
best in which market regimes.

Learning loop:
  Close trade → record outcome → update regime×strategy win-rate
             → adjust weight → notify risk engine if streak detected
             → persist to JSON

Weight adaptation rules:
  win_rate > 60 % in current regime → increase weight +0.05 (cap 1.0)
  win_rate < 40 % in current regime → decrease weight −0.10 (floor 0.1)
  3+ consecutive losses             → flag for risk engine to disable

Weights are used by OptionsOpportunityAI._base_confidence() as a
multiplicative modifier.  Higher weight → higher confidence score
→ more likely to pass the MIN_CONFIDENCE threshold.

Persistence:
  data/options_outcomes.json   — full trade history
  data/options_weights.json    — current strategy×regime weights
"""

from __future__ import annotations

import json
import os
import threading
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from utils import get_logger

if TYPE_CHECKING:
    from execution_engine.options_order_manager import OptionsOrderRecord

log = get_logger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
OUTCOMES_PATH = "data/options_outcomes.json"
WEIGHTS_PATH  = "data/options_weights.json"

# ── Learning hyper-parameters ──────────────────────────────────────────────
WIN_RATE_GOOD   = 0.60    # above this → increase weight
WIN_RATE_BAD    = 0.40    # below this → decrease weight
WEIGHT_INCREASE = 0.05
WEIGHT_DECREASE = 0.10
WEIGHT_MIN      = 0.10
WEIGHT_MAX      = 1.00
MIN_TRADES_TO_JUDGE = 5   # need at least this many trades before adapting
STREAK_WINDOW   = 20      # rolling window for win-rate calculation


class OptionsPerformanceTracker:
    """
    Tracks outcomes of options trades and updates strategy weights.

    Thread-safe — designed to be called from the OptionsOrderManager
    _close_position() hook.
    """

    def __init__(self) -> None:
        self._lock        = threading.Lock()
        self._outcomes:   List[Dict[str, Any]] = []
        self._weights:    Dict[str, float]     = {}
        # streak tracking: (strategy_type, regime) → deque of True/False (win/loss)
        self._streaks:    Dict[str, deque]     = defaultdict(lambda: deque(maxlen=STREAK_WINDOW))
        self._load()
        log.info(
            "[OptionsPerformanceTracker] Loaded %d outcomes, %d weight entries.",
            len(self._outcomes), len(self._weights),
        )

    # ── Public: record a closed trade ─────────────────────────────────

    def record_closed_trade(self, rec: "OptionsOrderRecord") -> None:
        """
        Record outcome of a closed options position and update weights.
        Call this after every options position close.
        """
        outcome = {
            "order_id":       rec.order_id,
            "symbol":         rec.symbol,
            "strategy_type":  rec.option_type,
            "regime":         rec.regime_at_entry,
            "lots":           rec.lots,
            "lot_size":       rec.lot_size,
            "entry_premium":  rec.entry_premium,
            "exit_premium":   rec.exit_premium,
            "pnl_rs":         rec.pnl_rs,
            "dte_at_entry":   rec.dte_at_entry,
            "iv_rank":        rec.iv_rank_at_entry,
            "exit_reason":    rec.exit_reason,
            "placed_at":      rec.placed_at.strftime("%Y-%m-%d %H:%M:%S"),
            "closed_at":      rec.closed_at.strftime("%Y-%m-%d %H:%M:%S") if rec.closed_at else "",
            "win":            rec.pnl_rs > 0,
        }

        with self._lock:
            self._outcomes.append(outcome)
            key = self._key(rec.option_type, rec.regime_at_entry)
            self._streaks[key].append(rec.pnl_rs > 0)
            self._adapt_weight(rec.option_type, rec.regime_at_entry)

        self._persist()

        log.info(
            "[OptionsPerformanceTracker] Recorded %s %s  PnL=₹%.0f  win=%s",
            rec.option_type, rec.regime_at_entry, rec.pnl_rs, rec.pnl_rs > 0,
        )

    # ── Public: query weights ──────────────────────────────────────────

    def get_weight(self, strategy_type: str, regime: str) -> float:
        """
        Return the current weight (0.10–1.00) for a strategy×regime pair.
        Used as a confidence multiplier in OptionsOpportunityAI.
        """
        with self._lock:
            return self._weights.get(self._key(strategy_type, regime), 1.0)

    def get_win_rate(self, strategy_type: str, regime: str) -> float:
        """Return rolling win rate for a strategy×regime pair (0.0–1.0)."""
        with self._lock:
            buf = self._streaks.get(self._key(strategy_type, regime), deque())
            if not buf:
                return 0.5
            return sum(buf) / len(buf)

    def get_consecutive_losses(self, strategy_type: str, regime: str) -> int:
        """Count consecutive losses at the tail of the rolling window."""
        with self._lock:
            buf = list(self._streaks.get(self._key(strategy_type, regime), deque()))
        streak = 0
        for win in reversed(buf):
            if not win:
                streak += 1
            else:
                break
        return streak

    def summary(self) -> str:
        """Human-readable summary of current weights."""
        lines = ["[OptionsPerformanceTracker] Strategy weights:"]
        with self._lock:
            for k, w in sorted(self._weights.items()):
                lines.append(f"  {k}: {w:.2f}")
        return "\n".join(lines)

    # ── Private: weight adaptation ─────────────────────────────────────

    def _adapt_weight(self, strategy_type: str, regime: str) -> None:
        key    = self._key(strategy_type, regime)
        buf    = self._streaks[key]
        n      = len(buf)
        if n < MIN_TRADES_TO_JUDGE:
            return

        win_rate = sum(buf) / n
        current  = self._weights.get(key, 1.0)

        if win_rate > WIN_RATE_GOOD:
            new_w = min(current + WEIGHT_INCREASE, WEIGHT_MAX)
            log.info(
                "[OptionsPerformanceTracker] %s win_rate=%.0f%% > %.0f%% "
                "→ weight %.2f → %.2f",
                key, win_rate * 100, WIN_RATE_GOOD * 100, current, new_w,
            )
        elif win_rate < WIN_RATE_BAD:
            new_w = max(current - WEIGHT_DECREASE, WEIGHT_MIN)
            log.info(
                "[OptionsPerformanceTracker] %s win_rate=%.0f%% < %.0f%% "
                "→ weight %.2f → %.2f",
                key, win_rate * 100, WIN_RATE_BAD * 100, current, new_w,
            )
        else:
            return   # no change

        self._weights[key] = round(new_w, 3)

        # Check loss streak — notify risk engine
        streak = 0
        for win in reversed(list(buf)):
            if not win:
                streak += 1
            else:
                break
        if streak >= 3:
            try:
                from risk_control.options_risk_engine import get_options_risk_engine
                get_options_risk_engine().notify_loss_streak(strategy_type, streak)
            except Exception as exc:
                log.debug("[OptionsPerformanceTracker] Risk engine notify failed: %s", exc)

    # ── Private: persistence ───────────────────────────────────────────

    def _key(self, strategy_type: str, regime: str) -> str:
        return f"{strategy_type}|{regime}"

    def _persist(self) -> None:
        os.makedirs("data", exist_ok=True)
        try:
            with self._lock:
                outcomes_copy = list(self._outcomes)
                weights_copy  = dict(self._weights)
            with open(OUTCOMES_PATH, "w", encoding="utf-8") as fh:
                json.dump(outcomes_copy, fh, indent=2)
            with open(WEIGHTS_PATH, "w", encoding="utf-8") as fh:
                json.dump(weights_copy, fh, indent=2)
        except Exception as exc:
            log.warning("[OptionsPerformanceTracker] Persist failed: %s", exc)

    def _load(self) -> None:
        os.makedirs("data", exist_ok=True)
        try:
            if os.path.exists(OUTCOMES_PATH):
                with open(OUTCOMES_PATH, encoding="utf-8") as fh:
                    loaded = json.load(fh)
                with self._lock:
                    self._outcomes = loaded
                # Rebuild streaks from history
                for outcome in loaded:
                    stype  = outcome.get("strategy_type", "")
                    regime = outcome.get("regime", "")
                    win    = outcome.get("win", False)
                    key    = self._key(stype, regime)
                    self._streaks[key].append(win)
        except Exception as exc:
            log.debug("[OptionsPerformanceTracker] Outcomes load failed: %s", exc)

        try:
            if os.path.exists(WEIGHTS_PATH):
                with open(WEIGHTS_PATH, encoding="utf-8") as fh:
                    loaded = json.load(fh)
                with self._lock:
                    self._weights = loaded
        except Exception as exc:
            log.debug("[OptionsPerformanceTracker] Weights load failed: %s", exc)


# ── Module-level singleton ─────────────────────────────────────────────────

import threading as _threading

_TRACKER:      Optional[OptionsPerformanceTracker] = None
_TRACKER_LOCK: _threading.Lock                     = _threading.Lock()


def get_options_performance_tracker() -> OptionsPerformanceTracker:
    """Return the process-wide OptionsPerformanceTracker singleton."""
    global _TRACKER
    with _TRACKER_LOCK:
        if _TRACKER is None:
            _TRACKER = OptionsPerformanceTracker()
    return _TRACKER
