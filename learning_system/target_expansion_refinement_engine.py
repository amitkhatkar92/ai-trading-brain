"""
learning_system/target_expansion_refinement_engine.py
========================================================
Self-learning module #29 (SYNTHESIS + GOVERNANCE) -- Dynamic Target
Expansion auto-tuning.

Validates, purely from real closed-trade evidence recorded by
target_expansion_evidence_log.py, whether Dynamic Target Expansion (see
config.py's ADAPTIVE_TARGET_EXPANSION_* constants) is net positive --
i.e. whether letting a strongly-trending winner run past its original
fixed target more often beats the original target than not. If so, the
expansion multiplier is auto-tuned (bounded) toward being more
aggressive; if evidence says the opposite, it's auto-tuned to be more
conservative. Multiplier is NEVER disabled entirely by this engine --
only the magnitude is adjusted, matching the "structural eligibility
stays intact, only the tuning parameter is evidence-adjusted" convention
used by every other refinement engine this session.

LIFECYCLE (fully automated, no human step at any transition -- mirrors
learning_system/sizing_bounds_refinement_engine.py and
knowledge_authority/kda_constant_refinement_engine.py exactly):
  WAITING_FOR_EVIDENCE -> SHADOW_ACTIVE -> ACTIVE/REJECTED
  ACTIVE -> ROLLED_BACK (auto-revert if post-activation evidence no
  longer supports the multiplier)

SAFETY CONTRACT
-----------------
Zero imports of execution_engine, order_manager, broker APIs.
get_effective_expansion_multiplier() is a pure, read-only accessor
consumed by trade_monitoring/trade_monitor.py; falls back to the exact
config.py default (ADAPTIVE_TARGET_EXPANSION_MULTIPLIER) on any error,
missing file, or no active adjustment. Never imports or modifies
trade_monitor.py directly.
"""
from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

ACTOR = "TARGET-EXPANSION-RE-001"

_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR  = os.path.join(_ROOT, "data", "learning_system", "target_expansion_calibration")
_STATE_PATH = os.path.join(_STORE_DIR, "state.json")
_TUNING_PATH = os.path.join(_STORE_DIR, "active_tuning.json")
_LEDGER_PATH = os.path.join(_STORE_DIR, "ledger.jsonl")

try:
    import config as _cfg
    DEFAULT_MULTIPLIER = float(getattr(_cfg, "ADAPTIVE_TARGET_EXPANSION_MULTIPLIER", 5.0))
except Exception:
    DEFAULT_MULTIPLIER = 5.0

MIN_MULTIPLIER            = 3.0
MAX_MULTIPLIER            = 8.0
MULTIPLIER_STEP           = 1.0    # bounded per-adjustment step, evidence-widened/narrowed
MIN_SAMPLE_FOR_VALIDATION = 20     # expansion fires rarely (strong-trend gate) -- lower floor
                                    # than KDA-CRE-001's 50, higher than RHV-001's 10 (real
                                    # money, but a narrower/rarer signal than either of those)
