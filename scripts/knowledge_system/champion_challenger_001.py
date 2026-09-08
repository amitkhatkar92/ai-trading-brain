"""
scripts/knowledge_system/champion_challenger_001.py
===================================================================
Phase 5 — Champion/Challenger Registry + Promotion Gate.

READ-ONLY, OBSERVATIONAL. Not imported by KDA, DecisionEngine,
StrategyLab, ExecutionEngine, OrderManager, or any live/paper trading
path. Still supports standalone/manual invocation (its original
cadence). As of Phase 6 (shadow_challenger_tracker_001.py), its
run_promotion_check() is ALSO called once per day as part of the EOD
pipeline — Phase 6 needs a freshly-computed status every day to decide
which fingerprints to shadow-track. This module is still never
DIRECTLY imported by master_orchestrator.py; its logic now runs daily
only indirectly, as a dependency of Phase 6. Writes only to its own
registry file (data/champion_challenger_registry.jsonl).

SCOPE (explicitly confirmed with the user before implementation):
Promotion in this phase is a REGISTRY/STATUS LABEL CHANGE ONLY.
Reaching CHALLENGER_ELIGIBLE status does NOT feed KDA, DecisionEngine,
or any paper/live trading path — that would be a separate, later phase
requiring its own explicit approval, per the standing rule that a
discovered characteristic must not influence live selection until it
clears the full validation gate AND a further, dedicated go-ahead.

STATUS LADDER (matches the user's diagram):
  OBSERVE_ONLY        — no validation verdict yet / INSUFFICIENT_DATA
  PRELIMINARY         — Phase 4 verdict is PRELIMINARY_PASS or
                        PRELIMINARY_FAIL (with only ~16-40 days of
                        history, a "fail" here isn't trustworthy enough
                        to permanently retire the hypothesis — it just
                        keeps being re-observed as more data arrives)
  VALIDATED_TRACKING  — Phase 4 verdict is VALIDATED_PASS (60+ days),
                        but hasn't yet met the repeatability bar
                        (MIN_CONSECUTIVE_VALIDATED_PASS consecutive
                        VALIDATED_PASS runs) or Phase 2E's daily
                        confidence isn't HIGH
  CHALLENGER_ELIGIBLE — ALL promotion criteria met (see below). Terminal
                        status reachable in this phase. Registry-only.
  REJECTED            — Phase 4 verdict is VALIDATED_FAIL (a fail with
                        enough statistical power to trust) — recorded
                        with the specific failing reason

PROMOTION CRITERIA (pre-specified, not tuned after seeing results):
  1. Latest Phase 4 validation verdict is VALIDATED_PASS
  2. That VALIDATED_PASS has held for >= MIN_CONSECUTIVE_VALIDATED_PASS
     consecutive registry checks (repeatability AT the validated tier —
     one validated pass alone is not enough)
  3. Phase 2E's independent daily fingerprint-tracker confidence is
     also HIGH (two independently-computed signals must agree)

ROLLBACK / MONITORING: status is recomputed FRESH from the current
validation run + current Phase 2E confidence + the registry's own
history every time this is invoked — never cached/sticky. If a
previously CHALLENGER_ELIGIBLE fingerprint's next check shows a
regression (FAIL verdict, broken consecutive streak, or confidence
drop), it is automatically demoted on the next run and the reason is
recorded. This is the rollback/monitoring behaviour the user asked for,
implemented at the registry level (there is nothing live to roll back
yet, since nothing here touches any trading path).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.knowledge_system.fingerprint_tracker_001 import (
    HISTORY_PATH,
    compute_trend,
    get_full_registry,
    load_history,
)
from scripts.knowledge_system.fingerprint_validation_001 import validate_fingerprint
from scripts.knowledge_system.selection_characteristic_analyzer_001 import load_records

ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = ROOT / "data" / "champion_challenger_registry.jsonl"

STATUS_OBSERVE_ONLY = "OBSERVE_ONLY"
STATUS_PRELIMINARY = "PRELIMINARY"
STATUS_VALIDATED_TRACKING = "VALIDATED_TRACKING"
STATUS_CHALLENGER_ELIGIBLE = "CHALLENGER_ELIGIBLE"
STATUS_REJECTED = "REJECTED"

MIN_CONSECUTIVE_VALIDATED_PASS = 3
REQUIRED_PHASE2E_CONFIDENCE = "HIGH"


def load_registry_history(fingerprint_name: str, direction: str,
                           path: Path = REGISTRY_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("fingerprint_name") == fingerprint_name and rec.get("direction") == direction:
            out.append(rec)
    return sorted(out, key=lambda r: r.get("checked_at", ""))


def _consecutive_validated_pass_streak(history: List[Dict[str, Any]], current_verdict: str) -> int:
    """Counts consecutive VALIDATED_PASS entries ending with (and including)
    the current check, walking backwards through registry history."""
    streak = 1 if current_verdict == "VALIDATED_PASS" else 0
    if streak == 0:
        return 0
    for entry in reversed(history):
        if entry.get("validation_verdict") == "VALIDATED_PASS":
            streak += 1
        else:
            break
    return streak


def determine_status(validation_report: Dict[str, Any], phase2e_confidence: Optional[str],
                      consecutive_validated_pass: int) -> Tuple[str, str]:
    """Pure decision function — given the latest validation verdict, the
    independent Phase 2E daily confidence, and the current repeatability
    streak, returns (status, reason). No side effects."""
    verdict = validation_report.get("verdict")

    if verdict == "INSUFFICIENT_DATA":
        return STATUS_OBSERVE_ONLY, "insufficient data for any validation verdict yet"

    if verdict == "PRELIMINARY_FAIL":
        return STATUS_PRELIMINARY, (
            "failed pass criteria at PRELIMINARY tier — with this little history "
            "a fail is not trustworthy enough to retire the hypothesis; continues "
            "to be re-observed as more data accumulates"
        )

    if verdict == "PRELIMINARY_PASS":
        return STATUS_PRELIMINARY, "passes criteria but insufficient history for a VALIDATED verdict"

    if verdict == "VALIDATED_FAIL":
        return STATUS_REJECTED, "failed pass criteria at VALIDATED tier (60+ days of history) — retired"

    # verdict == "VALIDATED_PASS"
    if consecutive_validated_pass < MIN_CONSECUTIVE_VALIDATED_PASS:
        return STATUS_VALIDATED_TRACKING, (
            f"VALIDATED_PASS but only {consecutive_validated_pass}/"
            f"{MIN_CONSECUTIVE_VALIDATED_PASS} consecutive validated-tier passes"
        )
    if phase2e_confidence != REQUIRED_PHASE2E_CONFIDENCE:
        return STATUS_VALIDATED_TRACKING, (
            f"repeatability met ({consecutive_validated_pass} consecutive) but Phase 2E's "
            f"independent daily confidence is {phase2e_confidence!r}, not "
            f"{REQUIRED_PHASE2E_CONFIDENCE!r}"
        )
    return STATUS_CHALLENGER_ELIGIBLE, (
        f"all promotion criteria met: VALIDATED_PASS x{consecutive_validated_pass} consecutive "
        f"+ Phase 2E confidence {REQUIRED_PHASE2E_CONFIDENCE} "
        "(registry status only — NOT wired into any live/paper trading path)"
    )


def append_registry_entry(entry: Dict[str, Any], path: Path = REGISTRY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def run_promotion_check(ledger_path=None) -> List[Dict[str, Any]]:
    """Main entry point. For every registered fingerprint: runs a fresh
    Phase 4 validation, reads Phase 2E's current daily confidence, checks
    the registry's own history for the consecutive-VALIDATED_PASS streak,
    determines status via determine_status(), appends one registry entry,
    and returns the list of entries."""
    from scripts.knowledge_system.selection_characteristic_analyzer_001 import LEDGER_PATH
    records = load_records(ledger_path or LEDGER_PATH)

    results = []
    for fingerprint in get_full_registry():
        direction = fingerprint["direction"]
        validation_report = validate_fingerprint(records, fingerprint)

        phase2e_history = load_history(fingerprint["name"], direction, HISTORY_PATH)
        phase2e_trend = compute_trend(phase2e_history)
        phase2e_confidence = phase2e_trend.get("confidence")

        registry_history = load_registry_history(fingerprint["name"], direction)
        streak = _consecutive_validated_pass_streak(registry_history, validation_report.get("verdict"))

        status, reason = determine_status(validation_report, phase2e_confidence, streak)

        entry = {
            "fingerprint_name": fingerprint["name"],
            "direction": direction,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "validation_verdict": validation_report.get("verdict"),
            "n_days": validation_report.get("n_days"),
            "validation_note": validation_report.get("validation_note"),
            "phase2e_confidence": phase2e_confidence,
            "consecutive_validated_pass": streak,
            "status": status,
            "reason": reason,
        }
        append_registry_entry(entry)
        results.append(entry)
    return results


def format_registry_report(entries: List[Dict[str, Any]]) -> str:
    lines = ["CHAMPION/CHALLENGER REGISTRY CHECK"]
    for e in entries:
        lines.append(
            f"  {e['fingerprint_name']} ({e['direction']}): status={e['status']}  "
            f"verdict={e['validation_verdict']}  n_days={e['n_days']}  "
            f"phase2e_confidence={e['phase2e_confidence']}  "
            f"consecutive_validated_pass={e['consecutive_validated_pass']}"
        )
        if e.get("validation_note"):
            lines.append(f"    validation_note: {e['validation_note']}")
        lines.append(f"    reason: {e['reason']}")
    return "\n".join(lines)


if __name__ == "__main__":
    entries = run_promotion_check()
    print(format_registry_report(entries))
