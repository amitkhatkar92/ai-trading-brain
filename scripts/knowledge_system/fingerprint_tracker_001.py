"""
scripts/knowledge_system/fingerprint_tracker_001.py
===================================================================
Phase 2E (Selection Intelligence Layer) — permanent Discovery Learning
Loop for candidate fingerprints.

READ-ONLY, ADDITIVE LEARNING COMPONENT. Not imported by
master_orchestrator.py or any live trading path. Writes only to its own
persistent history file (data/fingerprint_tracking_history.jsonl) — never
to mover_discovery_v3.py, final_c2_selector.py, StrategyLab, KDA,
DecisionEngine, Risk, or Execution. Nothing here is auto-applied to any
live rule; it only produces "TEST ONLY — DO NOT APPLY" style reports.

WHY THIS IS SEPARATE FROM selection_characteristic_analyzer_001.py:
The analyzer (Phase 2A-2D) is stateless — every run recomputes everything
from the evidence ledger from scratch. Phase 2E needs the opposite
property: a fingerprint's value comes from watching whether its effect
holds up as MORE evidence accumulates over time, so this module persists
one growing-window snapshot per run and never discards prior snapshots.

DESIGN — growing-window snapshots, not single-day snapshots:
Each time this is run, it recomputes the fingerprint's combined-condition
mover-rate/lift/concentration across ALL currently available evidence
(not just "today"), and records that as one snapshot keyed by the latest
trade_date present in the data. Single-day-only snapshots would have far
too few observations (a handful of UP candidates/day) to be meaningful;
a growing cumulative window gives a walk-forward-style curve showing
whether the lift is strengthening, weakening, or holding steady as more
days of history accumulate. Re-running on the same day's data is
idempotent (no duplicate snapshot for the same as-of date).

SCHEDULING: connected to orchestrator/master_orchestrator.py's
_do_eod_learning() (DTA-PHASE2E-EOD-001) — called once per EOD cycle,
after all evidence-producing stages (KSL-001, LOL-EOD, LOL-BRIDGE,
KLP->KSL) have run, via run_tracking_silent(). Wrapped in its own
try/except there: a tracker failure is logged and never aborts EOD
learning or any trading path. The tracker itself still performs zero
reads/writes on any trading, scoring, or decision module.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.knowledge_system.selection_characteristic_analyzer_001 import (
    FINGERPRINT_UP_LOW_RSI_HIGH_ACCEL,
    MIN_SAMPLE_FOR_STATS,
    analyze_fingerprint,
    load_records,
)

ROOT = Path(__file__).resolve().parent.parent.parent
HISTORY_PATH = ROOT / "data" / "fingerprint_tracking_history.jsonl"

# Extensible registry — seed with the one fingerprint that has cleared
# Phase 2C/2D so far. New candidates get added here only after they clear
# the same bar (Phase 2C combination lift + Phase 2D concentration check),
# never added speculatively.
FINGERPRINT_REGISTRY: List[Dict[str, Any]] = [FINGERPRINT_UP_LOW_RSI_HIGH_ACCEL]


def _latest_trade_date(records: List[Dict[str, Any]], direction: str) -> Optional[str]:
    dates = [r["trade_date"] for r in records if r.get("direction") == direction and r.get("trade_date")]
    return max(dates) if dates else None


def compute_snapshot(records: List[Dict[str, Any]], fingerprint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One growing-window snapshot of the fingerprint's 'combined' condition,
    as of the latest trade_date currently present in the evidence ledger."""
    direction = fingerprint["direction"]
    as_of_date = _latest_trade_date(records, direction)
    if as_of_date is None:
        return None

    fp_report = analyze_fingerprint(records, fingerprint)
    combined = fp_report["components"].get("combined")
    if combined is None:
        return None

    lift = (round(combined["mover_rate_true"] - combined["mover_rate_false"], 4)
            if combined["mover_rate_true"] is not None and combined["mover_rate_false"] is not None else None)

    return {
        "fingerprint_name": fingerprint["name"],
        "direction": direction,
        "as_of_date": as_of_date,
        "n_records_used": fp_report["n_records"],
        "n_true": combined["n_true"],
        "n_false": combined["n_false"],
        "mover_rate_true": combined["mover_rate_true"],
        "mover_rate_false": combined["mover_rate_false"],
        "lift": lift,
        "group_concentration": combined["group_concentration"],
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def append_snapshot(snapshot: Dict[str, Any], history_path: Path = HISTORY_PATH) -> bool:
    """Appends a snapshot unless one already exists for the same
    (fingerprint_name, direction, as_of_date) — idempotent across re-runs
    on the same day's data. Returns True if a new snapshot was written."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    key = (snapshot["fingerprint_name"], snapshot["direction"], snapshot["as_of_date"])
    if history_path.exists():
        for line in history_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (existing.get("fingerprint_name"), existing.get("direction"),
                    existing.get("as_of_date")) == key:
                return False  # already have a snapshot for this as-of date
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot) + "\n")
    return True


def load_history(fingerprint_name: str, direction: str,
                  history_path: Path = HISTORY_PATH) -> List[Dict[str, Any]]:
    if not history_path.exists():
        return []
    out = []
    for line in history_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("fingerprint_name") == fingerprint_name and rec.get("direction") == direction:
            out.append(rec)
    return sorted(out, key=lambda r: r["as_of_date"])


def compute_trend(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Explicit, documented heuristic — not a statistical test. Intended as
    a conservative starting rule, adjustable as more snapshots accumulate:

      LOW confidence    - fewer than 3 snapshots, OR latest n_true < 15
      MEDIUM confidence - >=3 snapshots, latest n_true >= 15, AND at least
                          half of all snapshots show positive lift
      HIGH confidence   - >=5 snapshots, latest n_true >= 30, AND the most
                          recent 3 consecutive snapshots all show positive lift

    trend label compares the mean lift of the most recent up-to-3 snapshots
    against the mean lift of the earliest up-to-3 snapshots.
    """
    n = len(history)
    if n == 0:
        return {"n_snapshots": 0, "confidence": "LOW", "trend": "NO_DATA",
                "consecutive_positive_lift": 0}

    lifts = [h["lift"] for h in history if h.get("lift") is not None]
    latest = history[-1]
    consecutive_positive = 0
    for h in reversed(history):
        if h.get("lift") is not None and h["lift"] > 0:
            consecutive_positive += 1
        else:
            break

    if n < 3:
        trend = "INSUFFICIENT_HISTORY"
    else:
        early_window = lifts[:min(3, len(lifts))]
        late_window = lifts[-min(3, len(lifts)):]
        early_mean = sum(early_window) / len(early_window) if early_window else 0.0
        late_mean = sum(late_window) / len(late_window) if late_window else 0.0
        diff = late_mean - early_mean
        if diff > 0.02:
            trend = "STRENGTHENING"
        elif diff < -0.02:
            trend = "WEAKENING"
        else:
            trend = "STABLE"

    latest_n_true = latest.get("n_true", 0)
    positive_ratio = (sum(1 for x in lifts if x > 0) / len(lifts)) if lifts else 0.0

    if n >= 5 and latest_n_true >= 30 and consecutive_positive >= 3:
        confidence = "HIGH"
    elif n >= 3 and latest_n_true >= MIN_SAMPLE_FOR_STATS and positive_ratio >= 0.5:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "n_snapshots": n,
        "latest_lift": latest.get("lift"),
        "latest_n_true": latest_n_true,
        "positive_lift_ratio": round(positive_ratio, 4),
        "consecutive_positive_lift": consecutive_positive,
        "trend": trend,
        "confidence": confidence,
    }