MIN_SHADOW_NEW_EVIDENCE   = 10
MIN_EFFECT_MAGNITUDE      = 0.10   # win-rate must clear 0.5 by at least this much
BOOTSTRAP_ITERS           = 1000
COOLDOWN_DAYS             = 30
ROLLBACK_DEGRADATION_N    = 10

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
            "event_id":  datetime.now(timezone.utc).isoformat() + "-" + event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor":     ACTOR,
            "event_type": event_type,
            "reason":    reason,
            **extra,
        }
        os.makedirs(_STORE_DIR, exist_ok=True)
        with open(_LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        log.debug("[TargetExpansionRE] ledger write failed: %s", exc)


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
# Statistical validation -- single-population win-rate vs 0.5 null
# (mirrors knowledge_authority/kda_constant_refinement_engine.py's shape)
# ─────────────────────────────────────────────────────────────────────────────

def _bootstrap_ci_winrate(outcomes: List[bool], iters: int = BOOTSTRAP_ITERS,
                           seed: int = 42) -> Optional[Tuple[float, float]]:
    if not outcomes:
        return None
    rng = random.Random(seed)
    n = len(outcomes)
    rates = []
    for _ in range(iters):
        rates.append(sum(outcomes[rng.randrange(n)] for _ in range(n)) / n)
    rates.sort()
    lo = rates[int(0.025 * iters)]
    hi = rates[int(0.975 * iters) - 1]
    return (lo, hi)


def _scorecard(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """records: time-ordered (oldest-first) [{"outcome": "WIN"|"LOSS", ...}]."""
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

    def _win_rate(recs: List[Dict[str, Any]]) -> float:
        return sum(1 for r in recs if r.get("outcome") == "WIN") / len(recs)

    train_wr = _win_rate(train)
    oos_wr   = _win_rate(oos)

    oos_outcomes = [r.get("outcome") == "WIN" for r in oos]
    ci = _bootstrap_ci_winrate(oos_outcomes)
    ci_excludes_half = ci is not None and (ci[0] > 0.5 or ci[1] < 0.5)
    result["checks"]["ci_excludes_null"] = ci_excludes_half

    sign_consistent = (train_wr > 0.5) == (oos_wr > 0.5)
    result["checks"]["sign_consistent"] = sign_consistent

    effect_ok = abs(oos_wr - 0.5) >= MIN_EFFECT_MAGNITUDE
    result["checks"]["effect_magnitude"] = effect_ok

    result.update({"train_wr": round(train_wr, 4), "oos_wr": round(oos_wr, 4), "ci": ci})
    result["passed"] = all(result["checks"].values())
    result["direction"] = 1 if oos_wr > 0.5 else (-1 if oos_wr < 0.5 else 0)
    result["strong"] = oos_wr >= 0.65
    return result


def _reconfirm_scorecard(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {"sample_size": 0, "passed": False, "direction": 0}
    wr = sum(1 for r in records if r.get("outcome") == "WIN") / len(records)
    direction = 1 if wr > 0.5 else (-1 if wr < 0.5 else 0)
    passed = abs(wr - 0.5) >= MIN_EFFECT_MAGNITUDE
    return {"sample_size": len(records), "win_rate": round(wr, 4), "passed": passed, "direction": direction}


def _candidate_multiplier(direction: int, strong: bool) -> float:
    step = MULTIPLIER_STEP if strong else MULTIPLIER_STEP * 0.5
    if direction == 1:
        return min(MAX_MULTIPLIER, DEFAULT_MULTIPLIER + step)
    if direction == -1:
        return max(MIN_MULTIPLIER, DEFAULT_MULTIPLIER - step)
    return DEFAULT_MULTIPLIER


# ─────────────────────────────────────────────────────────────────────────────
# Public read-side API -- consumed by trade_monitoring/trade_monitor.py
# ─────────────────────────────────────────────────────────────────────────────

_cache_mtime: Optional[float] = None
_cache_multiplier: Optional[float] = None


def get_effective_expansion_multiplier() -> float:
    """
    Return the expansion multiplier to use. Applies a validated, bounded
    adjustment only when real evidence justifies it; falls back to the
    exact config.py default on any error, missing file, or no active
    adjustment. Never raises.
    """
    global _cache_mtime, _cache_multiplier
    try:
        if not os.path.exists(_TUNING_PATH):
            return DEFAULT_MULTIPLIER
        mtime = os.path.getmtime(_TUNING_PATH)
        if _cache_multiplier is not None and _cache_mtime == mtime:
            return _cache_multiplier
        raw = _read_json(_TUNING_PATH, {})
        mult = raw.get("active_multiplier")
        if not isinstance(mult, (int, float)):
            return DEFAULT_MULTIPLIER
        mult = max(MIN_MULTIPLIER, min(MAX_MULTIPLIER, float(mult)))
        _cache_mtime, _cache_multiplier = mtime, mult
        return mult
    except Exception as exc:
        log.debug("[TargetExpansionRE] get_effective_expansion_multiplier fallback: %s", exc)
        return DEFAULT_MULTIPLIER


def get_refinement_status() -> Dict[str, Any]:
    state = _read_json(_STATE_PATH, {"status": STATUS_WAITING})
    tuning = _read_json(_TUNING_PATH, {})
    return {
        "status":            state.get("status", STATUS_WAITING),
        "sample_size":       state.get("last_sample_size", 0),
        "active_multiplier": tuning.get("active_multiplier", DEFAULT_MULTIPLIER),
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
        log.debug("[TargetExpansionRE] refinement check error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl() -> Dict[str, Any]:
    from learning_system.target_expansion_evidence_log import get_records

    records = get_records()
    state   = _read_json(_STATE_PATH, {"status": STATUS_WAITING})
    tuning  = _read_json(_TUNING_PATH, {})

    outcome = _evaluate(state, records)
    _write_json(_STATE_PATH, outcome["state"])
    if outcome.get("tuning_changed"):
        if outcome["state"]["status"] == STATUS_ACTIVE:
            tuning["active_multiplier"] = outcome["state"]["active_multiplier"]
        elif outcome["state"]["status"] in (STATUS_ROLLED_BACK, STATUS_REJECTED, STATUS_WAITING):
            tuning.pop("active_multiplier", None)
        _write_json(_TUNING_PATH, tuning)

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
            _append_ledger("ROLLED_BACK", "post-activation evidence no longer supports the multiplier",
                            confirm_scorecard=confirm)
            return {"state": {"status": STATUS_ROLLED_BACK, "last_sample_size": n},
                    "tuning_changed": True, "detail": "rolled back"}
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
            mult = state.get("candidate_multiplier", DEFAULT_MULTIPLIER)
            _append_ledger("PROMOTED", "shadow reconfirmed on new evidence", multiplier=mult, confirm_scorecard=confirm)
            return {
                "state": {"status": STATUS_ACTIVE, "active_multiplier": mult, "direction": expected_direction,
                          "activated_at_sample_size": n, "last_sample_size": n},
                "tuning_changed": True, "detail": f"promoted, multiplier={mult}",
            }
        _append_ledger("REJECTED", "shadow failed to reconfirm", confirm_scorecard=confirm)
        return {"state": {"status": STATUS_REJECTED, "last_sample_size": n},
                "tuning_changed": True, "detail": "shadow rejected"}

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

    mult = _candidate_multiplier(card["direction"], card.get("strong", False))
    _append_ledger("SHADOW_STARTED", "candidate validated on train/OOS split", multiplier=mult, scorecard=card)
    new_state.update({"status": STATUS_SHADOW, "candidate_multiplier": mult,
                       "direction": card["direction"], "shadow_started_at_sample_size": n})
    return {"state": new_state, "detail": f"shadow started, multiplier={mult}"}
