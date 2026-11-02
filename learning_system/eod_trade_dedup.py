"""
learning_system/eod_trade_dedup.py
=====================================
DTA-EOD-TRADE-REPROCESS-001 -- root-cause fix for silent evidence
duplication in the daily EOD learning loop.

Root cause (found 2026-11-02, live-verified): TradeMonitor._closed_orders
is never pruned after a trade is processed -- get_closed_trades() returns
the full, ever-growing history of every trade closed since the process
last restarted, and master_orchestrator.py's EOD loop re-feeds that ENTIRE
list into learning_engine.learn(), performance_evaluator/perf_tracker,
regime_map_evidence_log.record_regime_trade(), and sizing_bounds_
refinement_engine.record_sizing_outcome() every single day the process
keeps running, not just the day a trade actually closed.

Some consumers (perf_tracker) already have their own internal order_id
dedup and were not visibly affected. Others (regime_map_evidence_log,
sizing_bounds_refinement_engine) are explicitly documented as "additive-
only observers" with NO dedup of their own -- confirmed live: the same
real trade (CASTROLIND, order_id 221261028295303) was written into
regime_map_evidence_log on 3 separate consecutive days.

Fix: a persisted (restart-safe, same pattern as learning_system/
live_journal_trade_recovery.py's own state file), order_id-keyed "already
fed into EOD learning" set. filter_unprocessed() runs once per EOD cycle,
immediately after `trades` is fully assembled (in-memory + CSV + live-
journal recovery) and before ANY consumer sees it -- protects every
downstream observer in one place rather than requiring each one to
implement its own dedup.
"""
from __future__ import annotations

import json
import os
from typing import Any, List, Set

from utils import get_logger

log = get_logger(__name__)

_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STATE_PATH = os.path.join(_ROOT, "data", "learning_system", "eod_trade_dedup_state.json")
_MAX_TRACKED_IDS = 20_000   # bounded, same floor as live_journal_trade_recovery.py


def _load_processed_ids() -> Set[str]:
    try:
        if os.path.exists(_STATE_PATH):
            with open(_STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            ids = data.get("processed_order_ids", [])
            if isinstance(ids, list):
                return set(ids)
    except Exception as exc:
        log.debug("[EODTradeDedup] state load failed (starting fresh): %s", exc)
    return set()


def _save_processed_ids(ids: Set[str]) -> None:
    try:
        os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
        # Bounded: keep only the most recent MAX_TRACKED_IDS (insertion order
        # isn't tracked here, so on overflow we simply cap via arbitrary trim --
        # acceptable since this guards against re-processing, not audit history).
        trimmed = list(ids)[-_MAX_TRACKED_IDS:] if len(ids) > _MAX_TRACKED_IDS else list(ids)
        tmp_path = _STATE_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump({"processed_order_ids": trimmed}, f)
        os.replace(tmp_path, _STATE_PATH)
    except Exception as exc:
        log.debug("[EODTradeDedup] state save failed (non-fatal): %s", exc)


def filter_unprocessed(trades: List[Any]) -> List[Any]:
    """
    Return only the trades (OrderRecord-like, with .order_id) whose
    order_id has never been fed into EOD learning before. Never raises --
    fails open (returns the original list) on any error, so a dedup-state
    problem can never block real learning from happening.
    """
    try:
        processed = _load_processed_ids()
        if not processed:
            return trades
        skipped = 0
        out = []
        for t in trades:
            oid = getattr(t, "order_id", "") or ""
            if oid and oid in processed:
                skipped += 1
                continue
            out.append(t)
        if skipped:
            log.info("[EODTradeDedup] Skipped %d already-processed trade(s) "
                      "(prevents duplicate evidence/learning updates).", skipped)
        return out
    except Exception as exc:
        log.debug("[EODTradeDedup] filter_unprocessed failed open: %s", exc)
        return trades


def mark_processed(trades: List[Any]) -> None:
    """Record every trade's order_id as fed into EOD learning. Never raises."""
    try:
        oids = {getattr(t, "order_id", "") or "" for t in trades}
        oids.discard("")
        if not oids:
            return
        processed = _load_processed_ids()
        processed.update(oids)
        _save_processed_ids(processed)
    except Exception as exc:
        log.debug("[EODTradeDedup] mark_processed failed (non-fatal): %s", exc)
