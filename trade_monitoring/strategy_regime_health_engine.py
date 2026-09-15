"""
trade_monitoring/strategy_regime_health_engine.py
=====================================================
Self-learning module #24: StrategyHealthMonitor regime-aware disabling.

strategy_governance_roadmap.md's own human-authored Phase 2 design
("Trigger: After 30-50 clean live trades across multiple regimes... Min:
~10 trades per regime before regime-level disable fires") is implemented
here as a fully automated, evidence-gated mechanism, following the exact
shadow-then-live lifecycle already proven in this repo
(knowledge_authority/kda_constant_refinement_engine.py,
strategy_lab/regime_map_refinement_engine.py, debate_system/
debate_weight_refinement_engine.py), reused as a TEMPLATE only (zero
imports from any of those modules, zero shared storage).

ACQUISITION reuses meta_learning/regime_map_evidence_log.py's existing,
already-live per-(regime,strategy) trade evidence (built for Priority 5 --
additive alongside, never touched here) instead of duplicating tracking.

SCOPE
-----
A strategy can be disabled IN A SPECIFIC REGIME ONLY (not globally --
StrategyHealthMonitor's existing global EARLY_ABORT/win-rate/drawdown/
Sharpe gates are completely untouched) once real evidence shows it losing
money more often than not specifically in that regime. This is strictly
ADDITIVE to StrategyGeneratorAI's existing exclusion set
(strategy_lab/strategy_generator_ai.py's assign_strategy() already takes
excluded_strategies=shm_disabled|perf_disabled -- this module contributes
one more, regime-scoped set, unioned in at the orchestrator call site).

WHY A HIGHER BAR THAN THE ROADMAP'S OWN STATED FLOOR
-----------------------------------------------------
The roadmap's "~10 trades per regime" was written for a human-reviewed
decision. This is fully automated (zero human step), so it uses the
roadmap's own upper bound (MIN_SAMPLE_FOR_VALIDATION=30) as a floor,
mirroring the identical reasoning already used in
strategy_lab/regime_map_refinement_engine.py.

LIFECYCLE (fully automated, no human step at any transition)
--------------------------------------------------------------
  WAITING_FOR_EVIDENCE -> SHADOW_ACTIVE -> ACTIVE/REJECTED
  ACTIVE -> ROLLED_BACK (auto-revert if the strategy's win-rate in that
  regime recovers)

SAFETY CONTRACT
----------------
  Zero imports of execution_engine, order_manager, broker APIs, or
  risk_control. trade_monitoring/strategy_health_monitor.py's own global
  disable logic (EARLY_ABORT, MIN_WIN_RATE, MAX_DRAWDOWN, MIN_SHARPE) is
  never imported or modified -- this module only ever ADDS an extra,
  regime-scoped exclusion set at the orchestrator call site.
"""
from __future__ import annotations

import json
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from utils import get_logger

log = get_logger(__name__)

ACTOR = "SHM-REGIME-RE-001"

_ROOT           = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR      = os.path.join(_ROOT, "data", "trade_monitoring", "regime_health_refinement")
_STATE_PATH     = os.path.join(_STORE_DIR, "state.json")
_DISABLES_PATH  = os.path.join(_STORE_DIR, "active_disables.json")
_LEDGER_PATH    = os.path.join(_STORE_DIR, "ledger.jsonl")

MIN_SAMPLE_FOR_VALIDATION = 30
MIN_SHADOW_NEW_EVIDENCE   = 12
MIN_EFFECT_MAGNITUDE      = 0.05
BOOTSTRAP_ITERS           = 1000
COOLDOWN_DAYS             = 30
ROLLBACK_RECOVERY         = 0.05
MIN_POST_DISABLE_FOR_ROLLBACK_CHECK = 12

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
        log.debug("[SHMRegimeRE] ledger write failed: %s", exc)


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


def _bootstrap_ci_winrate(labels: List[bool], iters: int = BOOTSTRAP_ITERS, seed: int = 42) -> Optional[tuple]:
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

    result.update({"train_win_rate": round(train_wr, 4), "oos_win_rate": round(oos_wr, 4), "ci": ci})
    result["passed"] = all(result["checks"].values())
    result["direction"] = 1 if oos_wr > 0.5 else (-1 if oos_wr < 0.5 else 0)
    return result


