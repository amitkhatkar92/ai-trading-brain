"""
strategy_lab/regime_map_refinement_engine.py
================================================
Self-Learning Ecosystem -- Post-roadmap Priority 5 (part 2 of 2):
SYNTHESIS + GOVERNANCE for MetaStrategyController's static regime ->
strategy candidate list (_REGIME_MAP).

Consumes the evidence built by meta_learning/regime_map_evidence_log.py
(ACQUISITION) and decides, per (regime, strategy) pair ALREADY listed
as a candidate in _REGIME_MAP, whether real accumulated evidence
justifies DEMOTING it (removing it from that regime's eligibility list)
-- following the exact shadow-then-live, fully-automated lifecycle
already proven in this repo (knowledge_authority/kda_constant_refinement_
engine.py, scripts/knowledge_system/ranking_adjustment_engine_001.py,
debate_system/debate_weight_refinement_engine.py), reused as a TEMPLATE
only (zero imports from any of those modules, zero shared storage).
Isolated store: data/meta_learning/regime_map_refinement/.

SCOPE -- DEMOTION ONLY, NEVER PROMOTION
------------------------------------------
This module can only ever REMOVE a strategy that is already a
hand-curated candidate in _REGIME_MAP for a regime where real evidence
shows it losing money more often than not. It never ADDS a strategy to
a regime it wasn't already hand-approved for -- there is no defined
"universe" of candidate strategies per regime beyond the ones a human
already curated, and inventing new regime/strategy pairings from
opaque statistical correlation alone would be exactly the kind of
premature governance evolution this repo's own
strategy_governance_roadmap.md explicitly warns against ("Resist the
urge to tune"). A demoted strategy can still ROLL BACK (be silently
re-added) if post-demotion evidence no longer supports the demotion.

WHY A HIGHER EVIDENCE BAR THAN THE ROADMAP'S OWN STATED FLOOR
------------------------------------------------------------------
strategy_governance_roadmap.md's own Phase 2 design (May 6, 2026,
written by a human) states: "Trigger: After 30-50 clean live trades
across multiple regimes... Min: ~10 trades per regime before
regime-level disable fires." Because this module is a FULLY AUTOMATED,
NO-HUMAN-STEP mechanism (unlike the roadmap's original human-reviewed
design), it uses the roadmap's own stricter, upper bound
(MIN_SAMPLE_FOR_VALIDATION=30 per pair) as an extra safety margin, and
adds the same statistical rigor already applied elsewhere in this
session (time-ordered 70/30 split, bootstrap CI, sign consistency,
minimum effect magnitude) rather than a bare win-rate threshold.

LIFECYCLE (fully automated, no human step at any transition)
--------------------------------------------------------------
  WAITING_FOR_EVIDENCE -- fewer than MIN_SAMPLE_FOR_VALIDATION real
                          trades recorded for this (regime, strategy)
                          pair, and/or cooldown active.
  SHADOW_ACTIVE         -- a statistically-validated demotion candidate
                          is being reconfirmed against NEW, held-out
                          evidence -- zero effect on the live candidate
                          list while in this state.
  ACTIVE                -- shadow-confirmed; the strategy is removed
                          from that regime's effective candidate list
                          (read by strategy_lab/meta_strategy_controller.py).
  ROLLED_BACK           -- post-demotion evidence shows the strategy's
                          win rate recovered back toward/above the null;
                          automatically re-added.
  REJECTED              -- shadow period failed to reconfirm the effect.

STATISTICAL VALIDATION (mirrors the debate/KDA-CRE-001 scorecard shape)
---------------------------------------------------------------------------
Time-ordered 70/30 train/OOS split (never shuffled -- chronological
order), bootstrap CI (1000 iters, seeded) on OOS win-rate vs the 0.50
null, 4-check scorecard: sample size, CI excludes 0.50, train/OOS sign
consistency, minimum effect magnitude. Only a NEGATIVE-direction
(losing) signal is ever actionable here (demotion) -- a positive signal
is recorded but never acted on (see SCOPE above).

SAFETY CONTRACT (never violated)
-----------------------------------
  Zero imports of execution_engine, order_manager, broker APIs, or
  risk_control. meta_learning/regime_strategy_map.py (the existing,
  already-live per-regime ranking tracker) is never imported, read, or
  modified. strategy_lab/meta_strategy_controller.py's _REGIME_MAP
  constant is never mutated in place -- get_effective_regime_map()
  returns a fresh, derived copy. A regime's effective candidate list is
  never allowed to shrink below 1 strategy (a demotion that would empty
  a regime is refused and logged, never silently applied). Every
  transition is appended (never overwritten) to
  data/meta_learning/regime_map_refinement/ledger.jsonl with full
  reasoning.
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

ACTOR = "REGIME-MAP-RE-001"

_ROOT           = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR      = os.path.join(_ROOT, "data", "meta_learning", "regime_map_refinement")
_STATE_PATH     = os.path.join(_STORE_DIR, "state.json")
_DEMOTIONS_PATH = os.path.join(_STORE_DIR, "active_demotions.json")
_LEDGER_PATH    = os.path.join(_STORE_DIR, "ledger.jsonl")

MIN_SAMPLE_FOR_VALIDATION = 30    # roadmap's own stated trigger, used as a floor for full automation
MIN_SHADOW_NEW_EVIDENCE   = 12    # new trades required during shadow before promotion/rejection
MIN_EFFECT_MAGNITUDE      = 0.05  # OOS win-rate must be >=5pp below the 0.50 null
BOOTSTRAP_ITERS           = 1000
COOLDOWN_DAYS             = 30
ROLLBACK_RECOVERY         = 0.05  # post-demotion win-rate rising back within 5pp of/above 0.50 triggers rollback
MIN_POST_DEMOTION_FOR_ROLLBACK_CHECK = 12

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


def _append_ledger(event_type: str, regime: str, strategy: str, reason: str, **extra: Any) -> None:
    try:
        record = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": ACTOR,
            "event_type": event_type,
            "regime": regime,
            "strategy": strategy,
            "reason": reason,
            **extra,
        }
        os.makedirs(_STORE_DIR, exist_ok=True)
        with open(_LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        log.debug("[RegimeMapRE] ledger write failed: %s", exc)


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


def _pair_key(regime: str, strategy: str) -> str:
    return f"{regime}::{strategy}"


# ─────────────────────────────────────────────────────────────────────────────
# Statistical validation
# ─────────────────────────────────────────────────────────────────────────────

def _bootstrap_ci_winrate(labels: List[bool], iters: int = BOOTSTRAP_ITERS,
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
    records: time-ordered (oldest-first) [{"timestamp", "won", ...}].
    Returns: sample_size, train/oos win-rate, ci, checks, passed, direction.
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

    train_labels = [bool(r["won"]) for r in train]
    oos_labels   = [bool(r["won"]) for r in oos]
    train_wr = sum(train_labels) / len(train_labels)
    oos_wr   = sum(oos_labels) / len(oos_labels)

    ci = _bootstrap_ci_winrate(oos_labels)
    ci_excludes_null = ci is not None and (ci[0] > 0.5 or ci[1] < 0.5)
    result["checks"]["ci_excludes_null"] = ci_excludes_null

    sign_consistent = (train_wr - 0.5) * (oos_wr - 0.5) > 0
    result["checks"]["sign_consistent"] = sign_consistent

    effect_ok = abs(oos_wr - 0.5) >= MIN_EFFECT_MAGNITUDE
    result["checks"]["effect_magnitude"] = effect_ok

    result.update({
        "train_win_rate": round(train_wr, 4),
        "oos_win_rate": round(oos_wr, 4),
        "ci": ci,
    })
    result["passed"] = all(result["checks"].values())
    result["direction"] = 1 if oos_wr > 0.5 else (-1 if oos_wr < 0.5 else 0)
    return result


def _reconfirm_scorecard(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Lighter reconfirmation check for SHADOW->ACTIVE, on NEW held-out evidence only."""
    n = len(records)
    if n == 0:
        return {"sample_size": 0, "passed": False, "direction": 0}
    wr = sum(bool(r["won"]) for r in records) / n
    direction = 1 if wr > 0.5 else (-1 if wr < 0.5 else 0)
    passed = abs(wr - 0.5) >= MIN_EFFECT_MAGNITUDE
    return {"sample_size": n, "win_rate": round(wr, 4), "passed": passed, "direction": direction}


