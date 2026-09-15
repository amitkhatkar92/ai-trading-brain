"""
learning_system/sizing_bounds_refinement_engine.py
======================================================
Self-learning module #27: confidence + strategy-history combined sizing
-- calibration layer.

AUDIT FINDING (before writing any code)
------------------------------------------
Both halves of postponed_improvements.md's originally-proposed "combined
confidence + strategy history sizing" formula are ALREADY LIVE today, as
two independent, already evidence-gated multiplicative factors:
  1. Confidence-based risk_pct scaling (risk_control/portfolio_
     allocation_ai.py: `_risk_pct = MAX_RISK_PER_TRADE_PCT * (0.6 +
     conf_norm * 0.8)`) -- implemented 2026-05-25.
  2. Strategy-history perf_weight (learning_system/
     strategy_performance_tracker.py: `get_performance_weight()`, bounded
     [0.5x, 2.0x], gated on MIN_SAMPLE=10 OFFICIAL trades, returns 1.0
     (neutral) below that -- already fully self-learning).
Rebuilding a third, separate "combined_score" formula duplicating both
of these would not add anything new. The genuine remaining gap is:
nobody has ever validated whether perf_weight's bounds ([0.5x, 2.0x])
are actually well-calibrated against REAL realized outcomes, or whether
they should be tightened/widened based on evidence. This module closes
that gap -- a "constant refinement" mechanism (mirrors knowledge_
authority/kda_constant_refinement_engine.py's approach exactly) applied
to perf_weight's own clamp bounds, not a new sizing formula.

ACQUISITION reuses the exact EOD loop where perf_tracker.record_trade()
is already called (orchestrator/master_orchestrator.py's "Performance
Evaluation" block) -- additively records, per closed trade, the
perf_weight value get_performance_weight(strategy) WOULD return today
(a fair proxy for "was this trade boosted, reduced, or neutral") against
the trade's own realized r_multiple/win-loss outcome.

SYNTHESIS+GOVERNANCE splits trades into a "boosted" cohort
(perf_weight > 1.05) vs a "not boosted" cohort (<= 1.05), and validates
via the same time-ordered 70/30 bootstrap-CI scorecard already used
elsewhere in this session whether the boosted cohort's win-rate is
reliably HIGHER than the not-boosted cohort -- i.e. whether perf_weight
itself is a real, evidence-backed signal. If validated, the upper bound
may be evidence-widened (bounded, capped at +0.3 above the original 2.0x
ceiling); if the boosted cohort shows NO improvement or WORSE
performance, the upper bound is evidence-narrowed instead (dampens
perf_weight's effect), following the exact shadow-then-live lifecycle.

LIFECYCLE (fully automated, no human step at any transition)
--------------------------------------------------------------
  WAITING_FOR_EVIDENCE -> SHADOW_ACTIVE -> ACTIVE/REJECTED
  ACTIVE -> ROLLED_BACK (auto-revert if post-activation evidence no
  longer supports the adjustment)

SAFETY CONTRACT
-----------------
  Zero imports of execution_engine, order_manager, broker APIs. Lives in
  learning_system/ (not risk_control/) so sandy/sandy_supervisor.py's own
  safety contract -- which forbids importing risk_control anywhere -- can
  still poll this module's read-only status for observability. Never
  imports or modifies risk_control/portfolio_allocation_ai.py's sizing
  logic directly -- get_effective_perf_weight_bounds() is a pure,
  read-only accessor consumed by portfolio_allocation_ai.py via ONE
  additional re-clamp line, falling back to the original hardcoded
  (0.5, 2.0) bounds on any error. learning_system/strategy_performance_
  tracker.py's get_performance_weight() formula itself is never modified.
"""
from __future__ import annotations

import json
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

ACTOR = "SIZING-BOUNDS-RE-001"

_ROOT          = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR     = os.path.join(_ROOT, "data", "risk_control", "sizing_calibration")
_EVIDENCE_PATH = os.path.join(_STORE_DIR, "evidence.jsonl")
_STATE_PATH    = os.path.join(_STORE_DIR, "state.json")
_BOUNDS_PATH   = os.path.join(_STORE_DIR, "active_bounds.json")
_LEDGER_PATH   = os.path.join(_STORE_DIR, "ledger.jsonl")

# Original hardcoded bounds -- the ONLY source of truth for "no override".
# Mirrors learning_system/strategy_performance_tracker.py's
# get_performance_weight() clamp exactly (duplicated, not imported, so
# this module never depends on the live tracker's internals).
DEFAULT_LOWER_BOUND = 0.5
DEFAULT_UPPER_BOUND = 2.0

