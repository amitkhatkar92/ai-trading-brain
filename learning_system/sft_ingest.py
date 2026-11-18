"""
Feeds closed trades into the Symbol Follow-Through tracker (phase_d_sft.db).

SFTTracker.ingest_closed_trade() had no caller, so the store stayed empty. The SFT
score depends on how far price moved in favour (MFE) and whether it reached +0.25R,
+0.5R and +1R, so a trade is fed only when TradeMonitor really tracked its price
extremes while it was held. A trade without them (restored after a restart, closed by
carry expiry) is skipped rather than counted as "never reached 0.5R", which would bias
the score downward.
"""
from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)


def excursion_inputs(trade) -> Optional[dict]:
    """Return the keyword arguments for ingest_closed_trade(), or None if not measurable."""
    try:
        entry = float(getattr(trade, "actual_fill_price", 0) or getattr(trade, "entry_price", 0) or 0)
        stop = float(getattr(trade, "initial_stop_loss", 0) or getattr(trade, "stop_loss", 0) or 0)
        high = float(getattr(trade, "mfe_price", 0) or 0)
        low = float(getattr(trade, "mae_price", 0) or 0)
        direction = str(getattr(trade, "direction", "") or "").upper()
        symbol = str(getattr(trade, "symbol", "") or "")
        risk = abs(entry - stop)
        if not symbol or entry <= 0 or stop <= 0 or risk <= 0 or high <= 0 or low <= 0:
            return None
        if direction == "BUY":
            favourable, adverse = high - entry, entry - low
        elif direction in ("SELL", "SHORT"):
            favourable, adverse = entry - low, high - entry
        else:
            return None
        mfe_r = max(favourable, 0.0) / risk
        mae_r = max(adverse, 0.0) / risk
        return {
            "symbol": symbol, "trade_pnl": float(getattr(trade, "pnl", 0.0) or 0.0),
            "entry_price": entry, "stop_loss": stop,
            "mfe_r": round(mfe_r, 4), "mae_r": round(mae_r, 4),
            "reached_025r": mfe_r >= 0.25, "reached_050r": mfe_r >= 0.50, "reached_100r": mfe_r >= 1.0,
        }
    except Exception:
        return None


def record_trade_excursion(trade, tracker=None) -> bool:
    """Ingest one closed trade into the SFT tracker. Never raises; False when skipped."""
    inputs = excursion_inputs(trade)
    if inputs is None:
        return False
    try:
        if tracker is None:
            from phase_d_sft_recommendation import get_sft_tracker
            tracker = get_sft_tracker()
        tracker.ingest_closed_trade(**inputs)
        return True
    except Exception as exc:
        log.debug("[SFT] ingest failed (non-critical): %s", exc)
        return False
