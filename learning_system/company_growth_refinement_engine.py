"""
learning_system/company_growth_refinement_engine.py
=======================================================
Self-learning module #31 (SYNTHESIS + GOVERNANCE) -- Company
Intelligence (growth-screen) auto-validation and KDA wiring.

Validates, purely from real closed-trade evidence recorded by
company_growth_evidence_log.py, whether a strongly-positive company
growth score (real revenue/earnings growth, see
opportunity_engine/company_growth_signal.py) actually correlates with
a higher win rate than trades with a low/negative score. Same cohort-
diff, time-split 70/30 + bootstrap-CI validation shape used by
learning_system/institutional_flow_refinement_engine.py and
sizing_bounds_refinement_engine.py.

LIFECYCLE (fully automated, no human step at any transition):
  WAITING_FOR_EVIDENCE -> SHADOW_ACTIVE -> ACTIVE/REJECTED
  ACTIVE -> ROLLED_BACK (auto-revert if post-activation evidence no
  longer supports the adjustment)

WIRING INTO KDA
----------------
get_company_growth_adjustment(score) is consumed by
knowledge_authority/knowledge_decision_authority.py's
_compute_authority() as a THIRD, independent, bounded +/-0.05 nudge to
`relevance` (alongside the existing ARS bridge and the institutional-
flow bridge). Zero effect (0.0) until validated -- dormant on deploy.

SAFETY CONTRACT
-----------------
Zero imports of execution_engine, order_manager, broker APIs.
get_company_growth_adjustment() is a pure, read-only accessor; falls
back to 0.0 on any error, missing file, or no active adjustment. Never
imports or modifies equity_scanner_ai.py or
knowledge_decision_authority.py directly.
"""
from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

ACTOR = "COMPANY-GROWTH-RE-001"

_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR  = os.path.join(_ROOT, "data", "learning_system", "company_growth_calibration")
_STATE_PATH = os.path.join(_STORE_DIR, "state.json")
_ADJ_PATH   = os.path.join(_STORE_DIR, "active_adjustment.json")
_LEDGER_PATH = os.path.join(_STORE_DIR, "ledger.jsonl")

POSITIVE_THRESHOLD       = 0.30    # score above this = "high" cohort
MIN_SAMPLE_FOR_VALIDATION = 30
MIN_SHADOW_NEW_EVIDENCE   = 15
MIN_EFFECT_MAGNITUDE      = 0.05
BOOTSTRAP_ITERS           = 1000
COOLDOWN_DAYS             = 30
MAX_ADJUSTMENT            = 0.05
ROLLBACK_DEGRADATION_N    = 15

