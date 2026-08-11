"""
FRZ-001 Phase 2 — Stale journal reconciliation tests.

Verified:
  1.  Recent valid OPEN position → restored correctly.
  2.  Recent closed position → remains closed.
  3.  Old unmatched SIM_ OPEN → SESSION_EXPIRED_DEEP_ORPHAN written.
  4.  Original OPEN record preserved (append-only).
  5.  No duplicate CLOSE/SESSION_EXPIRED records.
  6.  Restart after reconciliation does NOT re-expire the same record.
  7.  Non-SIM_ order_ids are NEVER touched by deep orphan expiry.
  8.  Only SIM_-prefixed records are expired by the deep orphan pass.

Run with:  python -m pytest tests/test_frz001_journal.py -v
"""
import sys
import os
import csv
import io
import types
import unittest
import threading
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# ── Minimal stubs for order_manager import ───────────────────────────────────

_stub("utils", get_logger=MagicMock(return_value=MagicMock()))
_stub("config",
    PAPER_TRADING=True, MAX_POSITION_SIZE=100_000,
    RISK_PER_TRADE_PCT=1.0, INITIAL_CAPITAL=1_000_000,
    TOTAL_CAPITAL=1_000_000, ACTIVE_BROKER="dhan",
    ZERODHA_API_KEY="", ZERODHA_ACCESS_TOKEN="",
    DHAN_CLIENT_ID="", DHAN_ACCESS_TOKEN="",
    ANGELONE_API_KEY="", ANGELONE_CLIENT_ID="",
    ANGELONE_PASSWORD="", ANGELONE_TOTP_SECRET="",
    LOG_DIR=os.path.join(ROOT, "data", "logs"),
    LOG_LEVEL="DEBUG", ATR_ZONE_MULTIPLIER=1.5,
    MAX_RISK_PER_TRADE_PCT=0.0025, MAX_CAPITAL_PER_TRADE_PCT=15.0,
)
_stub("execution_engine.brokers")
_stub("execution_engine.brokers.dhan_broker", DhanBroker=MagicMock)
_stub("data_feeds", get_feed_manager=MagicMock(return_value=MagicMock()))
_stub("communication.event_bus", EventBus=MagicMock)
_stub("communication.events",
    EventType=type("ET", (), {"ORDER_PLACED": "ORDER_PLACED",
                              "ORDER_REJECTED": "ORDER_REJECTED"})())
_stub("learning_system.strategy_performance_tracker",
    get_stability_ledger=MagicMock(return_value=MagicMock()))


# ── Helpers ───────────────────────────────────────────────────────────────────

_HEADER = [
    "timestamp", "order_id", "symbol", "direction", "quantity",
    "entry_price", "stop_loss", "target", "strategy", "confidence",
    "rr", "event", "exit_price", "pnl", "reason",
]

def _ts(days_ago: float) -> str:
    dt = datetime.now() - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def _write_csv(path: str, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_HEADER)
        w.writeheader()
        for r in rows:
            row = {k: r.get(k, "") for k in _HEADER}
            w.writerow(row)

def _read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [{k: v for k, v in r.items() if k} for r in csv.DictReader(fh)]

def _count_events(rows: list[dict], oid: str, event: str) -> int:
    return sum(1 for r in rows if r["order_id"] == oid and r["event"].upper() == event)


def _run_restore(data_dir: str, csv_path: str):
    """
    Import OrderManager and run _restore_from_journal() against a temp CSV.
    Patches the DATA_DIR and PAPER_TRADE_LOG constants.
    """
    # Patch module-level constants before importing
    import execution_engine.order_manager as om_mod
    orig_log = om_mod.PAPER_TRADE_LOG
    orig_dir = om_mod._DATA_DIR
    try:
        om_mod.PAPER_TRADE_LOG = csv_path
        om_mod._DATA_DIR       = data_dir
        om = MagicMock()
        om._journal_lock = threading.Lock()
        om._orders       = {}
        om._portfolio    = MagicMock()
        om._portfolio.positions = {}
        om._restore_stats     = {}
        om._restored_extended_oids = set()
        # Call _restore_from_journal as an unbound method
        om_mod.OrderManager._restore_from_journal(om)
        return om
    finally:
        om_mod.PAPER_TRADE_LOG = orig_log
        om_mod._DATA_DIR       = orig_dir


