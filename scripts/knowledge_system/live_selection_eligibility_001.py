"""
scripts/knowledge_system/live_selection_eligibility_001.py
===================================================================
Phase 9 — PASS -> SELECTION_ELIGIBLE: bridges Phase 8's fingerprint-level
CONTROLLED_LIVE_CANDIDATE status into the ACTUAL LIVE candidate-generation
system (opportunity_engine/equity_scanner_ai.py's EquityScannerAI.scan())
as ONE additive, bounded evidence input.

THIS IS THE FIRST MODULE IN THE SELECTION INTELLIGENCE LAYER THAT
ACTUALLY TOUCHES THE LIVE PATH. Read carefully.

WHAT THIS DOES NOT DO:
  - Does NOT select, override, or veto any candidate.
  - Does NOT change risk controls, position sizing, or execution logic.
  - Does NOT bypass decision_engine.decide()'s approval logic.
  - Does NOT compute any NEW live/intraday features. Matching uses the
    MOST RECENT (prior-close) evidence already computed by the existing
    EOD pipeline (final_trading_architecture_shadow_001.py via
    selection_characteristic_analyzer_001.load_records()) — the same
    honest "prior-close screen, looked up intraday" technique used by
    conventional technical screening, not a live recomputation.

WHAT THIS DOES:
  For every fingerprint currently at Phase 8's CONTROLLED_LIVE_CANDIDATE
  status (data/controlled_live_candidates.json), finds which symbols'
  MOST RECENT resolved evidence (prior close) match that fingerprint's
  band-condition pattern, and publishes them to
  data/live_selection_eligibility.json — REBUILT FRESH every EOD run
  (rollback: a fingerprint or symbol that stops matching simply
  disappears from the next day's file; nothing "manually withdraws" it).

  equity_scanner_ai.py reads this file once per scan() call and, for any
  live candidate whose (symbol, direction) appears in it, attaches a
  small, bounded, configurable confidence nudge
  (config.FINGERPRINT_EVIDENCE_BOOST_AMOUNT, default 0.3 on a 0-10 scale)
  plus a full audit annotation on the TradeSignal itself
  (_fingerprint_evidence_boost, _fingerprint_evidence_match) — never
  large enough to single-handedly force approval of an otherwise clearly
  rejected signal; the normal debate/decision/risk/execution chain
  remains fully in control of the final outcome.

AUDIT TRAIL (append-only, never rewritten):
  data/live_selection_eligibility_audit.jsonl — one ELIGIBLE entry per
  (as_of_date, symbol, direction, fingerprint_name) the first time (and
  every subsequent day) a symbol matches, plus one explicit WITHDRAWN
  entry the day a previously-matching (symbol, direction, fingerprint)
  combination stops matching or its fingerprint loses CONTROLLED_LIVE_
  CANDIDATE status — a complete, permanent record of why/when eligible
  and why/when withdrawn.

ELIGIBILITY GATE (confirmed with the user before implementation):
  Gated on Phase 8's CONTROLLED_LIVE_CANDIDATE (PASS + >=10 shadow days
  + >=60% cumulative win-rate + zero FAIL/RETIRED ever) — Phase 8's
  already-built, stricter, more-vetted tier — NOT the bare Phase 7 PASS
  state alone. No intermediate state (PRELIMINARY_PASS, VALIDATED_
  TRACKING, CHALLENGER_ELIGIBLE, SHADOW_TEST, bare PASS) ever reaches
  this module's output.

SCHEDULING: wired into master_orchestrator.py's _do_eod_learning()
(DTA-PHASE9-SELECTION-ELIGIBILITY-001), AFTER Phase 8's live-candidate
check and BEFORE the final _write_eod_status("COMPLETED"). Wrapped in
its own try/except: a failure here is logged and never aborts EOD
learning or any trading path.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.knowledge_system.controlled_live_candidates_001 import load_export
from scripts.knowledge_system.fingerprint_tracker_001 import _latest_trade_date, get_full_registry
from scripts.knowledge_system.selection_characteristic_analyzer_001 import (
    FEATURES,
    _band_of,
    _build_band_thresholds,
    load_records,
)

ROOT = Path(__file__).resolve().parent.parent.parent
ELIGIBILITY_PATH = ROOT / "data" / "live_selection_eligibility.json"
AUDIT_LOG_PATH = ROOT / "data" / "live_selection_eligibility_audit.jsonl"

EVENT_ELIGIBLE = "ELIGIBLE"
EVENT_WITHDRAWN = "WITHDRAWN"


def _find_fingerprint(registry: List[Dict[str, Any]], name: str, direction: str) -> Optional[Dict[str, Any]]:
    for fp in registry:
        if fp["name"] == name and fp["direction"] == direction:
            return fp
    return None


def match_symbols_for_fingerprint(records: List[Dict[str, Any]], fingerprint: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Finds which symbols' MOST RECENT resolved evidence (as of the
    latest available trade_date for this direction) match the
    fingerprint's 'combined' band-condition rule. Thresholds are built
    from ALL PRIOR data (strictly before that date) — no look-ahead,
    same technique as Phase 6's compute_daily_shadow_entry()."""
    direction = fingerprint["direction"]
    dir_records = [r for r in records if r.get("direction") == direction]
    as_of_date = _latest_trade_date(records, direction)
    if as_of_date is None:
        return []

    prior_records = [r for r in dir_records if r.get("trade_date", "") < as_of_date]
    day_records = [r for r in dir_records if r.get("trade_date") == as_of_date]
    if not day_records:
        return []

    thresholds = _build_band_thresholds(prior_records, direction) if prior_records else \
        _build_band_thresholds(dir_records, direction)
    rule = fingerprint["components"]["combined"]

    matches = []
    for r in day_records:
        bands = {feat: _band_of(feat, r[feat], direction, thresholds)
                  for feat in FEATURES if r.get(feat) is not None}
        try:
            if not rule(bands):
                continue
        except KeyError:
            continue
        matches.append({
            "symbol": r.get("symbol"), "direction": direction,
            "fingerprint_name": fingerprint["name"], "as_of_date": as_of_date,
            "reason": f"prior-close evidence as of {as_of_date} matches "
                       f"{fingerprint['label']} (fingerprint status: CONTROLLED_LIVE_CANDIDATE)",
        })
    return matches


