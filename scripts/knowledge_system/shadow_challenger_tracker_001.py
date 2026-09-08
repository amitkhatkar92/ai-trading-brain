"""
scripts/knowledge_system/shadow_challenger_tracker_001.py
===================================================================
Phase 6 — Shadow Challenger Tracking (prospective, day-by-day
Champion-vs-Challenger monitoring for CHALLENGER_ELIGIBLE fingerprints).

READ-ONLY, OBSERVATIONAL. Not imported by KDA, DecisionEngine,
StrategyLab, ExecutionEngine, OrderManager, or any live/paper trading
path. Writes only to its own append-only log
(data/shadow_challenger_daily.jsonl). Never modifies V3 discovery, C2
ranking, or any candidate's selected_final_5.

THE QUESTION THIS ANSWERS: once a fingerprint reaches CHALLENGER_ELIGIBLE
(Phase 5's champion_challenger_001.py), how does the system test whether
adding it continues to improve selection — WITHOUT immediately changing
any live decision? Phase 4's validator answers this once, retrospectively,
over a fixed historical OOS window. This module answers it CONTINUOUSLY,
prospectively: every day, for every currently-eligible fingerprint, it
records one more real Champion-vs-Challenger data point (using that day's
actual resolved outcome, the moment it becomes available via the shadow
evidence pipeline) — building a genuine, forward-accumulating shadow
track record, exactly like Phase 2E turned Phase 2A-2D's one-time
analysis into a continuous tracker.

RELATIONSHIP TO PHASE 5 (champion_challenger_001.py): that module was
scoped as "standalone, manually invoked" when built. This module calls
its run_promotion_check() directly as its own first step (so Phase 5's
status is always freshly computed, not stale), which means Phase 5's
logic NOW ALSO executes once per day as a side effect of THIS module
running in the EOD pipeline — Phase 5 itself is still not directly
imported by master_orchestrator.py, and still runs standalone if invoked
manually. This is a deliberate, documented widening of Phase 5's
execution cadence, not a scope change to what it's allowed to touch
(still registry-only, still zero live-path wiring).

WHAT THIS DOES, PER DAY:
  1. Freshly runs Phase 5's promotion check (fresh validation + fresh
     Phase 2E confidence + registry streak).
  2. For every fingerprint whose FRESH status is CHALLENGER_ELIGIBLE:
     compute that single day's (the latest resolved trade_date's)
     Champion-vs-Challenger comparison (reusing Phase 4's
     _split_champion_challenger / _metrics — same logic, one day's
     candidates instead of a whole OOS window).
  3. Persist one shadow-tracking entry (idempotent per
     (fingerprint_name, direction, trade_date)).
  4. Maintain a running CUMULATIVE tally: out of all days tracked since
     eligibility began, how many days did the Challenger's ge2_rate
     meet or beat the Champion's? This is the ongoing prospective
     monitor — if this cumulative win-rate starts falling, that is
     visible immediately on the next check, well before any
     hypothetical future live-wiring decision would ever be considered.

For fingerprints NOT currently CHALLENGER_ELIGIBLE, nothing is recorded
here — Phase 2E/3 already provide their continuous daily observation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.knowledge_system.champion_challenger_001 import (
    STATUS_CHALLENGER_ELIGIBLE,
    run_promotion_check,
)
from scripts.knowledge_system.fingerprint_tracker_001 import _latest_trade_date, get_full_registry
from scripts.knowledge_system.fingerprint_validation_001 import (
    _build_band_thresholds,
    _metrics,
    _split_champion_challenger,
)
from scripts.knowledge_system.selection_characteristic_analyzer_001 import load_records

ROOT = Path(__file__).resolve().parent.parent.parent
SHADOW_PATH = ROOT / "data" / "shadow_challenger_daily.jsonl"


def _load_existing_shadow_keys(path: Path) -> set:
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
        keys.add((rec.get("fingerprint_name"), rec.get("direction"), rec.get("trade_date")))
    return keys


def load_shadow_history(fingerprint_name: str, direction: str,
                         path: Path = SHADOW_PATH) -> List[Dict[str, Any]]:
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
    return sorted(out, key=lambda r: r["trade_date"])


def compute_daily_shadow_entry(records: List[Dict[str, Any]], fingerprint: Dict[str, Any],
                                trade_date: str) -> Optional[Dict[str, Any]]:
    """One day's Champion-vs-Challenger comparison for a single fingerprint.
    Thresholds are computed from ALL history strictly BEFORE trade_date
    (no look-ahead into the very day being scored)."""
    direction = fingerprint["direction"]
    dir_records = [r for r in records if r.get("direction") == direction]
    prior_records = [r for r in dir_records if r.get("trade_date", "") < trade_date]
    day_records = [r for r in dir_records if r.get("trade_date") == trade_date]
    if not day_records:
        return None

    thresholds = _build_band_thresholds(prior_records, direction) if prior_records else \
        _build_band_thresholds(dir_records, direction)

    champion, challenger, added, added_fp = _split_champion_challenger(
        day_records, fingerprint, thresholds
    )
    champion_metrics = _metrics(champion, direction)
    challenger_metrics = _metrics(challenger, direction)

    challenger_at_least_as_good = bool(
        challenger_metrics["ge2_rate"] is not None and champion_metrics["ge2_rate"] is not None
        and challenger_metrics["ge2_rate"] >= champion_metrics["ge2_rate"]
    )

    return {
        "fingerprint_name": fingerprint["name"],
        "direction": direction,
        "trade_date": trade_date,
        "champion": champion_metrics,
        "challenger": challenger_metrics,
        "candidates_added": len(added),
        "false_positives_added": len(added_fp),
        "challenger_at_least_as_good": challenger_at_least_as_good,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def append_shadow_entry(entry: Dict[str, Any], path: Path = SHADOW_PATH) -> bool:
    """Idempotent per (fingerprint_name, direction, trade_date)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    key = (entry["fingerprint_name"], entry["direction"], entry["trade_date"])
    if key in _load_existing_shadow_keys(path):
        return False
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return True


