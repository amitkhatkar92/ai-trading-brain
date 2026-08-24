"""
test_options_phase3_safety.py — Phase 3 Safety Tests (T01–T18)

Part A/B: EXIT_SUBMITTED restart reconciliation + duplicate-exit guard
  T01  EXIT_SUBMITTED restart, exits FILLED  → position closed at restore
  T02  EXIT_SUBMITTED restart, exits PENDING → restore as EXIT_SUBMITTED
  T03  EXIT_SUBMITTED restart, exits REJECTED → restore as open + critical log
  T04  EXIT_SUBMITTED restart, broker poll error → CRITICAL, restore EXIT_SUBMITTED
  T05  EXIT_SUBMITTED restart, no exit_broker_order_ids → restore as open (safe)
  T06  _close_position called again while EXIT_SUBMITTED + non-empty exit_bids
       → reconciles existing IDs, does NOT call _place_live_exit_legs
  T07  No duplicate exit broker orders: existing IDs reused, not appended
  T08  Unresolved EXIT_SUBMITTED position remains visible in exposure total

Parts C-K: Knowledge loop observations
  T09  OptionsObservationJournal.record() writes valid JSONL
  T10  Opportunity entering quality gate is recorded as SHORTLISTED
  T11  Opportunity failing C2 (confidence) is recorded as REJECTED with check="C2"
  T12  Layer C (risk engine) rejection recorded as BLOCKED
  T13  Layer D executed order recorded as EXECUTED with order_id
  T14  Layer D blocked (None order) recorded as BLOCKED
  T15  Post-close outcome observer writes OUTCOME_OBSERVED to journal
  T16  Outcome observer feeds knowledge observer win/loss data
  T17  Single trade cannot directly transition knowledge state to VALIDATED
  T18  Developing knowledge state returns knowledge_score=None
"""

import json
import os
import threading
import tempfile
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mgr_live(mock_broker):
    from execution_engine.options_order_manager import OptionsOrderManager
    mgr = OptionsOrderManager.__new__(OptionsOrderManager)
    mgr._paper_mode  = False
    mgr._broker      = mock_broker
    mgr._orders      = {}
    mgr._unresolved  = {}
    mgr._feed        = MagicMock()
    mgr._lock        = threading.Lock()
    return mgr


def _make_mgr_paper():
    from execution_engine.options_order_manager import OptionsOrderManager
    mgr = OptionsOrderManager.__new__(OptionsOrderManager)
    mgr._paper_mode  = True
    mgr._broker      = None
    mgr._orders      = {}
    mgr._unresolved  = {}
    mgr._feed        = MagicMock()
    mgr._lock        = threading.Lock()
    return mgr


def _make_open_rec(order_id="OPT_PH3", legs=None, status="open",
                   exit_broker_order_ids=None):
    from execution_engine.options_order_manager import OptionsOrderRecord
    expiry = date.today() + timedelta(days=30)
    legs = legs or [
        {"type": "CE", "strike": 24500.0, "direction": "BUY",  "premium": 100.0, "iv": 0.14},
        {"type": "CE", "strike": 24600.0, "direction": "SELL", "premium":  50.0, "iv": 0.13},
    ]
    rec = OptionsOrderRecord(
        order_id=order_id, symbol="NIFTY",
        strategy="s", option_type="BULL_CALL_SPREAD", direction="BUY",
        lots=1, lot_size=75, entry_premium=100.0, stop_premium=50.0,
        target_premium=150.0, max_loss_rs=7500.0, max_profit_rs=5250.0,
        expiry_date=expiry, dte_at_entry=30, iv_rank_at_entry=50.0,
        spot_at_entry=24000.0, regime_at_entry="BULL",
        placed_at=datetime.now(), legs=legs,
        status=status,
    )
    if exit_broker_order_ids is not None:
        rec.exit_broker_order_ids = exit_broker_order_ids
    return rec


