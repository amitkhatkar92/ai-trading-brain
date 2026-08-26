"""
K-002 — Exit Analytics
=======================
Research-only exit quality analytics.  Called from OrderManager.close_position()
for every completed trade.

SAFETY CONTRACT
---------------
• No broker calls, orders, modifications, or cancellations.
• No changes to production targets, stops, or risk limits.
• Append-only writes to data/exit_analytics/exit_analytics_YYYY-MM-DD.jsonl.
• Never raises — all errors are swallowed (non-fatal research record).

EXIT OUTCOME CLASSES
--------------------
  TARGET_HIT      — price reached target
  STOP_HIT        — stop-loss triggered
  SESSION_EXPIRED — held past session / carry expired
  EARLY_EXIT      — manual or system early exit before target/stop
  EARLY_LOSS      — adaptive early-exit on loss signal
  PROFIT_GIVEBACK — closed in profit but well short of target
  REPLACEMENT     — position replaced by higher-conviction signal
  UNKNOWN         — close_reason not recognised
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT         = Path(__file__).resolve().parents[1]
_ANALYTICS_DIR = _ROOT / "data" / "exit_analytics"

# Map OrderManager close_reason values to canonical classes
_REASON_MAP: Dict[str, str] = {
    "TARGET_HIT":      "TARGET_HIT",
    "target_hit":      "TARGET_HIT",
    "STOP_HIT":        "STOP_HIT",
    "stop_hit":        "STOP_HIT",
    "SL_HIT":          "STOP_HIT",
    "SESSION_EXPIRED": "SESSION_EXPIRED",
    "session_expired": "SESSION_EXPIRED",
    "EARLY_LOSS":      "EARLY_LOSS",
    "early_loss":      "EARLY_LOSS",
    "REPLACEMENT":     "REPLACEMENT",
    "replacement":     "REPLACEMENT",
}

_PROFIT_GIVEBACK_THRESHOLD = 0.20  # pnl > 0 but < 20% of target move → giveback


def _classify_exit(reason: str, pnl: float, entry: float,
                   target: float, direction: str) -> str:
    canonical = _REASON_MAP.get(reason, "")
    if canonical:
        return canonical
    reason_up = reason.upper()
    if "TARGET" in reason_up:
        return "TARGET_HIT"
    if "STOP" in reason_up or "SL" in reason_up:
        return "STOP_HIT"
    if "SESSION" in reason_up or "EXPIRED" in reason_up:
        return "SESSION_EXPIRED"
    if "EARLY" in reason_up and "LOSS" in reason_up:
        return "EARLY_LOSS"
    if "EARLY" in reason_up:
        return "EARLY_EXIT"
    if "REPLACE" in reason_up:
        return "REPLACEMENT"
    # Heuristic: in profit but fell short of target
    if pnl > 0 and target and entry and entry != target:
        target_move = abs(target - entry)
        actual_move = abs(pnl / max(1, 1))  # rough proxy; full calc requires qty
        if target_move > 0 and actual_move < _PROFIT_GIVEBACK_THRESHOLD * target_move:
            return "PROFIT_GIVEBACK"
    return "UNKNOWN"


def record_exit(
    rec: Any,                       # OrderRecord instance
    exit_price: float,
    pnl: float,
    reason: str,
    trading_date: Optional[str] = None,
) -> None:
    """
    Append one exit analytics record.  Called from close_position().
    rec is an OrderRecord; all fields accessed via getattr for safety.
    """
    try:
        today = trading_date or date.today().isoformat()
        entry     = float(getattr(rec, "entry_price", 0) or 0)
        target    = float(getattr(rec, "target", 0) or 0)
        stop      = float(getattr(rec, "stop_loss", 0) or 0)
        direction = str(getattr(rec, "direction", "BUY") or "BUY").upper()
        strategy  = str(getattr(rec, "strategy", "") or "")
        symbol    = str(getattr(rec, "symbol", "") or "")
        qty       = int(getattr(rec, "quantity", 0) or 0)
        placed_at = getattr(rec, "placed_at", None)
        closed_at = datetime.now(timezone.utc)

        # Holding duration in minutes
        holding_mins: Optional[float] = None
        if placed_at is not None:
            try:
                _placed = placed_at if hasattr(placed_at, "tzinfo") else \
                    placed_at.replace(tzinfo=None)
                holding_mins = round(
                    (closed_at.replace(tzinfo=None) -
                     (placed_at.replace(tzinfo=None) if hasattr(placed_at, "tzinfo")
                      else placed_at)).total_seconds() / 60.0, 1)
            except Exception:
                pass

        # Actual return % based on actual fill price
        fill_price = float(getattr(rec, "actual_fill_price", 0) or 0) or entry
        actual_ret_pct: Optional[float] = None
        if fill_price > 0:
            if direction == "BUY":
                actual_ret_pct = round((exit_price / fill_price - 1.0) * 100.0, 4)
            else:
                actual_ret_pct = round((fill_price / exit_price - 1.0) * 100.0, 4) \
                    if exit_price > 0 else None

        # Target vs stop distance
        target_dist_pct: Optional[float] = None
        stop_dist_pct:   Optional[float] = None
        if entry > 0:
            if target > 0:
                target_dist_pct = round(abs(target - entry) / entry * 100.0, 4)
            if stop > 0:
                stop_dist_pct = round(abs(entry - stop) / entry * 100.0, 4)

        exit_class = _classify_exit(reason, pnl, entry, target, direction)

        row: Dict[str, Any] = {
            "ts_utc":           closed_at.isoformat(),
            "trading_date":     today,
            "order_id":         str(getattr(rec, "order_id", "") or ""),
            "opportunity_id":   str(getattr(rec, "opportunity_id", "") or ""),
            "symbol":           symbol,
            "strategy":         strategy,
            "direction":        direction,
            "regime":           str(getattr(rec, "signal_regime", "") or ""),
            "entry_price":      entry,
            "actual_fill_price": fill_price,
            "exit_price":       exit_price,
            "quantity":         qty,
            "stop_loss":        stop,
            "target":           target,
            "pnl":              round(pnl, 2),
            "actual_ret_pct":   actual_ret_pct,
            "target_dist_pct":  target_dist_pct,
            "stop_dist_pct":    stop_dist_pct,
            "holding_mins":     holding_mins,
            "close_reason":     reason,
            "exit_class":       exit_class,
            "confidence_score": float(getattr(rec, "confidence_score", 0) or 0),
            "no_lookahead":     True,
            "broker_calls":     0,
        }

        _ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = _ANALYTICS_DIR / f"exit_analytics_{today}.jsonl"
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")

    except Exception as exc:
        log.debug("[ExitAnalytics] record_exit failed: %s", exc)