def _load_prior_eligible_keys(audit_path: Path = AUDIT_LOG_PATH) -> Dict[tuple, Dict[str, Any]]:
    """Returns the MOST RECENT ELIGIBLE-not-yet-WITHDRAWN entry per
    (symbol, direction, fingerprint_name) key, used to detect withdrawals."""
    if not audit_path.exists():
        return {}
    state: Dict[tuple, Dict[str, Any]] = {}
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = (rec.get("symbol"), rec.get("direction"), rec.get("fingerprint_name"))
        if rec.get("event") == EVENT_ELIGIBLE:
            state[key] = rec
        elif rec.get("event") == EVENT_WITHDRAWN:
            state.pop(key, None)
    return state


def _append_audit_entries(entries: List[Dict[str, Any]], path: Path = AUDIT_LOG_PATH) -> int:
    """Append-only, idempotent per (as_of_date, symbol, direction,
    fingerprint_name, event). Returns count of new lines written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            existing.add((rec.get("as_of_date"), rec.get("symbol"), rec.get("direction"),
                          rec.get("fingerprint_name"), rec.get("event")))
    written = 0
    with open(path, "a", encoding="utf-8") as f:
        for e in entries:
            key = (e["as_of_date"], e["symbol"], e["direction"], e["fingerprint_name"], e["event"])
            if key in existing:
                continue
            f.write(json.dumps(e) + "\n")
            existing.add(key)
            written += 1
    return written


def _write_eligibility_export(entries: List[Dict[str, Any]], path: Path = ELIGIBILITY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def load_eligibility(path: Path = ELIGIBILITY_PATH) -> List[Dict[str, Any]]:
    """Reader used by equity_scanner_ai.py. Never raises — returns []
    on any missing/corrupt file so the live scanner is never blocked."""
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def run_eligibility_check_silent(ledger_path=None) -> Dict[str, Any]:
    """Main entry point, no stdout output — safe to embed in the EOD
    orchestrator pipeline. Rebuilds data/live_selection_eligibility.json
    fresh from the CURRENTLY CONTROLLED_LIVE_CANDIDATE fingerprints, and
    appends ELIGIBLE/WITHDRAWN entries to the permanent audit log."""
    from scripts.knowledge_system.selection_characteristic_analyzer_001 import LEDGER_PATH
    records = load_records(ledger_path or LEDGER_PATH)

    live_candidates = load_export()  # Phase 8's CONTROLLED_LIVE_CANDIDATE fingerprints only
    registry = get_full_registry()

    fresh_matches: List[Dict[str, Any]] = []
    for lc in live_candidates:
        fingerprint = _find_fingerprint(registry, lc["name"], lc["direction"])
        if fingerprint is None:
            continue
        fresh_matches.extend(match_symbols_for_fingerprint(records, fingerprint))

    fresh_keys = {(m["symbol"], m["direction"], m["fingerprint_name"]) for m in fresh_matches}
    prior_eligible = _load_prior_eligible_keys(AUDIT_LOG_PATH)

    audit_entries: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    for m in fresh_matches:
        audit_entries.append({**m, "event": EVENT_ELIGIBLE, "checked_at": now})
    for key in prior_eligible:
        if key not in fresh_keys:
            symbol, direction, fingerprint_name = key
            audit_entries.append({
                "symbol": symbol, "direction": direction, "fingerprint_name": fingerprint_name,
                "as_of_date": fresh_matches[0]["as_of_date"] if fresh_matches else None,
                "event": EVENT_WITHDRAWN, "checked_at": now,
                "reason": "no longer matches CONTROLLED_LIVE_CANDIDATE fingerprint on latest check "
                           "(fingerprint lost eligibility, or symbol's prior-close evidence no longer matches)",
            })

    new_audit_written = _append_audit_entries(audit_entries, AUDIT_LOG_PATH)
    _write_eligibility_export(fresh_matches, ELIGIBILITY_PATH)

    return {
        "n_eligible_fingerprints": len(live_candidates),
        "n_matching_symbols": len(fresh_matches),
        "n_withdrawn": sum(1 for e in audit_entries if e["event"] == EVENT_WITHDRAWN),
        "new_audit_entries_written": new_audit_written,
        "matches": fresh_matches,
    }


def format_eligibility_report(result: Dict[str, Any]) -> str:
    lines = [
        "LIVE SELECTION ELIGIBILITY CHECK (Phase 9 — bounded, additive evidence input)",
        f"  eligible fingerprints (CONTROLLED_LIVE_CANDIDATE): {result['n_eligible_fingerprints']}",
        f"  matching symbols today: {result['n_matching_symbols']}",
        f"  withdrawn since last check: {result['n_withdrawn']}",
    ]
    for m in result["matches"]:
        lines.append(f"    {m['symbol']} ({m['direction']}) via {m['fingerprint_name']} as_of={m['as_of_date']}")
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_eligibility_check_silent()
    print(format_eligibility_report(result))