def generate_candidate_improvement_report(fingerprint: Dict[str, Any],
                                           history_path: Path = HISTORY_PATH) -> str:
    history = load_history(fingerprint["name"], fingerprint["direction"], history_path)
    trend = compute_trend(history)
    latest = history[-1] if history else None

    gc = latest["group_concentration"] if latest else {}
    evidence_line = (
        f"Missed winners: {gc.get('REJECTED_WON')}   "
        f"Correct rejects: {gc.get('REJECTED_FAILED')}   "
        f"Selected+won: {gc.get('SELECTED_WON')}   "
        f"Selected+failed: {gc.get('SELECTED_FAILED')}"
        if latest else "No snapshot yet"
    )

    return (
        "SELECTION INTELLIGENCE REPORT\n"
        f"\n{fingerprint['direction']}\n"
        "────────────────────────\n"
        "Current selector:\n"
        "  V3 discovery + C2 opening-gap ranking (unchanged)\n"
        "\n"
        f"Candidate characteristic:\n"
        f"  {fingerprint['label']}\n"
        "\n"
        "Evidence (most recent snapshot, group concentration):\n"
        f"  {evidence_line}\n"
        f"  Latest lift: {trend.get('latest_lift')}   Latest n_true: {trend.get('latest_n_true')}\n"
        "\n"
        "Repeatability:\n"
        f"  Snapshots observed: {trend['n_snapshots']}\n"
        f"  Consecutive positive-lift snapshots: {trend['consecutive_positive_lift']}\n"
        f"  Positive-lift ratio across all snapshots: {trend['positive_lift_ratio']}\n"
        f"  Trend: {trend['trend']}\n"
        "\n"
        f"Confidence: {trend['confidence']}\n"
        "\n"
        "Recommendation: TEST ONLY — DO NOT APPLY\n"
        "  (No change to V3/C2/KDA/DecisionEngine until confidence reaches\n"
        "  HIGH and a formal backtest/OOS validation is run separately.)\n"
    )


