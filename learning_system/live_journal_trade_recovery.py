"""
learning_system/live_journal_trade_recovery.py
=================================================
DTA-EOD-LIVE-JOURNAL-RECOVERY-001 (root cause)

TradeMonitor._closed_orders is in-memory only -- no persistence, no
restart recovery. Any trade that closes and then the container restarts
BEFORE that day's EOD learning cycle consumes it is permanently lost
from learning evidence (StrategyPerformanceTracker, RegimeStrategyMap,
sizing-bounds evidence, etc). master_orchestrator.py's _do_eod_learning()
already has a recovery block for exactly this scenario -- but it only
reads data/paper_trades.csv (the PAPER-mode journal) and only for TODAY's
date. In LIVE mode (this account's real state since 2026-09-14), real
closes are written to data/live/live_orders.jsonl instead, so that
existing safety net silently recovers nothing for live trades.

Confirmed live (2026-10-27): StrategyPerformanceTracker showed only 12 of
~40 real closed trades reaching evidence over 30 days of live trading --
consistent with the many container restarts this session (every code
deploy restarts both containers) each silently dropping any trades closed
since the last successful EOD run.

This module adds the missing counterpart: recovers CLOSE events from the
REAL live journal, for ANY previously-missed date (not just today), using
a persisted processed-order-id set so repeated EOD runs never double-
count. Mirrors the exact same reason/classification rules already used
by the existing (paper-only) CSV recovery block in master_orchestrator.py.

Safety contract: read-only w.r.t. live_orders.jsonl (never writes to it).
Never raises -- any internal error returns an empty list, matching the
existing CSV-recovery block's own fail-open behaviour.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, List, Set

from utils import get_logger

log = get_logger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LIVE_JOURNAL_PATH = os.path.join(_ROOT, "data", "live", "live_orders.jsonl")
_STATE_PATH = os.path.join(_ROOT, "data", "learning_system", "live_journal_recovery_state.json")

# Mirrors the exact classification rules already established in
# master_orchestrator.py's _do_eod_learning() CSV-recovery block.
_SKIP_REASONS = {
    "REPLACEMENT", "emergency_close", "close_emergency", "ORPHAN_CLOSE",
    "EOD_CLOSE", "SYSTEM_CLEANUP", "SESSION_EXPIRED_DEEP_ORPHAN",
    "PAPER_MODE_ARTIFACT",
}
_SESSION_EXPIRED_REASONS = {"SESSION_EXPIRED", "SESSION_EXPIRED_EXTENDED"}

# Bounds unbounded growth of the persisted processed-id set over time.
_MAX_TRACKED_IDS = 20_000


def _load_processed_ids() -> Set[str]:
    if not os.path.exists(_STATE_PATH):
        return set()
    try:
        with open(_STATE_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return set(data.get("processed_order_ids", []))
    except Exception as exc:
        log.warning("[LiveJournalRecovery] state load failed: %s", exc)
        return set()


def _save_processed_ids(ids: Set[str]) -> None:
    try:
        os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
        trimmed = list(ids)[-_MAX_TRACKED_IDS:]
        with open(_STATE_PATH, "w", encoding="utf-8") as fh:
            json.dump({"processed_order_ids": trimmed}, fh)
    except Exception as exc:
        log.warning("[LiveJournalRecovery] state save failed: %s", exc)


def recover_missed_closed_trades(already_seen_order_ids: Set[str]) -> List[Any]:
    """
    Returns OrderRecord-like objects for real CLOSE events in
    data/live/live_orders.jsonl not in `already_seen_order_ids` (this
    run's in-memory trades) and not already recorded by a previous EOD
    run (persisted set). Never raises -- returns [] on any error.
    """
    try:
        return _recover_impl(already_seen_order_ids)
    except Exception as exc:
        log.warning("[LiveJournalRecovery] recovery error (non-critical): %s", exc)
        return []


def _recover_impl(already_seen_order_ids: Set[str]) -> List[Any]:
    if not os.path.exists(_LIVE_JOURNAL_PATH):
        return []

    from execution_engine.order_manager import OrderRecord

    processed = _load_processed_ids()
    recovered: List[Any] = []
    newly_processed: Set[str] = set()

    with open(_LIVE_JOURNAL_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("event") != "CLOSE":
                continue
            oid = str(row.get("order_id", "")).strip()
            if not oid or oid in already_seen_order_ids or oid in processed:
                continue
            reason = str(row.get("reason", ""))
            if reason in _SKIP_REASONS:
                continue

            try:
                pnl = float(row.get("pnl"))
            except (TypeError, ValueError):
                continue

            if reason in _SESSION_EXPIRED_REASONS and pnl == 0.0:
                continue   # synthetic zero-pnl exit, no signal value

            try:
                entry = float(row.get("entry_price", 0) or 0)
                qty = int(float(row.get("quantity", 1) or 1))
                sl = float(row.get("stop_loss", 0) or 0)
                r_risk = abs(entry - sl) if sl else 1.0
                r_mult = pnl / (r_risk * qty) if r_risk * qty else 0.0

                rec = OrderRecord(
                    order_id=oid,
                    symbol=str(row.get("symbol", "")),
                    direction=str(row.get("direction", "BUY")),
                    quantity=qty,
                    entry_price=entry,
                    stop_loss=sl,
                    target=float(row.get("target_price", 0) or 0),
                    strategy=str(row.get("strategy", "")),
                    status="closed",
                    order_type="MARKET",
                    placed_at=datetime.now(),
                )
                rec.pnl = pnl
                rec.r_multiple = r_mult
            except Exception as row_exc:
                log.debug("[LiveJournalRecovery] skipping malformed row %s: %s", oid, row_exc)
                continue

            recovered.append(rec)
            newly_processed.add(oid)
            log.info(
                "[LiveJournalRecovery] Recovered missed live-journal CLOSE: "
                "%s %s pnl=Rs%+.0f reason=%s",
                oid, row.get("symbol", ""), pnl, reason,
            )

    if newly_processed:
        _save_processed_ids(processed | newly_processed)

    return recovered
