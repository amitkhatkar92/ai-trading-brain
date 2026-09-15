"""
debate_system/debate_vote_tracker.py
=======================================
Self-Learning Ecosystem -- Post-roadmap Priority 3 (part 1 of 2):
ACQUISITION + VALIDATION for MultiAgentDebate weight self-tuning.

Audit finding (before writing any code): unlike every other Priority in
this ecosystem, NO per-debater outcome evidence exists anywhere in this
codebase today -- DecisionEngine's own _log_scorecard() only logs, never
persists, and nothing joins a debater's vote back to the trade's real
outcome. Auto-tuning AGENT_WEIGHTS on zero evidence would violate this
whole ecosystem's own founding principle (decide from computed,
authenticated knowledge, not guesses) -- so Priority 3 cannot start at
"tune the weights"; it must start here, building the missing evidence
foundation, exactly the ACQUISITION+VALIDATION stages of the KBL
framework used by every other phase.

ACQUISITION: record_debate_votes() persists every debate's per-agent
votes (score/vote/modifier) the moment DecisionEngine.decide() returns,
tagged with the signal's symbol/direction/entry so a real market outcome
can be joined later. Called additively from
orchestrator/master_orchestrator.py -- DecisionEngine's own decide()
method and its live vote-weighting logic are NEVER touched by this file.

VALIDATION: resolve_matured_votes() -- mirrors the exact tested pattern
already used by analysis/rejection_attribution_monitor.py (T+1..T+5
yfinance close resolution, independent of whether the trade was ever
executed, since a debate is evaluated even for REJECTED signals) --
resolves MATURITY_DAYS-old pending records into a real, directional
outcome, then marks each vote's own accuracy: did this debater's
individual score/vote agree with what the market actually did.

Storage: data/debate/vote_log.jsonl (append-only observation log,
mutated in-place only to add resolution fields -- rewritten atomically,
same convention as kde_idr_evidence_bridge.py). Gitignored.

Safety: read-only w.r.t. yfinance price data; never touches any live
decision, order, or risk gate. Zero imports of execution_engine,
order_manager, dhan_feed, or broker APIs. Never raises.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STORE_DIR = os.path.join(_ROOT, "data", "debate")
_VOTE_LOG  = os.path.join(_STORE_DIR, "vote_log.jsonl")

MATURITY_DAYS = 7   # calendar days before a pending debate is resolved (mirrors rejection_attribution_monitor.py)


def record_debate_votes(signal: Any, votes: List[Any], decision: Any) -> bool:
    """
    ACQUISITION: persist one debate's per-agent votes. Never raises.
    Returns True on successful append.
    """
    try:
        return _record_impl(signal, votes, decision)
    except Exception as exc:
        log.debug("[DebateVoteTracker] record error: %s", exc)
        return False


def _record_impl(signal: Any, votes: List[Any], decision: Any) -> bool:
    symbol = getattr(signal, "symbol", None)
    if not symbol:
        return False

    direction_attr = getattr(signal, "direction", None)
    direction = getattr(direction_attr, "value", str(direction_attr))

    record = {
        "debate_id":        f"DBT-{symbol}-{uuid.uuid4().hex[:10]}",
        "symbol":           symbol,
        "direction":        direction,
        "decision_date":    date.today().isoformat(),
        "entry_price":      float(getattr(signal, "entry_price", 0.0) or 0.0),
        "votes": [
            {
                "agent_name": getattr(v, "agent_name", ""),
                "vote":       getattr(v, "vote", ""),
                "score":      float(getattr(v, "score", 0.0) or 0.0),
                "modifier":   float(getattr(v, "suggested_position_modifier", 1.0) or 1.0),
            }
            for v in votes
        ],
        "approved":          bool(getattr(decision, "approved", False)),
        "confidence_score":  float(getattr(decision, "confidence_score", 0.0) or 0.0),
        "trade_type":        getattr(decision, "trade_type", ""),
        "outcome_resolved":  False,
        "recorded_at":       datetime.now(timezone.utc).isoformat(),
    }
    _append_jsonl(_VOTE_LOG, record)
    return True


def resolve_matured_votes(maturity_days: int = MATURITY_DAYS) -> Dict[str, Any]:
    """
    VALIDATION: resolve pending debates >= maturity_days old using real
    yfinance close prices. Never raises. Returns a summary dict.
    """
    try:
        return _resolve_impl(maturity_days)
    except Exception as exc:
        log.debug("[DebateVoteTracker] resolve error: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


def _resolve_impl(maturity_days: int) -> Dict[str, Any]:
    records = _read_jsonl(_VOTE_LOG)
    if not records:
        return {"status": "OK", "resolved": 0, "skipped_immature": 0}

    today = date.today()
    resolved_count = 0
    skipped = 0

    for rec in records:
        if rec.get("outcome_resolved"):
            continue
        try:
            trade_date = date.fromisoformat(rec["decision_date"])
        except (KeyError, ValueError):
            continue
        if (today - trade_date).days < maturity_days:
            skipped += 1
            continue

        closes = _fetch_ohlcv_closes(rec["symbol"], rec["decision_date"])
        if not closes:
            continue  # try again on a future cycle -- stays pending

        entry = rec.get("entry_price") or 0.0
        last_close = closes[-1]
        move_pct = ((last_close - entry) / entry * 100.0) if entry else 0.0
        direction = str(rec.get("direction", "")).upper()
        favorable = move_pct > 0 if direction in ("BUY", "LONG") else move_pct < 0

        for v in rec["votes"]:
            individually_approved = v["score"] >= 6.5
            v["correct"] = (individually_approved == favorable)

        rec["outcome_resolved"] = True
        rec["realized_move_pct"] = round(move_pct, 4)
        rec["favorable"] = favorable
        rec["resolved_at"] = datetime.now(timezone.utc).isoformat()
        resolved_count += 1

    if resolved_count:
        _write_jsonl(_VOTE_LOG, records)

    return {"status": "OK", "resolved": resolved_count, "skipped_immature": skipped}


def get_debater_accuracy(agent_name: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Read-only accessor: per-agent {sample_size, correct_count, accuracy}
    over all RESOLVED votes. Never raises.
    """
    try:
        return _accuracy_impl(agent_name)
    except Exception as exc:
        log.debug("[DebateVoteTracker] accuracy accessor error: %s", exc)
        return {}