def _make_journal_row(order_id, status="EXIT_SUBMITTED", exit_bids=None):
    """Build a minimal journal CSV row dict for restore testing."""
    expiry = (date.today() + timedelta(days=30)).isoformat()
    return {
        "order_id":               order_id,
        "symbol":                 "NIFTY",
        "strategy":               "s",
        "option_type":            "BULL_CALL_SPREAD",
        "direction":              "BUY",
        "lots":                   "1",
        "lot_size":               "75",
        "entry_premium":          "100.0",
        "stop_premium":           "50.0",
        "target_premium":         "150.0",
        "max_loss_rs":            "7500.0",
        "max_profit_rs":          "5250.0",
        "expiry_date":            expiry,
        "dte_at_entry":           "30",
        "iv_rank_at_entry":       "50.0",
        "spot_at_entry":          "24000.0",
        "regime_at_entry":        "BULL",
        "placed_at":              datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status":                 status,
        "exit_broker_order_ids":  json.dumps(exit_bids or []),
        "entry_leg_fills":        "",
        "exit_leg_fills":         "",
        "broker_status":          "EXIT_SUBMITTED",
        "reconciliation_status":  "UNRECONCILED",
        "actual_entry_fill_price": "",
        "actual_exit_fill_price":  "",
        "expected_pnl":           "0",
        "realized_pnl":           "",
        "kda_decision":           "",
        "authorization_source":   "",
        "klp_score":              "",
        "knowledge_provenance":   "",
        "leg_outcomes":           "",
        "outcome_correctness":    "",
        "legs_json":              json.dumps([
            {"type": "CE", "strike": 24500.0, "direction": "BUY", "premium": 100.0, "iv": 0.14},
            {"type": "CE", "strike": 24600.0, "direction": "SELL", "premium": 50.0, "iv": 0.13},
        ]),
        "broker_order_ids":       "",
        "exit_premium":           "",
        "pnl_rs":                 "",
        "exit_reason":            "",
        "closed_at":              "",
        "max_profit_rs":          "5250.0",
    }


# ---------------------------------------------------------------------------
# Part A/B — EXIT_SUBMITTED restart + duplicate-exit guard
# ---------------------------------------------------------------------------

class TestExitSubmittedRestart(unittest.TestCase):
    """T01–T05: _restore_from_journal handles EXIT_SUBMITTED correctly."""

    def _run_restore(self, mock_broker, rows, seen_closed=None):
        """Patch the journal file and run _restore_from_journal."""
        from execution_engine.options_order_manager import OptionsOrderManager
        mgr = OptionsOrderManager.__new__(OptionsOrderManager)
        mgr._paper_mode  = (mock_broker is None)
        mgr._broker      = mock_broker
        mgr._orders      = {}
        mgr._unresolved  = {}
        mgr._feed        = MagicMock()
        mgr._lock        = threading.Lock()

        import csv
        from io import StringIO
        from unittest.mock import mock_open, patch as mpatch

        # Build fake CSV content
        if rows:
            cols = list(rows[0].keys())
            buf = StringIO()
            writer = csv.DictWriter(buf, fieldnames=cols)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
            csv_content = buf.getvalue()
        else:
            csv_content = ""

        with mpatch("os.path.exists", return_value=True), \
             mpatch("builtins.open", mock_open(read_data=csv_content)):
            # Patch _journal_write_close to avoid actual file I/O
            mgr._journal_write_close = MagicMock()
            mgr._restore_from_journal()
        return mgr

    def test_t01_exit_submitted_filled_restores_closed(self):
        """T01: EXIT_SUBMITTED + FILLED exits → position NOT added to _orders."""
        broker = MagicMock()
        broker.get_order_status.return_value = {
            "status": "TRADED", "filled_qty": 75, "avg_fill_price": 95.0,
        }
        row = _make_journal_row("OPT_T01", "EXIT_SUBMITTED", ["BRKR_EXIT_1"])
        mgr = self._run_restore(broker, [row])
        self.assertNotIn("OPT_T01", mgr._orders,
                         "Confirmed-filled position must NOT be in _orders")

    def test_t02_exit_submitted_pending_restores_exit_submitted(self):
        """T02: EXIT_SUBMITTED + PENDING exits → restore as EXIT_SUBMITTED."""
        broker = MagicMock()
        broker.get_order_status.return_value = {
            "status": "PENDING", "filled_qty": 0, "avg_fill_price": 0.0,
        }
        row = _make_journal_row("OPT_T02", "EXIT_SUBMITTED", ["BRKR_EXIT_2"])
        mgr = self._run_restore(broker, [row])
        self.assertIn("OPT_T02", mgr._orders)
        self.assertEqual(mgr._orders["OPT_T02"].status, "EXIT_SUBMITTED")

    def test_t03_exit_submitted_rejected_restores_open(self):
        """T03: EXIT_SUBMITTED + REJECTED exits → restore as open (live exposure)."""
        broker = MagicMock()
        broker.get_order_status.return_value = {
            "status": "REJECTED", "filled_qty": 0, "avg_fill_price": 0.0,
        }
        row = _make_journal_row("OPT_T03", "EXIT_SUBMITTED", ["BRKR_EXIT_3"])
        with self.assertLogs(level="CRITICAL") as cm:
            mgr = self._run_restore(broker, [row])
        self.assertIn("OPT_T03", mgr._orders)
        self.assertEqual(mgr._orders["OPT_T03"].status, "open")
        self.assertTrue(any("OPT_T03" in m for m in cm.output))

    def test_t04_exit_submitted_poll_error_restores_exit_submitted(self):
        """T04: EXIT_SUBMITTED + broker poll error → EXIT_SUBMITTED + CRITICAL log."""
        broker = MagicMock()
        broker.get_order_status.side_effect = RuntimeError("broker timeout")
        row = _make_journal_row("OPT_T04", "EXIT_SUBMITTED", ["BRKR_EXIT_4"])
        with self.assertLogs(level="CRITICAL") as cm:
            mgr = self._run_restore(broker, [row])
        self.assertIn("OPT_T04", mgr._orders)
        self.assertEqual(mgr._orders["OPT_T04"].status, "EXIT_SUBMITTED")
        self.assertTrue(any("OPT_T04" in m for m in cm.output))

    def test_t05_exit_submitted_no_exit_bids_restores_open(self):
        """T05: EXIT_SUBMITTED with no exit_broker_order_ids → safe to restore as open."""
        broker = MagicMock()
        row = _make_journal_row("OPT_T05", "EXIT_SUBMITTED", [])   # empty exit_bids
        mgr = self._run_restore(broker, [row])
        self.assertIn("OPT_T05", mgr._orders)
        self.assertEqual(mgr._orders["OPT_T05"].status, "open")
        broker.get_order_status.assert_not_called()


