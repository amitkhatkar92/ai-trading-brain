"""
learning_system/cle_fingerprint_refinement_engine.py
========================================================
DTA-RESEARCH-QUALITY-001 -- SYNTHESIS + GOVERNANCE for CLE-001's combination
fingerprint selection (cle_learning_executor/cle_research.py's
_select_best_fingerprint()).

CLE-001 already only ever creates a DNA candidate at lifecycle=DISCOVERED
after real entry-day evidence clears a strict bar (MIN_SAMPLE/MIN_WIN_RATE/
MIN_LIFT). What it could not previously know is whether the fingerprint it
picked THAT day tends to produce DNA that actually SURVIVES and progresses
(REPLICATED -> VERIFIED -> INSTITUTIONAL) versus DNA that stalls forever at
DISCOVERED or gets RETIRED. This engine closes that loop: it watches each
DNA candidate's OWN real, later IDR lifecycle outcome and, once enough
evidence accumulates PER FINGERPRINT TYPE, produces a small, bounded
preference nudge feeding back into _select_best_fingerprint()'s own
tie-breaking ranking -- never bypassing the entry-day evidence gate, only
influencing which already-qualifying fingerprint is preferred among ties.

LIFECYCLE (fully automated, no human step at any transition -- mirrors
strategy_lab/regime_map_refinement_engine.py's per-key state-machine shape,
reused as a template only; zero shared imports/storage):
  WAITING_FOR_EVIDENCE -> SHADOW_ACTIVE -> ACTIVE/REJECTED
  ACTIVE -> ROLLED_BACK (auto-revert if post-activation evidence degrades)

"GRADUATED" vs "STALLED" classification
------------------------------------------
A DNA candidate is only evaluated once mature (>= MATURITY_DAYS since
creation, matching CLE's own 30-trading-day first verification window).
GRADUATED  = IDR lifecycle in (REPLICATED, VERIFIED, INSTITUTIONAL,
             WEAKENING, DRIFTING) -- i.e. it progressed past first
             observation at least once.
STALLED    = lifecycle still DISCOVERED after the maturity window, or
             explicitly RETIRED.
Validated per fingerprint_name against a fixed, neutral 0.50 null (not a
cohort comparison against the other fingerprints -- each fingerprint type
is judged on its own absolute graduation rate).

SAFETY CONTRACT
-----------------
Zero imports of execution_engine, order_manager, broker APIs, risk_control.
get_fingerprint_preference_adjustment() is a pure, read-only accessor,
bounded +/-MAX_ADJUSTMENT, defaults to 0.0 on any error/missing evidence.
Never mutates any IDR record -- read-only w.r.t. market_learning/idr_repository.py.
"""
from __future__ import annotations

import json
import os
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

ACTOR = "CLE-FINGERPRINT-RE-001"

_ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR   = os.path.join(_ROOT, "data", "learning_system", "cle_fingerprint_refinement")
_STATE_PATH  = os.path.join(_STORE_DIR, "state.json")
_ADJ_PATH    = os.path.join(_STORE_DIR, "active_adjustments.json")
_RESOLVED_PATH = os.path.join(_STORE_DIR, "resolved_outcomes.json")
_LEDGER_PATH = os.path.join(_STORE_DIR, "ledger.jsonl")

MATURITY_DAYS             = 45     # ~30 trading days, matches CLE's own first verification window
MIN_SAMPLE_FOR_VALIDATION = 30
MIN_SHADOW_NEW_EVIDENCE   = 12
MIN_EFFECT_MAGNITUDE      = 0.05   # graduation rate must clear the 0.50 null by >=5pp
BOOTSTRAP_ITERS           = 1000
COOLDOWN_DAYS             = 30
MAX_ADJUSTMENT            = 0.15   # bounded lift-unit nudge, proportionate to typical 1.3-3.0 lift range
ROLLBACK_DEGRADATION_N    = 12