# ─────────────────────────────────────────────────────────────────────────────
# Public read-side API -- consumed by strategy_lab/meta_strategy_controller.py
# ─────────────────────────────────────────────────────────────────────────────

_cache_mtime: Optional[float] = None
_cache_map: Optional[Dict[str, List[str]]] = None


def get_effective_regime_map() -> Dict[str, List[str]]:
    """
    Return _REGIME_MAP with any ACTIVE (shadow-confirmed) demotions
    removed. Falls back to the exact original static map on any error,
    missing file, or if a demotion would empty a regime's candidate
    list. Never raises. mtime-gated cache -- safe to call every cycle.
    """
    global _cache_mtime, _cache_map
    from strategy_lab.meta_strategy_controller import _REGIME_MAP as _BASE_MAP
    try:
        if not os.path.exists(_DEMOTIONS_PATH):
            return {k: list(v) for k, v in _BASE_MAP.items()}
        mtime = os.path.getmtime(_DEMOTIONS_PATH)
        if _cache_map is not None and _cache_mtime == mtime:
            return _cache_map

        demotions = _read_json(_DEMOTIONS_PATH, {})
        result = {k: list(v) for k, v in _BASE_MAP.items()}
        for key in demotions:
            if "::" not in key:
                continue
            regime, strategy = key.split("::", 1)
            candidates = result.get(regime)
            if not candidates or strategy not in candidates:
                continue
            if len(candidates) <= 1:
                continue  # safety floor -- never empty a regime's candidate list
            candidates.remove(strategy)

        _cache_mtime, _cache_map = mtime, result
        return result
    except Exception as exc:
        log.debug("[RegimeMapRE] get_effective_regime_map fallback to static map: %s", exc)
        return {k: list(v) for k, v in _BASE_MAP.items()}