def _reconfirm_scorecard(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(records)
    if n == 0:
        return {"sample_size": 0, "passed": False, "direction": 0}
    wr = sum(bool(r["won"]) for r in records) / n
    direction = 1 if wr > 0.5 else (-1 if wr < 0.5 else 0)
    passed = abs(wr - 0.5) >= MIN_EFFECT_MAGNITUDE
    return {"sample_size": n, "win_rate": round(wr, 4), "passed": passed, "direction": direction}


# ─────────────────────────────────────────────────────────────────────────────
# Public read-side API -- consumed by orchestrator/master_orchestrator.py
# ─────────────────────────────────────────────────────────────────────────────

def get_regime_disabled_strategies(regime: str) -> Set[str]:
    """
    Read-only accessor: strategy names currently ACTIVE-disabled in the
    given regime. Falls back to an empty set on any error -- never raises,
    zero live effect until real per-(regime,strategy) evidence validates
    a regime-scoped disable.
    """
    try:
        demotions = _read_json(_DISABLES_PATH, {})
        out = set()
        for key in demotions:
            if "::" not in key:
                continue
            r, s = key.split("::", 1)
            if r == regime:
                out.add(s)
        return out
    except Exception as exc:
        log.debug("[SHMRegimeRE] get_regime_disabled_strategies fallback to empty: %s", exc)
        return set()


def get_refinement_status() -> Dict[str, Any]:
    state = _read_json(_STATE_PATH, {})
    disables = _read_json(_DISABLES_PATH, {})
    per_pair = {}
    for key, s in state.items():
        per_pair[key] = {
            "status": s.get("status", STATUS_WAITING),
            "sample_size": s.get("last_sample_size", 0),
            "disabled": key in disables,
        }
    return {"per_pair": per_pair}


def get_ledger_history(n: int = 20) -> List[Dict[str, Any]]:
    return _read_ledger(n)


# ─────────────────────────────────────────────────────────────────────────────
# GOVERNANCE -- fully automated daily/periodic check
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_refinement_check() -> Dict[str, Any]:
    """Self-scheduled, fully automated. Never raises."""
    try:
        return _run_impl()
    except Exception as exc:
        log.debug("[SHMRegimeRE] refinement check error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl() -> Dict[str, Any]:
    from meta_learning.regime_map_evidence_log import get_records, get_pairs_with_evidence

    state = _read_json(_STATE_PATH, {})
    disables = _read_json(_DISABLES_PATH, {})
    results: Dict[str, Any] = {}

    for regime, strategy in get_pairs_with_evidence():
        key = _pair_key(regime, strategy)
        pair_state = state.get(key, {"status": STATUS_WAITING})
        records = get_records(regime=regime, strategy=strategy)
        outcome = _evaluate_pair(regime, strategy, pair_state, records)
        state[key] = outcome["state"]
        if outcome.get("disables_changed"):
            if outcome["state"]["status"] == STATUS_ACTIVE:
                disables[key] = {"disabled_at": datetime.now(timezone.utc).isoformat()}
            elif key in disables and outcome["state"]["status"] in (STATUS_ROLLED_BACK, STATUS_REJECTED, STATUS_WAITING):
                disables.pop(key, None)
        results[key] = {"status": outcome["state"]["status"], "detail": outcome.get("detail", "")}

    _write_json(_STATE_PATH, state)
    _write_json(_DISABLES_PATH, disables)
    return {"status": "OK", "per_pair": results}


def _evaluate_pair(regime: str, strategy: str, pair_state: Dict[str, Any],
                    records: List[Dict[str, Any]]) -> Dict[str, Any]:
    status = pair_state.get("status", STATUS_WAITING)
    n = len(records)

    if status == STATUS_ACTIVE:
        disabled_at_n = pair_state.get("disabled_at_sample_size", 0)
        post = records[disabled_at_n:]
        if len(post) < MIN_POST_DISABLE_FOR_ROLLBACK_CHECK:
            return {"state": {**pair_state, "last_sample_size": n}, "detail": "monitoring"}
        post_wr = sum(bool(r["won"]) for r in post) / len(post)
        recovered = post_wr > 0.5 - MIN_EFFECT_MAGNITUDE + ROLLBACK_RECOVERY
        if recovered:
            _append_ledger("ROLLED_BACK", regime, strategy,
                            f"post-disable win-rate recovered to {post_wr:.3f}", post_win_rate=post_wr)
            return {"state": {"status": STATUS_ROLLED_BACK, "last_sample_size": n},
                    "disables_changed": True, "detail": f"rolled back, post_wr={post_wr:.3f}"}
        return {"state": {**pair_state, "last_sample_size": n}, "detail": "active, healthy disable"}

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
                "state": {"status": STATUS_ACTIVE, "direction": -1,
                          "disabled_at_sample_size": n, "last_sample_size": n},
                "disables_changed": True, "detail": "disable confirmed",
            }
        _append_ledger("REJECTED", regime, strategy, "shadow failed to reconfirm", confirm_scorecard=confirm_card)
        return {"state": {"status": STATUS_REJECTED, "last_sample_size": n},
                "disables_changed": True, "detail": "shadow rejected"}

    last_checked = pair_state.get("last_checked_at")
    if last_checked:
        try:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_checked)).days
            if elapsed < COOLDOWN_DAYS:
                return {"state": {**pair_state, "last_sample_size": n}, "detail": "cooldown"}
        except ValueError:
            pass

    card = _scorecard(records)
    new_state = {**pair_state, "last_sample_size": n, "last_checked_at": datetime.now(timezone.utc).isoformat()}
    if not card["passed"] or card["direction"] != -1:
        new_state["status"] = STATUS_WAITING
        return {"state": new_state, "detail": f"waiting or no negative signal, n={n}"}

    _append_ledger("SHADOW_STARTED", regime, strategy, "disable candidate validated on train/OOS split", scorecard=card)
    new_state.update({"status": STATUS_SHADOW, "shadow_started_at_sample_size": n})
    return {"state": new_state, "detail": "shadow started (candidate regime-disable)"}
