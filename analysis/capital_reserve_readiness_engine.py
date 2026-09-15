"""
analysis/capital_reserve_readiness_engine.py
================================================
Self-learning module #28: Intelligent Capital Reserve readiness gate
(postponed_improvements.md item #5, "Best-Trade Priority Queue").

SCOPE -- DELIBERATELY READINESS-ONLY, NOT A LIVE SWAP MECHANISM
--------------------------------------------------------------------
postponed_improvements.md's own author flagged this item explicitly:
"Complexity: Medium-high -- requires position replacement logic.
Discuss architecture before implementing." Unlike #24-27 (which only
ever excluded a strategy from FUTURE signals, nudged a ranking
multiplier, or adjusted a sizing bound), an actual "swap" would CLOSE an
already-open, real position early to free capital for a new signal --
categorically more consequential and execution-adjacent than any other
self-learning module built this session.

Per this repo's own protected-module discipline ("state the
architectural impact before writing a single line of code" for
execution-adjacent changes) and the operational-safety rule (do not take
hard-to-reverse action without explicit approval), this module builds
ONLY the safe, non-consequential half: an automatic, evidence-gated
READINESS SIGNAL answering "does real evidence justify building the
swap mechanism at all?" -- never the swap mechanism itself. This mirrors
the exact precedent already set by knowledge_system/
equity_hedge_shadow_engine.py's own READY_FOR_LIVE marker, which "marks
the AUTHENTICATION decision only, not a live-trading switch" since no
execution path exists for it either.

ACQUISITION -- reuses 100% existing evidence, builds NOTHING new
--------------------------------------------------------------------
analysis/rejection_attribution_monitor.py (Self-Learning Ecosystem
Phase 4, already live) already resolves every MAX_POSITIONS_CAP
rejection via real T+1/T+3/T+5 yfinance price follow-through and
classifies each as CORRECT_REJECTION / FALSE_REJECTION / NEUTRAL. A
FALSE_REJECTION on a MAX_POSITIONS_CAP rejection means: "this signal was
rejected purely because all position slots were full, and the market
subsequently proved it would have been profitable" -- i.e. real,
already-computed evidence of capital-constraint opportunity cost.

GOVERNANCE
------------
MIN_SAMPLES_FOR_READINESS=30 (mirrors this session's other governance
floors). FALSE_NEGATIVE_READY_THRESHOLD=40% -- if at least 40% of
resolved MAX_POSITIONS_CAP rejections turn out to have been
FALSE_REJECTION (i.e. the rejected signal would have worked), that is
real, meaningful evidence that a capital-reserve/swap mechanism is
worth the "discuss architecture before implementing" investment.
Below that (or below the sample floor), the module reports
NOT_YET_WARRANTED / WAITING_FOR_EVIDENCE -- never fabricates readiness.

SAFETY CONTRACT
-----------------
Zero imports of execution_engine, order_manager, broker APIs. Never
closes, modifies, or even reads a live open position. get_readiness_
status() is a pure read-only accessor over analysis/
rejection_attribution_monitor.py's own already-computed, already-live
statistics -- this module cannot affect any trade in any way.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

ACTOR = "CAPITAL-RESERVE-READINESS-001"

_ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR   = os.path.join(_ROOT, "data", "risk_control", "capital_reserve_readiness")
_STATE_PATH  = os.path.join(_STORE_DIR, "state.json")
_LEDGER_PATH = os.path.join(_STORE_DIR, "ledger.jsonl")

REJECTION_REASON               = "MAX_POSITIONS_CAP"
MIN_SAMPLES_FOR_READINESS      = 30
FALSE_NEGATIVE_READY_THRESHOLD = 40.0   # percent

STATUS_WAITING           = "WAITING_FOR_EVIDENCE"
STATUS_NOT_WARRANTED     = "NOT_YET_WARRANTED"
STATUS_READY_FOR_DESIGN  = "READY_FOR_DESIGN"


def _read_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, path)


def _append_ledger(event_type: str, reason: str, **extra: Any) -> None:
    try:
        record = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": ACTOR,
            "event_type": event_type,
            "reason": reason,
            **extra,
        }
        os.makedirs(_STORE_DIR, exist_ok=True)
        with open(_LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        log.debug("[CapitalReserveReadiness] ledger write failed: %s", exc)


def _read_ledger(n: Optional[int] = None) -> List[Dict[str, Any]]:
    if not os.path.exists(_LEDGER_PATH):
        return []
    out: List[Dict[str, Any]] = []
    try:
        with open(_LEDGER_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return out[-n:] if n else out


def get_readiness_status() -> Dict[str, Any]:
    """
    Read-only accessor: does real evidence justify DESIGNING a capital
    -reserve/swap mechanism? Never raises, never touches any trade.
    """
    try:
        from analysis.rejection_attribution_monitor import get_rejection_attribution_monitor
        stats = get_rejection_attribution_monitor().get_reason_reliability(
            REJECTION_REASON, min_samples=MIN_SAMPLES_FOR_READINESS,
        )
        if stats is None:
            return {
                "status": STATUS_WAITING, "reason": REJECTION_REASON,
                "min_samples_required": MIN_SAMPLES_FOR_READINESS,
                "classified_samples": 0,
            }
        false_negative_pct = stats.get("false_negative_pct", 0.0)
        ready = false_negative_pct >= FALSE_NEGATIVE_READY_THRESHOLD
        return {
            "status": STATUS_READY_FOR_DESIGN if ready else STATUS_NOT_WARRANTED,
            "reason": REJECTION_REASON,
            "classified_samples": stats.get("classified", 0),
            "false_negative_pct": false_negative_pct,
            "threshold_pct": FALSE_NEGATIVE_READY_THRESHOLD,
        }
    except Exception as exc:
        log.debug("[CapitalReserveReadiness] status error: %s", exc)
        return {"status": STATUS_WAITING, "reason": REJECTION_REASON, "error": str(exc)}


def run_daily_readiness_check() -> Dict[str, Any]:
    """
    Self-scheduled, fully automated. Logs a ledger event only on a
    status TRANSITION (mirrors the existing "alert only on state change"
    convention used elsewhere in this repo). Never raises, never takes
    any action beyond recording status.
    """
    try:
        current = get_readiness_status()
        state = _read_json(_STATE_PATH, {"status": STATUS_WAITING})
        if state.get("status") != current["status"]:
            _append_ledger("STATUS_CHANGED", REJECTION_REASON,
                            old_status=state.get("status"), new_status=current["status"],
                            detail=current)
            _write_json(_STATE_PATH, current)
        return current
    except Exception as exc:
        log.debug("[CapitalReserveReadiness] daily check error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def get_ledger_history(n: int = 20) -> List[Dict[str, Any]]:
    return _read_ledger(n)
