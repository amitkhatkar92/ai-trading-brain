"""
K-001 — Failure Learning Taxonomy
===================================
Assigns structured failure categories to completed LOL outcomes so the
learning pipeline can group and track recurring failure modes.

SAFETY CONTRACT
---------------
• No broker calls, orders, modifications, or cancellations.
• No mutations to PAPER_TRADING state or risk limits.
• Read-only access to LOL and KEL files.
• Append-only writes to failure_summary_YYYY-MM-DD.jsonl.

FAILURE CATEGORIES
------------------
The taxonomy is deliberately small and stable.  Each category maps to a
concrete, actionable root cause that an operator can investigate.

  ENTRY_EARLY       — Entered before setup was complete (entry < zone low)
  ENTRY_LATE        — Entered after breakout already extended
  STOP_TOO_TIGHT    — Stop triggered within first bar; ATR << spread
  STOP_TOO_WIDE     — Loss exceeded 2R before stop fired
  DIRECTION_WRONG   — Move was profitable in the opposite direction
  REGIME_MISMATCH   — Trade taken in an unfavourable regime (e.g. BEAR + BUY)
  THESIS_INTACT     — Stop hit but thesis was correct (T+5 moved as expected)
  LOW_FOLLOW_THROUGH — Moved initially, then reversed before target
  EXECUTION_SKIP    — Setup was correct but signal was filtered/blocked
  UNCATEGORISED     — Does not fit a known pattern

Taxonomy is additive — new categories can be appended without breaking
existing records.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT        = Path(__file__).resolve().parents[1]
_TAXONOMY_DIR = _ROOT / "data" / "failure_taxonomy"

CATEGORY_ENTRY_EARLY         = "ENTRY_EARLY"
CATEGORY_ENTRY_LATE          = "ENTRY_LATE"
CATEGORY_STOP_TOO_TIGHT      = "STOP_TOO_TIGHT"
CATEGORY_STOP_TOO_WIDE       = "STOP_TOO_WIDE"
CATEGORY_DIRECTION_WRONG     = "DIRECTION_WRONG"
CATEGORY_REGIME_MISMATCH     = "REGIME_MISMATCH"
CATEGORY_THESIS_INTACT       = "THESIS_INTACT"
CATEGORY_LOW_FOLLOW_THROUGH  = "LOW_FOLLOW_THROUGH"
CATEGORY_EXECUTION_SKIP      = "EXECUTION_SKIP"
CATEGORY_UNCATEGORISED       = "UNCATEGORISED"

# Outcome classes that represent failures / missed opportunities
_FAILURE_OUTCOME_CLASSES = {
    "EXECUTED_LOSS", "STOP_EXIT", "EARLY_EXIT",
    "REJECTED_INCORRECT", "BLOCKED_INCORRECT",
    "MISSED_OPPORTUNITY", "KDA_FALSE_NEGATIVE",
}

# Outcome classes that represent correct rejections (also informative)
_REJECTION_OUTCOME_CLASSES = {
    "REJECTED_CORRECT", "BLOCKED_CORRECT",
}


def classify_failure(rec: Dict[str, Any]) -> str:
    """
    Classify a single LOL OUTCOME_OBSERVED record into a failure category.
    Returns one of the CATEGORY_* constants.
    Never raises.
    """
    try:
        outcome_class = rec.get("outcome_class", "")
        direction     = str(rec.get("direction", "BUY")).upper()
        t1_ret        = rec.get("t1_ret_pct")
        t5_ret        = rec.get("t5_ret_pct")
        mfe_pct       = rec.get("mfe_pct", 0.0) or 0.0
        mae_pct       = rec.get("mae_pct", 0.0) or 0.0
        stop_hit      = rec.get("stop_hit", False)
        first_event   = rec.get("outcome_first_event", "")
        regime        = str(rec.get("regime", "") or "").upper()

        # Execution skips
        if outcome_class in ("REJECTED_INCORRECT", "BLOCKED_INCORRECT", "MISSED_OPPORTUNITY",
                             "KDA_FALSE_NEGATIVE"):
            return CATEGORY_EXECUTION_SKIP

        if outcome_class not in _FAILURE_OUTCOME_CLASSES:
            return CATEGORY_UNCATEGORISED

        # Direction-based categories
        is_buy = direction not in ("SELL", "SHORT", "BEAR")
        if t5_ret is not None:
            positive_if_correct = t5_ret > 0 if is_buy else t5_ret < 0
            if not positive_if_correct and abs(t5_ret or 0) > 1.0:
                return CATEGORY_DIRECTION_WRONG

        # Regime mismatch
        if is_buy and regime in ("BEAR", "VOLATILE") and outcome_class == "EXECUTED_LOSS":
            return CATEGORY_REGIME_MISMATCH
        if not is_buy and regime in ("BULL",) and outcome_class == "EXECUTED_LOSS":
            return CATEGORY_REGIME_MISMATCH

        # Stop too tight — stopped out immediately (first_event on bar 1)
        # Only classify as STOP_TOO_TIGHT if not THESIS_INTACT
        # (thesis intact takes priority — stop_loss placement not the root cause)
        if stop_hit and t5_ret is not None:
            positive_if_correct = t5_ret > 0 if is_buy else t5_ret < 0
            if positive_if_correct and abs(t5_ret) > 1.0:
                return CATEGORY_THESIS_INTACT

        if stop_hit and first_event == "STOP_HIT":
            if mae_pct is not None and abs(mae_pct) < 0.5:
                return CATEGORY_STOP_TOO_TIGHT

        # Stop too wide — loss was outsized
        if outcome_class == "EXECUTED_LOSS" and mae_pct is not None and abs(mae_pct) > 3.0:
            return CATEGORY_STOP_TOO_WIDE

        # Low follow-through — moved initially but reversed
        if t1_ret is not None and t5_ret is not None:
            moved_right_initially  = (t1_ret > 0 if is_buy else t1_ret < 0)
            reversed_by_t5         = (t5_ret <= 0 if is_buy else t5_ret >= 0)
            if moved_right_initially and reversed_by_t5:
                return CATEGORY_LOW_FOLLOW_THROUGH

        return CATEGORY_UNCATEGORISED
    except Exception:
        return CATEGORY_UNCATEGORISED


def write_failure_summary(
    lol_records: List[Dict[str, Any]],
    trading_date: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Classify all provided LOL OUTCOME_OBSERVED records and write a daily
    failure summary to data/failure_taxonomy/failure_summary_YYYY-MM-DD.jsonl.

    Returns a summary dict with category counts.
    Never raises.
    """
    result: Dict[str, Any] = {
        "trading_date": trading_date or date.today().isoformat(),
        "total_classified": 0,
        "categories": {},
        "error": None,
    }
    try:
        base = output_dir or _TAXONOMY_DIR
        base.mkdir(parents=True, exist_ok=True)
        today_str = trading_date or date.today().isoformat()
        out_path  = base / f"failure_summary_{today_str}.jsonl"

        category_counts: Dict[str, int] = {}
        rows: List[Dict[str, Any]] = []

        for rec in lol_records:
            lifecycle_state = rec.get("lifecycle_state", "")
            if lifecycle_state not in ("OUTCOME_OBSERVED", "LEARNING_PROCESSED"):
                continue
            cat = classify_failure(rec)
            category_counts[cat] = category_counts.get(cat, 0) + 1
            rows.append({
                "observation_id":  rec.get("observation_id") or rec.get("obs_id", ""),
                "symbol":          rec.get("symbol", ""),
                "outcome_class":   rec.get("outcome_class", ""),
                "failure_category": cat,
                "trading_date":    rec.get("trading_date", today_str),
                "ts_utc":          datetime.now(timezone.utc).isoformat(),
            })

        if rows:
            with out_path.open("a", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps(row) + "\n")

        result["total_classified"] = len(rows)
        result["categories"]       = category_counts
        log.info(
            "[FailureTaxonomy] Classified %d records: %s",
            len(rows),
            "  ".join(f"{k}={v}" for k, v in sorted(category_counts.items())),
        )
    except Exception as exc:
        result["error"] = str(exc)
        log.warning("[FailureTaxonomy] Failed: %s", exc)
    return result
