"""
trade_monitoring/strategy_profile_refinement_engine.py
==========================================================
Self-learning module #25: profile-aware governance auto-apply.

trade_monitoring/strategy_health_monitor.py already computes an
evidence-based profile suggestion via _compute_profile_suggestion()
(gated at PROFILE_SUGGEST_MIN_TRADES=30, returns confidence HIGH/MEDIUM/
LOW) -- but by explicit original design it NEVER auto-applies: "Manual
assignment always overrides auto-suggestion; requires explicit
confirmation to apply" (strategy_governance_roadmap.md).

This module builds the missing GOVERNANCE layer that was deliberately
left out until an evidence-gated, shadow-then-live mechanism existed --
mirroring the exact lifecycle already proven in this repo
(knowledge_authority/kda_constant_refinement_engine.py, strategy_lab/
regime_map_refinement_engine.py). It reuses _compute_profile_suggestion()
completely unchanged (via the new, additive public wrapper
StrategyHealthMonitor.get_profile_suggestion()) -- zero changes to its
heuristic logic.

WHY A HIGHER BAR THAN THE SUGGESTION'S OWN 30-TRADE FLOOR
------------------------------------------------------------
strategy_governance_roadmap.md's own human-authored Phase 3 design states
a stricter trigger for ACTING on profile classification: "Trigger: >= 50
official trades per strategy (classification too noisy below this)".
MIN_SAMPLE_FOR_AUTO_APPLY=50 here honors that stricter, stated floor --
below 50 trades, suggestions remain advisory-only exactly as before
(unchanged [ProfileSuggestion] log line), never auto-applied.

WHY THIS IS LOW-RISK TO AUTOMATE (unlike a P&L-consequential gate)
---------------------------------------------------------------------
strategy_profile_type is explicitly metadata-only today -- "no
governance logic reads this field yet" (strategy_health_monitor.py's own
docstring). Auto-applying it does not, by itself, change any trade
decision, disable threshold, or capital allocation. This makes automatic
application of a HIGH-confidence, twice-reconfirmed suggestion safe and
reversible (a future consumer of this field can always be safely built
in a separate, dedicated change).

LIFECYCLE (fully automated, no human step at any transition)
--------------------------------------------------------------
  WAITING_FOR_EVIDENCE -- fewer than MIN_SAMPLE_FOR_AUTO_APPLY trades,
                          no suggestion, or suggestion confidence < HIGH.
  SHADOW_ACTIVE         -- a HIGH-confidence suggestion differing from the
                          currently-stamped profile is being reconfirmed
                          against NEW trades only -- zero effect on the
                          live profile field while in this state.
  ACTIVE                -- shadow-confirmed; strategy_profile_type has
                          been auto-applied via
                          StrategyHealthMonitor.apply_profile_override().
  REJECTED              -- shadow period failed to reconfirm the same
                          suggestion.
  (ACTIVE strategies remain monitored -- if a later HIGH-confidence
  suggestion reconfirms a DIFFERENT profile after enough new evidence,
  the engine re-applies, self-correcting toward the best current read.)

SAFETY CONTRACT
-----------------
  Zero imports of execution_engine, order_manager, broker APIs, or
  risk_control. _compute_profile_suggestion()'s heuristic logic is never
  modified. Only ever writes strategy_profile_type (metadata) via the
  existing StrategyHealthMonitor's own public setter -- never touches
  disabled_reason, trades, total_r, or any other governance field.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

ACTOR = "SHM-PROFILE-RE-001"

_ROOT          = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR     = os.path.join(_ROOT, "data", "trade_monitoring", "profile_refinement")
_STATE_PATH    = os.path.join(_STORE_DIR, "state.json")
_LEDGER_PATH   = os.path.join(_STORE_DIR, "ledger.jsonl")

MIN_SAMPLE_FOR_AUTO_APPLY = 50
MIN_SHADOW_NEW_TRADES     = 15
COOLDOWN_DAYS             = 30

STATUS_WAITING     = "WAITING_FOR_EVIDENCE"
STATUS_SHADOW      = "SHADOW_ACTIVE"
STATUS_ACTIVE      = "ACTIVE"
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


def _append_ledger(event_type: str, strategy: str, reason: str, **extra: Any) -> None:
    try:
        record = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": ACTOR,
            "event_type": event_type,
            "strategy": strategy,
            "reason": reason,
            **extra,
        }
        os.makedirs(_STORE_DIR, exist_ok=True)
        with open(_LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        log.debug("[SHMProfileRE] ledger write failed: %s", exc)


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


def get_refinement_status() -> Dict[str, Any]:
    """Read-only accessor (Sandy-style)."""
    return {"per_strategy": _read_json(_STATE_PATH, {})}


def get_ledger_history(n: int = 20) -> List[Dict[str, Any]]:
    return _read_ledger(n)


def run_daily_refinement_check(strategy_health_monitor=None) -> Dict[str, Any]:
    """
    Self-scheduled, fully automated. Iterates every strategy currently
    tracked by StrategyHealthMonitor and evaluates whether a HIGH
    -confidence profile suggestion should be auto-applied. Never raises.
    """
    try:
        return _run_impl(strategy_health_monitor)
    except Exception as exc:
        log.debug("[SHMProfileRE] refinement check error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl(shm=None) -> Dict[str, Any]:
    if shm is None:
        from trade_monitoring.strategy_health_monitor import StrategyHealthMonitor
        shm = StrategyHealthMonitor()

    state = _read_json(_STATE_PATH, {})
    results: Dict[str, Any] = {}

    for name in shm.get_tracked_strategy_names():
        trades = shm.get_trades_count(name)
        current_profile = shm.get_profile_type(name)
        strat_state = state.get(name, {"status": STATUS_WAITING})
        outcome = _evaluate_strategy(shm, name, trades, current_profile, strat_state)
        state[name] = outcome["state"]
        results[name] = {"status": outcome["state"]["status"], "detail": outcome.get("detail", "")}

    _write_json(_STATE_PATH, state)
    return {"status": "OK", "per_strategy": results}


def _evaluate_strategy(shm, name: str, trades: int, current_profile: str,
                        strat_state: Dict[str, Any]) -> Dict[str, Any]:
    status = strat_state.get("status", STATUS_WAITING)

    suggestion, confidence, reasoning = shm.get_profile_suggestion(name)

    if status == STATUS_SHADOW:
        shadow_started_at = strat_state.get("shadow_started_at_trades", 0)
        new_trades = trades - shadow_started_at
        if new_trades < MIN_SHADOW_NEW_TRADES:
            return {"state": {**strat_state, "last_trades": trades},
                    "detail": f"shadow, {new_trades}/{MIN_SHADOW_NEW_TRADES} new trades"}
        candidate = strat_state.get("candidate_profile")
        if suggestion == candidate and confidence == "HIGH":
            shm.apply_profile_override(name, candidate, f"reconfirmed: {reasoning}")
            _append_ledger("PROMOTED", name, "shadow reconfirmed on new trades",
                            candidate_profile=candidate, reasoning=reasoning)
            return {"state": {"status": STATUS_ACTIVE, "applied_profile": candidate,
                               "last_trades": trades},
                     "detail": f"applied profile={candidate}"}
        _append_ledger("REJECTED", name, "shadow failed to reconfirm",
                        candidate_profile=candidate, new_suggestion=suggestion, new_confidence=confidence)
        return {"state": {"status": STATUS_REJECTED, "last_trades": trades},
                 "detail": "shadow rejected"}

    if status == STATUS_ACTIVE:
        applied = strat_state.get("applied_profile")
        # Self-correcting: if a NEW, different HIGH-confidence suggestion
        # has now reconfirmed enough new evidence, start a fresh shadow
        # for it (never write directly -- go through the same shadow gate).
        if suggestion and confidence == "HIGH" and suggestion != applied:
            last_checked = strat_state.get("last_checked_at")
            if last_checked:
                try:
                    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_checked)).days
                    if elapsed < COOLDOWN_DAYS:
                        return {"state": {**strat_state, "last_trades": trades}, "detail": "cooldown"}
                except ValueError:
                    pass
            _append_ledger("SHADOW_STARTED", name, "new profile candidate diverges from applied",
                            candidate_profile=suggestion, reasoning=reasoning)
            return {
                "state": {
                    "status": STATUS_SHADOW, "candidate_profile": suggestion,
                    "shadow_started_at_trades": trades, "last_trades": trades,
                    "last_checked_at": datetime.now(timezone.utc).isoformat(),
                },
                "detail": f"re-shadowing candidate={suggestion}",
            }
        return {"state": {**strat_state, "last_trades": trades}, "detail": f"active, profile={applied}"}

    # STATUS_WAITING or STATUS_REJECTED
    last_checked = strat_state.get("last_checked_at")
    if last_checked:
        try:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_checked)).days
            if elapsed < COOLDOWN_DAYS:
                return {"state": {**strat_state, "last_trades": trades}, "detail": "cooldown"}
        except ValueError:
            pass

    new_state = {**strat_state, "last_trades": trades, "last_checked_at": datetime.now(timezone.utc).isoformat()}
    if trades < MIN_SAMPLE_FOR_AUTO_APPLY or suggestion is None or confidence != "HIGH" or suggestion == current_profile:
        new_state["status"] = STATUS_WAITING
        return {"state": new_state, "detail": f"waiting, trades={trades}"}

    _append_ledger("SHADOW_STARTED", name, "HIGH-confidence candidate differs from current profile",
                    candidate_profile=suggestion, current_profile=current_profile, reasoning=reasoning)
    new_state.update({"status": STATUS_SHADOW, "candidate_profile": suggestion,
                       "shadow_started_at_trades": trades})
    return {"state": new_state, "detail": f"shadow started, candidate={suggestion}"}
