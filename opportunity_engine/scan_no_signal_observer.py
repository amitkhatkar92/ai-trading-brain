"""
D-009 — Scan No-Signal Observer
==================================
Records SCAN_NO_SETUP observations for prepared-universe symbols that were
scanned and passed quality checks but did not generate a trading signal.

These records are written to the KLP daily JSONL file as
event_type="SCAN_NO_SETUP" so the LOL/KLP outcome pipeline can later
compute theoretical outcomes and feed them into the knowledge system.

SAFETY CONTRACT
---------------
• No broker calls, orders, modifications, or cancellations.
• Append-only writes to data/klp/KLP_YYYY-MM-DD.jsonl.
• Never raises — all errors are swallowed (non-fatal observation).
• no_lookahead = True on every output.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from utils import get_logger

log = get_logger(__name__)

_KLP_DIR = Path(__file__).resolve().parents[1] / "data" / "klp"


def record_no_signal(
    stock:    Dict[str, Any],
    snapshot: Any,
    reason:   str,
) -> None:
    """
    Append a SCAN_NO_SETUP record to today's KLP file.

    Parameters
    ----------
    stock    : stock dict from scanner watchlist (has symbol, ltp, rsi, score…)
    snapshot : MarketSnapshot
    reason   : rejection reason from _identify_setup()
    """
    try:
        symbol = str(stock.get("symbol", "")).strip()
        if not symbol:
            return

        today = date.today().isoformat()
        regime = getattr(snapshot, "regime", None)
        regime_str = getattr(regime, "value", str(regime)) if regime else ""

        obs_id = str(uuid.uuid4())
        ltp    = float(stock.get("ltp", 0) or 0)
        rec: Dict[str, Any] = {
            "event_type":          "SCAN_NO_SETUP",
            "observation_id":      obs_id,
            "obs_id":              obs_id,   # backward-compat alias
            "trading_date":        today,
            "ts_utc":              datetime.now(timezone.utc).isoformat(),
            "symbol":              symbol,
            "rejection_reason":    reason,
            "regime":              regime_str,
            "vix":                 float(getattr(snapshot, "vix", 0) or 0),
            "ltp":                 ltp,
            "rsi":                 float(stock.get("rsi", 0) or 0),
            "volume_ratio":        float(stock.get("volume_ratio", 0) or 0),
            "atr":                 float(stock.get("atr", 0) or 0),
            "score":               stock.get("score"),
            "support":             stock.get("support"),
            "resistance":          stock.get("resistance"),
            "no_lookahead":        True,
            "broker_calls":        0,
        }

        _KLP_DIR.mkdir(parents=True, exist_ok=True)
        klp_path = _KLP_DIR / f"KLP_{today}.jsonl"
        with klp_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")

    except Exception as exc:
        log.debug("[D009] scan_no_signal_observer error: %s", exc)