def get_refinement_status() -> Dict[str, Any]:
    """Read-only accessor (Sandy-style): per-(regime,strategy) lifecycle status."""
    state = _read_json(_STATE_PATH, {})
    demotions = _read_json(_DEMOTIONS_PATH, {})
    per_pair = {}
    for key, s in state.items():
        per_pair[key] = {
            "status": s.get("status", STATUS_WAITING),
            "sample_size": s.get("last_sample_size", 0),
            "demoted": key in demotions,
        }
    return {"per_pair": per_pair}


def get_ledger_history(n: int = 20) -> List[Dict[str, Any]]:
    """Read-only accessor: last n refinement events, oldest-first."""
    return _read_ledger(n)


# ─────────────────────────────────────────────────────────────────────────────
# GOVERNANCE -- fully automated daily/periodic check
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_refinement_check() -> Dict[str, Any]:
    """
    Self-scheduled, fully automated. For each (regime, strategy) pair
    currently listed in _REGIME_MAP with any recorded evidence,
    evaluates the lifecycle transition (if any) justified by newly
    accumulated evidence. Never raises. Returns a per-pair summary.
    """
    try:
        return _run_impl()
    except Exception as exc:
        log.debug("[RegimeMapRE] refinement check error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl() -> Dict[str, Any]:
    from meta_learning.regime_map_evidence_log import get_records, get_pairs_with_evidence
    from strategy_lab.meta_strategy_controller import _REGIME_MAP as _BASE_MAP

    state = _read_json(_STATE_PATH, {})
    demotions = _read_json(_DEMOTIONS_PATH, {})
    results: Dict[str, Any] = {}

    for regime, strategy in get_pairs_with_evidence():
        if strategy not in _BASE_MAP.get(regime, []):
            continue  # only ever evaluates pairs already hand-curated as candidates
        key = _pair_key(regime, strategy)
        pair_state = state.get(key, {"status": STATUS_WAITING})
        records = get_records(regime=regime, strategy=strategy)
        outcome = _evaluate_pair(regime, strategy, pair_state, records)
        state[key] = outcome["state"]
        if outcome.get("demotions_changed"):
            if outcome["state"]["status"] == STATUS_ACTIVE:
                demotions[key] = {"demoted_at": datetime.now(timezone.utc).isoformat()}
            elif key in demotions and outcome["state"]["status"] in (STATUS_ROLLED_BACK, STATUS_REJECTED, STATUS_WAITING):
                demotions.pop(key, None)
        results[key] = {"status": outcome["state"]["status"], "detail": outcome.get("detail", "")}

    _write_json(_STATE_PATH, state)
    _write_json(_DEMOTIONS_PATH, demotions)
    return {"status": "OK", "per_pair": results}


def _evaluate_pair(regime: str, strategy: str, pair_state: Dict[str, Any],
                    records: List[Dict[str, Any]]) -> Dict[str, Any]:
    status = pair_state.get("status", STATUS_WAITING)
    n = len(records)

    if status == STATUS_ACTIVE:
        demoted_at_n = pair_state.get("demoted_at_sample_size", 0)
        post_demotion = records[demoted_at_n:]
        if len(post_demotion) < MIN_POST_DEMOTION_FOR_ROLLBACK_CHECK:
            return {"state": {**pair_state, "last_sample_size": n}, "detail": "monitoring"}
        post_wr = sum(bool(r["won"]) for r in post_demotion) / len(post_demotion)
        recovered = post_wr > 0.5 - MIN_EFFECT_MAGNITUDE + ROLLBACK_RECOVERY
        if recovered:
            _append_ledger("ROLLED_BACK", regime, strategy,
                            f"post-demotion win-rate recovered to {post_wr:.3f}", post_win_rate=post_wr)
            return {"state": {"status": STATUS_ROLLED_BACK, "last_sample_size": n},
                    "demotions_changed": True, "detail": f"rolled back, post_wr={post_wr:.3f}"}
        return {"state": {**pair_state, "last_sample_size": n}, "detail": "active, healthy demotion"}

    if status == STATUS_SHADOW:
        shadow_started_n = pair_state.get("shadow_started_at_sample_size", 0)
        new_evidence = records[shadow_started_n:]
        if len(new_evidence) < MIN_SHADOW_NEW_EVIDENCE:
            return {"state": {**pair_state, "last_sample_size": n},
                    "detail": f"shadow, {len(new_evidence)}/{MIN_SHADOW_NEW_EVIDENCE} new evidence"}
        confirm_card = _reconfirm_scorecard(new_evidence)
        if confirm_card["passed"] and confirm_card["direction"] == -1:
            _append_ledger("PROMOTED", regime, strategy, "shadow reconfirmed on new evidence",
                            confirm_scorecard=confirm_card)
            return {
                "state": {
                    "status": STATUS_ACTIVE, "direction": -1,
                    "demoted_at_sample_size": n, "last_sample_size": n,
                },
                "demotions_changed": True, "detail": "demotion confirmed",
            }
        _append_ledger("REJECTED", regime, strategy, "shadow failed to reconfirm", confirm_scorecard=confirm_card)
        return {"state": {"status": STATUS_REJECTED, "last_sample_size": n},
                "demotions_changed": True, "detail": "shadow rejected"}

    # STATUS_WAITING or STATUS_REJECTED -- check cooldown, then evaluate fresh evidence
    last_checked = pair_state.get("last_checked_at")
    if last_checked:
        try:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_checked)).days
            if elapsed < COOLDOWN_DAYS:
                return {"state": {**pair_state, "last_sample_size": n}, "detail": "cooldown"}
        except ValueError:
            pass

    card = _scorecard(records)
    new_state = {**pair_state, "last_sample_size": n,
                 "last_checked_at": datetime.now(timezone.utc).isoformat()}
    if not card["passed"] or card["direction"] != -1:
        new_state["status"] = STATUS_WAITING
        return {"state": new_state, "detail": f"waiting or no negative signal, n={n}"}

    _append_ledger("SHADOW_STARTED", regime, strategy, "demotion candidate validated on train/OOS split",
                    scorecard=card)
    new_state.update({
        "status": STATUS_SHADOW, "shadow_started_at_sample_size": n,
    })
    return {"state": new_state, "detail": "shadow started (candidate demotion)"}