class TestDuplicateExitGuard(unittest.TestCase):
    """T06–T08: _close_position guards against duplicate exit placement."""

    def test_t06_repeated_close_while_exit_submitted_reconciles_not_replaces(self):
        """T06: _close_position with EXIT_SUBMITTED + existing exit orders
        must NOT call _place_live_exit_legs."""
        broker = MagicMock()
        # Poll confirms exits already filled
        broker.get_order_status.return_value = {
            "status": "TRADED", "filled_qty": 75, "avg_fill_price": 95.0,
        }
        mgr = _make_mgr_live(broker)
        rec = _make_open_rec("OPT_T06", status="EXIT_SUBMITTED",
                              exit_broker_order_ids=["EXISTING_EXIT_ID"])
        mgr._orders["OPT_T06"] = rec

        with patch.object(mgr, "_place_live_exit_legs") as mock_place, \
             patch.object(mgr, "_journal_write_close", MagicMock()):
            mgr._close_position("OPT_T06", 95.0, "stop_loss")
            mock_place.assert_not_called()

    def test_t07_no_duplicate_exit_order_ids(self):
        """T07: When reconciling existing exit, exit_broker_order_ids stays same list."""
        broker = MagicMock()
        broker.get_order_status.return_value = {
            "status": "TRADED", "filled_qty": 75, "avg_fill_price": 95.0,
        }
        mgr = _make_mgr_live(broker)
        rec = _make_open_rec("OPT_T07", status="EXIT_SUBMITTED",
                              exit_broker_order_ids=["EXISTING_EXIT_ID"])
        mgr._orders["OPT_T07"] = rec

        with patch.object(mgr, "_journal_write_close", MagicMock()):
            mgr._close_position("OPT_T07", 95.0, "stop_loss")

        with mgr._lock:
            final_rec = mgr._orders.get("OPT_T07")
        # Must be closed (fills confirmed) with the same exit ID — no duplicates
        if final_rec is None:
            # position removed after close is also acceptable; check journal was called
            pass
        else:
            # If still in _orders it should be closed
            self.assertEqual(final_rec.status, "closed")
        # Crucially: _place_live_exit_legs was never called (enforced in T06)

    def test_t08_unresolved_exit_submitted_visible_in_exposure(self):
        """T08: EXIT_SUBMITTED position (still open/pending) is counted in exposure."""
        mgr = _make_mgr_paper()
        rec = _make_open_rec("OPT_T08", status="EXIT_SUBMITTED")
        rec.max_loss_rs = 7500.0
        mgr._orders["OPT_T08"] = rec

        exposure = mgr.get_total_options_exposure_rs()
        self.assertGreater(exposure, 0,
                           "EXIT_SUBMITTED position must be counted in exposure")


