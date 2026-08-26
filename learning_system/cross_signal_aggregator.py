"""
K-003 — Cross-Signal Aggregator
=================================
Research-only aggregation for signals generated in the same decision window.
Captures portfolio-level signal correlation for research purposes.

SAFETY CONTRACT
---------------
• No broker calls, orders, modifications, or cancellations.
• No changes to execution authority, risk limits, or strategy parameters.
• Append-only writes to data/cross_signal/cross_signal_YYYY-MM-DD.jsonl.
• Never raises — all errors are swallowed (non-fatal research record).
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT            = Path(__file__).resolve().parents[1]
_CROSS_SIGNAL_DIR = _ROOT / "data" / "cross_signal"


def record_signal_window(
    signals:      List[Any],                  # list of TradeSignal
    snapshot:     Any,                        # MarketSnapshot
    trading_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Aggregate all signals from one decision window into a single research record.
    Returns the summary dict (also written to disk).
    """
    result: Dict[str, Any] = {"total_signals": 0, "error": None}
    try:
        if not signals:
            return result

        today   = trading_date or date.today().isoformat()
        now_utc = datetime.now(timezone.utc).isoformat()
        regime  = ""
        vix     = 0.0
        try:
            regime = str(getattr(snapshot.regime, "value", snapshot.regime) or "")
            vix    = float(getattr(snapshot, "vix", 0) or 0)
        except Exception:
            pass

        entries: List[Dict[str, Any]] = []
        directions:   Dict[str, int] = {}
        sectors:      Dict[str, int] = {}
        strategies:   Dict[str, int] = {}
        opp_ids:      List[str] = []

        for sig in signals:
            sym        = str(getattr(sig, "symbol", "") or "")
            direction  = str(getattr(sig, "direction", "") or "")
            if hasattr(direction, "value"):
                direction = direction.value
            strategy   = str(getattr(sig, "strategy_name", "") or "")
            sector     = str(getattr(sig, "sector", "") or "")
            opp_id     = str(getattr(sig, "opportunity_id", "") or "")
            confidence = float(getattr(sig, "confidence", 0) or 0)

            if opp_id:
                opp_ids.append(opp_id)
            directions[direction] = directions.get(direction, 0) + 1
            if sector:
                sectors[sector] = sectors.get(sector, 0) + 1
            strategies[strategy] = strategies.get(strategy, 0) + 1

            entries.append({
                "symbol":         sym,
                "direction":      direction,
                "strategy":       strategy,
                "sector":         sector,
                "opportunity_id": opp_id,
                "confidence":     confidence,
                "entry_price":    float(getattr(sig, "entry_price", 0) or 0),
            })

        same_dir_count = max(directions.values()) if directions else 0
        top_direction  = max(directions, key=directions.get) if directions else ""
        top_strategy   = max(strategies, key=strategies.get) if strategies else ""

        row: Dict[str, Any] = {
            "ts_utc":              now_utc,
            "trading_date":        today,
            "regime":              regime,
            "vix":                 vix,
            "signal_count":        len(signals),
            "opportunity_ids":     opp_ids,
            "top_direction":       top_direction,
            "same_direction_count": same_dir_count,
            "direction_breakdown": directions,
            "strategy_breakdown":  strategies,
            "sector_breakdown":    sectors,
            "signals":             entries,
            "no_lookahead":        True,
            "broker_calls":        0,
        }

        _CROSS_SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
        out_path = _CROSS_SIGNAL_DIR / f"cross_signal_{today}.jsonl"
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")

        result["total_signals"] = len(signals)
        log.debug("[CrossSignal] Recorded window: %d signals, regime=%s",
                  len(signals), regime)
    except Exception as exc:
        result["error"] = str(exc)
        log.debug("[CrossSignal] record_signal_window failed: %s", exc)
    return result
