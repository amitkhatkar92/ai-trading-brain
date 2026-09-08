"""
scripts/knowledge_system/fingerprint_discovery_001.py
===================================================================
Phase 7 — Automatic, rule-based Fingerprint Discovery & Promotion +
Research Lifecycle Status.

READ-ONLY, OBSERVATIONAL. Not imported by KDA, DecisionEngine,
StrategyLab, ExecutionEngine, OrderManager, or any live/paper trading
path. Writes only to its own files (data/fingerprint_discovery_daily.jsonl,
data/discovered_fingerprints.json). Never modifies V3 discovery, C2
ranking, or selected_final_5.

WHAT THIS REPLACES: Phase 2D was a ONE-TIME, human-reviewed step — "take
the single strongest Phase 2C finding". This module makes that decision
continuously and automatically: every day, it re-evaluates ALL 5
pre-specified, hypothesis-driven combinations
(selection_characteristic_analyzer_001.COMBINATIONS) across BOTH
directions (10 candidate-direction pairs total) against an explicit,
pre-specified bar, and promotes any combo/direction that clears it into
a persisted discovered-fingerprint store. NO blind combinatorial search
is introduced — the candidate SET is still exactly the same 5
pre-specified combinations that already existed; only the DECISION to
promote one is now automatic and rule-based instead of manual.

PROMOTION BAR (pre-specified, reuses already-established constants, not
invented for this module):
  - overall lift        >= EXPECTED_GE2_DELTA (0.02), imported from
                            fingerprint_validation_001.py for consistency
  - rejected-only lift  >= EXPECTED_GE2_DELTA (0.02) — the "does it
                            actually catch missed winners" question,
                            the project's stated mission
  - n (rejected-only)    >= MIN_SAMPLE_FOR_STATS (15)

Both overall AND rejected-only must clear the bar — overall alone would
promote characteristics that only work within the already-selected pool
(irrelevant to catching missed winners); rejected-only alone would ignore
whether the characteristic sharpens the full candidate pool.

Real production check (2026-09-08, 640 records): only the one
combination already manually promoted in Phase 2D clears this bar
(overall_lift=+0.1541, rejected_only_lift=+0.1264). The other 9
candidate-direction pairs do not (best of the rest: +0.018 overall,
under the 0.02 bar) — confirming this is a genuine bar, not a rubber
stamp.

ALREADY-REGISTERED EXCLUSION: the one combination that was manually
promoted in Phase 2D ("low_rsi_and_high_mom_accel", UP — hard-coded as
FINGERPRINT_UP_LOW_RSI_HIGH_ACCEL in fingerprint_tracker_001.py's
FINGERPRINT_REGISTRY) is permanently excluded from re-evaluation/
re-promotion here via STATICALLY_REGISTERED, to avoid a duplicate
registry entry. This module has NO import dependency on
fingerprint_tracker_001.py at module load time (one-way DAG: analyzer ->
discovery -> {tracker, champion_challenger, shadow_challenger} via
LOCAL/lazy imports only inside those other modules' functions) to avoid
any circular import.

PROMOTION IS PERMANENT, LIKE A RESEARCH LOG ENTRY: once a candidate
clears the bar and is written to discovered_fingerprints.json, it is
never silently removed by this module even if a LATER day's
re-evaluation would no longer clear the bar — exactly like Phase 5's
PRELIMINARY_FAIL does not retire a hypothesis. Retirement/rejection of
an already-promoted research candidate is what the downstream chain
(Phase 4 VALIDATED_FAIL -> Phase 5 REJECTED, or a broken repeatability
streak -> RETIRED below) is for, not this module. This keeps a stable
audit trail: "when was X first identified as worth studying" never
changes retroactively.

RESEARCH LIFECYCLE STATUS (requested by the user on top of the existing
Phase 5 status ladder, to give a single, explicit state per candidate
covering the whole chain):

  NOT_YET             candidate combo has not cleared the discovery bar
  RESEARCH_CANDIDATE  cleared discovery bar; being tracked/scored/
                      validated, but Phase 5 hasn't reached
                      VALIDATED_TRACKING yet (or no Phase 5 check has
                      run for it yet)
  VALIDATED_TRACKING  Phase 5 status == VALIDATED_TRACKING
  CHALLENGER_ELIGIBLE Phase 5 status == CHALLENGER_ELIGIBLE, Phase 6
                      shadow tracking has not yet accumulated any days
  SHADOW_TEST         Phase 5 status == CHALLENGER_ELIGIBLE AND Phase 6
                      has >=1 shadow day recorded, but has not yet
                      reached the consecutive-win-day PASS bar
  PASS                Phase 6 shadow history shows
                      >= SHADOW_PASS_MIN_CONSECUTIVE_WIN_DAYS (3)
                      consecutive challenger-win days (proves out
                      prospectively) — STILL registry-only; "PASS"
                      means "proven research candidate", NOT "approved
                      for live trading" (a separate, later, explicitly-
                      approved phase)
  FAIL                Phase 4/5 verdict is VALIDATED_FAIL (a
                      statistically-powered rejection)
  RETIRED             candidate had reached VALIDATED_TRACKING or
                      beyond, previously accumulated a consecutive-
                      VALIDATED_PASS streak, and that streak has since
                      broken back to zero — a softer "stopped
                      replicating" outcome, distinct from a hard
                      statistical FAIL

This status is a REPORTING ROLLUP only — it reads Phase 5/6's existing,
untouched outputs and computes a label; it does not change any of their
behaviour, persistence, or interfaces.

SCHEDULING: wired into master_orchestrator.py's _do_eod_learning()
(DTA-PHASE7-DISCOVERY-001), BEFORE Phase 2E's block, so any
freshly-promoted fingerprint is immediately trackable in the same EOD
cycle. Wrapped in its own try/except: a failure here is logged and never
aborts EOD learning or any trading path.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.knowledge_system.selection_characteristic_analyzer_001 import (
    COMBINATIONS,
    FEATURES,
    MIN_SAMPLE_FOR_STATS,
    _band_of,
    _build_band_thresholds,
    _mover_rate,
    load_records,
)
from scripts.knowledge_system.fingerprint_validation_001 import EXPECTED_GE2_DELTA

ROOT = Path(__file__).resolve().parent.parent.parent
DISCOVERY_LOG_PATH = ROOT / "data" / "fingerprint_discovery_daily.jsonl"
DISCOVERED_FINGERPRINTS_PATH = ROOT / "data" / "discovered_fingerprints.json"

# The one combination already manually promoted in Phase 2D — permanently
# excluded here to avoid a duplicate registry entry (see module docstring).
# NOTE: its combo name in COMBINATIONS ("low_rsi_and_high_mom_accel") is
# NOT the same string as its actual, persisted fingerprint name
# ("UP_low_rsi_high_accel", used throughout Phase 2E/3/5/6's history
# files) — COMBO_TO_FINGERPRINT_NAME bridges the two identity spaces for
# this one exception. Every Phase-7-discovered fingerprint uses its combo
# name AS its fingerprint name directly (build_fingerprint_from_conditions),
# so no mapping is needed for them (identity resolution, unaffected).
COMBO_TO_FINGERPRINT_NAME = {"low_rsi_and_high_mom_accel": "UP_low_rsi_high_accel"}
STATICALLY_REGISTERED = {("UP_low_rsi_high_accel", "UP")}  # fingerprint-name-keyed


def _resolve_fingerprint_name(combo_name: str) -> str:
    return COMBO_TO_FINGERPRINT_NAME.get(combo_name, combo_name)


PROMOTION_LIFT_THRESHOLD = EXPECTED_GE2_DELTA  # 0.02, reused for consistency
PROMOTION_MIN_SAMPLE = MIN_SAMPLE_FOR_STATS      # 15

LIFECYCLE_NOT_YET = "NOT_YET"
LIFECYCLE_RESEARCH_CANDIDATE = "RESEARCH_CANDIDATE"
LIFECYCLE_VALIDATED_TRACKING = "VALIDATED_TRACKING"
LIFECYCLE_CHALLENGER_ELIGIBLE = "CHALLENGER_ELIGIBLE"
LIFECYCLE_SHADOW_TEST = "SHADOW_TEST"
LIFECYCLE_PASS = "PASS"
LIFECYCLE_FAIL = "FAIL"
LIFECYCLE_RETIRED = "RETIRED"

# Mirrors champion_challenger_001.MIN_CONSECUTIVE_VALIDATED_PASS=3's
# repeatability convention, applied at the shadow-tracking tier.
SHADOW_PASS_MIN_CONSECUTIVE_WIN_DAYS = 3


def _latest_date_for_direction(records: List[Dict[str, Any]], direction: str) -> Optional[str]:
    dates = [r["trade_date"] for r in records if r.get("direction") == direction and r.get("trade_date")]
    return max(dates) if dates else None


def evaluate_candidate(records: List[Dict[str, Any]], combo: Dict[str, Any],
                        direction: str) -> Dict[str, Any]:
    """Evaluates one pre-specified combination for one direction against
    the promotion bar. Does NOT search for new combinations — `combo` is
    always one of selection_characteristic_analyzer_001.COMBINATIONS."""
    dir_records = [r for r in records if r.get("direction") == direction]
    thresholds = _build_band_thresholds(dir_records, direction)

    true_all: List[Dict[str, Any]] = []
    false_all: List[Dict[str, Any]] = []
    true_rej: List[Dict[str, Any]] = []
    false_rej: List[Dict[str, Any]] = []
    for r in dir_records:
        bands = {feat: _band_of(feat, r[feat], direction, thresholds)
                  for feat in FEATURES if r.get(feat) is not None}
        try:
            matches = bool(combo["rule"](bands))
        except KeyError:
            continue
        selected = bool(r.get("selected_final_5", False))
        (true_all if matches else false_all).append(r)
        if not selected:
            (true_rej if matches else false_rej).append(r)

    rate_true_all, rate_false_all = _mover_rate(true_all), _mover_rate(false_all)
    rate_true_rej, rate_false_rej = _mover_rate(true_rej), _mover_rate(false_rej)

    overall_lift = (round(rate_true_all - rate_false_all, 4)
                    if rate_true_all is not None and rate_false_all is not None else None)
    rejected_lift = (round(rate_true_rej - rate_false_rej, 4)
                     if rate_true_rej is not None and rate_false_rej is not None else None)

    meets_bar = bool(
        overall_lift is not None and overall_lift >= PROMOTION_LIFT_THRESHOLD
        and rejected_lift is not None and rejected_lift >= PROMOTION_LIFT_THRESHOLD
        and len(true_rej) >= PROMOTION_MIN_SAMPLE
    )

    return {
        "name": combo["name"], "label": combo["label"], "direction": direction,
        "n_true_overall": len(true_all), "n_true_rejected": len(true_rej),
        "overall_lift": overall_lift, "rejected_only_lift": rejected_lift,
        "meets_promotion_bar": meets_bar,
    }


def build_fingerprint_from_conditions(name: str, label: str, direction: str,
                                       conditions: List[Tuple[str, str]]) -> Dict[str, Any]:
    """Mechanically builds a fingerprint dict in the same shape as
    FINGERPRINT_UP_LOW_RSI_HIGH_ACCEL (name/label/direction/components),
    purely from a JSON-serializable list of (feature, band) AND-conditions
    — no hand-authored lambdas needed for newly-discovered candidates."""
    components: Dict[str, Any] = {}
    for feat, band in conditions:
        components[f"{feat}_alone"] = (lambda b, f=feat, v=band: b.get(f) == v)
    conds = tuple(conditions)
    components["combined"] = (lambda b, conds=conds: all(b.get(f) == v for f, v in conds))
    return {"name": name, "label": label, "direction": direction, "components": components}


def load_discovered_fingerprints(path: Path = DISCOVERED_FINGERPRINTS_PATH) -> List[Dict[str, Any]]:
    """Rebuilds executable fingerprint dicts from the persisted, data-only
    (JSON-serializable) specs Phase 7 has promoted so far."""
    if not path.exists():
        return []
    try:
        specs = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    out = []
    for spec in specs:
        conditions = [tuple(c) for c in spec["conditions"]]
        out.append(build_fingerprint_from_conditions(spec["name"], spec["label"], spec["direction"], conditions))
    return out


def _already_discovered(name: str, direction: str, path: Path = DISCOVERED_FINGERPRINTS_PATH) -> bool:
    if not path.exists():
        return False
    try:
        specs = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return any(s["name"] == name and s["direction"] == direction for s in specs)


def _persist_new_discovery(name: str, label: str, direction: str,
                            conditions: List[Tuple[str, str]],
                            path: Path = DISCOVERED_FINGERPRINTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    specs = []
    if path.exists():
        try:
            specs = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            specs = []
    specs.append({
        "name": name, "label": label, "direction": direction,
        "conditions": [list(c) for c in conditions],
        "promoted_at": datetime.now(timezone.utc).isoformat(),
    })
    path.write_text(json.dumps(specs, indent=2), encoding="utf-8")


def _load_existing_log_keys(path: Path) -> set:
    keys = set()
    if not path.exists():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        keys.add((rec.get("as_of_date"), rec.get("name"), rec.get("direction")))
    return keys


def append_discovery_log(entry: Dict[str, Any], path: Path = DISCOVERY_LOG_PATH) -> bool:
    """Idempotent per (as_of_date, name, direction)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    key = (entry["as_of_date"], entry["name"], entry["direction"])
    if key in _load_existing_log_keys(path):
        return False
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return True