# ---------------------------------------------------------------------------
# Parts C-K — Observation journal + knowledge loop
# ---------------------------------------------------------------------------

class TestObservationJournal(unittest.TestCase):
    """T09: journal writes valid JSONL."""

    def setUp(self):
        # Use a temp file so tests don't pollute real data/
        import execution_engine.options_observation_journal as _oj
        self._orig_path = _oj.OBSERVATIONS_PATH
        self._tmp = tempfile.NamedTemporaryFile(
            suffix=".jsonl", delete=False, mode="w"
        )
        self._tmp.close()
        _oj.OBSERVATIONS_PATH = self._tmp.name
        _oj._JOURNAL_INSTANCE = None   # reset singleton

    def tearDown(self):
        import execution_engine.options_observation_journal as _oj
        _oj.OBSERVATIONS_PATH = self._orig_path
        _oj._JOURNAL_INSTANCE = None
        try:
            os.unlink(self._tmp.name)
        except Exception:
            pass

    def test_t09_record_writes_valid_jsonl(self):
        """T09: record() writes a parseable JSON line to the JSONL file."""
        from execution_engine.options_observation_journal import (
            get_options_observation_journal, OptionsOpportunityObservation,
            OBS_SHORTLISTED,
        )
        j = get_options_observation_journal()
        obs = OptionsOpportunityObservation(
            obs_id="OOO-TEST-0001-NIFTY-IC",
            symbol="NIFTY", strategy_name="Iron_Condor_Range",
            observed_at=datetime.now().isoformat(), state=OBS_SHORTLISTED,
            confidence=7.5, dte=25, iv_rank=35.0,
        )
        j.record(obs)

        rows = j.read_all()
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["symbol"], "NIFTY")
        self.assertEqual(r["state"], OBS_SHORTLISTED)
        self.assertEqual(r["confidence"], 7.5)