MIN_SAMPLE_FOR_VALIDATION = 30
MIN_SHADOW_NEW_EVIDENCE   = 15
MIN_EFFECT_MAGNITUDE      = 0.05
BOOTSTRAP_ITERS           = 1000
COOLDOWN_DAYS             = 30
BOOSTED_THRESHOLD         = 1.05
MAX_BOUND_ADJUSTMENT      = 0.30   # bounded evidence-driven widen/narrow of the upper bound
ROLLBACK_DEGRADATION      = 0.05
MIN_POST_ACTIVE_FOR_ROLLBACK_CHECK = 15

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
        log.debug("[SizingBoundsRE] ledger write failed: %s", exc)


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
# ACQUISITION
# ─────────────────────────────────────────────────────────────────────────────

def record_sizing_outcome(strategy: str, perf_weight: float, r_multiple: float, won: bool) -> None:
    """
    Append one real, closed trade's (perf_weight, outcome) pair. Never
    raises -- a failure here must never affect learning, risk, execution,
    or reporting.
    """
    try:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategy": strategy,
            "perf_weight": float(perf_weight),
            "r_multiple": float(r_multiple),
            "won": bool(won),
        }
        os.makedirs(_STORE_DIR, exist_ok=True)
        with open(_EVIDENCE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        log.debug("[SizingBoundsRE] record failed (non-critical): %s", exc)


def get_records() -> List[Dict[str, Any]]:
    """Read-only accessor: time-ordered (oldest-first) persisted evidence."""
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
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Statistical validation
# ─────────────────────────────────────────────────────────────────────────────

def _bootstrap_ci_diff(boosted: List[bool], not_boosted: List[bool],
                        iters: int = BOOTSTRAP_ITERS, seed: int = 42) -> Optional[Tuple[float, float]]:
    if not boosted or not not_boosted:
        return None
    rng = random.Random(seed)
    nb, nn = len(boosted), len(not_boosted)
    diffs = []
    for _ in range(iters):
        b_wr = sum(boosted[rng.randrange(nb)] for _ in range(nb)) / nb
        n_wr = sum(not_boosted[rng.randrange(nn)] for _ in range(nn)) / nn
        diffs.append(b_wr - n_wr)
    diffs.sort()
    lo = diffs[int(0.025 * iters)]
    hi = diffs[int(0.975 * iters) - 1]
    return (lo, hi)


def _scorecard(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    records: time-ordered (oldest-first) [{"perf_weight", "won", ...}].
    Splits into boosted/not-boosted cohorts; validates via time-ordered
    70/30 split + bootstrap CI on the win-rate DIFFERENCE between cohorts.
    """
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

    def _cohort_diff(recs: List[Dict[str, Any]]) -> Optional[float]:
        boosted = [bool(r["won"]) for r in recs if r["perf_weight"] > BOOSTED_THRESHOLD]
        not_boosted = [bool(r["won"]) for r in recs if r["perf_weight"] <= BOOSTED_THRESHOLD]
        if not boosted or not not_boosted:
            return None
        return (sum(boosted) / len(boosted)) - (sum(not_boosted) / len(not_boosted))

    train_diff = _cohort_diff(train)
    oos_diff   = _cohort_diff(oos)
    if train_diff is None or oos_diff is None:
        result["checks"]["sample_size"] = False
        result["detail"] = "insufficient cohort split (need both boosted and not-boosted trades)"
        return result

    oos_boosted = [bool(r["won"]) for r in oos if r["perf_weight"] > BOOSTED_THRESHOLD]
    oos_not     = [bool(r["won"]) for r in oos if r["perf_weight"] <= BOOSTED_THRESHOLD]
    ci = _bootstrap_ci_diff(oos_boosted, oos_not)
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
    boosted = [bool(r["won"]) for r in records if r["perf_weight"] > BOOSTED_THRESHOLD]
    not_boosted = [bool(r["won"]) for r in records if r["perf_weight"] <= BOOSTED_THRESHOLD]
    if not boosted or not not_boosted:
        return {"sample_size": len(records), "passed": False, "direction": 0}
    diff = (sum(boosted) / len(boosted)) - (sum(not_boosted) / len(not_boosted))
    direction = 1 if diff > 0 else (-1 if diff < 0 else 0)
    passed = abs(diff) >= MIN_EFFECT_MAGNITUDE
    return {"sample_size": len(records), "diff": round(diff, 4), "passed": passed, "direction": direction}


def _candidate_adjustment(direction: int) -> float:
    return MAX_BOUND_ADJUSTMENT if direction == 1 else -MAX_BOUND_ADJUSTMENT


# ─────────────────────────────────────────────────────────────────────────────
# Public read-side API -- consumed by risk_control/portfolio_allocation_ai.py
# ─────────────────────────────────────────────────────────────────────────────

_cache_mtime: Optional[float] = None
_cache_bounds: Optional[Tuple[float, float]] = None


def get_effective_perf_weight_bounds() -> Tuple[float, float]:
    """
    Return (lower, upper) perf_weight clamp bounds. Applies a validated,
    bounded adjustment to the upper bound only when real evidence
    justifies it; falls back to the exact original hardcoded (0.5, 2.0)
    on any error, missing file, or no active adjustment. Never raises.
    """
    global _cache_mtime, _cache_bounds
    try:
        if not os.path.exists(_BOUNDS_PATH):
            return (DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
        mtime = os.path.getmtime(_BOUNDS_PATH)
        if _cache_bounds is not None and _cache_mtime == mtime:
            return _cache_bounds

        raw = _read_json(_BOUNDS_PATH, {})
        adj = raw.get("upper_adjustment")
        if not isinstance(adj, (int, float)):
            return (DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
        adj = max(-MAX_BOUND_ADJUSTMENT, min(MAX_BOUND_ADJUSTMENT, float(adj)))
        result = (DEFAULT_LOWER_BOUND, round(DEFAULT_UPPER_BOUND + adj, 4))
        _cache_mtime, _cache_bounds = mtime, result
        return result
    except Exception as exc:
        log.debug("[SizingBoundsRE] get_effective_perf_weight_bounds fallback to defaults: %s", exc)
        return (DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)


def get_refinement_status() -> Dict[str, Any]:
    state = _read_json(_STATE_PATH, {"status": STATUS_WAITING})
    bounds = _read_json(_BOUNDS_PATH, {})
    return {
        "status": state.get("status", STATUS_WAITING),
        "sample_size": state.get("last_sample_size", 0),
        "active_adjustment": bounds.get("upper_adjustment", 0.0),
    }


def get_ledger_history(n: int = 20) -> List[Dict[str, Any]]:
    return _read_ledger(n)


# ─────────────────────────────────────────────────────────────────────────────
# GOVERNANCE -- fully automated daily/periodic check
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_refinement_check() -> Dict[str, Any]:
    try:
        return _run_impl()
    except Exception as exc:
        log.debug("[SizingBoundsRE] refinement check error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl() -> Dict[str, Any]:
    records = get_records()
    state = _read_json(_STATE_PATH, {"status": STATUS_WAITING})
    bounds = _read_json(_BOUNDS_PATH, {})

    outcome = _evaluate(state, records)
    _write_json(_STATE_PATH, outcome["state"])
    if outcome.get("bounds_changed"):
        if outcome["state"]["status"] == STATUS_ACTIVE:
            bounds["upper_adjustment"] = outcome["state"]["active_adjustment"]
        elif outcome["state"]["status"] in (STATUS_ROLLED_BACK, STATUS_REJECTED, STATUS_WAITING):
            bounds.pop("upper_adjustment", None)
        _write_json(_BOUNDS_PATH, bounds)

    return {"status": "OK", "detail": outcome.get("detail", ""), "state_status": outcome["state"]["status"]}


def _evaluate(state: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    status = state.get("status", STATUS_WAITING)
    n = len(records)

    if status == STATUS_ACTIVE:
        activated_at_n = state.get("activated_at_sample_size", 0)
        post_active = records[activated_at_n:]
        if len(post_active) < MIN_POST_ACTIVE_FOR_ROLLBACK_CHECK:
            return {"state": {**state, "last_sample_size": n}, "detail": "monitoring"}
        confirm = _reconfirm_scorecard(post_active)
        expected_direction = state.get("direction", 1)
        degraded = confirm["direction"] != expected_direction or not confirm["passed"]
        if degraded:
            _append_ledger("ROLLED_BACK", "post-activation evidence no longer supports the adjustment",
                            confirm_scorecard=confirm)
            return {"state": {"status": STATUS_ROLLED_BACK, "last_sample_size": n},
                    "bounds_changed": True, "detail": "rolled back"}
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
                "bounds_changed": True, "detail": f"promoted, adjustment={adj}",
            }
        _append_ledger("REJECTED", "shadow failed to reconfirm", confirm_scorecard=confirm)
        return {"state": {"status": STATUS_REJECTED, "last_sample_size": n},
                "bounds_changed": True, "detail": "shadow rejected"}

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
