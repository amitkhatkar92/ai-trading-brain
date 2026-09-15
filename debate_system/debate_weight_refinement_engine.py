"""
debate_system/debate_weight_refinement_engine.py
===================================================
Self-Learning Ecosystem -- Post-roadmap Priority 3 (part 2 of 2):
SYNTHESIS + GOVERNANCE for MultiAgentDebate weight self-tuning.

Consumes the evidence built by debate_vote_tracker.py (ACQUISITION+
VALIDATION) and decides, per debater, whether real accumulated evidence
justifies a small, BOUNDED weight nudge -- following the exact
shadow-then-live, fully-automated lifecycle already proven twice in
this repo (knowledge_authority/kda_constant_refinement_engine.py,
scripts/knowledge_system/ranking_adjustment_engine_001.py), reused as a
TEMPLATE only (zero imports from either module, zero shared storage).
Isolated store: data/debate/.

WHY A HIGHER EVIDENCE BAR THAN OTHER PHASES
----------------------------------------------
This gates a live-money vote weight directly (unlike e.g. RHV-001's
research-ranking shadow score) -- MIN_SAMPLE_FOR_VALIDATION mirrors
KDA-CRE-001's own reasoning for using a materially higher minimum than
a generic research hypothesis.

LIFECYCLE (fully automated, no human step at any transition)
--------------------------------------------------------------
  WAITING_FOR_EVIDENCE -- fewer than MIN_SAMPLE_FOR_VALIDATION resolved
                          votes for this debater, and/or cooldown active.
  SHADOW_ACTIVE         -- a statistically-validated candidate delta is
                          being reconfirmed against NEW, held-out
                          evidence (never the same evidence used to
                          propose it) -- zero effect on the live weight
                          while in this state.
  ACTIVE                -- shadow-confirmed; the bounded delta is now
                          applied to this debater's live weight (read by
                          decision_ai/decision_engine.py).
  ROLLED_BACK           -- post-activation evidence shows the debater's
                          accuracy degraded back toward/below baseline;
                          automatically reverted to the original weight.
  REJECTED              -- shadow period failed to reconfirm the effect.

STATISTICAL VALIDATION (mirrors RHV-001/KDA-CRE-001's proven scorecard)
---------------------------------------------------------------------------
Time-ordered 70/30 train/OOS split (never shuffled -- decision_date
order), bootstrap CI (1000 iters, seeded) on OOS accuracy vs the 0.50
null (a debater whose approve/reject signal is no better than a coin
flip), 4-check scorecard: sample size, CI excludes 0.50, train/OOS sign
consistency (both sides of 0.50 agree), minimum effect magnitude.

SAFETY CONTRACT (never violated)
-----------------------------------
  Zero imports of execution_engine, order_manager, broker APIs, or
  risk_control. decision_ai/decision_engine.py's decide() logic and
  DebateVote/DecisionResult shapes are completely unchanged -- only the
  WEIGHT VALUE fed into the existing weighted-average formula can move,
  bounded to +/-MAX_WEIGHT_DELTA, and only after full validation.
  Every transition is appended (never overwritten) to
  data/debate/weight_refinement_ledger.jsonl with full reasoning.
"""
from __future__ import annotations

import json
import math
import os
import random
import statistics
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

ACTOR = "DEBATE-WRE-001"

_ROOT           = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR      = os.path.join(_ROOT, "data", "debate")
_STATE_PATH     = os.path.join(_STORE_DIR, "weight_refinement_state.json")
_OVERRIDES_PATH = os.path.join(_STORE_DIR, "active_weight_overrides.json")
_LEDGER_PATH    = os.path.join(_STORE_DIR, "weight_refinement_ledger.jsonl")

# Original hardcoded defaults -- the ONLY source of truth for "no override".
# Mirrors decision_ai/decision_engine.py's AGENT_WEIGHTS exactly; duplicated
# here (not imported) so this module never depends on the live decision path.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "TechnicalAnalystAI": 0.30,
    "MacroAnalystAI":     0.20,
    "RiskDebateAI":       0.25,
    "SentimentAI":        0.15,
    "RegimeDebateAI":     0.10,
    "InstitutionalDNAAI": 0.08,
}

