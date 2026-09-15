"""
data_feeds/trust_score_history.py
====================================
Self-learning module #26 (part 1 of 2): ACQUISITION for trust-weighted
candidate ranking.

Root-cause: DataIntegrityTracker (data_feeds/data_integrity_tracker.py)
is deliberately session-scoped (resets at midnight -- correct for
"today's data quality"), so its trust scores are meaningless as a
multi-day reliability signal on their own -- postponed_improvements.md's
own explicit architectural prerequisite for "Trust-Weighted Candidate
Ranking" was: "Persist DataIntegrityTracker state to disk... otherwise
trust scores are meaningless over multi-day horizon."

This module is the persistence fix: once per real trading day (EOD), it
snapshots every symbol's CURRENT (today's, in-memory) trust score into
an isolated, append-only, gitignored JSONL history
(data/data_integrity/trust_score_history.jsonl) that survives container
restarts. DataIntegrityTracker itself is never modified beyond the one
small additive read-only accessor already added
(get_all_tracked_symbols_today()) -- its own reset-at-midnight behavior
is completely untouched.

Consumed by opportunity_engine/trust_weighted_ranking_engine.py
(SYNTHESIS+GOVERNANCE) -- never read back into any decision by this
module itself.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT          = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR     = os.path.join(_ROOT, "data", "data_integrity")
_HISTORY_PATH  = os.path.join(_STORE_DIR, "trust_score_history.jsonl")
_STATE_PATH    = os.path.join(_STORE_DIR, "snapshot_state.json")


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


def record_daily_trust_snapshot(trade_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Snapshot every symbol's current (today's) trust score to persisted
    history. Guarded to run at most once per calendar date (safe against
    a same-day re-trigger). Never raises.
    """
    try:
        return _run_impl(trade_date or date.today().isoformat())
    except Exception as exc:
        log.debug("[TrustScoreHistory] snapshot error (non-critical): %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl(trade_date: str) -> Dict[str, Any]:
    state = _read_json(_STATE_PATH, {})
    if state.get("last_snapshot_date") == trade_date:
        return {"status": "OK", "trade_date": trade_date, "symbols_recorded": 0, "skipped": "already_recorded_today"}

    from data_feeds.data_integrity_tracker import get_data_integrity_tracker
    tracker = get_data_integrity_tracker()
    symbols = tracker.get_all_tracked_symbols_today()

    n = 0
    if symbols:
        os.makedirs(_STORE_DIR, exist_ok=True)
        with open(_HISTORY_PATH, "a", encoding="utf-8") as f:
            for symbol in sorted(symbols):
                record = {
                    "date": trade_date,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "symbol": symbol,
                    "trust_score": tracker.get_trust_score(symbol),
                }
                f.write(json.dumps(record, default=str) + "\n")
                n += 1

    _write_json(_STATE_PATH, {"last_snapshot_date": trade_date})
    return {"status": "OK", "trade_date": trade_date, "symbols_recorded": n}


def get_records(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read-only accessor: time-ordered (oldest-first) persisted snapshots."""
    if not os.path.exists(_HISTORY_PATH):
        return []
    out: List[Dict[str, Any]] = []
    try:
        with open(_HISTORY_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if symbol is not None and rec.get("symbol") != symbol:
                    continue
                out.append(rec)
    except OSError:
        return []
    return out


def get_history_days_count() -> int:
    """Read-only accessor: distinct calendar dates with a persisted snapshot."""
    return len({r["date"] for r in get_records() if "date" in r})


def get_multi_day_trust_score(symbol: str, window_days: int = 5) -> Optional[float]:
    """
    Read-only accessor: average persisted trust score for *symbol* over
    the most recent *window_days* distinct snapshot dates. Returns None
    if fewer than window_days of history exist for this symbol (correctly
    gated -- caller must fall back to a neutral score).
    """
    recs = get_records(symbol=symbol)
    if not recs:
        return None
    by_date: Dict[str, float] = {}
    for r in recs:
        d = r.get("date")
        if d:
            by_date[d] = r.get("trust_score", 1.0)
    if len(by_date) < window_days:
        return None
    recent_dates = sorted(by_date.keys())[-window_days:]
    scores = [by_date[d] for d in recent_dates]
    return sum(scores) / len(scores)