def run_tracking_silent(ledger_path=None) -> List[Dict[str, Any]]:
    """Core entry point, no stdout output — safe to embed in the EOD
    orchestrator pipeline. Loads current evidence, appends one snapshot per
    registered fingerprint (idempotent per as-of-date via append_snapshot's
    key check), and returns a summary per fingerprint:
      {fingerprint_name, direction, as_of_date, wrote_new, confidence, trend}
    wrote_new/as_of_date are None/False when no evidence exists yet for
    that fingerprint's direction (nothing to snapshot)."""
    from scripts.knowledge_system.selection_characteristic_analyzer_001 import LEDGER_PATH
    records = load_records(ledger_path or LEDGER_PATH)

    results: List[Dict[str, Any]] = []
    for fingerprint in FINGERPRINT_REGISTRY:
        snapshot = compute_snapshot(records, fingerprint)
        if snapshot is None:
            results.append({
                "fingerprint_name": fingerprint["name"],
                "direction": fingerprint["direction"],
                "as_of_date": None,
                "wrote_new": False,
                "confidence": None,
                "trend": None,
            })
            continue
        wrote_new = append_snapshot(snapshot)
        history = load_history(fingerprint["name"], fingerprint["direction"])
        trend = compute_trend(history)
        results.append({
            "fingerprint_name": fingerprint["name"],
            "direction": fingerprint["direction"],
            "as_of_date": snapshot["as_of_date"],
            "wrote_new": wrote_new,
            "confidence": trend["confidence"],
            "trend": trend["trend"],
        })
    return results


def run_tracking(ledger_path=None) -> List[Dict[str, Any]]:
    """CLI entry point. Same computation/persistence as
    run_tracking_silent(), plus prints each fingerprint's human-readable
    candidate-improvement report. Returns the same summary list."""
    results = run_tracking_silent(ledger_path)
    for fingerprint, result in zip(FINGERPRINT_REGISTRY, results):
        if result["as_of_date"] is None:
            print(f"[{fingerprint['name']}] no data available — skipped")
            continue
        status = "NEW SNAPSHOT" if result["wrote_new"] else "already recorded for this as-of date"
        print(f"[{fingerprint['name']}] as_of={result['as_of_date']} ({status})")
        print(generate_candidate_improvement_report(fingerprint))
        print()
    return results


if __name__ == "__main__":
    run_tracking()
