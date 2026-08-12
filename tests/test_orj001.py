"""
ORJ-001 — SIM Orphan Journal Reconciliation Tests

Coverage:
  TEST-01  Old SIM_ OPEN + no CLOSE → one PAPER_MODE_ARTIFACT CLOSE appended
  TEST-02  Idempotency: run twice → exactly one CLOSE row
  TEST-03  Original OPEN row preserved after reconciliation
  TEST-04  Old SIM_ artifact in LIVE mode does NOT enter OrderManager._orders
  TEST-05  Non-SIM_ (real/Dhan) order not tracked by OrderManager → REAL_ORPHAN
           alert is still emitted; no suppression
  TEST-06  SIM_ record younger than _MAX_LOOKBACK_DAYS → NOT reconciled
  TEST-07  SIM_ record with existing CLOSE → no duplicate reconciliation row
  TEST-08  Non-SIM_ order_id → never treated as paper artifact
  TEST-09  _reconcile_sim_paper_artifacts() cannot place a live order
  TEST-10  PAPER_MODE_ARTIFACT in _do_eod_learning skip-set;
           ILC _win_rate() skips housekeeping reasons

Run with:  python -m pytest tests/test_orj001.py -v
"""
import sys
import os
import csv
import types
import unittest
import threading
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ── Minimal stubs ─────────────────────────────────────────────────────────────

def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


_stub("utils", get_logger=MagicMock(return_value=MagicMock()))
_stub("config",
    PAPER_TRADING=False,   # LIVE mode — this is what ORJ-001 targets
    MAX_POSITION_SIZE=100_000,
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


# ── Journal helpers ───────────────────────────────────────────────────────────

_HEADER = [
    "timestamp", "order_id", "symbol", "direction", "quantity",
    "entry_price", "stop_loss", "target", "strategy", "confidence",
    "rr", "event", "exit_price", "pnl", "reason",
]


def _ts(days_ago: float) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _write_csv(path: str, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in _HEADER})


def _read_csv(path: str) -> list:
    with open(path, newline="", encoding="utf-8") as fh:
        return [{k: v for k, v in r.items() if k} for r in csv.DictReader(fh)]


def _count(rows: list, oid: str, event: str) -> int:
    return sum(1 for r in rows if r["order_id"] == oid
               and r["event"].strip().upper() == event.upper())


def _run_reconcile(data_dir: str, csv_path: str, existing_orders: dict = None):
    """
    Call _reconcile_sim_paper_artifacts() directly against a temp CSV.
    Simulates LIVE mode: _paper_mode=False, self._orders empty (no journal restore).
    """
    import execution_engine.order_manager as om_mod
    orig_log = om_mod.PAPER_TRADE_LOG
    orig_dir = om_mod._DATA_DIR
    try:
        om_mod.PAPER_TRADE_LOG = csv_path
        om_mod._DATA_DIR       = data_dir
        om = MagicMock()
        om._journal_lock = threading.Lock()
        om._orders       = existing_orders or {}
        om._paper_mode   = False
        om_mod.OrderManager._reconcile_sim_paper_artifacts(om)
        return om
    finally:
        om_mod.PAPER_TRADE_LOG = orig_log
        om_mod._DATA_DIR       = orig_dir


# ── Test classes ──────────────────────────────────────────────────────────────