def _consecutive_challenger_win_streak(shadow_history: List[Dict[str, Any]]) -> int:
    streak = 0
    for h in reversed(shadow_history):
        if h.get("challenger_at_least_as_good"):
            streak += 1
        else:
            break
    return streak


def compute_lifecycle_status(name: str, direction: str,
                              discovered_path: Path = DISCOVERED_FINGERPRINTS_PATH) -> Dict[str, Any]:
    """Pure rollup — reads Phase 5's registry history and Phase 6's shadow
    history (both already-persisted, untouched by this call) and returns
    {name, direction, lifecycle_status, reason}."""
    # Local imports: breaks the module-load-time import cycle (those
    # modules import fingerprint_tracker_001, which lazily imports THIS
    # module only inside a function body — see fingerprint_tracker_001.
    from scripts.knowledge_system.champion_challenger_001 import (
        STATUS_CHALLENGER_ELIGIBLE,
        STATUS_OBSERVE_ONLY,
        STATUS_PRELIMINARY,
        STATUS_REJECTED,
        STATUS_VALIDATED_TRACKING,
        load_registry_history,
    )
    from scripts.knowledge_system.shadow_challenger_tracker_001 import load_shadow_history

    is_statically_registered = (name, direction) in STATICALLY_REGISTERED
    if not is_statically_registered and not _already_discovered(name, direction, discovered_path):
        return {"name": name, "direction": direction, "lifecycle_status": LIFECYCLE_NOT_YET,
                "reason": "has not cleared the automatic discovery promotion bar yet"}

    registry_history = load_registry_history(name, direction)
    if not registry_history:
        return {"name": name, "direction": direction, "lifecycle_status": LIFECYCLE_RESEARCH_CANDIDATE,
                "reason": "promoted as a research candidate; no Phase 5 validation check has run yet"}

    latest = registry_history[-1]
    status = latest.get("status")

    if status == STATUS_REJECTED:
        return {"name": name, "direction": direction, "lifecycle_status": LIFECYCLE_FAIL,
                "reason": latest.get("reason")}

    if status in (STATUS_OBSERVE_ONLY, STATUS_PRELIMINARY):
        return {"name": name, "direction": direction, "lifecycle_status": LIFECYCLE_RESEARCH_CANDIDATE,
                "reason": latest.get("reason")}

    if status == STATUS_VALIDATED_TRACKING:
        ever_had_streak = any(e.get("consecutive_validated_pass", 0) >= 1 for e in registry_history[:-1])
        if ever_had_streak and latest.get("consecutive_validated_pass", 0) == 0:
            return {"name": name, "direction": direction, "lifecycle_status": LIFECYCLE_RETIRED,
                    "reason": "previously accumulating a validated-pass streak, which has now broken"}
        return {"name": name, "direction": direction, "lifecycle_status": LIFECYCLE_VALIDATED_TRACKING,
                "reason": latest.get("reason")}

    # status == STATUS_CHALLENGER_ELIGIBLE
    shadow_history = load_shadow_history(name, direction)
    if not shadow_history:
        return {"name": name, "direction": direction, "lifecycle_status": LIFECYCLE_CHALLENGER_ELIGIBLE,
                "reason": "eligible; shadow tracking has not recorded a day yet"}
    streak = _consecutive_challenger_win_streak(shadow_history)
    if streak >= SHADOW_PASS_MIN_CONSECUTIVE_WIN_DAYS:
        return {"name": name, "direction": direction, "lifecycle_status": LIFECYCLE_PASS,
                "reason": f"{streak} consecutive shadow days where challenger >= champion "
                           "(research-proven; still requires a SEPARATE, explicit go-ahead "
                           "before any live consideration)"}
    return {"name": name, "direction": direction, "lifecycle_status": LIFECYCLE_SHADOW_TEST,
            "reason": f"shadow tracking in progress ({streak}/{SHADOW_PASS_MIN_CONSECUTIVE_WIN_DAYS} "
                       "consecutive challenger-win days so far)"}


