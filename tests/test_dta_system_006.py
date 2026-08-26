"""
DTA-SYSTEM-006 — Production Readiness Audit Test Suite
=======================================================
Tests that verify every confirmed defect from the DTA-006 read-only audit.

Coverage map:
  T001-T015  D-001  close_position exit-order failure handling
  T016-T025  D-002  EARLY_LOSS cooldown restored from live journal on restart
  T026-T035  D-003  RiskGuardian corrupt state file → quarantine + halt
  T036-T045  D-004  LOL bridge UTC vs IST timestamp comparison
  T046-T050  D-005  scheduler_health uses UTC timestamps
  T051-T060  D-006  AET pending slot startup log
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch, MagicMock, PropertyMock

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_order_rec(**kwargs):
    """Build a minimal OrderRecord-like dict for journal manipulation."""
    defaults = {
        "order_id": "ORD_TEST_001",
        "broker_order_id": "BRK001",
        "symbol": "RELIANCE",
        "direction": "BUY",
        "quantity": 10,
        "entry_price": 2800.0,
        "stop_loss": 2760.0,
        "target_price": 2880.0,
        "strategy": "TEST_STRATEGY",
        "fill_status": "FILLED",
        "actual_fill_price": 2800.0,
        "opportunity_id": "opp-001",
    }
    defaults.update(kwargs)
    return defaults


# ─────────────────────────────────────────────────────────────────────────────
# D-001  close_position exit-order failure handling (T001-T015)
# ─────────────────────────────────────────────────────────────────────────────

class TestD001ExitOrderFailure:
    """D-001: close_position must NOT mark position closed when broker returns None."""

    def _make_om(self, paper_mode: bool = False):
        """Return a minimal OrderManager instance with _paper_mode forced."""
        import importlib
        import execution_engine.order_manager as om_mod
        importlib.reload(om_mod)
        from execution_engine.order_manager import OrderManager, OrderRecord
        # Build a bare instance without running __init__
        om = OrderManager.__new__(OrderManager)
        om._paper_mode = paper_mode
        om._orders = {}
        om._portfolio = MagicMock()
        om._portfolio.positions = {}
        om._broker = None
        om._reentry_slots = {}
        om._aet_pending = {}
        om._ltp_stale_at = {}
        om._journal_lock = threading.Lock()
        om._restore_stats = {"restored_today": 0}
        om._trade_monitor = None
        return om, OrderRecord

    def _make_open_rec(self, OrderRecord, symbol="RELIANCE"):
        from execution_engine.order_manager import OrderRecord as OR
        rec = OR(
            order_id="ORD_CLOSE_001",
            broker_order_id="BRK001",
            symbol=symbol,
            direction="BUY",
            quantity=10,
            entry_price=2800.0,
            stop_loss=2760.0,
            target=2880.0,
            strategy="TEST",
        )
        rec.status = "open"
        rec.initial_stop_loss = 2760.0
        rec.actual_fill_price = 2800.0
        return rec

    # T001: In paper mode, None broker return still allows close (paper always succeeds)
    def test_T001_paper_mode_nil_broker_place_still_closes(self):
        om, OrderRecord = self._make_om(paper_mode=True)
        rec = self._make_open_rec(OrderRecord)
        om._orders["ORD_CLOSE_001"] = rec
        with (
            patch.object(om, "_broker_place", return_value=None),
            patch.object(om, "_append_live_journal"),
            patch.object(om, "_journal_write_close"),
            patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError),
        ):
            result = om.close_position("ORD_CLOSE_001", exit_price=2900.0, reason="test")
        # Paper mode: None return is OK, close should proceed
        assert result is True, "Paper mode close should succeed even when _broker_place returns None"

    # T002: In live mode, None broker return → close_position returns False
    def test_T002_live_mode_nil_broker_place_returns_false(self):
        om, OrderRecord = self._make_om(paper_mode=False)
        rec = self._make_open_rec(OrderRecord)
        om._orders["ORD_CLOSE_001"] = rec
        with (
            patch.object(om, "_broker_place", return_value=None),
            patch.object(om, "_append_live_journal"),
            patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError),
        ):
            result = om.close_position("ORD_CLOSE_001", exit_price=2900.0, reason="test")
        assert result is False, "Live mode close must return False when broker returns None"

    # T003: In live mode, None return leaves position status as 'open'
    def test_T003_live_mode_nil_broker_leaves_position_open(self):
        om, OrderRecord = self._make_om(paper_mode=False)
        rec = self._make_open_rec(OrderRecord)
        om._orders["ORD_CLOSE_001"] = rec
        with (
            patch.object(om, "_broker_place", return_value=None),
            patch.object(om, "_append_live_journal"),
            patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError),
        ):
            om.close_position("ORD_CLOSE_001", exit_price=2900.0, reason="test")
        assert om._orders["ORD_CLOSE_001"].status == "open", (
            "Position must remain 'open' when exit order fails"
        )

    # T004: In live mode, None return does NOT remove position from portfolio
    def test_T004_live_mode_nil_broker_keeps_portfolio_position(self):
        om, OrderRecord = self._make_om(paper_mode=False)
        rec = self._make_open_rec(OrderRecord)
        om._orders["ORD_CLOSE_001"] = rec
        om._portfolio.positions["RELIANCE"] = {"order_id": "ORD_CLOSE_001"}
        with (
            patch.object(om, "_broker_place", return_value=None),
            patch.object(om, "_append_live_journal"),
            patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError),
        ):
            om.close_position("ORD_CLOSE_001", exit_price=2900.0, reason="test")
        assert "RELIANCE" in om._portfolio.positions, (
            "Portfolio position must NOT be removed when exit order fails"
        )

    # T005: In live mode, valid order_id from broker → close succeeds
    def test_T005_live_mode_valid_broker_order_id_closes(self):
        om, OrderRecord = self._make_om(paper_mode=False)
        rec = self._make_open_rec(OrderRecord)
        om._orders["ORD_CLOSE_001"] = rec
        with (
            patch.object(om, "_broker_place", return_value="BRK_EXIT_001"),
            patch.object(om, "_append_live_journal"),
            patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError),
        ):
            result = om.close_position("ORD_CLOSE_001", exit_price=2900.0, reason="test")
        assert result is True, "Live mode close must succeed when broker returns valid order_id"

    # T006: Close on non-existent order_id → returns False immediately
    def test_T006_unknown_order_id_returns_false(self):
        om, OrderRecord = self._make_om(paper_mode=False)
        result = om.close_position("DOES_NOT_EXIST", exit_price=2900.0)
        assert result is False

    # T007: Close on already-closed position → returns False
    def test_T007_already_closed_returns_false(self):
        om, OrderRecord = self._make_om(paper_mode=False)
        rec = self._make_open_rec(OrderRecord)
        rec.status = "closed"
        om._orders["ORD_CLOSE_001"] = rec
        result = om.close_position("ORD_CLOSE_001", exit_price=2900.0)
        assert result is False

    # T008: Alert is sent when exit order fails in live mode
    def test_T008_alert_sent_on_exit_failure(self):
        om, OrderRecord = self._make_om(paper_mode=False)
        rec = self._make_open_rec(OrderRecord)
        om._orders["ORD_CLOSE_001"] = rec
        mock_notifier = MagicMock()
        with (
            patch.object(om, "_broker_place", return_value=None),
            patch.object(om, "_append_live_journal"),
            patch("notifications.notifier_manager.get_notifier", return_value=mock_notifier),
        ):
            om.close_position("ORD_CLOSE_001", exit_price=2900.0, reason="test")
        assert mock_notifier.send_alert.called, "Alert must be sent when exit order fails"

    # T009: Alert message contains symbol
    def test_T009_alert_contains_symbol(self):
        om, OrderRecord = self._make_om(paper_mode=False)
        rec = self._make_open_rec(OrderRecord, symbol="INFY")
        om._orders["ORD_CLOSE_001"] = rec
        mock_notifier = MagicMock()
        with (
            patch.object(om, "_broker_place", return_value=None),
            patch.object(om, "_append_live_journal"),
            patch("notifications.notifier_manager.get_notifier", return_value=mock_notifier),
        ):
            om.close_position("ORD_CLOSE_001", exit_price=2900.0)
        call_args = mock_notifier.send_alert.call_args[0][0]
        assert "INFY" in call_args

    # T010: Alert message contains order_id
    def test_T010_alert_contains_order_id(self):
        om, OrderRecord = self._make_om(paper_mode=False)
        rec = self._make_open_rec(OrderRecord)
        om._orders["ORD_CLOSE_001"] = rec
        mock_notifier = MagicMock()
        with (
            patch.object(om, "_broker_place", return_value=None),
            patch.object(om, "_append_live_journal"),
            patch("notifications.notifier_manager.get_notifier", return_value=mock_notifier),
        ):
            om.close_position("ORD_CLOSE_001", exit_price=2900.0)
        call_args = mock_notifier.send_alert.call_args[0][0]
        assert "ORD_CLOSE_001" in call_args

    # T011: Notifier import failure does not crash close_position
    def test_T011_notifier_import_failure_safe(self):
        om, OrderRecord = self._make_om(paper_mode=False)
        rec = self._make_open_rec(OrderRecord)
        om._orders["ORD_CLOSE_001"] = rec
        with (
            patch.object(om, "_broker_place", return_value=None),
            patch.object(om, "_append_live_journal"),
            patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError("test")),
        ):
            result = om.close_position("ORD_CLOSE_001", exit_price=2900.0)
        assert result is False  # still returns False, not crashes

    # T012: Paper mode close succeeds with valid broker return
    def test_T012_paper_mode_valid_broker_return_closes(self):
        om, OrderRecord = self._make_om(paper_mode=True)
        rec = self._make_open_rec(OrderRecord)
        om._orders["ORD_CLOSE_001"] = rec
        with (
            patch.object(om, "_broker_place", return_value="SIM_BRK001"),
            patch.object(om, "_append_live_journal"),
            patch.object(om, "_journal_write_close"),
            patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError),
        ):
            result = om.close_position("ORD_CLOSE_001", exit_price=2900.0)
        assert result is True

    # T013: SELL position close (BUY to close) — direction reversed correctly
    def test_T013_sell_position_uses_buy_to_close(self):
        om, OrderRecord = self._make_om(paper_mode=True)
        from execution_engine.order_manager import OrderRecord as OR
        rec = OR(
            order_id="ORD_CLOSE_002",
            broker_order_id="BRK002",
            symbol="INFY",
            direction="SELL",
            quantity=5,
            entry_price=1900.0,
            stop_loss=1940.0,
            target=1840.0,
            strategy="TEST",
        )
        rec.status = "open"
        rec.initial_stop_loss = 1940.0
        rec.actual_fill_price = 1900.0
        om._orders["ORD_CLOSE_002"] = rec
        captured_dirs = []
        def _capture_place(sym, direction, qty, price, order_type="LIMIT"):
            captured_dirs.append(direction)
            return "SIM_001"
        with (
            patch.object(om, "_broker_place", side_effect=_capture_place),
            patch.object(om, "_append_live_journal"),
            patch.object(om, "_journal_write_close"),
            patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError),
        ):
            om.close_position("ORD_CLOSE_002", exit_price=1850.0)
        assert "BUY" in captured_dirs, "SELL position must be closed with BUY direction"

    # T014: BUY position close (SELL to close)
    def test_T014_buy_position_uses_sell_to_close(self):
        om, OrderRecord = self._make_om(paper_mode=True)
        rec = self._make_open_rec(OrderRecord, symbol="WIPRO")
        om._orders["ORD_CLOSE_001"] = rec
        captured_dirs = []
        def _capture_place(sym, direction, qty, price, order_type="LIMIT"):
            captured_dirs.append(direction)
            return "SIM_002"
        with (
            patch.object(om, "_broker_place", side_effect=_capture_place),
            patch.object(om, "_append_live_journal"),
            patch.object(om, "_journal_write_close"),
            patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError),
        ):
            om.close_position("ORD_CLOSE_001", exit_price=2950.0)
        assert "SELL" in captured_dirs, "BUY position must be closed with SELL direction"

    # T015: Multiple simultaneous close failures don't interfere with each other
    def test_T015_multiple_close_failures_independent(self):
        om, OrderRecord = self._make_om(paper_mode=False)
        from execution_engine.order_manager import OrderRecord as OR
        for i, sym in enumerate(["REL", "INFY", "TCS"]):
            rec = OR(
                order_id=f"ORD_{i}",
                broker_order_id=f"BRK_{i}",
                symbol=sym,
                direction="BUY",
                quantity=5,
                entry_price=1000.0,
                stop_loss=980.0,
                target=1050.0,
                strategy="TEST",
            )
            rec.status = "open"
            rec.initial_stop_loss = 980.0
            rec.actual_fill_price = 1000.0
            om._orders[f"ORD_{i}"] = rec
        with (
            patch.object(om, "_broker_place", return_value=None),
            patch.object(om, "_append_live_journal"),
            patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError),
        ):
            results = [
                om.close_position(f"ORD_{i}", exit_price=1100.0)
                for i in range(3)
            ]
        assert all(r is False for r in results), "All failed closes must return False"
        for i in range(3):
            assert om._orders[f"ORD_{i}"].status == "open"


# ─────────────────────────────────────────────────────────────────────────────
# D-002  EARLY_LOSS cooldown restored from live journal (T016-T025)
# ─────────────────────────────────────────────────────────────────────────────

class TestD002CooldownRestore:
    """D-003: _RECENT_CLOSE_TIMES must be repopulated from the live journal on restart."""

    def _write_journal(self, path: str, rows: list) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")

    def _get_rct(self):
        import execution_engine.order_manager as om_mod
        return om_mod._RECENT_CLOSE_TIMES

    # T016: After restore, closed symbols are present in _RECENT_CLOSE_TIMES
    def test_T016_closed_symbol_in_recent_close_times(self, tmp_path):
        import execution_engine.order_manager as om_mod
        ts_now = datetime.now(timezone.utc).isoformat()
        rows = [
            {"event": "OPEN",  "timestamp": ts_now, "order_id": "O1",
             "symbol": "RELIANCE", "direction": "BUY", "quantity": 10,
             "entry_price": 2800.0, "stop_loss": 2760.0, "target_price": 2880.0,
             "strategy": "T", "fill_status": "FILLED", "actual_fill_price": 2800.0,
             "opportunity_id": ""},
            {"event": "CLOSE", "timestamp": ts_now, "order_id": "O1",
             "symbol": "RELIANCE", "direction": "BUY", "quantity": 10,
             "entry_price": 2800.0, "stop_loss": 2760.0, "target_price": 2880.0,
             "strategy": "T", "fill_status": "FILLED", "actual_fill_price": 2800.0,
             "opportunity_id": "", "reason": "EARLY_LOSS", "pnl": -120.0},
        ]
        journal_path = str(tmp_path / "live_orders.jsonl")
        self._write_journal(journal_path, rows)
        om_mod._RECENT_CLOSE_TIMES.clear()
        with patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path):
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders = {}
            om._portfolio = MagicMock()
            om._portfolio.positions = {}
            om._restore_stats = {"restored_today": 0}
            om._journal_lock = threading.Lock()
            om._restore_from_live_journal()
        rct = self._get_rct()
        assert "RELIANCE" in rct, "Closed RELIANCE must be in _RECENT_CLOSE_TIMES"

    # T017: Reason is preserved in _RECENT_CLOSE_TIMES entry
    def test_T017_reason_preserved_in_cooldown_entry(self, tmp_path):
        import execution_engine.order_manager as om_mod
        ts_now = datetime.now(timezone.utc).isoformat()
        rows = [
            {"event": "CLOSE", "timestamp": ts_now, "order_id": "O2",
             "symbol": "INFY", "direction": "BUY", "quantity": 5,
             "entry_price": 1900.0, "stop_loss": 1870.0, "target_price": 1950.0,
             "strategy": "T", "fill_status": "FILLED", "actual_fill_price": 1900.0,
             "opportunity_id": "", "reason": "STOP_HIT", "pnl": -150.0},
        ]
        journal_path = str(tmp_path / "live_orders2.jsonl")
        self._write_journal(journal_path, rows)
        om_mod._RECENT_CLOSE_TIMES.clear()
        with patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path):
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders = {}
            om._portfolio = MagicMock()
            om._portfolio.positions = {}
            om._restore_stats = {"restored_today": 0}
            om._journal_lock = threading.Lock()
            om._restore_from_live_journal()
        rct = self._get_rct()
        assert rct.get("INFY", {}).get("reason") == "STOP_HIT"

    # T018: OPEN positions are still restored to _orders after cooldown restore runs
    def test_T018_open_positions_still_restored(self, tmp_path):
        import execution_engine.order_manager as om_mod
        ts_now = datetime.now(timezone.utc).isoformat()
        rows = [
            {"event": "OPEN", "timestamp": ts_now, "order_id": "O3",
             "symbol": "TCS", "direction": "BUY", "quantity": 8,
             "entry_price": 4000.0, "stop_loss": 3950.0, "target_price": 4100.0,
             "strategy": "T", "fill_status": "FILLED", "actual_fill_price": 4000.0,
             "opportunity_id": ""},
            {"event": "CLOSE", "timestamp": ts_now, "order_id": "O_STALE",
             "symbol": "WIPRO", "direction": "SELL", "quantity": 5,
             "entry_price": 600.0, "stop_loss": 610.0, "target_price": 580.0,
             "strategy": "T", "fill_status": "FILLED", "actual_fill_price": 600.0,
             "opportunity_id": "", "reason": "STOP_HIT", "pnl": -50.0},
        ]
        journal_path = str(tmp_path / "live_orders3.jsonl")
        self._write_journal(journal_path, rows)
        om_mod._RECENT_CLOSE_TIMES.clear()
        with patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path):
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders = {}
            om._portfolio = MagicMock()
            om._portfolio.positions = {}
            om._restore_stats = {"restored_today": 0}
            om._journal_lock = threading.Lock()
            om._restore_from_live_journal()
        assert "O3" in om._orders, "OPEN TCS position must be restored to _orders"

    # T019: Paper mode skips restore entirely (no journal in paper mode)
    def test_T019_paper_mode_skips_restore(self, tmp_path):
        import execution_engine.order_manager as om_mod
        om_mod._RECENT_CLOSE_TIMES.clear()
        from execution_engine.order_manager import OrderManager
        om = OrderManager.__new__(OrderManager)
        om._paper_mode = True
        om._orders = {}
        om._portfolio = MagicMock()
        om._portfolio.positions = {}
        om._restore_stats = {"restored_today": 0}
        om._journal_lock = threading.Lock()
        om._restore_from_live_journal()
        rct = self._get_rct()
        assert len(rct) == 0, "Paper mode must not populate _RECENT_CLOSE_TIMES"

    # T020: Non-existent journal file is handled gracefully
    def test_T020_missing_journal_no_crash(self, tmp_path):
        import execution_engine.order_manager as om_mod
        om_mod._RECENT_CLOSE_TIMES.clear()
        with patch("execution_engine.order_manager.LIVE_ORDER_LOG",
                   str(tmp_path / "nonexistent.jsonl")):
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders = {}
            om._portfolio = MagicMock()
            om._portfolio.positions = {}
            om._restore_stats = {"restored_today": 0}
            om._journal_lock = threading.Lock()
            om._restore_from_live_journal()  # must not raise

    # T021: Malformed journal line does not abort restore
    def test_T021_malformed_line_safe(self, tmp_path):
        import execution_engine.order_manager as om_mod
        ts_now = datetime.now(timezone.utc).isoformat()
        journal_path = str(tmp_path / "live_malformed.jsonl")
        with open(journal_path, "w") as fh:
            fh.write("NOT_JSON\n")
            fh.write(json.dumps({
                "event": "CLOSE", "timestamp": ts_now, "order_id": "O9",
                "symbol": "ONGC", "direction": "BUY", "quantity": 10,
                "entry_price": 180.0, "stop_loss": 175.0, "target_price": 190.0,
                "strategy": "T", "fill_status": "FILLED", "actual_fill_price": 180.0,
                "opportunity_id": "", "reason": "STOP_HIT", "pnl": -50.0,
            }) + "\n")
        om_mod._RECENT_CLOSE_TIMES.clear()
        with patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path):
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders = {}
            om._portfolio = MagicMock()
            om._portfolio.positions = {}
            om._restore_stats = {"restored_today": 0}
            om._journal_lock = threading.Lock()
            om._restore_from_live_journal()  # must not raise
        rct = self._get_rct()
        # ONGC should still be added from the valid line
        assert "ONGC" in rct

    # T022: Entries older than cutoff (7 days) are not restored
    def test_T022_old_entries_skipped(self, tmp_path):
        import execution_engine.order_manager as om_mod
        old_ts = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        journal_path = str(tmp_path / "old_journal.jsonl")
        with open(journal_path, "w") as fh:
            fh.write(json.dumps({
                "event": "CLOSE", "timestamp": old_ts, "order_id": "O_OLD",
                "symbol": "WIPRO", "direction": "BUY", "quantity": 5,
                "entry_price": 600.0, "stop_loss": 590.0, "target_price": 620.0,
                "strategy": "T", "fill_status": "FILLED", "actual_fill_price": 600.0,
                "opportunity_id": "", "reason": "STOP_HIT", "pnl": -50.0,
            }) + "\n")
        om_mod._RECENT_CLOSE_TIMES.clear()
        with patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path):
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders = {}
            om._portfolio = MagicMock()
            om._portfolio.positions = {}
            om._restore_stats = {"restored_today": 0}
            om._journal_lock = threading.Lock()
            om._restore_from_live_journal()
        rct = self._get_rct()
        assert "WIPRO" not in rct, "8-day-old entries must not be restored"

    # T023: Direction is preserved in cooldown entry
    def test_T023_direction_preserved(self, tmp_path):
        import execution_engine.order_manager as om_mod
        ts_now = datetime.now(timezone.utc).isoformat()
        journal_path = str(tmp_path / "dir_journal.jsonl")
        with open(journal_path, "w") as fh:
            fh.write(json.dumps({
                "event": "CLOSE", "timestamp": ts_now, "order_id": "O10",
                "symbol": "HDFC", "direction": "SELL", "quantity": 3,
                "entry_price": 2500.0, "stop_loss": 2530.0, "target_price": 2450.0,
                "strategy": "T", "fill_status": "FILLED", "actual_fill_price": 2500.0,
                "opportunity_id": "", "reason": "EARLY_LOSS", "pnl": -90.0,
            }) + "\n")
        om_mod._RECENT_CLOSE_TIMES.clear()
        with patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path):
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders = {}
            om._portfolio = MagicMock()
            om._portfolio.positions = {}
            om._restore_stats = {"restored_today": 0}
            om._journal_lock = threading.Lock()
            om._restore_from_live_journal()
        rct = self._get_rct()
        assert rct.get("HDFC", {}).get("direction") == "SELL"

    # T024: Empty journal does not crash and leaves _RECENT_CLOSE_TIMES empty
    def test_T024_empty_journal_safe(self, tmp_path):
        import execution_engine.order_manager as om_mod
        journal_path = str(tmp_path / "empty.jsonl")
        Path(journal_path).write_text("")
        om_mod._RECENT_CLOSE_TIMES.clear()
        with patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path):
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders = {}
            om._portfolio = MagicMock()
            om._portfolio.positions = {}
            om._restore_stats = {"restored_today": 0}
            om._journal_lock = threading.Lock()
            om._restore_from_live_journal()
        rct = self._get_rct()
        assert len(rct) == 0

    # T025: Cooldown dict has "time" key as datetime
    def test_T025_time_key_is_datetime(self, tmp_path):
        import execution_engine.order_manager as om_mod
        ts_now = datetime.now(timezone.utc).isoformat()
        journal_path = str(tmp_path / "time_journal.jsonl")
        with open(journal_path, "w") as fh:
            fh.write(json.dumps({
                "event": "CLOSE", "timestamp": ts_now, "order_id": "O11",
                "symbol": "BAJAJFINSV", "direction": "BUY", "quantity": 2,
                "entry_price": 14000.0, "stop_loss": 13900.0, "target_price": 14200.0,
                "strategy": "T", "fill_status": "FILLED", "actual_fill_price": 14000.0,
                "opportunity_id": "", "reason": "STOP_HIT", "pnl": -200.0,
            }) + "\n")
        om_mod._RECENT_CLOSE_TIMES.clear()
        with patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path):
            from execution_engine.order_manager import OrderManager
            om = OrderManager.__new__(OrderManager)
            om._paper_mode = False
            om._orders = {}
            om._portfolio = MagicMock()
            om._portfolio.positions = {}
            om._restore_stats = {"restored_today": 0}
            om._journal_lock = threading.Lock()
            om._restore_from_live_journal()
        rct = self._get_rct()
        entry = rct.get("BAJAJFINSV", {})
        assert isinstance(entry.get("time"), datetime), (
            "'time' in _RECENT_CLOSE_TIMES must be a datetime object"
        )


# ─────────────────────────────────────────────────────────────────────────────
# D-003  RiskGuardian corrupt state file (T026-T035)
# ─────────────────────────────────────────────────────────────────────────────

class TestD003RiskGuardianCorruptState:
    """D-002: Corrupt state file must quarantine the file and HALT trading."""

    def _make_rg(self, state_path: str):
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        return FailSafeRiskGuardian(total_capital=100_000, state_file=state_path)

    # T026: Corrupt JSON state file → _trading_halted is True
    def test_T026_corrupt_json_sets_trading_halted(self, tmp_path):
        state_file = str(tmp_path / "rg_corrupt.json")
        Path(state_file).write_text("{NOT VALID JSON{{")
        with patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError):
            rg = self._make_rg(state_file)
        assert rg._trading_halted is True, (
            "Corrupt state file must halt trading (fail closed)"
        )

    # T027: Corrupt state → halt reason is set
    def test_T027_corrupt_json_sets_halt_reason(self, tmp_path):
        state_file = str(tmp_path / "rg_corrupt2.json")
        Path(state_file).write_text("<<<broken>>>")
        with patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError):
            rg = self._make_rg(state_file)
        assert "CORRUPT" in rg._halt_reason.upper()

    # T028: Corrupt state → original file is quarantined (renamed or deleted)
    def test_T028_corrupt_file_is_quarantined(self, tmp_path):
        state_file = str(tmp_path / "rg_corrupt3.json")
        Path(state_file).write_text("{{{broken_json")
        with patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError):
            self._make_rg(state_file)
        # Original file should not exist (quarantined to .corrupt sidecar)
        assert not os.path.exists(state_file), (
            "Corrupt state file must be quarantined (moved away from original path)"
        )

    # T029: Valid same-day state → restored normally (not halted)
    def test_T029_valid_state_restored_normally(self, tmp_path):
        state_file = str(tmp_path / "rg_valid.json")
        today_str = date.today().isoformat()
        state = {
            "session_date": today_str,
            "daily_pnl": -500.0,
            "trading_halted": False,
            "halt_reason": "",
            "consec_losses": 1,
            "last_updated": _utcnow(),
        }
        Path(state_file).write_text(json.dumps(state))
        rg = self._make_rg(state_file)
        assert rg._trading_halted is False
        assert rg._daily_pnl == -500.0

    # T030: Halted state from same day → halt preserved on restore
    def test_T030_halted_state_preserved(self, tmp_path):
        state_file = str(tmp_path / "rg_halted.json")
        today_str = date.today().isoformat()
        state = {
            "session_date": today_str,
            "daily_pnl": -1200.0,
            "trading_halted": True,
            "halt_reason": "DAILY_LOSS_LIMIT",
            "consec_losses": 3,
            "last_updated": _utcnow(),
        }
        Path(state_file).write_text(json.dumps(state))
        rg = self._make_rg(state_file)
        assert rg._trading_halted is True
        assert rg._halt_reason == "DAILY_LOSS_LIMIT"

    # T031: Empty JSON object (no session_date) → treated as missing, no halt
    def test_T031_empty_json_object_no_halt(self, tmp_path):
        state_file = str(tmp_path / "rg_empty.json")
        Path(state_file).write_text("{}")
        with patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError):
            rg = self._make_rg(state_file)
        # No session_date → fresh start, no halt
        assert rg._trading_halted is False

    # T032: State from yesterday → no halt (fresh session)
    def test_T032_yesterday_state_fresh_session(self, tmp_path):
        state_file = str(tmp_path / "rg_yesterday.json")
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        state = {
            "session_date": yesterday,
            "daily_pnl": -800.0,
            "trading_halted": True,  # was halted yesterday
            "halt_reason": "VIX_KILL_SWITCH",
            "consec_losses": 2,
        }
        Path(state_file).write_text(json.dumps(state))
        rg = self._make_rg(state_file)
        # Yesterday's halt does NOT persist to today
        assert rg._trading_halted is False

    # T033: Corrupt state alert is sent (if notifier available)
    def test_T033_corrupt_state_alert_sent(self, tmp_path):
        state_file = str(tmp_path / "rg_alert.json")
        Path(state_file).write_text("{BROKEN}")
        mock_notifier = MagicMock()
        with patch("notifications.notifier_manager.get_notifier", return_value=mock_notifier):
            self._make_rg(state_file)
        assert mock_notifier.send_alert.called, "Alert must be sent for corrupt state file"

    # T034: Corrupt state session_date is set to today
    def test_T034_corrupt_state_session_date_is_today(self, tmp_path):
        state_file = str(tmp_path / "rg_sdate.json")
        Path(state_file).write_text("XXXXXXX")
        with patch("notifications.notifier_manager.get_notifier", side_effect=RuntimeError):
            rg = self._make_rg(state_file)
        assert rg._session_date == date.today()

    # T035: Missing state file → normal fresh start (no halt, no crash)
    def test_T035_missing_state_file_fresh_start(self, tmp_path):
        state_file = str(tmp_path / "rg_nonexistent.json")
        rg = self._make_rg(state_file)
        assert rg._trading_halted is False
        assert rg._daily_pnl == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# D-004  LOL bridge UTC vs IST timestamp comparison (T036-T045)
# ─────────────────────────────────────────────────────────────────────────────

class TestD004LolBridgeTimezone:
    """D-004: LOL bridge must use proper datetime comparison, not lexicographic strings."""

    def _get_bridge_module(self):
        import learning_system.lol_evidence_bridge as bridge_mod
        return bridge_mod

    # T036: UTC decision_at vs IST outcome_at — valid outcome after decision is accepted
    def test_T036_utc_vs_ist_valid_outcome_accepted(self):
        """outcome 2026-08-26T15:30:00+05:30 = 10:00 UTC, decision 09:30 UTC → 30 min later → valid"""
        from datetime import timezone
        bridge = self._get_bridge_module()

        # Simulate the _to_utc helper behavior
        decision_at = "2026-08-26T09:30:00+00:00"  # 09:30 UTC
        outcome_at  = "2026-08-26T15:30:00+05:30"  # 10:00 UTC

        def _to_utc(ts: str) -> datetime:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        assert _to_utc(outcome_at) > _to_utc(decision_at), (
            "IST outcome after UTC decision must parse as strictly later"
        )

    # T037: UTC decision_at vs IST outcome_at — outcome before decision fails lookahead
    def test_T037_utc_vs_ist_lookahead_detected(self):
        """outcome 2026-08-26T12:00:00+05:30 = 06:30 UTC, decision 09:30 UTC → outcome is BEFORE decision"""
        from datetime import timezone

        decision_at = "2026-08-26T09:30:00+00:00"  # 09:30 UTC
        outcome_at  = "2026-08-26T12:00:00+05:30"  # 06:30 UTC — BEFORE decision

        def _to_utc(ts: str) -> datetime:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        assert _to_utc(outcome_at) < _to_utc(decision_at), (
            "IST outcome that is before UTC decision must be detected as lookahead violation"
        )

    # T038: Lexicographic comparison would FAIL to catch this case (regression demonstration)
    def test_T038_lexicographic_comparison_fails_for_mixed_tz(self):
        """Demonstrates why string comparison is wrong for mixed timezones."""
        decision_at = "2026-08-26T09:30:00+00:00"
        outcome_at  = "2026-08-26T12:00:00+05:30"  # 06:30 UTC, but string > decision_at

        # This is what the OLD code did — it would INCORRECTLY accept this as valid:
        lexicographic_result = outcome_at > decision_at
        assert lexicographic_result is True, (
            "REGRESSION PROOF: lexicographic comparison incorrectly accepts lookahead"
        )

        # But datetime-based comparison correctly rejects it:
        from datetime import timezone as _tz
        def _to_utc(ts: str) -> datetime:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_tz.utc)
            return dt.astimezone(_tz.utc)

        datetime_result = _to_utc(outcome_at) > _to_utc(decision_at)
        assert datetime_result is False, (
            "Datetime comparison correctly rejects this cross-timezone lookahead"
        )

    # T039: Both UTC → comparison works correctly
    def test_T039_both_utc_works_correctly(self):
        from datetime import timezone as _tz
        decision_at = "2026-08-26T09:30:00+00:00"
        outcome_at  = "2026-08-26T10:00:00Z"

        def _to_utc(ts: str) -> datetime:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_tz.utc)
            return dt.astimezone(_tz.utc)

        assert _to_utc(outcome_at) > _to_utc(decision_at)

    # T040: Both IST → comparison works correctly
    def test_T040_both_ist_works_correctly(self):
        from datetime import timezone as _tz
        decision_at = "2026-08-26T15:00:00+05:30"
        outcome_at  = "2026-08-26T15:30:00+05:30"

        def _to_utc(ts: str) -> datetime:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_tz.utc)
            return dt.astimezone(_tz.utc)

        assert _to_utc(outcome_at) > _to_utc(decision_at)

    # T041: Equal timestamps → rejected as lookahead
    def test_T041_equal_timestamps_rejected(self):
        from datetime import timezone as _tz
        ts = "2026-08-26T09:30:00+00:00"

        def _to_utc(ts_s: str) -> datetime:
            dt = datetime.fromisoformat(ts_s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_tz.utc)
            return dt.astimezone(_tz.utc)

        assert not (_to_utc(ts) > _to_utc(ts)), "Equal timestamps must be rejected"

    # T042: Naive datetime fallback (no tzinfo) still works
    def test_T042_naive_datetime_fallback(self):
        from datetime import timezone as _tz
        decision_at = "2026-08-26T09:30:00"  # no tz
        outcome_at  = "2026-08-26T10:00:00"  # no tz

        def _to_utc(ts_s: str) -> datetime:
            dt = datetime.fromisoformat(ts_s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_tz.utc)  # assume UTC
            return dt.astimezone(_tz.utc)

        assert _to_utc(outcome_at) > _to_utc(decision_at)

    # T043: Invalid timestamp format → raises (caught in bridge's except block)
    def test_T043_invalid_timestamp_raises_valueerror(self):
        with pytest.raises((ValueError, AttributeError)):
            datetime.fromisoformat("not-a-timestamp".replace("Z", "+00:00"))

    # T044: LOL bridge module source has _to_utc helper or fromisoformat call
    def test_T044_bridge_module_has_datetime_comparison(self):
        import inspect
        import learning_system.lol_evidence_bridge as bridge_mod
        src = inspect.getsource(bridge_mod)
        assert "fromisoformat" in src or "_to_utc" in src, (
            "LOL bridge must use proper datetime parsing for timestamp comparison"
        )

    # T045: LOL bridge does NOT use bare string <= for anti-lookahead check
    def test_T045_bridge_no_bare_string_comparison(self):
        import inspect
        import learning_system.lol_evidence_bridge as bridge_mod
        src = inspect.getsource(bridge_mod)
        # The old broken line was: if outcome_at <= decision_at:
        # After fix it should NOT have this pattern without datetime parsing
        # We verify the fix is present by checking _to_utc wrapper or fromisoformat
        lines = src.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Must not have bare string comparison without datetime parsing around it
            if "outcome_at <= decision_at" in stripped and "fromisoformat" not in stripped:
                # Check surrounding context for datetime conversion
                ctx_start = max(0, i - 5)
                ctx_end   = min(len(lines), i + 2)
                ctx = "\n".join(lines[ctx_start:ctx_end])
                assert "fromisoformat" in ctx or "_to_utc" in ctx, (
                    f"Bare string comparison at line {i+1} without datetime conversion"
                )


# ─────────────────────────────────────────────────────────────────────────────
# D-005  scheduler_health uses UTC timestamps (T046-T050)
# ─────────────────────────────────────────────────────────────────────────────

class TestD005SchedulerHealthTimestamps:
    """D-005: scheduler_health._now_iso() must use UTC-aware datetime."""

    # T046: _now_iso returns a string with UTC offset
    def test_T046_now_iso_has_utc_offset(self):
        from orchestrator.scheduler_health import _now_iso
        ts = _now_iso()
        assert "+" in ts or ts.endswith("Z"), (
            f"_now_iso must return UTC-offset timestamp, got: {ts!r}"
        )

    # T047: _now_iso can be parsed back to an aware datetime
    def test_T047_now_iso_parseable_to_aware_datetime(self):
        from orchestrator.scheduler_health import _now_iso
        ts = _now_iso()
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert dt.tzinfo is not None, "Parsed _now_iso must have tzinfo"

    # T048: _now_iso timestamp is within 5 seconds of now
    def test_T048_now_iso_near_current_time(self):
        from orchestrator.scheduler_health import _now_iso
        # _now_iso returns second-precision; floor before/after to same precision
        before = datetime.now(timezone.utc).replace(microsecond=0)
        ts = _now_iso()
        after = datetime.now(timezone.utc).replace(microsecond=0)
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert before <= dt <= after + timedelta(seconds=5)

    # T049: Two successive _now_iso calls produce comparable strings
    def test_T049_successive_calls_ordered(self):
        import time
        from orchestrator.scheduler_health import _now_iso
        t1 = _now_iso()
        time.sleep(0.01)
        t2 = _now_iso()
        dt1 = datetime.fromisoformat(t1.replace("Z", "+00:00"))
        dt2 = datetime.fromisoformat(t2.replace("Z", "+00:00"))
        assert dt2 >= dt1

    # T050: scheduler_health module source references timezone.utc
    def test_T050_module_source_uses_utc(self):
        import inspect
        import orchestrator.scheduler_health as sh_mod
        src = inspect.getsource(sh_mod)
        assert "timezone.utc" in src or "timezone" in src, (
            "scheduler_health must use timezone-aware datetime"
        )


# ─────────────────────────────────────────────────────────────────────────────
# D-006  AET pending slot startup log (T051-T060)
# ─────────────────────────────────────────────────────────────────────────────

class TestD006AetStartupWarning:
    """D-006: OrderManager must log at startup that AET pending slots are session-only."""

    # T051: Startup log contains AET-related message in live mode
    def test_T051_live_mode_logs_aet_warning(self, tmp_path, caplog):
        import logging
        import importlib
        import execution_engine.order_manager as om_mod
        importlib.reload(om_mod)
        from execution_engine.order_manager import OrderManager

        journal_path = str(tmp_path / "live_orders.jsonl")
        Path(journal_path).write_text("")
        with (
            patch.object(om_mod._cfg, "PAPER_TRADING", False),
            patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path),
            patch.object(OrderManager, "_load_broker", return_value=None),
            patch.object(OrderManager, "_reconcile_sim_paper_artifacts"),
            patch.object(OrderManager, "reconcile_startup_fills"),
            caplog.at_level(logging.INFO),
        ):
            om = OrderManager()
        aet_logged = any(
            "AET" in r.message or "confirmation" in r.message.lower()
            for r in caplog.records
        )
        assert aet_logged, "Startup must log a note about AET pending slots being session-only"

    # T052: _aet_pending starts as empty dict
    def test_T052_aet_pending_starts_empty(self, tmp_path):
        import importlib
        import execution_engine.order_manager as om_mod
        importlib.reload(om_mod)
        from execution_engine.order_manager import OrderManager

        journal_path = str(tmp_path / "live_orders.jsonl")
        Path(journal_path).write_text("")
        with (
            patch.object(om_mod._cfg, "PAPER_TRADING", False),
            patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path),
            patch.object(OrderManager, "_load_broker", return_value=None),
            patch.object(OrderManager, "_reconcile_sim_paper_artifacts"),
            patch.object(OrderManager, "reconcile_startup_fills"),
        ):
            om = OrderManager()
        assert om._aet_pending == {}, "_aet_pending must start empty on restart"

    # T053: AET module source has _aet_pending attribute defined
    def test_T053_aet_pending_attribute_defined(self):
        import inspect
        import execution_engine.order_manager as om_mod
        src = inspect.getsource(om_mod)
        assert "_aet_pending" in src

    # T054: AetPendingSlot dataclass is importable
    def test_T054_aet_pending_slot_importable(self):
        from execution_engine.order_manager import AetPendingSlot
        assert AetPendingSlot is not None

    # T055: AetPendingSlot has required fields
    def test_T055_aet_pending_slot_has_fields(self):
        import dataclasses
        from execution_engine.order_manager import AetPendingSlot
        fields = {f.name for f in dataclasses.fields(AetPendingSlot)}
        # Must have at least these core fields
        assert "signal" in fields or "order_id" in fields or "slot_id" in fields, (
            "AetPendingSlot must have at least one identifying field"
        )

    # T056: In paper mode, _aet_pending is also empty on startup
    def test_T056_paper_mode_aet_empty(self):
        import importlib
        import execution_engine.order_manager as om_mod
        importlib.reload(om_mod)
        from execution_engine.order_manager import OrderManager
        with (
            patch.object(om_mod._cfg, "PAPER_TRADING", True),
            patch.object(OrderManager, "_reconcile_sim_paper_artifacts"),
        ):
            om = OrderManager()
        assert om._aet_pending == {}

    # T057: Adding to _aet_pending is safe (basic interface)
    def test_T057_aet_pending_dict_assignable(self, tmp_path):
        import importlib
        import execution_engine.order_manager as om_mod
        importlib.reload(om_mod)
        from execution_engine.order_manager import OrderManager, AetPendingSlot
        journal_path = str(tmp_path / "live_orders.jsonl")
        Path(journal_path).write_text("")
        with (
            patch.object(om_mod._cfg, "PAPER_TRADING", False),
            patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path),
            patch.object(OrderManager, "_load_broker", return_value=None),
            patch.object(OrderManager, "_reconcile_sim_paper_artifacts"),
            patch.object(OrderManager, "reconcile_startup_fills"),
        ):
            om = OrderManager()
        # After startup it is empty; can be written to
        import dataclasses
        fields = {f.name for f in dataclasses.fields(AetPendingSlot)}
        dummy_kwargs = {f: None for f in fields}
        slot = AetPendingSlot(**dummy_kwargs)
        om._aet_pending["test_slot"] = slot
        assert "test_slot" in om._aet_pending

    # T058: _aet_pending dict is cleared between successive test cases (no shared state)
    def test_T058_aet_pending_isolated(self, tmp_path):
        import importlib
        import execution_engine.order_manager as om_mod
        importlib.reload(om_mod)
        from execution_engine.order_manager import OrderManager
        journal_path = str(tmp_path / "live_orders.jsonl")
        Path(journal_path).write_text("")
        with (
            patch.object(om_mod._cfg, "PAPER_TRADING", False),
            patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path),
            patch.object(OrderManager, "_load_broker", return_value=None),
            patch.object(OrderManager, "_reconcile_sim_paper_artifacts"),
            patch.object(OrderManager, "reconcile_startup_fills"),
        ):
            om1 = OrderManager()
            om2 = OrderManager()
        assert om1._aet_pending is not om2._aet_pending, (
            "Each OrderManager instance must have its own _aet_pending dict"
        )

    # T059: Module source contains 'AET confirmation' or 'AET pending' startup log
    def test_T059_module_source_has_aet_startup_log(self):
        import inspect
        import execution_engine.order_manager as om_mod
        src = inspect.getsource(om_mod)
        assert "AET" in src and "confirmation" in src.lower(), (
            "order_manager.py must contain AET startup log about session-only slots"
        )

    # T060: _aet_pending is thread-safe (dict access is GIL-safe, no deadlock)
    def test_T060_aet_pending_thread_safe(self, tmp_path):
        """Basic regression: concurrent reads/writes to _aet_pending must not crash."""
        import importlib
        import execution_engine.order_manager as om_mod
        importlib.reload(om_mod)
        from execution_engine.order_manager import OrderManager
        journal_path = str(tmp_path / "live_orders.jsonl")
        Path(journal_path).write_text("")
        with (
            patch.object(om_mod._cfg, "PAPER_TRADING", False),
            patch("execution_engine.order_manager.LIVE_ORDER_LOG", journal_path),
            patch.object(OrderManager, "_load_broker", return_value=None),
            patch.object(OrderManager, "_reconcile_sim_paper_artifacts"),
            patch.object(OrderManager, "reconcile_startup_fills"),
        ):
            om = OrderManager()
        errors = []
        def _writer():
            try:
                for i in range(50):
                    om._aet_pending[f"k{i}"] = i
            except Exception as e:
                errors.append(e)
        def _reader():
            try:
                for _ in range(50):
                    _ = dict(om._aet_pending)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=_writer), threading.Thread(target=_reader)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors, f"Thread-safety error in _aet_pending: {errors}"