def _cumulative_summary(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(history)
    if n == 0:
        return {"n_days_tracked": 0, "challenger_win_days": 0, "challenger_win_rate": None}
    wins = sum(1 for h in history if h.get("challenger_at_least_as_good"))
    return {
        "n_days_tracked": n,
        "challenger_win_days": wins,
        "challenger_win_rate": round(wins / n, 4),
    }


def run_shadow_tracking_silent(ledger_path=None) -> List[Dict[str, Any]]:
    """Main entry point. Runs Phase 5's promotion check fresh, then for
    every CHALLENGER_ELIGIBLE fingerprint records one more day of shadow
    comparison (idempotent) and returns a per-fingerprint summary
    (including fingerprints skipped because they're not yet eligible)."""
    from scripts.knowledge_system.selection_characteristic_analyzer_001 import LEDGER_PATH
    records = load_records(ledger_path or LEDGER_PATH)

    promotion_entries = run_promotion_check(ledger_path)
    eligibility = {(e["fingerprint_name"], e["direction"]): e["status"] for e in promotion_entries}

    results = []
    for fingerprint in get_full_registry():
        direction = fingerprint["direction"]
        status = eligibility.get((fingerprint["name"], direction))

        if status != STATUS_CHALLENGER_ELIGIBLE:
            results.append({
                "fingerprint_name": fingerprint["name"], "direction": direction,
                "tracked_today": False, "reason": f"status={status}, not CHALLENGER_ELIGIBLE",
            })
            continue

        as_of_date = _latest_trade_date(records, direction)
        if as_of_date is None:
            results.append({
                "fingerprint_name": fingerprint["name"], "direction": direction,
                "tracked_today": False, "reason": "no resolved trade_date available",
            })
            continue

        entry = compute_daily_shadow_entry(records, fingerprint, as_of_date)
        wrote_new = append_shadow_entry(entry) if entry else False

        history = load_shadow_history(fingerprint["name"], direction)
        cumulative = _cumulative_summary(history)

        results.append({
            "fingerprint_name": fingerprint["name"], "direction": direction,
            "tracked_today": True, "trade_date": as_of_date, "wrote_new": wrote_new,
            "cumulative": cumulative,
        })
    return results


def format_shadow_report(results: List[Dict[str, Any]]) -> str:
    lines = ["SHADOW CHALLENGER TRACKING"]
    for r in results:
        if not r.get("tracked_today"):
            lines.append(f"  {r['fingerprint_name']} ({r['direction']}): skipped — {r['reason']}")
            continue
        c = r["cumulative"]
        lines.append(
            f"  {r['fingerprint_name']} ({r['direction']}): trade_date={r['trade_date']}  "
            f"new_entry={r['wrote_new']}  "
            f"cumulative: n_days={c['n_days_tracked']}  "
            f"challenger_win_days={c['challenger_win_days']}  "
            f"challenger_win_rate={c['challenger_win_rate']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    results = run_shadow_tracking_silent()
    print(format_shadow_report(results))