STATUS_WAITING     = "WAITING_FOR_EVIDENCE"
STATUS_SHADOW      = "SHADOW_ACTIVE"
STATUS_ACTIVE      = "ACTIVE"
STATUS_ROLLED_BACK = "ROLLED_BACK"
STATUS_REJECTED    = "REJECTED"


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
            "event_id":   datetime.now(timezone.utc).isoformat() + "-" + event_type,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "actor":      ACTOR,
            "event_type": event_type,
            "reason":     reason,
            **extra,
        }
        os.makedirs(_STORE_DIR, exist_ok=True)
        with open(_LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        log.debug("[CompanyGrowthRE] ledger write failed: %s", exc)


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


# ─────────────────────────────────────────────────────────────────────────────
# Statistical validation -- cohort win-rate diff
# ─────────────────────────────────────────────────────────────────────────────

def _bootstrap_ci_diff(high: List[bool], low: List[bool],
                        iters: int = BOOTSTRAP_ITERS, seed: int = 42) -> Optional[Tuple[float, float]]:
    if not high or not low:
        return None
    rng = random.Random(seed)
    nh, nl = len(high), len(low)
    diffs = []
    for _ in range(iters):
        h_wr = sum(high[rng.randrange(nh)] for _ in range(nh)) / nh
        l_wr = sum(low[rng.randrange(nl)] for _ in range(nl)) / nl
        diffs.append(h_wr - l_wr)
    diffs.sort()
    lo = diffs[int(0.025 * iters)]
    hi = diffs[int(0.975 * iters) - 1]
    return (lo, hi)


def _cohort_split(recs: List[Dict[str, Any]]) -> Tuple[List[bool], List[bool]]:
    high = [bool(r["won"]) for r in recs if r["company_growth_score"] > POSITIVE_THRESHOLD]
    low  = [bool(r["won"]) for r in recs if r["company_growth_score"] <= POSITIVE_THRESHOLD]
    return high, low


def _scorecard(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(records)
    result: Dict[str, Any] = {"sample_size": n, "passed": False, "checks": {}}
    if n < MIN_SAMPLE_FOR_VALIDATION:
        result["checks"]["sample_size"] = False
        return result
    result["checks"]["sample_size"] = True

    split = int(n * 0.7)
    train, oos = records[:split], records[split:]
    if not oos:
        result["checks"]["sample_size"] = False
        return result

    def _diff(recs: List[Dict[str, Any]]) -> Optional[float]:
        high, low = _cohort_split(recs)
        if not high or not low:
            return None
        return (sum(high) / len(high)) - (sum(low) / len(low))

    train_diff = _diff(train)
    oos_diff   = _diff(oos)
    if train_diff is None or oos_diff is None:
        result["checks"]["sample_size"] = False
        result["detail"] = "insufficient cohort split (need both high and low score trades)"
        return result

    oos_high, oos_low = _cohort_split(oos)
    ci = _bootstrap_ci_diff(oos_high, oos_low)
    ci_excludes_null = ci is not None and (ci[0] > 0 or ci[1] < 0)
    result["checks"]["ci_excludes_null"] = ci_excludes_null

    sign_consistent = (train_diff > 0) == (oos_diff > 0)
    result["checks"]["sign_consistent"] = sign_consistent

    effect_ok = abs(oos_diff) >= MIN_EFFECT_MAGNITUDE
    result["checks"]["effect_magnitude"] = effect_ok

    result.update({"train_diff": round(train_diff, 4), "oos_diff": round(oos_diff, 4), "ci": ci})
    result["passed"] = all(result["checks"].values())
    result["direction"] = 1 if oos_diff > 0 else (-1 if oos_diff < 0 else 0)
    return result


def _reconfirm_scorecard(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    high, low = _cohort_split(records)
    if not high or not low:
        return {"sample_size": len(records), "passed": False, "direction": 0}
    diff = (sum(high) / len(high)) - (sum(low) / len(low))
    direction = 1 if diff > 0 else (-1 if diff < 0 else 0)
    passed = abs(diff) >= MIN_EFFECT_MAGNITUDE
    return {"sample_size": len(records), "diff": round(diff, 4), "passed": passed, "direction": direction}


def _candidate_adjustment(direction: int) -> float:
    return MAX_ADJUSTMENT if direction == 1 else -MAX_ADJUSTMENT


# ─────────────────────────────────────────────────────────────────────────────
# Public read-side API -- consumed by knowledge_authority/knowledge_decision_
# authority.py
# ─────────────────────────────────────────────────────────────────────────────

_cache_mtime: Optional[float] = None
_cache_adjustment: Optional[float] = None


def get_company_growth_adjustment(score: Optional[float]) -> float:
    """
    Return the bounded relevance nudge (+/- MAX_ADJUSTMENT) for a given
    company_growth_score. Returns 0.0 whenever: score is None, no active
    validated adjustment exists, or the score does not clear the
    validated POSITIVE_THRESHOLD. Never raises.
    """
    global _cache_mtime, _cache_adjustment
    if score is None:
        return 0.0
    try:
        if not os.path.exists(_ADJ_PATH):
            return 0.0
        mtime = os.path.getmtime(_ADJ_PATH)
        if _cache_adjustment is None or _cache_mtime != mtime:
            raw = _read_json(_ADJ_PATH, {})
            adj = raw.get("active_adjustment")
            _cache_adjustment = float(adj) if isinstance(adj, (int, float)) else None
            _cache_mtime = mtime
        if _cache_adjustment is None:
            return 0.0
        if score <= POSITIVE_THRESHOLD:
            return 0.0
        return max(-MAX_ADJUSTMENT, min(MAX_ADJUSTMENT, _cache_adjustment))
    except Exception as exc:
        log.debug("[CompanyGrowthRE] get_company_growth_adjustment fallback to 0.0: %s", exc)
        return 0.0


def get_refinement_status() -> Dict[str, Any]:
    state = _read_json(_STATE_PATH, {"status": STATUS_WAITING})
    adj = _read_json(_ADJ_PATH, {})
    return {
        "status":            state.get("status", STATUS_WAITING),
        "sample_size":       state.get("last_sample_size", 0),
        "active_adjustment": adj.get("active_adjustment", 0.0),
    }


def get_ledger_history(n: int = 20) -> List[Dict[str, Any]]:
    return _read_ledger(n)


# ─────────────────────────────────────────────────────────────────────────────
# GOVERNANCE -- fully automated daily/periodic check, no human step
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_refinement_check() -> Dict[str, Any]:
    try:
        return _run_impl()
    except Exception as exc:
        log.debug("[CompanyGrowthRE] refinement check error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl() -> Dict[str, Any]:
    from learning_system.company_growth_evidence_log import get_records

    records = get_records()
    state   = _read_json(_STATE_PATH, {"status": STATUS_WAITING})
    adj_store = _read_json(_ADJ_PATH, {})

    outcome = _evaluate(state, records)
    _write_json(_STATE_PATH, outcome["state"])
    if outcome.get("adjustment_changed"):
        if outcome["state"]["status"] == STATUS_ACTIVE:
            adj_store["active_adjustment"] = outcome["state"]["active_adjustment"]
        elif outcome["state"]["status"] in (STATUS_ROLLED_BACK, STATUS_REJECTED, STATUS_WAITING):
            adj_store.pop("active_adjustment", None)
        _write_json(_ADJ_PATH, adj_store)

    return {"status": "OK", "detail": outcome.get("detail", ""), "state_status": outcome["state"]["status"]}


def _evaluate(state: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    status = state.get("status", STATUS_WAITING)
    n = len(records)

    if status == STATUS_ACTIVE:
        activated_at_n = state.get("activated_at_sample_size", 0)
        post_active = records[activated_at_n:]
        if len(post_active) < ROLLBACK_DEGRADATION_N:
            return {"state": {**state, "last_sample_size": n}, "detail": "monitoring"}
        confirm = _reconfirm_scorecard(post_active)
        expected_direction = state.get("direction", 1)
        degraded = confirm["direction"] != expected_direction or not confirm["passed"]
        if degraded:
            _append_ledger("ROLLED_BACK", "post-activation evidence no longer supports the adjustment",
                            confirm_scorecard=confirm)
            return {"state": {"status": STATUS_ROLLED_BACK, "last_sample_size": n},
                    "adjustment_changed": True, "detail": "rolled back"}
        return {"state": {**state, "last_sample_size": n}, "detail": "active, healthy"}

    if status == STATUS_SHADOW:
        shadow_started_n = state.get("shadow_started_at_sample_size", 0)
        new_evidence = records[shadow_started_n:]
        if len(new_evidence) < MIN_SHADOW_NEW_EVIDENCE:
            return {"state": {**state, "last_sample_size": n},
                    "detail": f"shadow, {len(new_evidence)}/{MIN_SHADOW_NEW_EVIDENCE} new evidence"}
        confirm = _reconfirm_scorecard(new_evidence)
        expected_direction = state.get("direction", 1)
        if confirm["passed"] and confirm["direction"] == expected_direction:
            adj = state.get("candidate_adjustment", 0.0)
            _append_ledger("PROMOTED", "shadow reconfirmed on new evidence", adjustment=adj, confirm_scorecard=confirm)
            return {
                "state": {"status": STATUS_ACTIVE, "active_adjustment": adj, "direction": expected_direction,
                          "activated_at_sample_size": n, "last_sample_size": n},
                "adjustment_changed": True, "detail": f"promoted, adjustment={adj}",
            }
        _append_ledger("REJECTED", "shadow failed to reconfirm", confirm_scorecard=confirm)
        return {"state": {"status": STATUS_REJECTED, "last_sample_size": n},
                "adjustment_changed": True, "detail": "shadow rejected"}

    last_checked = state.get("last_checked_at")
    if last_checked:
        try:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_checked)).days
            if elapsed < COOLDOWN_DAYS:
                return {"state": {**state, "last_sample_size": n}, "detail": "cooldown"}
        except ValueError:
            pass

    card = _scorecard(records)
    new_state = {**state, "last_sample_size": n, "last_checked_at": datetime.now(timezone.utc).isoformat()}
    if not card["passed"]:
        new_state["status"] = STATUS_WAITING
        return {"state": new_state, "detail": f"waiting, n={n}"}

    adj = _candidate_adjustment(card["direction"])
    _append_ledger("SHADOW_STARTED", "candidate validated on train/OOS split", adjustment=adj, scorecard=card)
    new_state.update({"status": STATUS_SHADOW, "candidate_adjustment": adj,
                       "direction": card["direction"], "shadow_started_at_sample_size": n})
    return {"state": new_state, "detail": f"shadow started, adjustment={adj}"}