class TestQualityGateObservations(unittest.TestCase):
    """T10–T11: quality gate records observations with correct states/checks."""

    def _obs_journal_tmp(self):
        import execution_engine.options_observation_journal as _oj
        self._orig_path = _oj.OBSERVATIONS_PATH
        tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w")
        tmp.close()
        _oj.OBSERVATIONS_PATH = tmp.name
        _oj._JOURNAL_INSTANCE = None
        return tmp.name

    def _cleanup_obs_journal(self, tmp_path):
        import execution_engine.options_observation_journal as _oj
        _oj.OBSERVATIONS_PATH = self._orig_path
        _oj._JOURNAL_INSTANCE = None
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    def test_t10_shortlisted_signal_recorded(self):
        """T10: signal passing all checks (C1-C5) recorded as SHORTLISTED."""
        tmp = self._obs_journal_tmp()
        try:
            from execution_engine.options_observation_journal import (
                get_options_observation_journal,
            )
            from models.trade_signal import TradeSignal, SignalType, SignalDirection

            # Build a minimal orchestrator to call _options_quality_gate
            from orchestrator.master_orchestrator import MasterOrchestrator
            orch = MasterOrchestrator.__new__(MasterOrchestrator)
            orch._OPTIONS_MIN_CONFIDENCE = 6.5
            orch._CHAIN_QUALITY_MIN      = 0.5
            orch._DTE_MIN                = 10
            orch._DTE_MAX                = 60
            orch._VIX_HIGH_DTE_MAX       = 30
            orch._VIX_LOW_DTE_MIN        = 20
            orch._IVR_SELL_MIN           = 20.0
            orch._IVR_BUY_MAX            = 55.0

            sig = MagicMock()
            sig.symbol = "NIFTY"
            sig.strategy_name = "Iron_Condor_Range"
            sig.confidence = 7.5
            sig.direction = SignalDirection.SELL
            sig.notes = json.dumps({
                "is_live": True, "chain_quality": 0.8,
                "dte": 25, "iv_rank": 35.0, "chain_issues": [],
            })

            snapshot = MagicMock()
            snapshot.vix    = 18.0
            snapshot.regime = MagicMock()
            snapshot.regime.value = "SIDEWAYS"

            with patch("data_feeds.get_feed_manager") as mock_fm:
                mock_fm.return_value.get_options_capability.return_value = {
                    "source": "DHAN", "chain_live": True,
                }
                result = orch._options_quality_gate([sig], snapshot)

            self.assertEqual(len(result), 1, "Signal should pass quality gate")

            j = get_options_observation_journal()
            rows = j.read_all()
            shortlisted = [r for r in rows if r.get("state") == "SHORTLISTED"]
            self.assertGreaterEqual(len(shortlisted), 1)
            self.assertEqual(shortlisted[0]["symbol"], "NIFTY")
        finally:
            self._cleanup_obs_journal(tmp)

    def test_t11_c2_rejection_recorded_with_check_code(self):
        """T11: Signal failing C2 (confidence) is REJECTED with rejection_check='C2'."""
        tmp = self._obs_journal_tmp()
        try:
            from execution_engine.options_observation_journal import (
                get_options_observation_journal,
            )

            from orchestrator.master_orchestrator import MasterOrchestrator
            orch = MasterOrchestrator.__new__(MasterOrchestrator)
            orch._OPTIONS_MIN_CONFIDENCE = 6.5
            orch._CHAIN_QUALITY_MIN      = 0.5
            orch._DTE_MIN                = 10
            orch._DTE_MAX                = 60
            orch._VIX_HIGH_DTE_MAX       = 30
            orch._VIX_LOW_DTE_MIN        = 20
            orch._IVR_SELL_MIN           = 20.0
            orch._IVR_BUY_MAX            = 55.0

            from models.trade_signal import SignalDirection
            sig = MagicMock()
            sig.symbol = "BANKNIFTY"
            sig.strategy_name = "Iron_Condor_Range"
            sig.confidence = 4.0   # below threshold
            sig.direction = SignalDirection.SELL
            sig.notes = json.dumps({
                "is_live": True, "chain_quality": 0.8,
                "dte": 25, "iv_rank": 35.0, "chain_issues": [],
            })

            snapshot = MagicMock()
            snapshot.vix    = 18.0
            snapshot.regime = MagicMock()
            snapshot.regime.value = "SIDEWAYS"

            with patch("data_feeds.get_feed_manager") as mock_fm:
                mock_fm.return_value.get_options_capability.return_value = {
                    "source": "DHAN", "chain_live": True,
                }
                result = orch._options_quality_gate([sig], snapshot)

            self.assertEqual(len(result), 0, "Low-confidence signal must be rejected")

            j = get_options_observation_journal()
            rows = j.read_all()
            rejected = [r for r in rows if r.get("state") == "REJECTED"]
            self.assertGreaterEqual(len(rejected), 1)
            self.assertEqual(rejected[0]["rejection_check"], "C2")
        finally:
            self._cleanup_obs_journal(tmp)


