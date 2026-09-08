"""
scripts/knowledge_system/fingerprint_validation_001.py
===================================================================
Phase 4 — Formal Research & Validation of a discovered fingerprint.

READ-ONLY, OBSERVATIONAL. Not imported by KDA, DecisionEngine,
StrategyLab, ExecutionEngine, OrderManager, or any live/paper trading
path. Standalone, manually invoked (NOT wired into the daily EOD
pipeline — formal validation is a periodic research action, not a
continuous daily task; Phase 2E/3 already provide continuous daily
observation). Writes only to its own report file
(data/fingerprint_validation_reports.jsonl).

WHY NOT ResearchCoordinator (autonomous_research/research_coordinator.py):
Investigated first. It is a full 10-stage hypothesis-registry research
orchestrator (STUDY_PLAN -> REPLAY -> VALIDATION -> AUDIT -> EVIDENCE ->
KNOWLEDGE -> SYNTHESIS -> REPOSITORY -> REPORT -> EVOLUTION), designed for
multi-hypothesis research programs with injected modules (planner,
hypothesis_registry, evidence_validator, synthesizer, idr). Its 190 tests
run entirely against mocked modules — no evidence it has ever executed
against real historical data. Its frozen train/val/OOS split
(TRAIN_DAYS=107, VAL_DAYS=53, OOS_DAYS=54, OOS 2026-05-14..2026-07-30) is
defined over a DIFFERENT, non-overlapping dataset
(post_open_gap_analysis.csv, 214 days) than our shadow_evidence_ledger.jsonl
(~30 usable trading days, Jul27..Sep04). Wiring this single fingerprint into
ResearchCoordinator would mean stubbing out most of its module dependencies
just to pass stages through — more complexity than value for validating
ONE already-well-understood characteristic. A purpose-built, lightweight
validator is the right-sized tool; ResearchCoordinator remains available
for a future multi-hypothesis research PROGRAM.

WHAT THIS DOES — Champion vs Challenger comparison, historical:
  CHAMPION   = candidates C2 already selected (SELECTED_WON + SELECTED_FAILED)
  CHALLENGER = CHAMPION + candidates flagged MISSED_WINNER_CANDIDATE by
               Phase 3's selection_intelligence_001.py (i.e. "what if we
               had also included fingerprint-matched rejects")
For each, computes dir_acc / ge1/ge2/ge3_rate / avg_t1_ret, then reports
the CHALLENGER's improvement (or regression) over CHAMPION, missed-winner
recovery count, and false-positive cost (fingerprint-matched adds that
did NOT work).

PRELIMINARY vs VALIDATED (explicit, never blurred):
Given only ~30 usable trading days exist right now, results are almost
certainly PRELIMINARY, not a fully-powered VALIDATED verdict. This module
computes an honest confidence-scoped verdict rather than overclaiming:
  INSUFFICIENT_DATA — fewer than MIN_SAMPLE_FOR_VERDICT total OOS-period
                       candidates in a group
  PRELIMINARY_PASS / PRELIMINARY_FAIL — passes/fails the pass criteria,
                       but on too little data / too short a period to
                       call VALIDATED
  VALIDATED_PASS / VALIDATED_FAIL — only reachable once enough history
                       (MIN_DAYS_FOR_VALIDATED trading days) has
                       accumulated via the now-live Phase 2E/3 pipeline

PASS CRITERIA (pre-specified, not tuned after seeing results):
  - Challenger's OOS ge2_rate must exceed Champion's by >= EXPECTED_GE2_DELTA
    (0.02 — the same bar research_proposal_builder_001.py already uses for
    "expected_delta" on a proposed change, reused here for consistency)
  - Challenger must recover at least 1 genuine missed winner in the OOS window
  - Challenger's dir_acc must not regress by more than MAX_DIR_ACC_REGRESSION
    (0.01, matching research_proposal_builder_001.py's own
    "risk_of_regression" bar)

OOS SPLIT: chronological, NOT random (avoids look-ahead). Available dates
for the fingerprint's direction are split into an EARLY period (used to
compute the fingerprint's own baseline/behaviour — the same period Phase
2A-2D already analyzed) and a LATE period, treated as the OOS window.
This is the same honest limitation already flagged in Phase 2D's
"preliminary stability check" and Phase 2E's growing-snapshot design —
a TRUE, never-touched OOS period only exists once genuinely NEW trading
days accumulate through the now-live daily pipeline.

REGIME BREAKDOWN: reuses Phase 2B's regime field; reports per-regime
where sample size allows, explicitly marks BULL/BEAR insufficient (same
finding as Phase 2B — not re-litigated here).

Verdict NEVER auto-applies to V3/C2/KDA/DecisionEngine. Output is a
report only, for the user to review before any further action.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.knowledge_system.fingerprint_tracker_001 import FINGERPRINT_REGISTRY
from scripts.knowledge_system.selection_characteristic_analyzer_001 import (
    FEATURES,
    GE2_THRESHOLD,
    MIN_SAMPLE_FOR_STATS,
    _band_of,
    _build_band_thresholds,
    _direction_correct,
    load_records,
)

ROOT = Path(__file__).resolve().parent.parent.parent
REPORT_PATH = ROOT / "data" / "fingerprint_validation_reports.jsonl"

GE1_THRESHOLD = 1.0
GE3_THRESHOLD = 3.0

EXPECTED_GE2_DELTA = 0.02       # reused from research_proposal_builder_001.py
MAX_DIR_ACC_REGRESSION = 0.01   # reused from research_proposal_builder_001.py
MIN_SAMPLE_FOR_VERDICT = MIN_SAMPLE_FOR_STATS  # 15 — below this: INSUFFICIENT_DATA
MIN_DAYS_FOR_VALIDATED = 60     # trading days of history required to call
                                 # anything VALIDATED rather than PRELIMINARY


def _metrics(records: List[Dict[str, Any]], direction: str) -> Dict[str, Any]:
    """dir_acc / ge1/ge2/ge3_rate / avg_t1_ret for a group of candidates."""
    n = len(records)
    if n == 0:
        return {"n": 0, "dir_acc": None, "ge1_rate": None, "ge2_rate": None,
                "ge3_rate": None, "avg_t1_ret": None}
    correct = [r for r in records if _direction_correct(direction, r["t1_ret_pct"])]
    ge = lambda thr: sum(1 for r in correct if abs(r["t1_ret_pct"]) >= thr) / n
    return {
        "n": n,
        "dir_acc": round(len(correct) / n, 4),
        "ge1_rate": round(ge(GE1_THRESHOLD), 4),
        "ge2_rate": round(ge(GE2_THRESHOLD), 4),
        "ge3_rate": round(ge(GE3_THRESHOLD), 4),
        "avg_t1_ret": round(sum(r["t1_ret_pct"] for r in records) / n, 4),
    }


def _split_champion_challenger(records: List[Dict[str, Any]], fingerprint: Dict[str, Any],
                                thresholds: Dict[str, Dict[str, float]]):
    """CHAMPION = C2-selected candidates. CHALLENGER = CHAMPION plus
    fingerprint-matched rejects (the Phase 3 MISSED_WINNER_CANDIDATE set)."""
    direction = fingerprint["direction"]
    rule = fingerprint["components"]["combined"]

    champion, added, added_false_positive = [], [], []
    for r in records:
        selected = bool(r.get("selected_final_5", False))
        if selected:
            champion.append(r)
            continue
        bands = {feat: _band_of(feat, r[feat], direction, thresholds)
                  for feat in FEATURES if r.get(feat) is not None}
        try:
            matches = bool(rule(bands))
        except KeyError:
            matches = False
        if matches:
            added.append(r)
            if not _direction_correct(direction, r["t1_ret_pct"]):
                added_false_positive.append(r)

    challenger = champion + added
    return champion, challenger, added, added_false_positive


def _classify_verdict(pass_criteria_met: bool, n_oos: int, n_days: int) -> str:
    if n_oos < MIN_SAMPLE_FOR_VERDICT:
        return "INSUFFICIENT_DATA"
    validated = n_days >= MIN_DAYS_FOR_VALIDATED
    if pass_criteria_met:
        return "VALIDATED_PASS" if validated else "PRELIMINARY_PASS"
    return "VALIDATED_FAIL" if validated else "PRELIMINARY_FAIL"


def validate_fingerprint(records: List[Dict[str, Any]], fingerprint: Dict[str, Any]) -> Dict[str, Any]:
    """Champion-vs-Challenger validation, chronological early/OOS split,
    plus per-regime breakdown. Returns a structured report — does not
    write anywhere, does not touch any live path."""
    direction = fingerprint["direction"]
    dir_records = [r for r in records if r.get("direction") == direction]
    dates = sorted({r["trade_date"] for r in dir_records if r.get("trade_date")})
    n_days = len(dates)

    if n_days < 4:
        return {
            "fingerprint_name": fingerprint["name"], "direction": direction,
            "n_days": n_days, "verdict": "INSUFFICIENT_DATA",
            "reason": "fewer than 4 distinct trading days available",
        }

    mid = len(dates) // 2
    early_dates, oos_dates = set(dates[:mid]), set(dates[mid:])
    early_records = [r for r in dir_records if r.get("trade_date") in early_dates]
    oos_records = [r for r in dir_records if r.get("trade_date") in oos_dates]

    # Thresholds computed from the EARLY period only (no OOS leakage into
    # band definitions), then applied to classify OOS-period candidates.
    thresholds = _build_band_thresholds(early_records, direction) if early_records else \
        _build_band_thresholds(dir_records, direction)

    champion, challenger, added, added_fp = _split_champion_challenger(
        oos_records, fingerprint, thresholds
    )

    champion_metrics = _metrics(champion, direction)
    challenger_metrics = _metrics(challenger, direction)

    ge2_delta = (
        round(challenger_metrics["ge2_rate"] - champion_metrics["ge2_rate"], 4)
        if champion_metrics["ge2_rate"] is not None and challenger_metrics["ge2_rate"] is not None
        else None
    )
    dir_acc_delta = (
        round(challenger_metrics["dir_acc"] - champion_metrics["dir_acc"], 4)
        if champion_metrics["dir_acc"] is not None and challenger_metrics["dir_acc"] is not None
        else None
    )
    recovered = [r for r in added if _direction_correct(direction, r["t1_ret_pct"])]

    pass_criteria_met = bool(
        ge2_delta is not None and ge2_delta >= EXPECTED_GE2_DELTA
        and len(recovered) >= 1
        and dir_acc_delta is not None and dir_acc_delta >= -MAX_DIR_ACC_REGRESSION
    )

    verdict = _classify_verdict(pass_criteria_met, len(challenger), n_days)

    # Per-regime breakdown (OOS period only), flagging insufficient samples.
    regimes: Dict[str, Any] = {}
    for regime in sorted({r.get("regime") for r in oos_records
                          if r.get("regime") not in (None, "UNAVAILABLE", "UNKNOWN")}):
        regime_records = [r for r in oos_records if r.get("regime") == regime]
        r_champion, r_challenger, r_added, _ = _split_champion_challenger(
            regime_records, fingerprint, thresholds
        )
        regimes[regime] = {
            "n_oos_candidates": len(regime_records),
            "champion": _metrics(r_champion, direction),
            "challenger": _metrics(r_challenger, direction),
            "low_confidence": len(regime_records) < MIN_SAMPLE_FOR_VERDICT,
        }

    return {
        "fingerprint_name": fingerprint["name"],
        "direction": direction,
        "n_days": n_days,
        "early_period": {"n_dates": len(early_dates),
                          "date_range": [min(early_dates), max(early_dates)] if early_dates else None},
        "oos_period": {"n_dates": len(oos_dates),
                        "date_range": [min(oos_dates), max(oos_dates)] if oos_dates else None},
        "champion": champion_metrics,
        "challenger": challenger_metrics,
        "ge2_rate_delta": ge2_delta,
        "dir_acc_delta": dir_acc_delta,
        "missed_winners_recovered": len(recovered),
        "false_positives_added": len(added_fp),
        "candidates_added_by_challenger": len(added),
        "pass_criteria": {
            "ge2_delta_required": EXPECTED_GE2_DELTA,
            "min_recovered_required": 1,
            "max_dir_acc_regression_allowed": MAX_DIR_ACC_REGRESSION,
            "met": pass_criteria_met,
        },
        "regimes": regimes,
        "verdict": verdict,
        "recommendation": (
            "TEST FURTHER — do not apply to V3/C2/KDA/DecisionEngine"
            if verdict in ("PRELIMINARY_PASS", "PRELIMINARY_FAIL", "INSUFFICIENT_DATA")
            else "ELIGIBLE FOR CHAMPION/CHALLENGER CANDIDACY — still requires "
                 "separate deployment approval before any live use"
            if verdict == "VALIDATED_PASS"
            else "REJECT HYPOTHESIS — record and continue learning"
        ),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def format_validation_report(report: Dict[str, Any]) -> str:
    if report.get("verdict") == "INSUFFICIENT_DATA" and "champion" not in report:
        return (f"FINGERPRINT VALIDATION — {report['fingerprint_name']} "
                f"({report['direction']}): INSUFFICIENT_DATA — {report.get('reason')}")

    lines = [
        "FINGERPRINT VALIDATION REPORT",
        f"Fingerprint: {report['fingerprint_name']}  Direction: {report['direction']}",
        f"History available: {report['n_days']} trading days "
        f"(need >= {MIN_DAYS_FOR_VALIDATED} for a VALIDATED verdict, not just PRELIMINARY)",
        f"Early period (used to define thresholds): {report['early_period']['date_range']} "
        f"({report['early_period']['n_dates']} days)",
        f"OOS period (challenger tested here): {report['oos_period']['date_range']} "
        f"({report['oos_period']['n_dates']} days)",
        "",
        "1. Does this characteristic improve mover discovery? (Champion vs Challenger, OOS)",
        f"   Champion (C2 only):        n={report['champion']['n']}  "
        f"dir_acc={report['champion']['dir_acc']}  ge1={report['champion']['ge1_rate']}  "
        f"ge2={report['champion']['ge2_rate']}  ge3={report['champion']['ge3_rate']}  "
        f"avg_t1_ret={report['champion']['avg_t1_ret']}",
        f"   Challenger (C2+fingerprint): n={report['challenger']['n']}  "
        f"dir_acc={report['challenger']['dir_acc']}  ge1={report['challenger']['ge1_rate']}  "
        f"ge2={report['challenger']['ge2_rate']}  ge3={report['challenger']['ge3_rate']}  "
        f"avg_t1_ret={report['challenger']['avg_t1_ret']}",
        f"   ge2_rate delta: {report['ge2_rate_delta']}  (required >= {EXPECTED_GE2_DELTA})",
        f"   dir_acc delta:  {report['dir_acc_delta']}  "
        f"(must not regress more than -{MAX_DIR_ACC_REGRESSION})",
        "",
        f"2. Missed winners recovered by challenger: {report['missed_winners_recovered']}",
        f"3. False positives added by challenger:    {report['false_positives_added']} "
        f"(out of {report['candidates_added_by_challenger']} candidates added)",
        "",
        "4. OOS validation: chronological split above IS the OOS test currently "
        "available — NOT yet a genuinely untouched future period (that requires "
        "new days accumulating via the live Phase 2E/3 pipeline).",
        "",
        "5. Regime robustness (OOS period):",
    ]
    for regime, r in report["regimes"].items():
        flag = " [LOW CONFIDENCE]" if r["low_confidence"] else ""
        lines.append(
            f"   {regime}: n={r['n_oos_candidates']}  "
            f"champion.ge2={r['champion']['ge2_rate']}  "
            f"challenger.ge2={r['challenger']['ge2_rate']}{flag}"
        )
    lines += [
        "",
        f"6/7. VERDICT: {report['verdict']}",
        f"     Recommendation: {report['recommendation']}",
    ]
    return "\n".join(lines)


def append_validation_report(report: Dict[str, Any], path: Path = REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(report) + "\n")


def run_validation(ledger_path=None) -> List[Dict[str, Any]]:
    """CLI/manual entry point. Validates every registered fingerprint,
    appends each report, prints the human-readable version."""
    from scripts.knowledge_system.selection_characteristic_analyzer_001 import LEDGER_PATH
    records = load_records(ledger_path or LEDGER_PATH)

    reports = []
    for fingerprint in FINGERPRINT_REGISTRY:
        report = validate_fingerprint(records, fingerprint)
        append_validation_report(report)
        print(format_validation_report(report))
        print()
        reports.append(report)
    return reports


if __name__ == "__main__":
    run_validation()