MIN_SAMPLE_FOR_VALIDATION = 50    # higher bar -- gates a live-money vote weight
MIN_SHADOW_NEW_EVIDENCE   = 20    # new resolved votes required during shadow before promotion
MAX_WEIGHT_DELTA          = 0.05  # bounded nudge -- cannot dominate the original weight
MIN_EFFECT_MAGNITUDE      = 0.05  # OOS accuracy must be >=5pp away from the 0.50 null
BOOTSTRAP_ITERS           = 1000
COOLDOWN_DAYS             = 30    # min days between refinement checks per debater
ROLLBACK_DEGRADATION      = 0.05  # post-activation accuracy dropping 5pp below 0.50+effect triggers rollback
MIN_POST_ACTIVE_FOR_ROLLBACK_CHECK = 20

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


def _append_ledger(event_type: str, agent_name: str, reason: str, **extra: Any) -> None:
    try:
        record = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": ACTOR,
            "event_type": event_type,
            "agent_name": agent_name,
            "reason": reason,
            **extra,
        }
        os.makedirs(_STORE_DIR, exist_ok=True)
        with open(_LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        log.debug("[DebateWRE] ledger write failed: %s", exc)


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
# Statistical validation (mirrors RHV-001/KDA-CRE-001's scorecard shape)
# ─────────────────────────────────────────────────────────────────────────────

def _bootstrap_ci_accuracy(labels: List[bool], iters: int = BOOTSTRAP_ITERS,
                            seed: int = 42) -> Optional[tuple]:
    if not labels:
        return None
    rng = random.Random(seed)
    n = len(labels)
    samples = []
    for _ in range(iters):
        resampled = [labels[rng.randrange(n)] for _ in range(n)]
        samples.append(sum(resampled) / n)
    samples.sort()
    lo = samples[int(0.025 * iters)]
    hi = samples[int(0.975 * iters) - 1]
    return (lo, hi)


def _scorecard(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    records: time-ordered (oldest-first) [{"decision_date","correct"}].
    Returns a scorecard dict: sample_size, train_acc, oos_acc, ci,
    checks (4 booleans), passed (bool), effective_direction (+1/-1/0).
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

    train_labels = [bool(r["correct"]) for r in train]
    oos_labels   = [bool(r["correct"]) for r in oos]
    train_acc = sum(train_labels) / len(train_labels)
    oos_acc   = sum(oos_labels) / len(oos_labels)

    ci = _bootstrap_ci_accuracy(oos_labels)
    ci_excludes_null = ci is not None and (ci[0] > 0.5 or ci[1] < 0.5)
    result["checks"]["ci_excludes_null"] = ci_excludes_null

    sign_consistent = (train_acc - 0.5) * (oos_acc - 0.5) > 0
    result["checks"]["sign_consistent"] = sign_consistent

    effect_ok = abs(oos_acc - 0.5) >= MIN_EFFECT_MAGNITUDE
    result["checks"]["effect_magnitude"] = effect_ok

    result.update({
        "train_accuracy": round(train_acc, 4),
        "oos_accuracy": round(oos_acc, 4),
        "ci": ci,
    })
    result["passed"] = all(result["checks"].values())
    result["direction"] = 1 if oos_acc > 0.5 else (-1 if oos_acc < 0.5 else 0)
    return result


def _candidate_delta(scorecard: Dict[str, Any]) -> float:
    oos_acc = scorecard.get("oos_accuracy", 0.5)
    raw = (oos_acc - 0.5) * 2 * MAX_WEIGHT_DELTA   # scale [0,0.5] excess -> [0, MAX_WEIGHT_DELTA]
    return round(max(-MAX_WEIGHT_DELTA, min(MAX_WEIGHT_DELTA, raw)), 4)


def _reconfirm_scorecard(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Lighter-weight reconfirmation check for the SHADOW->ACTIVE transition:
    uses only the NEW held-out evidence accumulated since shadow started
    (typically MIN_SHADOW_NEW_EVIDENCE, far smaller than
    MIN_SAMPLE_FOR_VALIDATION), so this deliberately does not require the
    full initial-validation sample-size/bootstrap-CI bar -- only that
    fresh, never-before-seen evidence still points the same direction
    with at least the same minimum effect magnitude.
    """
    n = len(records)
    if n == 0:
        return {"sample_size": 0, "passed": False, "direction": 0}
    acc = sum(bool(r["correct"]) for r in records) / n
    direction = 1 if acc > 0.5 else (-1 if acc < 0.5 else 0)
    passed = abs(acc - 0.5) >= MIN_EFFECT_MAGNITUDE
    return {"sample_size": n, "accuracy": round(acc, 4), "passed": passed, "direction": direction}


# ─────────────────────────────────────────────────────────────────────────────
# Public read-side API -- consumed by decision_ai/decision_engine.py
# ─────────────────────────────────────────────────────────────────────────────

_cache_mtime: Optional[float] = None
_cache_values: Optional[Dict[str, float]] = None


def get_effective_weights() -> Dict[str, float]:
    """
    Return the live debater weights. Sources validated (ACTIVE) overrides
    when present; falls back to the exact original hardcoded defaults on
    any error, missing file, or a debater simply not yet overridden.
    Never raises. mtime-gated cache -- safe to call on every decide().
    """
    global _cache_mtime, _cache_values
    try:
        if not os.path.exists(_OVERRIDES_PATH):
            return dict(DEFAULT_WEIGHTS)
        mtime = os.path.getmtime(_OVERRIDES_PATH)
        if _cache_values is not None and _cache_mtime == mtime:
            return _cache_values

        raw = _read_json(_OVERRIDES_PATH, {})
        result = dict(DEFAULT_WEIGHTS)
        for name, entry in raw.items():
            if name not in DEFAULT_WEIGHTS or not isinstance(entry, dict):
                continue
            delta = entry.get("delta")
            if not isinstance(delta, (int, float)):
                continue
            delta = max(-MAX_WEIGHT_DELTA, min(MAX_WEIGHT_DELTA, float(delta)))
            result[name] = round(DEFAULT_WEIGHTS[name] + delta, 4)

        _cache_mtime, _cache_values = mtime, result
        return result
    except Exception as exc:
        log.debug("[DebateWRE] get_effective_weights fallback to defaults: %s", exc)
        return dict(DEFAULT_WEIGHTS)


def get_refinement_status() -> Dict[str, Any]:
    """Read-only accessor (Sandy-style): per-debater lifecycle status."""
    state = _read_json(_STATE_PATH, {})
    overrides = _read_json(_OVERRIDES_PATH, {})
    per_agent = {}
    for name in DEFAULT_WEIGHTS:
        s = state.get(name, {"status": STATUS_WAITING})
        per_agent[name] = {
            "status": s.get("status", STATUS_WAITING),
            "sample_size": s.get("last_sample_size", 0),
            "active_delta": overrides.get(name, {}).get("delta", 0.0),
        }
    return {"per_agent": per_agent}


def get_ledger_history(n: int = 20) -> List[Dict[str, Any]]:
    """Read-only accessor: last n refinement events, oldest-first."""
    return _read_ledger(n)


# ─────────────────────────────────────────────────────────────────────────────
# GOVERNANCE -- fully automated daily/periodic check
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_refinement_check() -> Dict[str, Any]:
    """
    Self-scheduled, fully automated. For each debater, evaluates the
    lifecycle transition (if any) justified by newly accumulated
    evidence. Never raises. Returns a per-agent summary dict.
    """
    try:
        return _run_impl()
    except Exception as exc:
        log.debug("[DebateWRE] refinement check error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl() -> Dict[str, Any]:
    from debate_system.debate_vote_tracker import get_resolved_records_for_agent

    state = _read_json(_STATE_PATH, {})
    overrides = _read_json(_OVERRIDES_PATH, {})
    results: Dict[str, Any] = {}

    for name in DEFAULT_WEIGHTS:
        agent_state = state.get(name, {"status": STATUS_WAITING})
        records = get_resolved_records_for_agent(name)
        outcome = _evaluate_agent(name, agent_state, records, overrides)
        state[name] = outcome["state"]
        if outcome.get("overrides_changed"):
            if outcome["state"]["status"] == STATUS_ACTIVE:
                overrides[name] = {"delta": outcome["state"]["active_delta"]}
            elif name in overrides and outcome["state"]["status"] in (STATUS_ROLLED_BACK, STATUS_REJECTED, STATUS_WAITING):
                overrides.pop(name, None)
        results[name] = {"status": outcome["state"]["status"], "detail": outcome.get("detail", "")}

    _write_json(_STATE_PATH, state)
    _write_json(_OVERRIDES_PATH, overrides)
    return {"status": "OK", "per_agent": results}


def _evaluate_agent(name: str, agent_state: Dict[str, Any], records: List[Dict[str, Any]],
                     overrides: Dict[str, Any]) -> Dict[str, Any]:
    status = agent_state.get("status", STATUS_WAITING)
    n = len(records)

    if status == STATUS_ACTIVE:
        activated_at_n = agent_state.get("activated_at_sample_size", 0)
        post_active = records[activated_at_n:]
        if len(post_active) < MIN_POST_ACTIVE_FOR_ROLLBACK_CHECK:
            return {"state": {**agent_state, "last_sample_size": n}, "detail": "monitoring"}
        post_acc = sum(bool(r["correct"]) for r in post_active) / len(post_active)
        expected_direction = agent_state.get("direction", 1)
        degraded = (
            (expected_direction > 0 and post_acc < 0.5 + MIN_EFFECT_MAGNITUDE - ROLLBACK_DEGRADATION)
            or (expected_direction < 0 and post_acc > 0.5 - MIN_EFFECT_MAGNITUDE + ROLLBACK_DEGRADATION)
        )
        if degraded:
            _append_ledger("ROLLED_BACK", name, f"post-activation accuracy degraded to {post_acc:.3f}",
                            post_accuracy=post_acc)
            return {"state": {"status": STATUS_ROLLED_BACK, "last_sample_size": n},
                    "overrides_changed": True, "detail": f"rolled back, post_acc={post_acc:.3f}"}
        return {"state": {**agent_state, "last_sample_size": n}, "detail": "active, healthy"}

    if status == STATUS_SHADOW:
        shadow_started_n = agent_state.get("shadow_started_at_sample_size", 0)
        new_evidence = records[shadow_started_n:]
        if len(new_evidence) < MIN_SHADOW_NEW_EVIDENCE:
            return {"state": {**agent_state, "last_sample_size": n},
                    "detail": f"shadow, {len(new_evidence)}/{MIN_SHADOW_NEW_EVIDENCE} new evidence"}
        # Reconfirmation on the NEW held-out evidence only -- deliberately a
        # lighter directional check, not the full initial-validation scorecard
        # (which requires n>=MIN_SAMPLE_FOR_VALIDATION and would never pass on
        # just MIN_SHADOW_NEW_EVIDENCE samples). The bar here: does fresh,
        # never-before-seen evidence still point the same direction, with at
        # least the same minimum effect magnitude required initially.
        confirm_card = _reconfirm_scorecard(new_evidence)
        expected_direction = agent_state.get("direction", 1)
        if confirm_card["passed"] and confirm_card["direction"] == expected_direction:
            delta = agent_state.get("candidate_delta", 0.0)
            _append_ledger("PROMOTED", name, "shadow reconfirmed on new evidence",
                            candidate_delta=delta, confirm_scorecard=confirm_card)
            return {
                "state": {
                    "status": STATUS_ACTIVE, "active_delta": delta,
                    "direction": expected_direction,
                    "activated_at_sample_size": n, "last_sample_size": n,
                },
                "overrides_changed": True, "detail": f"promoted, delta={delta}",
            }
        _append_ledger("REJECTED", name, "shadow failed to reconfirm", confirm_scorecard=confirm_card)
        return {"state": {"status": STATUS_REJECTED, "last_sample_size": n},
                "overrides_changed": True, "detail": "shadow rejected"}

    # STATUS_WAITING or STATUS_REJECTED -- check cooldown, then evaluate fresh evidence
    last_checked = agent_state.get("last_checked_at")
    if last_checked:
        try:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_checked)).days
            if elapsed < COOLDOWN_DAYS:
                return {"state": {**agent_state, "last_sample_size": n}, "detail": "cooldown"}
        except ValueError:
            pass

    card = _scorecard(records)
    new_state = {**agent_state, "last_sample_size": n,
                 "last_checked_at": datetime.now(timezone.utc).isoformat()}
    if not card["passed"]:
        new_state["status"] = STATUS_WAITING
        return {"state": new_state, "detail": f"waiting, n={n}"}

    delta = _candidate_delta(card)
    _append_ledger("SHADOW_STARTED", name, "candidate validated on train/OOS split",
                    candidate_delta=delta, scorecard=card)
    new_state.update({
        "status": STATUS_SHADOW, "candidate_delta": delta,
        "direction": card["direction"], "shadow_started_at_sample_size": n,
    })
    return {"state": new_state, "detail": f"shadow started, delta={delta}"}