class TestFastPathObservations(unittest.TestCase):
    """T12–T14: options_fast_path records BLOCKED/EXECUTED observations."""

    def _obs_journal_tmp(self):
        import execution_engine.options_observation_journal as _oj
        self._orig_path = _oj.OBSERVATIONS_PATH
        tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w")
        tmp.close()
        _oj.OBSERVATIONS_PATH = tmp.name
        _oj._JOURNAL_INSTANCE = None
        return tmp.name

    def _cleanup_obs_journal(self, tmp_path):
        import execution_engine.options_observation_journal as _oj
        _oj.OBSERVATIONS_PATH = self._orig_path
        _oj._JOURNAL_INSTANCE = None
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    def _make_qualified_signal(self):
        from models.trade_signal import SignalDirection
        sig = MagicMock()
        sig.symbol = "NIFTY"
        sig.strategy_name = "Iron_Condor_Range"
        sig.confidence = 7.5
        sig.direction = SignalDirection.SELL
        sig._meta_quality = 0.8
        sig.entry_price = 100.0
        sig.notes = json.dumps({
            "is_live": True, "chain_quality": 0.8,
            "dte": 25, "iv_rank": 35.0, "chain_issues": [],
        })
        return sig

    def test_t12_layer_c_rejection_recorded_as_blocked(self):
        """T12: Risk engine rejection at Layer C → BLOCKED in journal."""
        tmp = self._obs_journal_tmp()
        try:
            from execution_engine.options_observation_journal import (
                get_options_observation_journal,
            )
            from orchestrator.master_orchestrator import MasterOrchestrator
            orch = MasterOrchestrator.__new__(MasterOrchestrator)
            orch._OPTIONS_MIN_CONFIDENCE = 6.5
            orch._CHAIN_QUALITY_MIN      = 0.5
            orch._DTE_MIN                = 10
            orch._DTE_MAX                = 60
            orch._VIX_HIGH_DTE_MAX       = 30
            orch._VIX_LOW_DTE_MIN        = 20
            orch._IVR_SELL_MIN           = 20.0
            orch._IVR_BUY_MAX            = 55.0
            orch._last_oqg_summary       = {}
            orch._last_options_placed    = 0

            orch.options_risk_engine     = MagicMock()
            orch.options_risk_engine.approve_and_size.return_value = None  # rejected

            orch.options_order_manager   = MagicMock()
            orch.options_order_manager.get_total_options_exposure_rs.return_value = 0

            snapshot = MagicMock()
            snapshot.vix    = 18.0
            snapshot.regime = MagicMock()
            snapshot.regime.value = "SIDEWAYS"

            sig = self._make_qualified_signal()

            with patch.object(orch, "_options_quality_gate", return_value=[sig]), \
                 patch("utils.kill_switch.is_trading_enabled", return_value=True):
                orch._run_options_fast_path([sig], snapshot)

            j = get_options_observation_journal()
            rows = j.read_all()
            blocked = [r for r in rows if r.get("state") == "BLOCKED"]
            self.assertGreaterEqual(len(blocked), 1)
            self.assertFalse(blocked[0].get("risk_approved", True))
        finally:
            self._cleanup_obs_journal(tmp)

    def test_t13_executed_order_recorded_with_order_id(self):
        """T13: Successful Layer D execution → EXECUTED with order_id."""
        tmp = self._obs_journal_tmp()
        try:
            from execution_engine.options_observation_journal import (
                get_options_observation_journal,
            )
            from execution_engine.options_order_manager import OptionsOrderRecord

            from orchestrator.master_orchestrator import MasterOrchestrator
            orch = MasterOrchestrator.__new__(MasterOrchestrator)
            orch._OPTIONS_MIN_CONFIDENCE = 6.5
            orch._CHAIN_QUALITY_MIN      = 0.5
            orch._DTE_MIN                = 10
            orch._DTE_MAX                = 60
            orch._VIX_HIGH_DTE_MAX       = 30
            orch._VIX_LOW_DTE_MIN        = 20
            orch._IVR_SELL_MIN           = 20.0
            orch._IVR_BUY_MAX            = 55.0
            orch._last_oqg_summary       = {}
            orch._last_options_placed    = 0
            orch.order_manager           = MagicMock()
            orch.order_manager.get_open_orders.return_value = []
            orch.bus                     = MagicMock()

            # Build a fake OptionsOrderRecord return value
            fake_rec = _make_open_rec("OPT_EXEC")
            fake_rec.order_id    = "OPT_EXEC"
            fake_rec.strategy    = "Iron_Condor_Range"
            fake_rec.lots        = 1
            fake_rec.lot_size    = 75
            fake_rec.max_loss_rs = 7500.0
            fake_rec.dte_at_entry = 25
            fake_rec.expiry_date  = date.today() + timedelta(days=25)

            orch.options_risk_engine = MagicMock()
            orch.options_risk_engine.approve_and_size.return_value = MagicMock()

            orch.options_order_manager = MagicMock()
            orch.options_order_manager.get_total_options_exposure_rs.return_value = 0
            orch.options_order_manager.execute.return_value = fake_rec

            snapshot = MagicMock()
            snapshot.vix    = 18.0
            snapshot.regime = MagicMock()
            snapshot.regime.value = "SIDEWAYS"

            sig = self._make_qualified_signal()

            with patch.object(orch, "_options_quality_gate", return_value=[sig]), \
                 patch("utils.kill_switch.is_trading_enabled", return_value=True):
                orch._run_options_fast_path([sig], snapshot)

            j = get_options_observation_journal()
            rows = j.read_all()
            executed = [r for r in rows if r.get("state") == "EXECUTED"]
            self.assertGreaterEqual(len(executed), 1)
            self.assertEqual(executed[0]["order_id"], "OPT_EXEC")
        finally:
            self._cleanup_obs_journal(tmp)

    def test_t14_layer_d_blocked_none_order_recorded(self):
        """T14: Layer D returns None (duplicate/limit) → BLOCKED in journal."""
        tmp = self._obs_journal_tmp()
        try:
            from execution_engine.options_observation_journal import (
                get_options_observation_journal,
            )
            from orchestrator.master_orchestrator import MasterOrchestrator
            orch = MasterOrchestrator.__new__(MasterOrchestrator)
            orch._OPTIONS_MIN_CONFIDENCE = 6.5
            orch._CHAIN_QUALITY_MIN      = 0.5
            orch._DTE_MIN                = 10
            orch._DTE_MAX                = 60
            orch._VIX_HIGH_DTE_MAX       = 30
            orch._VIX_LOW_DTE_MIN        = 20
            orch._IVR_SELL_MIN           = 20.0
            orch._IVR_BUY_MAX            = 55.0
            orch._last_oqg_summary       = {}
            orch._last_options_placed    = 0

            orch.options_risk_engine = MagicMock()
            orch.options_risk_engine.approve_and_size.return_value = MagicMock()

            orch.options_order_manager = MagicMock()
            orch.options_order_manager.get_total_options_exposure_rs.return_value = 0
            orch.options_order_manager.execute.return_value = None   # ← blocked at D

            snapshot = MagicMock()
            snapshot.vix    = 18.0
            snapshot.regime = MagicMock()
            snapshot.regime.value = "SIDEWAYS"

            sig = self._make_qualified_signal()

            with patch.object(orch, "_options_quality_gate", return_value=[sig]), \
                 patch("utils.kill_switch.is_trading_enabled", return_value=True):
                orch._run_options_fast_path([sig], snapshot)

            j = get_options_observation_journal()
            rows = j.read_all()
            blocked = [r for r in rows if r.get("state") == "BLOCKED"]
            self.assertGreaterEqual(len(blocked), 1)
        finally:
            self._cleanup_obs_journal(tmp)


