"""
data_feeds/options_health_history.py
========================================
Item #10: Options Health Metrics Dashboard (postponed_improvements.md,
flagged 2026-05-15, "meaningful now that options are LIVE").

Surfaces key options-chain quality metrics (freshness, strike
completeness, OI coverage, PCR plausibility) that already exist in
DataFeedManager's own per-cycle chain-fetch state
(get_options_chain_state_snapshot(), additive accessor) -- no new live
fetch is ever triggered by this module, it only reads what the real
options scan already fetched.

PREREQUISITE GATE (per the item's own explicit design)
----------------------------------------------------------
"Prerequisite: At least 1 week of stable LIVE options data to know what
'normal' looks like." This module is therefore evidence-gated exactly
like every other self-learning/observability module built this session:
MIN_HISTORY_DAYS=7. Below that, get_options_health_status() reports
WAITING_FOR_EVIDENCE and computes nothing else -- never fabricates a
"normal" baseline from too little data.

Persists one snapshot per real trading day per symbol to
data/data_feeds/options_health_history.jsonl (gitignored), guarded to
run at most once per calendar date.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR    = os.path.join(_ROOT, "data", "data_feeds")
_HISTORY_PATH = os.path.join(_STORE_DIR, "options_health_history.jsonl")
_STATE_PATH   = os.path.join(_STORE_DIR, "options_health_snapshot_state.json")

TRACKED_SYMBOLS   = ("NIFTY", "BANKNIFTY")
MIN_HISTORY_DAYS  = 7
# Plausible PCR range per postponed_improvements.md's own stated expectation
PLAUSIBLE_PCR_MIN = 0.5
PLAUSIBLE_PCR_MAX = 2.0


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


def _snapshot_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    try:
        from data_feeds import get_feed_manager
        state = get_feed_manager().get_options_chain_state_snapshot(symbol)
        chain = state.get("chain")
        if chain is None:
            return None
        contracts = getattr(chain, "contracts", []) or []
        strike_count = len(contracts)
        with_oi = sum(1 for c in contracts if (getattr(c, "open_interest", 0) or 0) > 0)
        oi_coverage_pct = round(with_oi / strike_count * 100, 1) if strike_count else 0.0
        fetched_at = state.get("fetched_at")
        age_minutes = (
            round((datetime.now() - fetched_at).total_seconds() / 60, 1)
            if fetched_at else None
        )
        pcr = getattr(chain, "pcr", None)
        pcr_plausible = (
            PLAUSIBLE_PCR_MIN <= pcr <= PLAUSIBLE_PCR_MAX
            if isinstance(pcr, (int, float)) else None
        )
        return {
            "symbol": symbol,
            "source": state.get("source"),
            "is_live": state.get("is_live", False),
            "age_minutes": age_minutes,
            "strike_count": strike_count,
            "oi_coverage_pct": oi_coverage_pct,
            "pcr": pcr,
            "pcr_plausible": pcr_plausible,
        }
    except Exception as exc:
        log.debug("[OptionsHealthHistory] snapshot failed for %s: %s", symbol, exc)
        return None


def record_daily_options_health_snapshot(trade_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Snapshot each tracked symbol's current options-chain quality metrics.
    Guarded to run at most once per calendar date. Never raises.
    """
    try:
        return _run_impl(trade_date or date.today().isoformat())
    except Exception as exc:
        log.debug("[OptionsHealthHistory] daily snapshot error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _run_impl(trade_date: str) -> Dict[str, Any]:
    state = _read_json(_STATE_PATH, {})
    if state.get("last_snapshot_date") == trade_date:
        return {"status": "OK", "trade_date": trade_date, "recorded": 0, "skipped": "already_recorded_today"}

    recorded = 0
    os.makedirs(_STORE_DIR, exist_ok=True)
    with open(_HISTORY_PATH, "a", encoding="utf-8") as f:
        for symbol in TRACKED_SYMBOLS:
            snap = _snapshot_symbol(symbol)
            if snap is None:
                continue
            record = {"date": trade_date, "timestamp": datetime.now(timezone.utc).isoformat(), **snap}
            f.write(json.dumps(record, default=str) + "\n")
            recorded += 1

    _write_json(_STATE_PATH, {"last_snapshot_date": trade_date})
    return {"status": "OK", "trade_date": trade_date, "recorded": recorded}


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


def get_options_health_status(symbol: str = "NIFTY") -> Dict[str, Any]:
    """
    Read-only accessor. Reports WAITING_FOR_EVIDENCE below MIN_HISTORY_DAYS
    of persisted history (per this item's own explicit prerequisite) --
    never fabricates a "normal" baseline from too little data. Never raises.
    """
    try:
        days = get_history_days_count()
        if days < MIN_HISTORY_DAYS:
            return {
                "status": "WAITING_FOR_EVIDENCE", "symbol": symbol,
                "history_days_count": days, "min_history_days": MIN_HISTORY_DAYS,
            }
        recs = get_records(symbol=symbol)
        if not recs:
            return {"status": "WAITING_FOR_EVIDENCE", "symbol": symbol,
                     "history_days_count": days, "min_history_days": MIN_HISTORY_DAYS}
        strike_counts = [r["strike_count"] for r in recs if r.get("strike_count") is not None]
        oi_coverages  = [r["oi_coverage_pct"] for r in recs if r.get("oi_coverage_pct") is not None]
        ages          = [r["age_minutes"] for r in recs if r.get("age_minutes") is not None]
        pcr_implausible = sum(1 for r in recs if r.get("pcr_plausible") is False)
        return {
            "status": "ACTIVE", "symbol": symbol,
            "history_days_count": days, "samples": len(recs),
            "avg_strike_count": round(sum(strike_counts) / len(strike_counts), 1) if strike_counts else None,
            "avg_oi_coverage_pct": round(sum(oi_coverages) / len(oi_coverages), 1) if oi_coverages else None,
            "avg_freshness_minutes": round(sum(ages) / len(ages), 1) if ages else None,
            "pcr_implausible_count": pcr_implausible,
        }
    except Exception as exc:
        log.debug("[OptionsHealthHistory] status error: %s", exc)
        return {"status": "WAITING_FOR_EVIDENCE", "symbol": symbol, "error": str(exc)}