def run_discovery_silent(ledger_path=None) -> List[Dict[str, Any]]:
    """Main entry point, no stdout output — safe to embed in the EOD
    orchestrator pipeline. Evaluates all 5 pre-specified combinations x
    both directions (10 candidate-direction pairs), logs a daily snapshot
    per candidate (idempotent per as_of_date), promotes (permanently,
    one-time) any candidate that newly clears the bar, and attaches each
    candidate's current research lifecycle status."""
    from scripts.knowledge_system.selection_characteristic_analyzer_001 import LEDGER_PATH
    records = load_records(ledger_path or LEDGER_PATH)

    results: List[Dict[str, Any]] = []
    for direction in ("UP", "DOWN"):
        as_of_date = _latest_date_for_direction(records, direction)
        for combo in COMBINATIONS:
            fp_name = _resolve_fingerprint_name(combo["name"])
            key = (fp_name, direction)
            statically_excluded = key in STATICALLY_REGISTERED
            evaluation = evaluate_candidate(records, combo, direction)
            already = statically_excluded or _already_discovered(fp_name, direction)
            newly_promoted = False

            if not statically_excluded and evaluation["meets_promotion_bar"] and not already:
                conditions = combo.get("conditions")
                if conditions is not None:
                    _persist_new_discovery(fp_name, combo["label"], direction, conditions)
                    newly_promoted = True
                    already = True

            lifecycle = compute_lifecycle_status(fp_name, direction)

            entry = {
                "as_of_date": as_of_date,
                "name": combo["name"], "label": combo["label"], "direction": direction,
                "overall_lift": evaluation["overall_lift"],
                "rejected_only_lift": evaluation["rejected_only_lift"],
                "n_true_rejected": evaluation["n_true_rejected"],
                "meets_promotion_bar": evaluation["meets_promotion_bar"],
                "already_registered": already,
                "newly_promoted_today": newly_promoted,
                "lifecycle_status": lifecycle["lifecycle_status"],
                "lifecycle_reason": lifecycle["reason"],
            }
            if as_of_date is not None:
                append_discovery_log(entry)
            results.append(entry)
    return results


def format_discovery_report(results: List[Dict[str, Any]]) -> str:
    lines = ["FINGERPRINT DISCOVERY & RESEARCH LIFECYCLE (Phase 7)"]
    for r in results:
        promoted_flag = "  <-- NEWLY PROMOTED" if r["newly_promoted_today"] else ""
        lines.append(
            f"  [{r['direction']}] {r['label']}: overall_lift={r['overall_lift']}  "
            f"rejected_only_lift={r['rejected_only_lift']}  n_rejected={r['n_true_rejected']}  "
            f"meets_bar={r['meets_promotion_bar']}  status={r['lifecycle_status']}{promoted_flag}"
        )
        lines.append(f"    reason: {r['lifecycle_reason']}")
    return "\n".join(lines)


if __name__ == "__main__":
    results = run_discovery_silent()
    print(format_discovery_report(results))