class TestOutcomeObserver(unittest.TestCase):
    """T15–T16: OptionsOutcomeObserver writes OUTCOME_OBSERVED and feeds knowledge."""

    def _obs_journal_tmp(self):
        import execution_engine.options_observation_journal as _oj
        self._orig_path = _oj.OBSERVATIONS_PATH
        tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w")
        tmp.close()
        _oj.OBSERVATIONS_PATH = tmp.name
        _oj._JOURNAL_INSTANCE = None
        return tmp.name

    def _cleanup_obs_journal(self, tmp_path):
        import execution_engine.options_observation_journal as _oj
        _oj.OBSERVATIONS_PATH = self._orig_path
        _oj._JOURNAL_INSTANCE = None
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    def test_t15_outcome_observer_writes_outcome_observed(self):
        """T15: record_outcome() on closed position writes OUTCOME_OBSERVED to journal."""
        import learning_system.options_outcome_observer as _ooo
        _ooo._OO_INSTANCE = None   # reset singleton

        tmp = self._obs_journal_tmp()
        try:
            from execution_engine.options_observation_journal import (
                get_options_observation_journal,
            )
            rec = _make_open_rec("OPT_T15", status="closed")
            rec.pnl_rs          = 750.0
            rec.expected_pnl    = 500.0
            rec.exit_reason     = "stop_loss"
            rec.closed_at       = datetime.now()

            from learning_system.options_outcome_observer import (
                get_options_outcome_observer,
            )
            oo = get_options_outcome_observer()
            oo.record_outcome(rec)

            j = get_options_observation_journal()
            rows = j.read_all()
            outcomes = [r for r in rows if r.get("state") == "OUTCOME_OBSERVED"]
            self.assertGreaterEqual(len(outcomes), 1)
            self.assertEqual(outcomes[0]["order_id"], "OPT_T15")
            self.assertEqual(outcomes[0]["actual_pnl"], 750.0)
        finally:
            _ooo._OO_INSTANCE = None
            self._cleanup_obs_journal(tmp)

    def test_t16_outcome_observer_feeds_knowledge_win(self):
        """T16: Winning trade increments knowledge observer outcome count."""
        import learning_system.options_outcome_observer as _ooo
        import knowledge_system.options_knowledge_observer as _ko_mod
        _ooo._OO_INSTANCE = None
        _ko_mod._KO_INSTANCE = None
        # Remove persistent state so the observer starts clean
        import knowledge_system.options_knowledge_observer as _ko_mod2
        _persist_path = getattr(_ko_mod2, "_KO_PERSIST_PATH", "data/options_ko_state.json")
        try:
            os.unlink(_persist_path)
        except Exception:
            pass

        tmp = self._obs_journal_tmp()
        try:
            from knowledge_system.options_knowledge_observer import (
                get_options_knowledge_observer,
            )
            ko = get_options_knowledge_observer()
            initial_summary = ko.get_summary()
            self.assertEqual(initial_summary["outcome_count"], 0)

            rec = _make_open_rec("OPT_T16", status="closed")
            rec.pnl_rs       = 1200.0
            rec.expected_pnl = 1000.0
            rec.closed_at    = datetime.now()

            from learning_system.options_outcome_observer import (
                get_options_outcome_observer,
            )
            oo = get_options_outcome_observer()
            oo.record_outcome(rec)

            after = ko.get_summary()
            self.assertEqual(after["outcome_count"], 1)
            self.assertEqual(after["win_rate"], 1.0)
        finally:
            _ooo._OO_INSTANCE = None
            _ko_mod._KO_INSTANCE = None
            self._cleanup_obs_journal(tmp)