_GRADUATED_STATES = ("REPLICATED", "VERIFIED", "INSTITUTIONAL", "WEAKENING", "DRIFTING")
_STALLED_STATES   = ("DISCOVERED", "RETIRED")

STATUS_WAITING     = "WAITING_FOR_EVIDENCE"
STATUS_SHADOW      = "SHADOW_ACTIVE"
STATUS_ACTIVE      = "ACTIVE"
STATUS_ROLLED_BACK = "ROLLED_BACK"
STATUS_REJECTED    = "REJECTED"


# ─────────────────────────────────────────────────────────────────────────────
# I/O helpers
# ─────────────────────────────────────────────────────────────────────────────

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


def _append_ledger(event_type: str, fingerprint_name: str, reason: str, **extra: Any) -> None:
    try:
        record = {
            "event_id": datetime.now(timezone.utc).isoformat() + "-" + event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": ACTOR,
            "event_type": event_type,
            "fingerprint_name": fingerprint_name,
            "reason": reason,
            **extra,
        }
        os.makedirs(_STORE_DIR, exist_ok=True)
        with open(_LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        log.debug("[CLEFingerprintRE] ledger write failed: %s", exc)


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
# Resolution -- maps a mature DNA candidate to GRADUATED/STALLED via the real
# IDR lifecycle state. Results are cached (a dna_id is only ever resolved
# once) since a graduated/stalled classification, once resolved, is durable
# evidence for this engine's own purposes.
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_new_outcomes(evidence_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    resolved = _read_json(_RESOLVED_PATH, {})
    today = date.today()

    try:
        from market_learning.idr_repository import IDRRepository, IDRNotFoundError
    except Exception:
        return resolved

    try:
        repo = IDRRepository()
    except Exception:
        return resolved

    changed = False
    for rec in evidence_records:
        dna_id = rec.get("dna_id")
        if not dna_id or dna_id in resolved:
            continue
        try:
            created = datetime.strptime(rec["created_date"], "%Y-%m-%d").date()
        except Exception:
            continue
        if (today - created).days < MATURITY_DAYS:
            continue  # not mature yet -- try again on a later run

        try:
            dna = repo.get(dna_id)
        except IDRNotFoundError:
            continue
        except Exception as exc:
            log.debug("[CLEFingerprintRE] IDR lookup failed for %s: %s", dna_id, exc)
            continue

        lifecycle = getattr(dna, "lifecycle", "DISCOVERED")
        graduated = lifecycle in _GRADUATED_STATES

        resolved[dna_id] = {
            "fingerprint_name": rec.get("fingerprint_name"),
            "graduated": graduated,
            "lifecycle_at_resolution": lifecycle,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
        changed = True

    if changed:
        _write_json(_RESOLVED_PATH, resolved)
    return resolved


def _records_for_fingerprint(resolved: Dict[str, Dict[str, Any]], name: str) -> List[bool]:
    return [r["graduated"] for r in resolved.values() if r.get("fingerprint_name") == name]


# ─────────────────────────────────────────────────────────────────────────────
# Statistical validation -- graduation rate vs a fixed 0.50 null (mirrors the
# time-split + bootstrap-CI scorecard shape used across this repo's other
# refinement engines).
# ─────────────────────────────────────────────────────────────────────────────

def _bootstrap_ci_vs_null(outcomes: List[bool], null_rate: float = 0.50,
                           iters: int = BOOTSTRAP_ITERS, seed: int = 42) -> Optional[Tuple[float, float]]:
    if not outcomes:
        return None
    rng = random.Random(seed)
    n = len(outcomes)
    diffs = []
    for _ in range(iters):
        sample_rate = sum(outcomes[rng.randrange(n)] for _ in range(n)) / n
        diffs.append(sample_rate - null_rate)
    diffs.sort()
    lo = diffs[int(0.025 * iters)]
    hi = diffs[int(0.975 * iters) - 1]
    return (lo, hi)


def _scorecard(outcomes: List[bool]) -> Dict[str, Any]:
    n = len(outcomes)
    result: Dict[str, Any] = {"sample_size": n, "passed": False, "checks": {}}
    if n < MIN_SAMPLE_FOR_VALIDATION:
        result["checks"]["sample_size"] = False
        return result
    result["checks"]["sample_size"] = True

    split = int(n * 0.7)
    train, oos = outcomes[:split], outcomes[split:]
    if not oos:
        result["checks"]["sample_size"] = False
        return result

    train_diff = (sum(train) / len(train)) - 0.50
    oos_diff   = (sum(oos) / len(oos)) - 0.50

    ci = _bootstrap_ci_vs_null(oos)
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


def _reconfirm_scorecard(outcomes: List[bool]) -> Dict[str, Any]:
    if not outcomes:
        return {"sample_size": 0, "passed": False, "direction": 0}
    diff = (sum(outcomes) / len(outcomes)) - 0.50
    direction = 1 if diff > 0 else (-1 if diff < 0 else 0)
    passed = abs(diff) >= MIN_EFFECT_MAGNITUDE
    return {"sample_size": len(outcomes), "diff": round(diff, 4), "passed": passed, "direction": direction}


def _candidate_adjustment(direction: int) -> float:
    return MAX_ADJUSTMENT if direction == 1 else -MAX_ADJUSTMENT


# ─────────────────────────────────────────────────────────────────────────────
# Public read-side API -- consumed by cle_learning_executor/cle_research.py
# ─────────────────────────────────────────────────────────────────────────────

def get_fingerprint_preference_adjustment(fingerprint_name: str) -> float:
    """
    Bounded +/-MAX_ADJUSTMENT nudge for a given fingerprint name's LIFT
    ranking. Returns 0.0 whenever no validated, ACTIVE adjustment exists
    for this fingerprint. Never raises.
    """
    try:
        adj_store = _read_json(_ADJ_PATH, {})
        val = adj_store.get(fingerprint_name)
        if val is None:
            return 0.0
        return max(-MAX_ADJUSTMENT, min(MAX_ADJUSTMENT, float(val)))
    except Exception as exc:
        log.debug("[CLEFingerprintRE] get_fingerprint_preference_adjustment fallback to 0.0: %s", exc)
        return 0.0


def get_refinement_status() -> Dict[str, Any]:
    state = _read_json(_STATE_PATH, {})
    adj = _read_json(_ADJ_PATH, {})
    per_fingerprint = {}
    for name, s in state.items():
        per_fingerprint[name] = {
            "status": s.get("status", STATUS_WAITING),
            "sample_size": s.get("last_sample_size", 0),
            "active_adjustment": adj.get(name, 0.0),
        }
    return {"per_fingerprint": per_fingerprint}


def get_ledger_history(n: int = 20) -> List[Dict[str, Any]]:
    return _read_ledger(n)


# ─────────────────────────────────────────────────────────────────────────────
# GOVERNANCE -- fully automated daily/periodic check, no human step
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_refinement_check() -> Dict[str, Any]:
    try:
        return _run_impl()
    except Exception as exc:
        log.debug("[CLEFingerprintRE] refinement check error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl() -> Dict[str, Any]:
    from learning_system.cle_fingerprint_evidence_log import get_records

    evidence = get_records()
    resolved = _resolve_new_outcomes(evidence)

    fingerprint_names = sorted({r.get("fingerprint_name") for r in evidence if r.get("fingerprint_name")})

    state = _read_json(_STATE_PATH, {})
    adj_store = _read_json(_ADJ_PATH, {})
    results: Dict[str, Any] = {}

    for name in fingerprint_names:
        outcomes = _records_for_fingerprint(resolved, name)
        fp_state = state.get(name, {"status": STATUS_WAITING})
        outcome = _evaluate_fingerprint(name, fp_state, outcomes)
        state[name] = outcome["state"]
        if outcome.get("adjustment_changed"):
            if outcome["state"]["status"] == STATUS_ACTIVE:
                adj_store[name] = outcome["state"]["active_adjustment"]
            elif outcome["state"]["status"] in (STATUS_ROLLED_BACK, STATUS_REJECTED, STATUS_WAITING):
                adj_store.pop(name, None)
        results[name] = {"status": outcome["state"]["status"], "detail": outcome.get("detail", "")}

    _write_json(_STATE_PATH, state)
    _write_json(_ADJ_PATH, adj_store)
    return {"status": "OK", "per_fingerprint": results}


def _evaluate_fingerprint(name: str, fp_state: Dict[str, Any],
                           outcomes: List[bool]) -> Dict[str, Any]:
    status = fp_state.get("status", STATUS_WAITING)
    n = len(outcomes)

    if status == STATUS_ACTIVE:
        activated_at_n = fp_state.get("activated_at_sample_size", 0)
        post_active = outcomes[activated_at_n:]
        if len(post_active) < ROLLBACK_DEGRADATION_N:
            return {"state": {**fp_state, "last_sample_size": n}, "detail": "monitoring"}
        confirm = _reconfirm_scorecard(post_active)
        expected_direction = fp_state.get("direction", 1)
        degraded = confirm["direction"] != expected_direction or not confirm["passed"]
        if degraded:
            _append_ledger("ROLLED_BACK", name, "post-activation evidence no longer supports the adjustment",
                            confirm_scorecard=confirm)
            return {"state": {"status": STATUS_ROLLED_BACK, "last_sample_size": n},
                    "adjustment_changed": True, "detail": "rolled back"}
        return {"state": {**fp_state, "last_sample_size": n}, "detail": "active, healthy"}

    if status == STATUS_SHADOW:
        shadow_started_n = fp_state.get("shadow_started_at_sample_size", 0)
        new_evidence = outcomes[shadow_started_n:]
        if len(new_evidence) < MIN_SHADOW_NEW_EVIDENCE:
            return {"state": {**fp_state, "last_sample_size": n},
                    "detail": f"shadow, {len(new_evidence)}/{MIN_SHADOW_NEW_EVIDENCE} new evidence"}
        confirm = _reconfirm_scorecard(new_evidence)
        expected_direction = fp_state.get("direction", 1)
        if confirm["passed"] and confirm["direction"] == expected_direction:
            adj = fp_state.get("candidate_adjustment", 0.0)
            _append_ledger("PROMOTED", name, "shadow reconfirmed on new evidence",
                            adjustment=adj, confirm_scorecard=confirm)
            return {
                "state": {"status": STATUS_ACTIVE, "active_adjustment": adj, "direction": expected_direction,
                          "activated_at_sample_size": n, "last_sample_size": n},
                "adjustment_changed": True, "detail": f"promoted, adjustment={adj}",
            }
        _append_ledger("REJECTED", name, "shadow failed to reconfirm", confirm_scorecard=confirm)
        return {"state": {"status": STATUS_REJECTED, "last_sample_size": n},
                "adjustment_changed": True, "detail": "shadow rejected"}

    last_checked = fp_state.get("last_checked_at")
    if last_checked:
        try:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_checked)).days
            if elapsed < COOLDOWN_DAYS:
                return {"state": {**fp_state, "last_sample_size": n}, "detail": "cooldown"}
        except ValueError:
            pass

    card = _scorecard(outcomes)
    new_state = {**fp_state, "last_sample_size": n, "last_checked_at": datetime.now(timezone.utc).isoformat()}
    if not card["passed"]:
        new_state["status"] = STATUS_WAITING
        return {"state": new_state, "detail": f"waiting, n={n}"}

    adj = _candidate_adjustment(card["direction"])
    _append_ledger("SHADOW_STARTED", name, "candidate validated on train/OOS split", adjustment=adj, scorecard=card)
    new_state.update({"status": STATUS_SHADOW, "candidate_adjustment": adj,
                       "direction": card["direction"], "shadow_started_at_sample_size": n})
    return {"state": new_state, "detail": f"shadow started, adjustment={adj}"}
