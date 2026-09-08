"""
scripts/knowledge_system/selection_intelligence_001.py
===================================================================
Phase 3 — Live Selection Intelligence (Daily Missed-Winner Candidate
Report).

READ-ONLY, OBSERVATIONAL. Not imported by KDA, DecisionEngine,
StrategyLab, ExecutionEngine, OrderManager, or any live/paper trading
path. Writes only to its own append-only log
(data/selection_intelligence_daily.jsonl). Never modifies V3 discovery,
C2 ranking, or selected_final_5 in any way — it only re-labels each
candidate the shadow system already recorded.

SCOPE DECISION (explicitly confirmed with the user before implementation):
  - Output does NOT feed KDA/DecisionEngine's candidate stream. It is a
    separate, parallel report. Per the user's own standing rule
    ("a discovered characteristic must not influence live selection
    until it clears research/validation/OOS"), this fingerprint (LOW
    confidence, ~30 days evidence) has not cleared that bar.
  - Scoring runs against the EOD/shadow system's daily pool (same
    timing as Phase 2E's fingerprint tracker), NOT the live real-time
    morning V3 discovery cycle. This means it is necessarily
    RETROSPECTIVE: by the time it runs, that day's move has already
    happened and the outcome is already resolved. It does NOT flag
    "tomorrow's" candidates before their move — it builds a same-day
    -lag track record of what a registered fingerprint would have
    caught, which is the evidence-accumulation step that would need to
    exist before any future real-time (pre-move) wiring could even be
    considered.

CLASSIFICATION (per candidate, per registered fingerprint):
  CONFIRMED_MATCH          selected_final_5=True,  fingerprint matches
  SELECTED_NO_MATCH        selected_final_5=True,  fingerprint doesn't match
  MISSED_WINNER_CANDIDATE  selected_final_5=False, fingerprint matches
                           (the valuable tag — a stock V3/C2 rejected
                           that resembles the learned strong-mover
                           fingerprint)
  REJECTED_NO_MATCH        selected_final_5=False, fingerprint doesn't match

Fingerprint definitions are NOT hard-coded here — they are read from
fingerprint_tracker_001.FINGERPRINT_REGISTRY (the same registry Phase 2E
uses), so this stays fully data-driven: if the registry only has a UP
fingerprint, DOWN is simply not scored yet (no forced symmetry), and if
a fingerprint's confidence later falls or a new one is added, this
module picks that up automatically with no code change.

Idempotent per (trade_date, symbol, direction, fingerprint_name) — safe
to re-run on the same day's data without creating duplicate records.

SCHEDULING: connected to orchestrator/master_orchestrator.py's
_do_eod_learning() (DTA-PHASE3-SELECTION-INTEL-001), immediately after
Phase 2E's fingerprint tracker block. Wrapped in its own try/except: a
failure here is logged and never aborts EOD learning or any trading path.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.knowledge_system.fingerprint_tracker_001 import (
    HISTORY_PATH,
    _latest_trade_date,
    compute_trend,
    get_full_registry,
    load_history,
)
from scripts.knowledge_system.selection_characteristic_analyzer_001 import (
    FEATURES,
    GE2_THRESHOLD,
    _band_of,
    _build_band_thresholds,
    _direction_correct,
    load_records,
)

ROOT = Path(__file__).resolve().parent.parent.parent
INTEL_PATH = ROOT / "data" / "selection_intelligence_daily.jsonl"

CLASS_CONFIRMED_MATCH = "CONFIRMED_MATCH"
CLASS_SELECTED_NO_MATCH = "SELECTED_NO_MATCH"
CLASS_MISSED_WINNER_CANDIDATE = "MISSED_WINNER_CANDIDATE"
CLASS_REJECTED_NO_MATCH = "REJECTED_NO_MATCH"


def classify_candidate(rec: Dict[str, Any], matches: bool) -> str:
    selected = bool(rec.get("selected_final_5", False))
    if selected:
        return CLASS_CONFIRMED_MATCH if matches else CLASS_SELECTED_NO_MATCH
    return CLASS_MISSED_WINNER_CANDIDATE if matches else CLASS_REJECTED_NO_MATCH


def score_date_for_fingerprint(records: List[Dict[str, Any]], fingerprint: Dict[str, Any],
                                trade_date: str) -> List[Dict[str, Any]]:
    """Classify every candidate on `trade_date` for one direction against
    one fingerprint. Band thresholds are computed from the FULL historical
    population for that direction (not just this one day) so classification
    stays stable day-to-day rather than re-defining "high/low" every run."""
    direction = fingerprint["direction"]
    dir_records = [r for r in records if r.get("direction") == direction]
    thresholds = _build_band_thresholds(dir_records, direction)
    rule = fingerprint["components"]["combined"]

    day_records = [r for r in dir_records if r.get("trade_date") == trade_date]
    results: List[Dict[str, Any]] = []
    for r in day_records:
        bands = {feat: _band_of(feat, r[feat], direction, thresholds)
                  for feat in FEATURES if r.get(feat) is not None}
        try:
            matches = bool(rule(bands))
        except KeyError:
            matches = False

        t1 = r.get("t1_ret_pct")
        direction_correct = _direction_correct(direction, t1) if t1 is not None else None
        meaningful = bool(direction_correct and t1 is not None and abs(t1) >= GE2_THRESHOLD)

        results.append({
            "trade_date": trade_date,
            "symbol": r.get("symbol"),
            "direction": direction,
            "fingerprint_name": fingerprint["name"],
            "selected_final_5": bool(r.get("selected_final_5", False)),
            "classification": classify_candidate(r, matches),
            "regime": r.get("regime"),
            "t1_ret_pct": t1,
            "direction_correct": direction_correct,
            "meaningful_move": meaningful,
        })
    return results


def _load_existing_intel_keys(path: Path) -> set:
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
        keys.add((rec.get("trade_date"), rec.get("symbol"), rec.get("direction"),
                   rec.get("fingerprint_name")))
    return keys


def append_intelligence_records(records_to_write: List[Dict[str, Any]],
                                 path: Path = INTEL_PATH) -> int:
    """Append-only, idempotent per (trade_date, symbol, direction,
    fingerprint_name). Returns count of genuinely new records written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_keys = _load_existing_intel_keys(path)
    written = 0
    with open(path, "a", encoding="utf-8") as f:
        for rec in records_to_write:
            key = (rec["trade_date"], rec["symbol"], rec["direction"], rec["fingerprint_name"])
            if key in existing_keys:
                continue
            f.write(json.dumps(rec) + "\n")
            existing_keys.add(key)
            written += 1
    return written