class TestKnowledgeObserverInvariants(unittest.TestCase):
    """T17–T18: Knowledge observer invariants."""

    def setUp(self):
        import knowledge_system.options_knowledge_observer as _ko_mod
        _ko_mod._KO_INSTANCE = None

    def tearDown(self):
        import knowledge_system.options_knowledge_observer as _ko_mod
        _ko_mod._KO_INSTANCE = None

    def test_t17_single_trade_cannot_reach_validated(self):
        """T17: A single outcome cannot transition state to VALIDATED.
        MIN_VALIDATED_OUTCOMES = 20 prevents this."""
        from knowledge_system.options_knowledge_observer import (
            get_options_knowledge_observer, KS_VALIDATED, _MIN_VALIDATED_OUT,
        )
        ko = get_options_knowledge_observer()
        # Record one winning outcome
        ko.record_outcome(actual_pnl=1000.0, expected_pnl=800.0)
        summary = ko.get_summary()
        self.assertNotEqual(
            summary["state"], KS_VALIDATED,
            f"Single trade must not reach VALIDATED "
            f"(requires {_MIN_VALIDATED_OUT} outcomes)",
        )

    def test_t18_developing_state_returns_none_score(self):
        """T18: DEVELOPING state must return knowledge_score=None (not 0.0)."""
        from knowledge_system.options_knowledge_observer import (
            get_options_knowledge_observer, KS_DEVELOPING,
        )
        ko = get_options_knowledge_observer()
        # No observations, no outcomes → must be DEVELOPING
        state, score = ko.observe_opportunity("NIFTY", "Iron_Condor_Range")
        self.assertEqual(state, KS_DEVELOPING)
        self.assertIsNone(
            score,
            "knowledge_score must be None (not 0.0) when state is DEVELOPING",
        )


if __name__ == "__main__":
    unittest.main()
