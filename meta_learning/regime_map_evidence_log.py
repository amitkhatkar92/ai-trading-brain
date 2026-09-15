"""
meta_learning/regime_map_evidence_log.py
===========================================
Self-Learning Ecosystem -- Post-roadmap Priority 5 (part 1 of 2):
ACQUISITION for MetaStrategyController's regime->strategy candidate list.

_REGIME_MAP (strategy_lab/meta_strategy_controller.py) is a hand-written,
static per-regime strategy ELIGIBILITY list -- unlike RegimeStrategyMap
(meta_learning/regime_strategy_map.py, already live, already-active,
tracks per-(regime,strategy) win-rate/expectancy to RANK strategies that
are already eligible), nothing in this repo has ever tracked whether a
regime's own ELIGIBILITY list itself should change.

RegimeStrategyMap only persists RUNNING AGGREGATES (trades/wins/total_r)
per (regime,strategy) pair -- not the individual, time-ordered trade
records a proper train/OOS statistical validation requires. Rather than
modify that already-live tracker, this module is a separate, additive,
isolated observer of the exact same underlying trade events (recorded
from the same call site in orchestrator/master_orchestrator.py,
alongside -- never replacing -- the existing regime_strategy_map.record()
call).

Isolated, append-only store: data/meta_learning/regime_map_evidence.jsonl
Never consumed by this module -- read only by
strategy_lab/regime_map_refinement_engine.py (SYNTHESIS+GOVERNANCE).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

_ROOT          = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR     = os.path.join(_ROOT, "data", "meta_learning")
_EVIDENCE_PATH = os.path.join(_STORE_DIR, "regime_map_evidence.jsonl")


def record_regime_trade(regime: str, strategy: str, r_multiple: float, won: bool,
                         order_id: str = "") -> None:
    """
    Append one real, closed trade's (regime, strategy) outcome.
    Never raises -- a failure here must never affect learning, risk,
    execution, or reporting.
    """
    try:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "regime": regime,
            "strategy": strategy,
            "r_multiple": float(r_multiple),
            "won": bool(won),
            "order_id": order_id,
        }
        os.makedirs(_STORE_DIR, exist_ok=True)
        with open(_EVIDENCE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        log.debug("[RegimeMapEvidence] record failed (non-critical): %s", exc)


def get_records(regime: Optional[str] = None, strategy: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Read-only accessor. Returns time-ordered (oldest-first, insertion
    order) records, optionally filtered by regime and/or strategy.
    Never raises.
    """
    if not os.path.exists(_EVIDENCE_PATH):
        return []
    out: List[Dict[str, Any]] = []
    try:
        with open(_EVIDENCE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if regime is not None and rec.get("regime") != regime:
                    continue
                if strategy is not None and rec.get("strategy") != strategy:
                    continue
                out.append(rec)
    except OSError:
        return []
    return out


def get_pairs_with_evidence() -> List[Tuple[str, str]]:
    """Read-only accessor: distinct (regime, strategy) pairs with >=1 record."""
    pairs = set()
    for rec in get_records():
        pairs.add((rec.get("regime"), rec.get("strategy")))
    return sorted(pairs)
