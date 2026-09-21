"""
tests/test_dta_cancelled_journal_restore_001.py
=================================================
DTA-CANCELLED-JOURNAL-RESTORE-001 — _restore_from_live_journal() must treat
a "CANCELLED" journal event as terminal, same as "CLOSE"/"SESSION_EXPIRED"/
"REJECTED".

Root cause (confirmed live, 2026-09-21): two NIFTYBEES limit orders
(34126091819503, 321260918299703) were correctly OPENed then correctly
CANCELLED by the system's own limit-expiry logic ("limit_expired_8_candles",
never filled, actual_fill_price=0.0) — but `_restore_from_live_journal()`'s
closing-event set was `("CLOSE", "SESSION_EXPIRED", "REJECTED")`, missing
"CANCELLED". Every other place in this same file that scans the same
journal format (paper-trade CSV pass-1 dedup, EARLY_LOSS cooldown restore,
D-003 tracking) already includes "CANCELLED" in its closing-event set —
this one function was the sole omission. Result: on every container
restart, these 2 never-filled, already-cancelled orders were incorrectly
restored as live "open positions" (StalePositionAudit/ConcentrationAudit
reporting them for days), even though the broker (`get_positions()`)
correctly showed nothing.

Fix: added "CANCELLED" to the recognized closing-event tuple.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone


def _restore_with_journal(tmp_path, lines):
    import execution_engine.order_manager as _om
    from execution_engine.order_manager import OrderManager
    from models import Portfolio

    jf = tmp_path / "live_orders.jsonl"
    jf.write_text("\n".join(json.dumps(l) for l in lines) + "\n")

    orig = _om.LIVE_ORDER_LOG
    orig_dir = _om._LIVE_DIR
    try:
        _om.LIVE_ORDER_LOG = str(jf)
        _om._LIVE_DIR = str(tmp_path)
        om = OrderManager.__new__(OrderManager)
        om._paper_mode = False
        om._orders = {}
        om._restore_stats = {"restored_today": 0}
        om._portfolio = Portfolio(capital=100_000)
        om._restore_from_live_journal()
    finally:
        _om.LIVE_ORDER_LOG = orig
        _om._LIVE_DIR = orig_dir
    return om


def _open_row(order_id, symbol="NIFTYBEES", ts=None):
    return {
        "event": "OPEN", "timestamp": ts or datetime.now(timezone.utc).isoformat(),
        "order_id": order_id, "broker_order_id": order_id, "symbol": symbol,
        "direction": "BUY", "quantity": 16, "entry_price": 265.02,
        "stop_loss": 257.56, "target_price": 283.68, "strategy": "Momentum_Retest",
        "opportunity_id": "TEST-OPP-CANCEL", "fill_status": "PENDING",
        "actual_fill_price": 0.0,
    }


def _cancelled_row(order_id, symbol="NIFTYBEES", ts=None):
    row = _open_row(order_id, symbol, ts)
    row["event"] = "CANCELLED"
    row["reason"] = "limit_expired_8_candles"
    return row


class TestCancelledJournalEventExcludedFromRestore:

    def test_cancelled_never_filled_order_not_restored(self, tmp_path):
        """A never-filled limit order OPENed then CANCELLED must NOT come
        back as a live position on restart — reproduces the real NIFTYBEES
        phantom-position bug exactly."""
        om = _restore_with_journal(tmp_path, [
            _open_row("34126091819503"),
            _cancelled_row("34126091819503"),
        ])
        assert "34126091819503" not in om._orders
        assert "NIFTYBEES" not in om._portfolio.positions

    def test_two_sequential_cancelled_retries_neither_restored(self, tmp_path):
        """Reproduces the exact real sequence: OPEN -> CANCELLED (retry 1),
        OPEN -> CANCELLED (retry 2, new order_id) — neither should survive."""
        om = _restore_with_journal(tmp_path, [
            _open_row("34126091819503"),
            _cancelled_row("34126091819503"),
            _open_row("321260918299703"),
            _cancelled_row("321260918299703"),
        ])
        assert "34126091819503" not in om._orders
        assert "321260918299703" not in om._orders
        assert "NIFTYBEES" not in om._portfolio.positions

    def test_genuinely_filled_open_position_still_restored(self, tmp_path):
        """Regression guard: a real, filled, never-closed position must
        still be restored normally (fix must not over-exclude)."""
        row = _open_row("LIVE_REAL_001", symbol="TCS")
        row["fill_status"] = "FILLED"
        row["actual_fill_price"] = 4005.0
        om = _restore_with_journal(tmp_path, [row])
        assert "LIVE_REAL_001" in om._orders
        assert "TCS" in om._portfolio.positions

    def test_close_and_rejected_events_still_excluded_as_before(self, tmp_path):
        """Regression guard: pre-existing CLOSE/REJECTED handling unchanged."""
        close_row = _open_row("CLOSED_001", symbol="INFY")
        om = _restore_with_journal(tmp_path, [
            close_row,
            {**close_row, "event": "CLOSE", "exit_price": 1500.0, "pnl": 50.0,
             "reason": "TARGET_HIT"},
        ])
        assert "CLOSED_001" not in om._orders

        rej_row = _open_row("REJECTED_001", symbol="WIPRO")
        om2 = _restore_with_journal(tmp_path, [
            rej_row,
            {**rej_row, "event": "REJECTED"},
        ])
        assert "REJECTED_001" not in om2._orders
