"""
scripts/knowledge_system/controlled_live_candidates_001.py
===================================================================
Phase 8 — Controlled evidence eligibility with auditable requalification.

READ-ONLY, OBSERVATIONAL. Not imported by KDA, DecisionEngine,
StrategyLab, ExecutionEngine, OrderManager, mover_discovery_v3.py,
final_c2_selector.py, or any order-placement path. Writes only its own eligibility export, consumed
by Phase 9's existing bounded scanner-confidence evidence bridge.

WHAT THIS IS: the automatic extension of Phase 7's research lifecycle
(NOT_YET -> RESEARCH_CANDIDATE -> VALIDATED_TRACKING -> CHALLENGER_
ELIGIBLE -> SHADOW_TEST -> PASS) with two further states:

  CONTROLLED_LIVE_CANDIDATE  Eligible for Phase 9's bounded scanner
                             confidence evidence. Recomputed each run;
                             regression withdraws eligibility.
  LIVE                       Never returned; no order is placed here.

LIVE-ENTRY SAFETY BAR (pre-specified, applied ON TOP OF Phase 7's PASS
bar, not instead of it):
  - Phase 7 lifecycle_status == PASS (already means >= 3 consecutive
    shadow-win days — see fingerprint_discovery_001.py)
  - total shadow days tracked >= MIN_SHADOW_DAYS_FOR_LIVE_CANDIDATE (10,
    matching fingerprint_validation_001.MIN_DAYS_FOR_VALIDATED's
    established "minimum real evidence, not a mythical perfect N"
    convention)
  - cumulative challenger win-rate across distinct epoch shadow days (not
    just the most recent streak) >= MIN_LIVE_CANDIDATE_WIN_RATE (0.6) —
    a stricter, whole-history check so a lucky 3-day streak alone cannot
    qualify
  - After a FAIL or RETIRED event, start a new evidence epoch. Only
    distinct shadow trading dates strictly after that event count toward
    the unchanged 10-day/60% bar. The old failure remains in history.

The export is consumed by live_selection_eligibility_001, not directly by
KDA or execution. No risk gate or scanner boost limit is changed here.
Failed recovery epochs close after 30 evidence dates; a new epoch must
earn its own unchanged evidence bar, never reuse the old observations.

SCHEDULING: wired into master_orchestrator.py's _do_eod_learning()
(DTA-PHASE8-LIVE-CANDIDATE-001), AFTER Phase 6's shadow tracking block
(needs that day's freshly-written shadow history) and BEFORE the final
_write_eod_status("COMPLETED"). Wrapped in its own try/except: a failure
here is logged and never aborts EOD learning or any trading path.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
import hashlib
from pathlib import Path
from typing import Any, Dict, List

from config import is_nse_holiday
from scripts.knowledge_system.fingerprint_discovery_001 import (
    LIFECYCLE_PASS,
    compute_lifecycle_status,
)
from scripts.knowledge_system.fingerprint_tracker_001 import get_full_registry

ROOT = Path(__file__).resolve().parent.parent.parent
LIVE_CANDIDATE_PATH = ROOT / "data" / "controlled_live_candidates.json"
log = logging.getLogger(__name__)

LIFECYCLE_CONTROLLED_LIVE_CANDIDATE = "CONTROLLED_LIVE_CANDIDATE"
LIFECYCLE_LIVE = "LIVE"  # never returned by this module — see docstring

MIN_SHADOW_DAYS_FOR_LIVE_CANDIDATE = 10  # matches MIN_DAYS_FOR_VALIDATED convention
MIN_LIVE_CANDIDATE_WIN_RATE = 0.6


def _requalification_history(
    registry_history: List[Dict[str, Any]], shadow_history: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], date | None, str | None]:
    """Keep distinct, genuinely new evidence after the latest regression."""
    failures = []
    had_streak = False
    for entry in registry_history:
        streak = entry.get("consecutive_validated_pass", 0)
        if entry.get("status") == "REJECTED" or (had_streak and streak == 0):
            failures.append(entry)
        had_streak = streak >= 1
    cutoff = None
    if failures:
        try:
            cutoff = max(date.fromisoformat(str(e["checked_at"])[:10]) for e in failures)
        except (KeyError, TypeError, ValueError):
            return [], None, "historical regression has no verifiable evidence date"
    unique = {}
    for entry in shadow_history:
        try:
            trading_date = date.fromisoformat(entry["trade_date"])
        except (KeyError, TypeError, ValueError):
            continue
        if is_nse_holiday(trading_date):
            continue
        if cutoff is None or trading_date > cutoff:
            # First persisted observation wins; reruns cannot manufacture votes.
            unique.setdefault(trading_date, entry)
    dates = sorted(unique)
    if cutoff and dates:
        epoch = (len(dates) - 1) // 30
        dates = dates[epoch * 30:]
    return [unique[d] for d in dates], cutoff, None


def _ever_regressed(registry_history: List[Dict[str, Any]]) -> bool:
    """True if the fingerprint's Phase 5 registry history ever shows a
    REJECTED (hard FAIL) verdict, or a consecutive-validated-pass streak
    that was building (>=1) and then broke back to 0 (RETIRED)."""
    if any(e.get("status") == "REJECTED" for e in registry_history):
        return True
    had_streak = False
    for e in registry_history:
        streak = e.get("consecutive_validated_pass", 0)
        if had_streak and streak == 0:
            return True
        if streak >= 1:
            had_streak = True
    return False


def evaluate_live_candidacy(name: str, direction: str) -> Dict[str, Any]:
    """Pure evaluation — reads Phase 5/6/7's existing, untouched outputs
    and returns {name, direction, lifecycle_status, controlled_live_candidate,
    live_entry_reason}. Never writes anywhere."""
    from scripts.knowledge_system.champion_challenger_001 import load_registry_history
    from scripts.knowledge_system.shadow_challenger_tracker_001 import (
        _cumulative_summary,
        load_shadow_history,
    )

    base = compute_lifecycle_status(name, direction)
    if base["lifecycle_status"] != LIFECYCLE_PASS:
        return {
            "name": name, "direction": direction,
            "lifecycle_status": base["lifecycle_status"],
            "controlled_live_candidate": False,
            "live_entry_reason": f"base lifecycle status is {base['lifecycle_status']}, not PASS",
        }

    registry_history = load_registry_history(name, direction)
    shadow_history, cutoff, history_error = _requalification_history(
        registry_history, load_shadow_history(name, direction)
    )
    cumulative = _cumulative_summary(shadow_history)
    epoch_start = shadow_history[0]["trade_date"] if cutoff and shadow_history else "initial"
    epoch = f"{name}|{direction}|{cutoff}|{epoch_start}|requalification-v2"
    experiment = {
        "experiment_id": hashlib.sha256(epoch.encode()).hexdigest()[:16],
        "evidence_epoch_after": str(cutoff) if cutoff else None,
        "shadow_days": cumulative["n_days_tracked"],
        "challenger_day_win_rate": cumulative["challenger_win_rate"],
        "review_status": ("REJECTED_EPOCH" if cutoff and cumulative["n_days_tracked"] >= 30
                          and (cumulative["challenger_win_rate"] or 0) < MIN_LIVE_CANDIDATE_WIN_RATE
                          else "EVALUATING"),
        "next_review_after": (
            (date.fromisoformat(shadow_history[-1]["trade_date"]) + timedelta(days=1)).isoformat()
            if shadow_history else None
        ),
    }

    n_days = cumulative["n_days_tracked"]
    win_rate = cumulative["challenger_win_rate"] or 0.0

    meets_days = n_days >= MIN_SHADOW_DAYS_FOR_LIVE_CANDIDATE
    meets_rate = win_rate >= MIN_LIVE_CANDIDATE_WIN_RATE

    if meets_days and meets_rate and not history_error:
        return {
            "name": name, "direction": direction,
            "lifecycle_status": LIFECYCLE_CONTROLLED_LIVE_CANDIDATE,
            "controlled_live_candidate": True,
            **experiment,
            "review_status": "QUALIFIED",
            "live_entry_reason": (
                f"PASS + {n_days} shadow days (>= {MIN_SHADOW_DAYS_FOR_LIVE_CANDIDATE}) "
                f"+ {win_rate} cumulative win-rate (>= {MIN_LIVE_CANDIDATE_WIN_RATE}) "
                "+ fresh distinct evidence since the latest regression; "
                "eligible only for the existing bounded scanner evidence bridge"
            ),
        }

    reasons = []
    if not meets_days:
        reasons.append(f"only {n_days}/{MIN_SHADOW_DAYS_FOR_LIVE_CANDIDATE} shadow days tracked")
    if not meets_rate:
        reasons.append(f"cumulative win-rate {win_rate} < {MIN_LIVE_CANDIDATE_WIN_RATE}")
    if history_error:
        reasons.append(history_error)
    elif cutoff:
        reasons.append(f"FAIL or RETIRED retained; requalification uses only dates after {cutoff}")

    return {
        "name": name, "direction": direction,
        "lifecycle_status": LIFECYCLE_PASS,
        "controlled_live_candidate": False,
        **experiment,
        "live_entry_reason": "PASS but not yet a controlled live candidate: " + "; ".join(reasons),
    }


def _write_export(entries: List[Dict[str, Any]], path: Path = LIVE_CANDIDATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def load_export(path: Path = LIVE_CANDIDATE_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def run_live_candidate_check_silent(ledger_path=None) -> List[Dict[str, Any]]:
    """Main entry point, no stdout output — safe to embed in the EOD
    orchestrator pipeline. Evaluates every fingerprint in the full
    registry (static + Phase 7 discovered) and REBUILDS the export file
    from scratch each run with only the fingerprints CURRENTLY qualifying
    — a regression on any later check immediately removes an entry
    (rollback). There is no permanent-promotion guarantee at this tier (unlike Phase 7's
    research-candidate discovery log)."""
    results: List[Dict[str, Any]] = []
    qualifying: List[Dict[str, Any]] = []
    for fingerprint in get_full_registry():
        result = evaluate_live_candidacy(fingerprint["name"], fingerprint["direction"])
        results.append(result)
        if result["controlled_live_candidate"]:
            qualifying.append({
                "name": result["name"], "direction": result["direction"],
                "qualified_reason": result["live_entry_reason"],
                "experiment_id": result["experiment_id"],
                "evidence_epoch_after": result["evidence_epoch_after"],
                "checked_at": datetime.now(timezone.utc).isoformat(),
            })
    _write_export(qualifying, LIVE_CANDIDATE_PATH)
    try:
        _write_export(results, LIVE_CANDIDATE_PATH.parent / "universe_selection_learning" / "fingerprint_reviews.json")
    except OSError:
        log.warning("[FingerprintReview] Review persistence failed", exc_info=True)
    return results


def format_live_candidate_report(results: List[Dict[str, Any]]) -> str:
    lines = ["CONTROLLED LIVE CANDIDATE CHECK (bounded scanner evidence eligibility)"]
    for r in results:
        flag = "  <-- CONTROLLED LIVE CANDIDATE" if r["controlled_live_candidate"] else ""
        lines.append(f"  {r['name']} ({r['direction']}): status={r['lifecycle_status']}{flag}")
        lines.append(f"    {r['live_entry_reason']}")
    return "\n".join(lines)


if __name__ == "__main__":
    results = run_live_candidate_check_silent()
    print(format_live_candidate_report(results))
