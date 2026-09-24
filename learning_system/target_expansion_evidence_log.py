"""
learning_system/target_expansion_evidence_log.py
==================================================
Self-learning module #29 (ACQUISITION) -- Dynamic Target Expansion evidence.

TradeMonitor's `_maybe_expand_target()` extends a trade's effective exit
price (order.adaptive_target) once, well before the original fixed target,
when strong-trend conditions hold (see config.py's
ADAPTIVE_TARGET_EXPANSION_* constants and adaptive_exit_roadmap.md Phase 3).

This module is the append-only, isolated evidence store answering the one
question that matters: did the extra room actually pay off, or would the
trade have been better off closing at the original target?

`record_expansion_outcome()` is called exactly once per trade, from
OrderManager.close_position(), only when `rec.adaptive_target is not None`
-- i.e. only for trades where expansion genuinely fired. It compares the
REAL achieved R-multiple against the R-multiple implied by the ORIGINAL
(un-expanded) target:

  outcome = "WIN"  if final_r_multiple >= original_target_r  (expansion
                     captured at least as much as the original target would
                     have, usually more)
  outcome = "LOSS" if final_r_multiple <  original_target_r  (expansion gave
                     back gains that a fixed exit at the original target
                     would have locked in)

Zero effect on any live decision. Read-only accessors are consumed by
target_expansion_refinement_engine.py for the evidence-gated, shadow-then-
live auto-tuning of the expansion multiplier -- fully automatic, no human
step, matching every other self-learning module built this session.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "learning_system",
)
_EVIDENCE_FILE = os.path.join(_DATA_DIR, "target_expansion_evidence.jsonl")


def record_expansion_outcome(
    order_id: str,
    symbol: str,
    strategy: str,
    direction: str,
    entry_price: float,
    risk_per_share: float,
    original_target: float,
    expanded_target: float,
    exit_price: float,
    final_r_multiple: float,
) -> None:
    """Append one resolved target-expansion outcome record. Fail-open."""
    try:
        if risk_per_share <= 0:
            log.debug(
                "[TargetExpansionEvidence] skipped %s order_id=%s -- "
                "risk_per_share<=0, cannot compute original_target_r",
                symbol, order_id,
            )
            return

        # R-multiple the ORIGINAL (un-expanded) target implied, using the
        # real per-share risk distance the trade was sized against.
        original_target_r = abs(original_target - entry_price) / risk_per_share
        outcome = "WIN" if final_r_multiple >= original_target_r else "LOSS"

        os.makedirs(_DATA_DIR, exist_ok=True)
        record = {
            "timestamp":          datetime.now().isoformat(),
            "order_id":           order_id,
            "symbol":             symbol,
            "strategy":           strategy,
            "direction":          direction,
            "entry_price":        entry_price,
            "original_target":    original_target,
            "expanded_target":    expanded_target,
            "exit_price":         exit_price,
            "final_r_multiple":   round(final_r_multiple, 4),
            "original_target_r":  round(original_target_r, 4),
            "outcome":            outcome,
        }
        with open(_EVIDENCE_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        log.info(
            "[TargetExpansionEvidence] %s order_id=%s outcome=%s "
            "final_r=%.2fR original_target_r=%.2fR",
            symbol, order_id, outcome, final_r_multiple, original_target_r,
        )
    except Exception as exc:
        log.debug("[TargetExpansionEvidence] record failed (non-critical): %s", exc)


def get_records(n: Optional[int] = None) -> List[Dict]:
    """Return all (or last n) resolved records, oldest-first. Fail-open."""
    if not os.path.exists(_EVIDENCE_FILE):
        return []
    records: List[Dict] = []
    try:
        with open(_EVIDENCE_FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        log.debug("[TargetExpansionEvidence] read failed (non-critical): %s", exc)
        return []
    if n is not None:
        records = records[-n:]
    return records


def get_evidence_summary() -> Dict:
    """Read-only summary: sample size, win rate, mean R delta vs baseline."""
    records = get_records()
    n = len(records)
    if n == 0:
        return {"sample_size": 0, "win_rate": None, "mean_r_delta": None}
    wins = sum(1 for r in records if r.get("outcome") == "WIN")
    deltas = [
        r.get("final_r_multiple", 0.0) - r.get("original_target_r", 0.0)
        for r in records
    ]
    return {
        "sample_size":  n,
        "win_rate":     round(wins / n, 4),
        "mean_r_delta": round(sum(deltas) / n, 4),
    }