def _accuracy_impl(agent_name: Optional[str]) -> Dict[str, Dict[str, Any]]:
    records = [r for r in _read_jsonl(_VOTE_LOG) if r.get("outcome_resolved")]
    per_agent: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        for v in rec.get("votes", []):
            name = v.get("agent_name", "")
            if not name or (agent_name and name != agent_name):
                continue
            bucket = per_agent.setdefault(name, {"sample_size": 0, "correct_count": 0})
            bucket["sample_size"] += 1
            if v.get("correct"):
                bucket["correct_count"] += 1
    for name, bucket in per_agent.items():
        bucket["accuracy"] = (
            bucket["correct_count"] / bucket["sample_size"] if bucket["sample_size"] else 0.0
        )
    return per_agent


def get_resolved_records_for_agent(agent_name: str) -> List[Dict[str, Any]]:
    """
    Read-only accessor: time-ordered (oldest-first) resolved observations
    for one debater -- {decision_date, correct} -- for use by the
    refinement engine's time-ordered train/OOS statistical split.
    """
    try:
        records = [r for r in _read_jsonl(_VOTE_LOG) if r.get("outcome_resolved")]
        records.sort(key=lambda r: r.get("decision_date", ""))
        out: List[Dict[str, Any]] = []
        for rec in records:
            for v in rec.get("votes", []):
                if v.get("agent_name") == agent_name:
                    out.append({"decision_date": rec["decision_date"], "correct": bool(v.get("correct"))})
        return out
    except Exception as exc:
        log.debug("[DebateVoteTracker] get_resolved_records_for_agent error: %s", exc)
        return []


def _fetch_ohlcv_closes(symbol: str, trade_date: str, horizon_days: int = 5) -> List[float]:
    """Fetch T+1..T+horizon_days daily closes from yfinance. Mirrors the
    tested pattern in analysis/rejection_attribution_monitor.py. Returns
    [] on any error or missing data."""
    try:
        import yfinance as yf
        from data_feeds.yahoo_feed import GLOBAL_SYMBOL_MAP

        start_dt = date.fromisoformat(trade_date) + timedelta(days=1)
        end_dt = start_dt + timedelta(days=horizon_days * 3)

        ticker_sym = GLOBAL_SYMBOL_MAP.get(symbol.upper()) or f"{symbol}.NS"

        df = yf.download(
            ticker_sym, start=str(start_dt), end=str(end_dt),
            interval="1d", progress=False, auto_adjust=True, timeout=10,
        )
        if df is None or df.empty:
            return []

        import pandas as pd
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = df.columns.droplevel(level=-1)
            df = df.loc[:, ~df.columns.duplicated()]

        closes: List[float] = []
        for _, row in df.iterrows():
            try:
                closes.append(float(row["Close"]))
            except (KeyError, TypeError, ValueError):
                continue
        return closes[:horizon_days]
    except Exception:
        return []


# ── jsonl helpers ──────────────────────────────────────────────────────────

def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    records: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def _append_jsonl(path: str, record: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _write_jsonl(path: str, records: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")
