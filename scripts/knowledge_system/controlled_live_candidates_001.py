"""
scripts/knowledge_system/controlled_live_candidates_001.py
===================================================================
Phase 8 — Controlled Live-Path Consideration (mechanism only, dormant).

READ-ONLY, OBSERVATIONAL. Not imported by KDA, DecisionEngine,
StrategyLab, ExecutionEngine, OrderManager, mover_discovery_v3.py,
final_c2_selector.py, or any live/paper trading path. Writes only to its
own file (data/controlled_live_candidates.json).

WHAT THIS IS: the automatic extension of Phase 7's research lifecycle
(NOT_YET -> RESEARCH_CANDIDATE -> VALIDATED_TRACKING -> CHALLENGER_
ELIGIBLE -> SHADOW_TEST -> PASS) with two further states:

  CONTROLLED_LIVE_CANDIDATE  Reached automatically, by objective
                             criteria, once a fingerprint has reached
                             PASS (Phase 7) AND additionally clears the
                             live-entry safety bar below. STILL
                             registry-only — reaching this state has
                             ZERO effect on any trading path. Unlike
                             Phase 7's discovery log (a permanent
                             research-history fact), eligibility here is
                             recomputed FRESH every run and immediately
                             withdrawn on any regression — this is the
                             "rollback" mechanism for the live-candidate
                             tier specifically.
  LIVE                       NOT REACHABLE BY THIS MODULE. Defined here
                             only as a placeholder constant for a
                             future phase. Reaching LIVE would require
                             BOTH (a) a separate, explicit future change
                             that wires mover_discovery_v3.py/final_c2_
                             selector.py to actually read
                             data/controlled_live_candidates.json, AND
                             (b) config.ENABLE_CONTROLLED_LIVE_CANDIDATES
                             being explicitly set True. Neither exists
                             yet, and this module's own logic never
                             returns LIVE for anything.

LIVE-ENTRY SAFETY BAR (pre-specified, applied ON TOP OF Phase 7's PASS
bar, not instead of it):
  - Phase 7 lifecycle_status == PASS (already means >= 3 consecutive
    shadow-win days — see fingerprint_discovery_001.py)
  - total shadow days tracked >= MIN_SHADOW_DAYS_FOR_LIVE_CANDIDATE (10,
    matching fingerprint_validation_001.MIN_DAYS_FOR_VALIDATED's
    established "minimum real evidence, not a mythical perfect N"
    convention)
  - cumulative challenger win-rate across ALL tracked shadow days (not
    just the most recent streak) >= MIN_LIVE_CANDIDATE_WIN_RATE (0.6) —
    a stricter, whole-history check so a lucky 3-day streak alone cannot
    qualify
  - ZERO REJECTED (Phase 5 "FAIL") verdicts, and no broken consecutive-
    validated-pass streak ("RETIRED"), anywhere in the fingerprint's
    Phase 5 registry history — no regression at any point in its life,
    ever, disqualifies it permanently from this tier

CONFIG FLAG: config.ENABLE_CONTROLLED_LIVE_CANDIDATES (default False).
This module writes the export file regardless of the flag (so the
mechanism and its output are fully testable/observable) — nothing
anywhere currently reads that file.

SCHEDULING: wired into master_orchestrator.py's _do_eod_learning()
(DTA-PHASE8-LIVE-CANDIDATE-001), AFTER Phase 6's shadow tracking block
(needs that day's freshly-written shadow history) and BEFORE the final
_write_eod_status("COMPLETED"). Wrapped in its own try/except: a failure
here is logged and never aborts EOD learning or any trading path.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from scripts.knowledge_system.fingerprint_discovery_001 import (
    LIFECYCLE_PASS,
    compute_lifecycle_status,
)
from scripts.knowledge_system.fingerprint_tracker_001 import get_full_registry

ROOT = Path(__file__).resolve().parent.parent.parent
LIVE_CANDIDATE_PATH = ROOT / "data" / "controlled_live_candidates.json"

LIFECYCLE_CONTROLLED_LIVE_CANDIDATE = "CONTROLLED_LIVE_CANDIDATE"
LIFECYCLE_LIVE = "LIVE"  # never returned by this module — see docstring

MIN_SHADOW_DAYS_FOR_LIVE_CANDIDATE = 10  # matches MIN_DAYS_FOR_VALIDATED convention
MIN_LIVE_CANDIDATE_WIN_RATE = 0.6


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

    shadow_history = load_shadow_history(name, direction)
    cumulative = _cumulative_summary(shadow_history)
    registry_history = load_registry_history(name, direction)
    regressed = _ever_regressed(registry_history)

    n_days = cumulative["n_days_tracked"]
    win_rate = cumulative["challenger_win_rate"] or 0.0

    meets_days = n_days >= MIN_SHADOW_DAYS_FOR_LIVE_CANDIDATE
    meets_rate = win_rate >= MIN_LIVE_CANDIDATE_WIN_RATE

    if meets_days and meets_rate and not regressed:
        return {
            "name": name, "direction": direction,
            "lifecycle_status": LIFECYCLE_CONTROLLED_LIVE_CANDIDATE,
            "controlled_live_candidate": True,
            "live_entry_reason": (
                f"PASS + {n_days} shadow days (>= {MIN_SHADOW_DAYS_FOR_LIVE_CANDIDATE}) "
                f"+ {win_rate} cumulative win-rate (>= {MIN_LIVE_CANDIDATE_WIN_RATE}) "
                "+ no FAIL/RETIRED ever in history — registry-only, zero live effect, "
                "not consumed by any trading path"
            ),
        }

    reasons = []
    if not meets_days:
        reasons.append(f"only {n_days}/{MIN_SHADOW_DAYS_FOR_LIVE_CANDIDATE} shadow days tracked")
    if not meets_rate:
        reasons.append(f"cumulative win-rate {win_rate} < {MIN_LIVE_CANDIDATE_WIN_RATE}")
    if regressed:
        reasons.append("has a FAIL or RETIRED occurrence somewhere in its history")

    return {
        "name": name, "direction": direction,
        "lifecycle_status": LIFECYCLE_PASS,
        "controlled_live_candidate": False,
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
    (rollback), since nothing has ever consumed this file and there is
    no permanent-promotion guarantee at this tier (unlike Phase 7's
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
                "checked_at": datetime.now(timezone.utc).isoformat(),
            })
    _write_export(qualifying, LIVE_CANDIDATE_PATH)
    return results


def format_live_candidate_report(results: List[Dict[str, Any]]) -> str:
    lines = ["CONTROLLED LIVE CANDIDATE CHECK (Phase 8 — mechanism only, nothing consumes this yet)"]
    for r in results:
        flag = "  <-- CONTROLLED LIVE CANDIDATE" if r["controlled_live_candidate"] else ""
        lines.append(f"  {r['name']} ({r['direction']}): status={r['lifecycle_status']}{flag}")
        lines.append(f"    {r['live_entry_reason']}")
    return "\n".join(lines)


if __name__ == "__main__":
    results = run_live_candidate_check_silent()
    print(format_live_candidate_report(results))