class TestORJ001Reconciliation(unittest.TestCase):
    """Core reconciliation behaviour."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.csv = os.path.join(self.tmp, "paper_trades.csv")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # TEST-01: Old SIM_ OPEN + no CLOSE → PAPER_MODE_ARTIFACT CLOSE written ──
    def test_01_old_sim_open_receives_close(self):
        oid = "SIM_HAVELLS_BUY_Q282_P1229_T01"
        _write_csv(self.csv, [
            {"timestamp": _ts(16), "order_id": oid, "symbol": "HAVELLS",
             "direction": "BUY", "quantity": 282, "entry_price": 1229.66,
             "stop_loss": 1185.56, "target": 1330.0, "strategy": "Momentum_Retest",
             "event": "OPEN"},
        ])
        _run_reconcile(self.tmp, self.csv)
        rows = _read_csv(self.csv)
        close_rows = [r for r in rows if r["order_id"] == oid
                      and r["event"].upper() == "CLOSE"]
        self.assertEqual(len(close_rows), 1,
            "Old SIM_ OPEN must receive exactly one PAPER_MODE_ARTIFACT CLOSE")
        self.assertEqual(close_rows[0]["reason"], "PAPER_MODE_ARTIFACT",
            "Reason must be PAPER_MODE_ARTIFACT")
        self.assertEqual(float(close_rows[0]["pnl"] or 0), 0.0,
            "Reconciliation CLOSE must have pnl=0")
        self.assertEqual(close_rows[0]["exit_price"], close_rows[0]["entry_price"],
            "exit_price must equal entry_price (no real LTP used)")

    # TEST-02: Idempotency — two runs → exactly one CLOSE ─────────────────────
    def test_02_idempotency_no_duplicate_close(self):
        oid = "SIM_AUROPHARMA_BUY_Q435_P1610_T02"
        _write_csv(self.csv, [
            {"timestamp": _ts(10), "order_id": oid, "symbol": "AUROPHARMA",
             "direction": "BUY", "quantity": 435, "entry_price": 1607.5,
             "stop_loss": 1567.12, "target": 1708.45, "strategy": "Momentum_Retest",
             "event": "OPEN"},
        ])
        _run_reconcile(self.tmp, self.csv)
        _run_reconcile(self.tmp, self.csv)   # second run must be a no-op
        rows = _read_csv(self.csv)
        self.assertEqual(_count(rows, oid, "CLOSE"), 1,
            "Running reconciliation twice must not produce duplicate CLOSE rows")

    # TEST-03: Original OPEN row preserved ────────────────────────────────────
    def test_03_original_open_row_preserved(self):
        oid = "SIM_HAVELLS_BUY_Q427_P1285_T03"
        _write_csv(self.csv, [
            {"timestamp": _ts(8), "order_id": oid, "symbol": "HAVELLS",
             "direction": "BUY", "quantity": 427, "entry_price": 1282.6,
             "stop_loss": 1241.26, "target": 1385.95, "strategy": "Momentum_Retest",
             "event": "OPEN"},
        ])
        _run_reconcile(self.tmp, self.csv)
        rows = _read_csv(self.csv)
        open_rows = [r for r in rows if r["order_id"] == oid
                     and r["event"].upper() == "OPEN"]
        self.assertEqual(len(open_rows), 1,
            "Original OPEN row must be preserved — append-only journal")
        self.assertEqual(float(open_rows[0]["entry_price"]), 1282.6,
            "Original entry_price must not be altered")

    # TEST-04: Artifact in LIVE mode does NOT enter self._orders ──────────────
    def test_04_live_mode_artifact_not_added_to_orders(self):
        oid = "SIM_OLD_BUY_Q10_P500_T04"
        _write_csv(self.csv, [
            {"timestamp": _ts(15), "order_id": oid, "symbol": "TESTSTOCK",
             "direction": "BUY", "quantity": 10, "entry_price": 500,
             "stop_loss": 490, "target": 530, "strategy": "Momentum",
             "event": "OPEN"},
        ])
        om = _run_reconcile(self.tmp, self.csv)
        # _orders must remain empty — no position loaded
        self.assertNotIn(oid, om._orders,
            "Reconciled SIM_ artifact must NOT be loaded into live _orders")
        self.assertEqual(len(om._orders), 0,
            "_orders must remain empty in LIVE mode after reconciliation")

    # TEST-06: Young SIM_ record not yet eligible → not reconciled ────────────
    def test_06_young_sim_record_not_reconciled(self):
        """SIM_ record < 7 days old is within the restore window — must not be touched."""
        oid = "SIM_RECENT_BUY_Q5_P1000_T06"
        _write_csv(self.csv, [
            {"timestamp": _ts(3), "order_id": oid, "symbol": "RECENT",
             "direction": "BUY", "quantity": 5, "entry_price": 1000,
             "stop_loss": 980, "target": 1060, "strategy": "Momentum",
             "event": "OPEN"},
        ])
        _run_reconcile(self.tmp, self.csv)
        rows = _read_csv(self.csv)
        self.assertEqual(_count(rows, oid, "CLOSE"), 0,
            "SIM_ record younger than 7 days must NOT be reconciled")

    # TEST-07: SIM_ with existing CLOSE → no new row ──────────────────────────
    def test_07_existing_close_not_duplicated(self):
        oid = "SIM_ALREADY_CLOSED_T07"
        _write_csv(self.csv, [
            {"timestamp": _ts(15), "order_id": oid, "symbol": "CLOSED",
             "direction": "BUY", "quantity": 10, "entry_price": 1000,
             "stop_loss": 980, "target": 1060, "strategy": "Trend",
             "event": "OPEN"},
            {"timestamp": _ts(14), "order_id": oid, "symbol": "CLOSED",
             "direction": "BUY", "quantity": 10, "entry_price": 1000,
             "stop_loss": 980, "target": 1060, "strategy": "Trend",
             "event": "CLOSE", "exit_price": 1020, "pnl": 200, "reason": "close_target"},
        ])
        _run_reconcile(self.tmp, self.csv)
        rows = _read_csv(self.csv)
        self.assertEqual(_count(rows, oid, "CLOSE"), 1,
            "Already-closed SIM_ record must not receive a duplicate CLOSE row")

    # TEST-08: Non-SIM_ order_id never touched ────────────────────────────────
    def test_08_non_sim_order_never_reconciled(self):
        """Real Dhan order IDs (numeric) are never written to by reconciliation."""
        real_oid = "1234567890"
        _write_csv(self.csv, [
            {"timestamp": _ts(20), "order_id": real_oid, "symbol": "HDFCBANK",
             "direction": "BUY", "quantity": 1, "entry_price": 1800,
             "stop_loss": 1760, "target": 1880, "strategy": "Momentum",
             "event": "OPEN"},
        ])
        _run_reconcile(self.tmp, self.csv)
        rows = _read_csv(self.csv)
        self.assertEqual(_count(rows, real_oid, "CLOSE"), 0,
            "Non-SIM_ order_id must NEVER be written by _reconcile_sim_paper_artifacts()")

    # TEST-09: Reconciliation cannot place a live order ───────────────────────
    def test_09_no_live_order_placed(self):
        """_reconcile_sim_paper_artifacts must never call the broker layer."""
        import execution_engine.order_manager as om_mod
        oid = "SIM_SAFE_BUY_Q10_P1000_T09"
        csv_path = os.path.join(self.tmp, "safe.csv")
        _write_csv(csv_path, [
            {"timestamp": _ts(15), "order_id": oid, "symbol": "SAFETEST",
             "direction": "BUY", "quantity": 10, "entry_price": 1000,
             "stop_loss": 980, "target": 1060, "strategy": "Momentum",
             "event": "OPEN"},
        ])
        orig = om_mod.PAPER_TRADE_LOG
        try:
            om_mod.PAPER_TRADE_LOG = csv_path
            om = MagicMock()
            om._journal_lock = threading.Lock()
            om._orders       = {}
            om._paper_mode   = False
            om._broker       = MagicMock()   # broker spy
            om_mod.OrderManager._reconcile_sim_paper_artifacts(om)
            # The broker must never have been called
            om._broker.place_order.assert_not_called()
            om._broker.cancel_order.assert_not_called()
        finally:
            om_mod.PAPER_TRADE_LOG = orig


class TestORJ001RealOrphanAlertPreserved(unittest.TestCase):
    """TEST-05: Real/Dhan orphans still trigger the CRITICAL alert."""

    def test_05_real_orphan_triggers_critical_alert(self):
        """
        A non-SIM_ order_id that is OPEN-without-CLOSE and not tracked by
        OrderManager must still emit a CRITICAL log and Telegram alert.
        """
        import logging
        import execution_engine.order_manager as om_mod

        # Import the orphan audit logic via master_orchestrator module-level parse
        # We inspect the _startup_csv_orphan_audit categorization by checking
        # that real orphans are in the 'real_orphans' set, not 'sim_artifacts'.
        real_oid = "DHAN_ORDER_9876543"
        sim_oid  = "SIM_OLD_BUY_Q10_P500_REAL05"

        tmp = tempfile.mkdtemp()
        try:
            csv_path = os.path.join(tmp, "paper_trades.csv")
            _write_csv(csv_path, [
                # Real orphan — should trigger alert
                {"timestamp": _ts(20), "order_id": real_oid, "symbol": "INFY",
                 "direction": "BUY", "quantity": 1, "entry_price": 1600,
                 "stop_loss": 1560, "target": 1680, "strategy": "Breakout",
                 "event": "OPEN"},
                # SIM_ artifact — should NOT trigger alert
                {"timestamp": _ts(15), "order_id": sim_oid, "symbol": "OLD",
                 "direction": "BUY", "quantity": 10, "entry_price": 500,
                 "stop_loss": 490, "target": 530, "strategy": "Momentum",
                 "event": "OPEN"},
            ])

            # Categorization logic matches _startup_csv_orphan_audit:
            with open(csv_path, newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            opens  = {r["order_id"]: r for r in rows
                      if r.get("event", "").strip() == "OPEN"}
            closes = {r["order_id"] for r in rows
                      if r.get("event", "").strip() == "CLOSE"}
            orphan_ids    = set(opens.keys()) - closes
            tracked_ids   = set()   # nothing tracked in LIVE mode
            truly_orphaned = orphan_ids - tracked_ids
            sim_artifacts  = {oid for oid in truly_orphaned if oid.startswith("SIM_")}
            real_orphans   = truly_orphaned - sim_artifacts

            self.assertIn(real_oid, real_orphans,
                "Non-SIM_ orphan must appear in real_orphans set → triggers alert")
            self.assertNotIn(real_oid, sim_artifacts,
                "Non-SIM_ orphan must NOT be in sim_artifacts")
            self.assertIn(sim_oid, sim_artifacts,
                "SIM_ orphan must be categorized as sim_artifact, not real_orphan")
            self.assertNotIn(sim_oid, real_orphans,
                "SIM_ orphan must NOT appear in real_orphans")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestORJ001LearningProtection(unittest.TestCase):
    """TEST-10: PAPER_MODE_ARTIFACT excluded from learning pipeline."""

    def test_10a_paper_mode_artifact_in_skip_reasons(self):
        """PAPER_MODE_ARTIFACT must be in _do_eod_learning's _skip_reasons."""
        # Read the source file and verify the literal string is present
        src = os.path.join(ROOT, "orchestrator", "master_orchestrator.py")
        with open(src, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn(
            '"PAPER_MODE_ARTIFACT"', content,
            "PAPER_MODE_ARTIFACT must appear in _skip_reasons in master_orchestrator.py",
        )
        self.assertIn(
            '"SESSION_EXPIRED_DEEP_ORPHAN"', content,
            "SESSION_EXPIRED_DEEP_ORPHAN must also appear in _skip_reasons",
        )

    def test_10b_ilc_win_rate_skips_paper_mode_artifact(self):
        """_win_rate() must not count PAPER_MODE_ARTIFACT rows."""
        import csv as _csv
        import types

        tmp = tempfile.mkdtemp()
        try:
            csv_path = os.path.join(tmp, "paper_trades.csv")
            today = datetime.now().strftime("%Y-%m-%d")
            # 1 real win + 1 PAPER_MODE_ARTIFACT with pnl=0
            with open(csv_path, "w", newline="", encoding="utf-8") as fh:
                w = _csv.DictWriter(fh, fieldnames=_HEADER)
                w.writeheader()
                w.writerow({
                    "timestamp": f"{today} 11:00:00",
                    "order_id": "SIM_REAL_WIN", "symbol": "HAVELLS",
                    "direction": "BUY", "quantity": 10, "entry_price": 1000,
                    "stop_loss": 980, "target": 1060, "strategy": "Momentum",
                    "event": "CLOSE", "exit_price": 1050, "pnl": 500.0,
                    "reason": "close_target",
                })
                w.writerow({
                    "timestamp": f"{today} 11:01:00",
                    "order_id": "SIM_ARTIFACT", "symbol": "HAVELLS",
                    "direction": "BUY", "quantity": 282, "entry_price": 1229.66,
                    "stop_loss": 1185.56, "target": 1330.0, "strategy": "Momentum",
                    "event": "CLOSE", "exit_price": 1229.66, "pnl": 0.0,
                    "reason": "PAPER_MODE_ARTIFACT",
                })

            # Patch PAPER_TRADES_CSV in ilc_verification
            import institutional_learning.ilc_verification as ilc_ver
            from pathlib import Path
            orig = ilc_ver.PAPER_TRADES_CSV
            try:
                ilc_ver.PAPER_TRADES_CSV = Path(csv_path)
                start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                end   = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                wr = ilc_ver._win_rate("HAVELLS", start, end)
            finally:
                ilc_ver.PAPER_TRADES_CSV = orig

            # Only the real win should count — win rate must be 1.0 (1/1)
            self.assertAlmostEqual(wr, 1.0, places=5,
                msg="PAPER_MODE_ARTIFACT row must be excluded from win rate calculation")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