class TestDeepOrphanExpiry(unittest.TestCase):
    """Core: old SIM_ records are expired, recent/real records are untouched."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.csv = os.path.join(self.tmp, "paper_trades.csv")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── Test 1: Recent valid OPEN → restored ─────────────────────────────────
    def test_recent_valid_open_is_restored(self):
        oid = "SIM_RECENT_BUY_Q10_P1000_9999"
        _write_csv(self.csv, [
            {"timestamp": _ts(1), "order_id": oid, "symbol": "RECENT",
             "direction": "BUY", "quantity": 10, "entry_price": 1000,
             "stop_loss": 980, "target": 1060, "strategy": "Momentum",
             "event": "OPEN"},
        ])
        om = _run_restore(self.tmp, self.csv)
        # Position should be in _orders
        self.assertIn(oid, om._orders,
            "Recent OPEN position must be restored into _orders")
        rows = _read_csv(self.csv)
        closes = _count_events(rows, oid, "CLOSE")
        self.assertEqual(closes, 0,
            "No CLOSE should be written for a recently-opened position")

    # ── Test 2: Recent closed position → no action ───────────────────────────
    def test_recent_closed_position_stays_closed(self):
        oid = "SIM_CLOSED_BUY_Q5_P500_1111"
        _write_csv(self.csv, [
            {"timestamp": _ts(2), "order_id": oid, "symbol": "CLOSED",
             "direction": "BUY", "quantity": 5, "entry_price": 500,
             "stop_loss": 490, "target": 530, "strategy": "Trend",
             "event": "OPEN"},
            {"timestamp": _ts(1), "order_id": oid, "symbol": "CLOSED",
             "direction": "BUY", "quantity": 5, "entry_price": 500,
             "stop_loss": 490, "target": 530, "strategy": "Trend",
             "event": "CLOSE", "exit_price": 520, "pnl": 100, "reason": "TARGET"},
        ])
        _run_restore(self.tmp, self.csv)
        rows = _read_csv(self.csv)
        # Exactly one CLOSE still
        self.assertEqual(_count_events(rows, oid, "CLOSE"), 1,
            "Already-closed position must not get an extra CLOSE row")

    # ── Test 3: Old SIM_ OPEN → SESSION_EXPIRED_DEEP_ORPHAN written ──────────
    def test_old_sim_open_is_expired(self):
        oid = "SIM_HAVELLS_BUY_Q282_P1229_OLD"
        _write_csv(self.csv, [
            {"timestamp": _ts(15), "order_id": oid, "symbol": "HAVELLS",
             "direction": "BUY", "quantity": 282, "entry_price": 1229.66,
             "stop_loss": 1200, "target": 1300, "strategy": "Mean_Reversion",
             "event": "OPEN"},
        ])
        _run_restore(self.tmp, self.csv)
        rows = _read_csv(self.csv)
        close_rows = [r for r in rows if r["order_id"] == oid and r["event"].upper() == "CLOSE"]
        self.assertEqual(len(close_rows), 1,
            "Old SIM_ OPEN must receive exactly one SESSION_EXPIRED_DEEP_ORPHAN CLOSE")
        self.assertEqual(close_rows[0]["reason"], "SESSION_EXPIRED_DEEP_ORPHAN",
            "CLOSE reason must be SESSION_EXPIRED_DEEP_ORPHAN")

    # ── Test 4: Original OPEN record is preserved ─────────────────────────────
    def test_original_open_row_preserved(self):
        oid = "SIM_HAVELLS_BUY_Q282_P1229_ORIG"
        _write_csv(self.csv, [
            {"timestamp": _ts(15), "order_id": oid, "symbol": "HAVELLS",
             "direction": "BUY", "quantity": 282, "entry_price": 1229.66,
             "stop_loss": 1200, "target": 1300, "strategy": "Mean_Reversion",
             "event": "OPEN"},
        ])
        _run_restore(self.tmp, self.csv)
        rows = _read_csv(self.csv)
        open_rows = [r for r in rows if r["order_id"] == oid and r["event"].upper() == "OPEN"]
        self.assertEqual(len(open_rows), 1,
            "Original OPEN row must be preserved in the journal")

    # ── Test 5: No duplicate CLOSE records ────────────────────────────────────
    def test_no_duplicate_close(self):
        oid = "SIM_DUPE_TEST_BUY_Q10_P2000_DUPE"
        _write_csv(self.csv, [
            {"timestamp": _ts(15), "order_id": oid, "symbol": "DUPE",
             "direction": "BUY", "quantity": 10, "entry_price": 2000,
             "stop_loss": 1950, "target": 2100, "strategy": "Swing",
             "event": "OPEN"},
        ])
        _run_restore(self.tmp, self.csv)
        _run_restore(self.tmp, self.csv)   # second run (idempotency)
        rows = _read_csv(self.csv)
        self.assertEqual(_count_events(rows, oid, "CLOSE"), 1,
            "Running restore twice must not produce duplicate CLOSE rows")

    # ── Test 6: After reconciliation, restart does NOT re-expire ─────────────
    def test_restart_does_not_re_expire_reconciled_record(self):
        oid = "SIM_IDEMPOTENT_BUY_Q10_P500_IDEM"
        _write_csv(self.csv, [
            {"timestamp": _ts(15), "order_id": oid, "symbol": "IDEMPOTENT",
             "direction": "BUY", "quantity": 10, "entry_price": 500,
             "stop_loss": 490, "target": 520, "strategy": "Trend",
             "event": "OPEN"},
        ])
        # First restart — should expire
        _run_restore(self.tmp, self.csv)
        rows_after_first = _read_csv(self.csv)
        closes_1 = _count_events(rows_after_first, oid, "CLOSE")
        self.assertEqual(closes_1, 1, "First restore must write exactly one CLOSE")

        # Second restart — must be a no-op
        _run_restore(self.tmp, self.csv)
        rows_after_second = _read_csv(self.csv)
        closes_2 = _count_events(rows_after_second, oid, "CLOSE")
        self.assertEqual(closes_2, 1,
            "Second restore must NOT add a duplicate CLOSE (idempotency)")

    # ── Test 7: Non-SIM_ real order_ids are NEVER expired ────────────────────
    def test_real_broker_order_not_expired(self):
        """Real Dhan order IDs do NOT start with SIM_ — they must never be touched."""
        real_oid = "1234567890"   # numeric Dhan order_id pattern
        _write_csv(self.csv, [
            {"timestamp": _ts(15), "order_id": real_oid, "symbol": "HDFCBANK",
             "direction": "BUY", "quantity": 1, "entry_price": 1800,
             "stop_loss": 1760, "target": 1880, "strategy": "Momentum",
             "event": "OPEN"},
        ])
        _run_restore(self.tmp, self.csv)
        rows = _read_csv(self.csv)
        close_rows = [r for r in rows if r["order_id"] == real_oid and r["event"].upper() == "CLOSE"]
        self.assertEqual(len(close_rows), 0,
            "Non-SIM_ (real broker) order_id must NEVER be expired by deep orphan pass")

    # ── Test 8: Only SIM_-prefixed records go through deep orphan expiry ──────
    def test_only_sim_prefix_records_expired(self):
        """Mix of SIM_ and non-SIM_ old records — only SIM_ gets expired."""
        sim_oid   = "SIM_OLD_BUY_Q5_P1000_MIX"
        real_oid  = "DHAN9876543210"
        _write_csv(self.csv, [
            {"timestamp": _ts(20), "order_id": sim_oid, "symbol": "OLD",
             "direction": "BUY", "quantity": 5, "entry_price": 1000,
             "stop_loss": 980, "target": 1040, "strategy": "Swing",
             "event": "OPEN"},
            {"timestamp": _ts(20), "order_id": real_oid, "symbol": "REAL",
             "direction": "BUY", "quantity": 2, "entry_price": 2000,
             "stop_loss": 1960, "target": 2080, "strategy": "Trend",
             "event": "OPEN"},
        ])
        _run_restore(self.tmp, self.csv)
        rows = _read_csv(self.csv)
        sim_closes  = _count_events(rows, sim_oid,  "CLOSE")
        real_closes = _count_events(rows, real_oid, "CLOSE")
        self.assertEqual(sim_closes,  1, "Old SIM_ record must be expired")
        self.assertEqual(real_closes, 0, "Non-SIM_ record must NOT be expired")


if __name__ == "__main__":
    unittest.main()