def run_daily_scoring_silent(ledger_path=None) -> Dict[str, Any]:
    """Core entry point, no stdout output — safe to embed in the EOD
    orchestrator pipeline. For each registered fingerprint, scores the
    latest available trade_date's full candidate pool, persists
    idempotently, and returns a summary:
      {fingerprints_scored, per_fingerprint: [...], total_missed_winner_candidates,
       total_new_records_written}
    """
    from scripts.knowledge_system.selection_characteristic_analyzer_001 import LEDGER_PATH
    records = load_records(ledger_path or LEDGER_PATH)

    per_fingerprint: List[Dict[str, Any]] = []
    total_missed = 0
    total_new = 0

    for fingerprint in get_full_registry():
        direction = fingerprint["direction"]
        as_of_date = _latest_trade_date(records, direction)
        if as_of_date is None:
            per_fingerprint.append({
                "fingerprint_name": fingerprint["name"], "direction": direction,
                "as_of_date": None, "n_candidates": 0, "missed_winner_candidates": 0,
                "new_records_written": 0, "confidence": None,
            })
            continue

        day_results = score_date_for_fingerprint(records, fingerprint, as_of_date)
        new_written = append_intelligence_records(day_results)
        missed = sum(1 for r in day_results if r["classification"] == CLASS_MISSED_WINNER_CANDIDATE)

        history = load_history(fingerprint["name"], direction, HISTORY_PATH)
        trend = compute_trend(history)

        per_fingerprint.append({
            "fingerprint_name": fingerprint["name"],
            "direction": direction,
            "as_of_date": as_of_date,
            "n_candidates": len(day_results),
            "missed_winner_candidates": missed,
            "new_records_written": new_written,
            "confidence": trend["confidence"],
        })
        total_missed += missed
        total_new += new_written

    return {
        "fingerprints_scored": len(per_fingerprint),
        "per_fingerprint": per_fingerprint,
        "total_missed_winner_candidates": total_missed,
        "total_new_records_written": total_new,
    }


def format_missed_winner_report(records_to_write: List[Dict[str, Any]], fingerprint: Dict[str, Any],
                                 confidence: Optional[str]) -> str:
    """Human-readable listing of MISSED_WINNER_CANDIDATE entries for one
    fingerprint/day, in the style the user specified: symbol, V3/C2
    status, fingerprint, classification, and the actual (already-known,
    retrospective) outcome."""
    missed = [r for r in records_to_write if r["classification"] == CLASS_MISSED_WINNER_CANDIDATE]
    lines = [
        f"[{fingerprint['label']}]  confidence={confidence}  "
        f"missed_winner_candidates={len(missed)}",
    ]
    for r in missed:
        lines.append(
            f"  {r['symbol']:12s} direction={r['direction']}  "
            f"V3/C2 status=Rejected  classification=MISSED_WINNER_CANDIDATE  "
            f"regime={r['regime']}  actual_t1_ret_pct={r['t1_ret_pct']}  "
            f"direction_correct={r['direction_correct']}  meaningful_move={r['meaningful_move']}"
        )
    return "\n".join(lines)


def run_daily_scoring(ledger_path=None) -> Dict[str, Any]:
    """CLI entry point. Same computation/persistence as
    run_daily_scoring_silent(), plus prints a human-readable report per
    fingerprint highlighting MISSED_WINNER_CANDIDATE entries."""
    from scripts.knowledge_system.selection_characteristic_analyzer_001 import LEDGER_PATH
    records = load_records(ledger_path or LEDGER_PATH)

    summary = run_daily_scoring_silent(ledger_path)
    for fp_summary in summary["per_fingerprint"]:
        fingerprint = next(
            f for f in get_full_registry() if f["name"] == fp_summary["fingerprint_name"]
        )
        if fp_summary["as_of_date"] is None:
            print(f"[{fingerprint['name']}] no data available — skipped")
            continue
        day_results = score_date_for_fingerprint(records, fingerprint, fp_summary["as_of_date"])
        print(f"=== {fingerprint['direction']}  as_of={fp_summary['as_of_date']} "
              f"n_candidates={fp_summary['n_candidates']} "
              f"new_records={fp_summary['new_records_written']} ===")
        print(format_missed_winner_report(day_results, fingerprint, fp_summary["confidence"]))
        print()

    return summary


if __name__ == "__main__":
    run_daily_scoring()
