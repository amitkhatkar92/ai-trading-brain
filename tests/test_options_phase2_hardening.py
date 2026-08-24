"""
test_options_phase2_hardening.py — Phase 2 Hardening Safety Tests (A-P)

Covers:
  A. max_loss_rs_estimate persisted in rollback journal (Phase 1)
  B. _restore_unresolved raises CRITICAL when max_loss_rs_estimate missing (Phase 1)
  C. _ensure_rollback_journal migrates missing columns from old files (Phase 1)
  D. _poll_entry_fills returns dicts with expected keys (Phase 2)
  E. _poll_entry_fills handles broker exception gracefully (Phase 2)
  F. _poll_exit_fills reverses leg direction (Phase 2/3)
  G. _compute_net_fill_price returns abs net for valid fills (Phase 4)
  H. _compute_net_fill_price returns None for zero qty/price (Phase 4)
  I. _compute_realized_pnl returns None when actual prices absent (Phase 4)
  J. _compute_realized_pnl correct for credit spread (Phase 4)
  K. _compute_realized_pnl correct for debit spread (Phase 4)
  L. _close_position: EXIT_SUBMITTED set before exit placement (Phase 3)
  M. _close_position: stays EXIT_SUBMITTED on unconfirmed fills (Phase 3)
  N. _close_position: stays EXIT_SUBMITTED when place_live_exit_legs returns None (Phase 3)
  O. _close_position: marks closed when fills confirmed; realized_pnl written (Phase 3/4)
  P. knowledge provenance fields captured in execute() (Phase 5)
"""

import csv
import json
import os
import threading
import unittest
from datetime import date, datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _make_open_rec(order_id="OPT_PH2", legs=None):
    from execution_engine.options_order_manager import OptionsOrderRecord
    expiry = date.today() + timedelta(days=30)
    if legs is None:
        legs = [
            {"type": "CE", "strike": 24500.0, "direction": "BUY",  "premium": 100.0, "iv": 0.14},
            {"type": "CE", "strike": 24600.0, "direction": "SELL", "premium":  50.0, "iv": 0.13},
        ]
    return OptionsOrderRecord(
        order_id=order_id, symbol="NIFTY",
        strategy="s", option_type="BULL_CALL_SPREAD", direction="BUY",
        lots=1, lot_size=75, entry_premium=100.0, stop_premium=50.0,
        target_premium=150.0, max_loss_rs=7500.0, max_profit_rs=5250.0,
        expiry_date=expiry, dte_at_entry=30, iv_rank_at_entry=50.0,
        spot_at_entry=24000.0, regime_at_entry="BULL",
        placed_at=datetime.now(), legs=legs,
    )


# ---------------------------------------------------------------------------
# A — max_loss_rs_estimate persisted in rollback journal
# ---------------------------------------------------------------------------
class TestA_RollbackEstimatePersisted(unittest.TestCase):

    def test_a01_estimate_written_to_csv_row(self):
        """_record_rollback_failure writes max_loss_rs_estimate to the CSV row."""
        import tempfile, shutil
        from execution_engine.options_order_manager import (
            OptionsOrderManager, ROLLBACK_FAILURE_COLUMNS, ROLLBACK_FAILURES_PATH,
        )

        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "rf.csv")
        try:
            # Write header manually
            with open(tmp_path, "w", newline="", encoding="utf-8") as fh:
                csv.DictWriter(fh, fieldnames=ROLLBACK_FAILURE_COLUMNS).writeheader()

            mgr = _make_mgr_live(MagicMock())
            rec  = _make_open_rec()
            leg  = {"type": "CE", "strike": 24500.0, "direction": "BUY", "premium": 100.0}

            with patch(
                "execution_engine.options_order_manager.ROLLBACK_FAILURES_PATH",
                tmp_path,
            ):
                mgr._record_rollback_failure(
                    original_order_id="OID1",
                    security_id="99",
                    leg=leg,
                    rec=rec,
                    original_tx="BUY",
                    filled_qty_raw=75,
                    reversal_tx="SELL",
                    reversal_order_id=None,
                    status="ROLLBACK_FAILED",
                    reason="order rejected",
                    per_leg_max_loss=2500.0,
                )

            with open(tmp_path, newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["max_loss_rs_estimate"], "2500.0")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# B — _restore_unresolved logs CRITICAL when estimate missing
# ---------------------------------------------------------------------------
class TestB_RestoreUnresolvedCritical(unittest.TestCase):

    def test_b01_critical_logged_when_estimate_empty(self):
        """_restore_unresolved logs CRITICAL if max_loss_rs_estimate is empty."""
        import tempfile, shutil
        from execution_engine.options_order_manager import (
            OptionsOrderManager, ROLLBACK_FAILURE_COLUMNS,
        )

        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "rf.csv")
        try:
            row = {c: "" for c in ROLLBACK_FAILURE_COLUMNS}
            row.update({
                "recorded_at": "2026-01-01 09:00:00",
                "exposure_id": "EXP_001",
                "trade_id": "T1",
                "original_order_id": "OID1",
                "status": "UNRESOLVED_LIVE_EXPOSURE",
                "max_loss_rs_estimate": "",  # empty
            })
            with open(tmp_path, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=ROLLBACK_FAILURE_COLUMNS)
                w.writeheader()
                w.writerow(row)

            mgr = _make_mgr_live(MagicMock())
            with patch(
                "execution_engine.options_order_manager.ROLLBACK_FAILURES_PATH",
                tmp_path,
            ):
                with self.assertLogs(
                    "execution_engine.options_order_manager", level="CRITICAL"
                ) as cm:
                    mgr._restore_unresolved()

            self.assertTrue(any("CRITICAL" in msg for msg in cm.output))
            self.assertIn("EXP_001", mgr._unresolved)
            self.assertEqual(mgr._unresolved["EXP_001"]["max_loss_rs_estimate"], 0.0)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_b02_estimate_restored_when_present(self):
        """_restore_unresolved correctly restores a float estimate."""
        import tempfile, shutil
        from execution_engine.options_order_manager import (
            OptionsOrderManager, ROLLBACK_FAILURE_COLUMNS,
        )

        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "rf.csv")
        try:
            row = {c: "" for c in ROLLBACK_FAILURE_COLUMNS}
            row.update({
                "recorded_at": "2026-01-01 09:00:00",
                "exposure_id": "EXP_002",
                "trade_id": "T2",
                "original_order_id": "OID2",
                "status": "UNRESOLVED_LIVE_EXPOSURE",
                "max_loss_rs_estimate": "3750.5",
            })
            with open(tmp_path, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=ROLLBACK_FAILURE_COLUMNS)
                w.writeheader()
                w.writerow(row)

            mgr = _make_mgr_live(MagicMock())
            with patch(
                "execution_engine.options_order_manager.ROLLBACK_FAILURES_PATH",
                tmp_path,
            ):
                mgr._restore_unresolved()

            self.assertIn("EXP_002", mgr._unresolved)
            self.assertAlmostEqual(mgr._unresolved["EXP_002"]["max_loss_rs_estimate"], 3750.5)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# C — _ensure_rollback_journal migration
# ---------------------------------------------------------------------------
class TestC_RollbackJournalMigration(unittest.TestCase):

    def test_c01_adds_missing_column_to_existing_file(self):
        """_ensure_rollback_journal migrates an old CSV missing max_loss_rs_estimate."""
        import tempfile, shutil
        from execution_engine.options_order_manager import ROLLBACK_FAILURE_COLUMNS

        old_cols = [c for c in ROLLBACK_FAILURE_COLUMNS if c != "max_loss_rs_estimate"]
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "rf.csv")
        try:
            # Write an old-format file (without max_loss_rs_estimate)
            with open(tmp_path, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=old_cols)
                w.writeheader()
                w.writerow({c: f"val_{c}" for c in old_cols})

            mgr = _make_mgr_paper()
            with patch(
                "execution_engine.options_order_manager.ROLLBACK_FAILURES_PATH",
                tmp_path,
            ):
                mgr._ensure_rollback_journal()

            with open(tmp_path, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                header = reader.fieldnames or []
                rows = list(reader)

            self.assertIn("max_loss_rs_estimate", header)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["max_loss_rs_estimate"], "")  # backfilled as empty
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# D — _poll_entry_fills
# ---------------------------------------------------------------------------
class TestD_PollEntryFills(unittest.TestCase):

    def test_d01_returns_correct_structure(self):
        """_poll_entry_fills returns list of dicts with expected keys."""
        mock_broker = MagicMock()
        mock_broker.get_order_status.return_value = {
            "status": "TRADED", "filled_qty": 75, "avg_fill_price": 120.0,
        }
        mgr = _make_mgr_live(mock_broker)
        rec = _make_open_rec()
        rec.broker_order_ids = ["BID_001", "BID_002"]

        fills = mgr._poll_entry_fills(rec, ["BID_001", "BID_002"])

        self.assertEqual(len(fills), 2)
        for fill in fills:
            for key in ("order_id", "direction", "status", "qty_filled", "avg_price", "ts"):
                self.assertIn(key, fill)

    def test_d02_fills_use_buy_first_order(self):
        """_poll_entry_fills correlates in BUY-first sorted order."""
        mock_broker = MagicMock()
        mock_broker.get_order_status.return_value = {
            "status": "TRADED", "filled_qty": 75, "avg_fill_price": 100.0,
        }
        mgr = _make_mgr_live(mock_broker)
        rec = _make_open_rec()   # legs: BUY CE 24500, SELL CE 24600

        fills = mgr._poll_entry_fills(rec, ["ID_1", "ID_2"])

        # First fill should correspond to BUY leg
        self.assertEqual(fills[0]["direction"], "BUY")
        self.assertEqual(fills[1]["direction"], "SELL")


# ---------------------------------------------------------------------------
# E — _poll_entry_fills exception handling
# ---------------------------------------------------------------------------
class TestE_PollEntryFillsExc(unittest.TestCase):

    def test_e01_exception_returns_poll_error_entry(self):
        """_poll_entry_fills catches broker exception and returns POLL_ERROR."""
        mock_broker = MagicMock()
        mock_broker.get_order_status.side_effect = RuntimeError("broker down")
        mgr = _make_mgr_live(mock_broker)
        rec = _make_open_rec()

        fills = mgr._poll_entry_fills(rec, ["BID_ERR"])

        self.assertEqual(len(fills), 1)
        self.assertEqual(fills[0]["status"], "POLL_ERROR")
        self.assertIn("error", fills[0])
        self.assertEqual(fills[0]["qty_filled"], 0)


# ---------------------------------------------------------------------------
# F — _poll_exit_fills direction reversal
# ---------------------------------------------------------------------------
class TestF_PollExitFills(unittest.TestCase):

    def test_f01_buy_leg_exit_is_sell(self):
        """_poll_exit_fills reverses BUY → SELL for exit direction."""
        mock_broker = MagicMock()
        mock_broker.get_order_status.return_value = {
            "status": "TRADED", "filled_qty": 75, "avg_fill_price": 90.0,
        }
        mgr = _make_mgr_live(mock_broker)
        rec = _make_open_rec(legs=[
            {"type": "CE", "strike": 24500.0, "direction": "BUY", "premium": 100.0, "iv": 0.14},
        ])

        fills = mgr._poll_exit_fills(rec, ["EXIT_001"])

        self.assertEqual(fills[0]["direction"], "SELL")

    def test_f02_sell_leg_exit_is_buy(self):
        """_poll_exit_fills reverses SELL → BUY for exit direction."""
        mock_broker = MagicMock()
        mock_broker.get_order_status.return_value = {
            "status": "TRADED", "filled_qty": 75, "avg_fill_price": 90.0,
        }
        mgr = _make_mgr_live(mock_broker)
        rec = _make_open_rec(legs=[
            {"type": "CE", "strike": 24600.0, "direction": "SELL", "premium": 50.0, "iv": 0.13},
        ])

        fills = mgr._poll_exit_fills(rec, ["EXIT_002"])

        self.assertEqual(fills[0]["direction"], "BUY")


# ---------------------------------------------------------------------------
# G — _compute_net_fill_price valid fills
# ---------------------------------------------------------------------------
class TestG_ComputeNetFillPrice(unittest.TestCase):

    def test_g01_net_price_credit_spread(self):
        """Credit spread: SELL premium - BUY premium = net credit."""
        mgr = _make_mgr_paper()
        fills = [
            {"direction": "SELL", "qty_filled": 75, "avg_price": 150.0},
            {"direction": "BUY",  "qty_filled": 75, "avg_price":  80.0},
        ]
        net = mgr._compute_net_fill_price(fills)
        self.assertAlmostEqual(net, abs(-150.0 + 80.0))  # abs(−70) = 70

    def test_g02_net_price_debit_spread(self):
        """Debit spread: BUY premium - SELL premium = net debit."""
        mgr = _make_mgr_paper()
        fills = [
            {"direction": "BUY",  "qty_filled": 75, "avg_price": 150.0},
            {"direction": "SELL", "qty_filled": 75, "avg_price":  80.0},
        ]
        net = mgr._compute_net_fill_price(fills)
        self.assertAlmostEqual(net, abs(150.0 - 80.0))  # 70


# ---------------------------------------------------------------------------
# H — _compute_net_fill_price incomplete fills
# ---------------------------------------------------------------------------
class TestH_ComputeNetFillPriceIncomplete(unittest.TestCase):

    def test_h01_zero_qty_returns_none(self):
        mgr = _make_mgr_paper()
        fills = [
            {"direction": "BUY", "qty_filled": 0, "avg_price": 100.0},
        ]
        self.assertIsNone(mgr._compute_net_fill_price(fills))

    def test_h02_zero_price_returns_none(self):
        mgr = _make_mgr_paper()
        fills = [
            {"direction": "BUY", "qty_filled": 75, "avg_price": 0.0},
        ]
        self.assertIsNone(mgr._compute_net_fill_price(fills))

    def test_h03_empty_list_returns_none(self):
        mgr = _make_mgr_paper()
        self.assertIsNone(mgr._compute_net_fill_price([]))


# ---------------------------------------------------------------------------
# I — _compute_realized_pnl missing prices
# ---------------------------------------------------------------------------
class TestI_ComputeRealizedPnlMissing(unittest.TestCase):

    def test_i01_returns_none_when_entry_missing(self):
        mgr = _make_mgr_paper()
        rec = _make_open_rec()
        rec.actual_entry_fill_price = None
        rec.actual_exit_fill_price  = 90.0
        self.assertIsNone(mgr._compute_realized_pnl(rec))

    def test_i02_returns_none_when_exit_missing(self):
        mgr = _make_mgr_paper()
        rec = _make_open_rec()
        rec.actual_entry_fill_price = 100.0
        rec.actual_exit_fill_price  = None
        self.assertIsNone(mgr._compute_realized_pnl(rec))


# ---------------------------------------------------------------------------
# J — _compute_realized_pnl credit spread
# ---------------------------------------------------------------------------
class TestJ_ComputeRealizedPnlCredit(unittest.TestCase):

    def test_j01_credit_spread_profit(self):
        """Credit spread: entry=70 credit, exit=30 debit → profit = (70-30)*75 = 3000."""
        mgr = _make_mgr_paper()
        rec = _make_open_rec()
        rec.option_type = "IRON_CONDOR"   # is_credit = True via property
        rec.lots = 1
        rec.lot_size = 75
        rec.actual_entry_fill_price = 70.0
        rec.actual_exit_fill_price  = 30.0
        pnl = mgr._compute_realized_pnl(rec)
        self.assertAlmostEqual(pnl, 3000.0)

    def test_j02_credit_spread_loss(self):
        """Credit spread loss: entry=70, exit=100 → (70-100)*75 = -2250."""
        mgr = _make_mgr_paper()
        rec = _make_open_rec()
        rec.option_type = "IRON_CONDOR"
        rec.lots = 1
        rec.lot_size = 75
        rec.actual_entry_fill_price = 70.0
        rec.actual_exit_fill_price  = 100.0
        pnl = mgr._compute_realized_pnl(rec)
        self.assertAlmostEqual(pnl, -2250.0)


# ---------------------------------------------------------------------------
# K — _compute_realized_pnl debit spread
# ---------------------------------------------------------------------------
class TestK_ComputeRealizedPnlDebit(unittest.TestCase):

    def test_k01_debit_spread_profit(self):
        """Debit spread profit: entry=50, exit=90 → (90-50)*75 = 3000."""
        mgr = _make_mgr_paper()
        rec = _make_open_rec()
        rec.option_type = "BULL_CALL_SPREAD"   # is_credit = False (not IRON_CONDOR, not SELL)
        rec.direction   = "BUY"
        rec.lots = 1
        rec.lot_size = 75
        rec.actual_entry_fill_price = 50.0
        rec.actual_exit_fill_price  = 90.0
        pnl = mgr._compute_realized_pnl(rec)
        self.assertAlmostEqual(pnl, 3000.0)


# ---------------------------------------------------------------------------
# L — EXIT_SUBMITTED set before exit placement
# ---------------------------------------------------------------------------
class TestL_ExitSubmittedBeforePlacement(unittest.TestCase):

    def test_l01_status_set_to_exit_submitted_before_broker_call(self):
        """_close_position sets EXIT_SUBMITTED before calling _place_live_exit_legs."""
        call_order = []

        def record_status_then_fail(rec):
            call_order.append(("place_called", rec.status))
            return None   # simulate failure

        mock_broker = MagicMock()
        mgr = _make_mgr_live(mock_broker)
        rec = _make_open_rec()
        mgr._orders[rec.order_id] = rec

        with patch.object(mgr, "_place_live_exit_legs", side_effect=record_status_then_fail):
            mgr._close_position(rec.order_id, 90.0, "DTE_EXIT")

        self.assertTrue(any(
            status == "EXIT_SUBMITTED" for _, status in call_order
        ), "Status must be EXIT_SUBMITTED before _place_live_exit_legs is called")


# ---------------------------------------------------------------------------
# M — stays EXIT_SUBMITTED on unconfirmed fills
# ---------------------------------------------------------------------------
class TestM_StaysExitSubmittedUnconfirmed(unittest.TestCase):

    def test_m01_unconfirmed_fills_keep_exit_submitted(self):
        """_close_position stays EXIT_SUBMITTED when fills are not confirmed."""
        mock_broker = MagicMock()
        mock_broker.place_order.side_effect = ["EXIT_001", "EXIT_002"]
        # Return PENDING fill status → not confirmed
        mock_broker.get_order_status.return_value = {
            "status": "PENDING", "filled_qty": 0, "avg_fill_price": 0.0,
        }
        mgr = _make_mgr_live(mock_broker)
        rec = _make_open_rec()
        mgr._orders[rec.order_id] = rec

        fno_map = MagicMock()
        fno_map.lookup = MagicMock(return_value="99999")

        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map", return_value=fno_map), \
             patch("execution_engine.options_order_manager.OptionsOrderManager._journal_write_close"):
            with self.assertLogs(
                "execution_engine.options_order_manager", level="CRITICAL"
            ):
                mgr._close_position(rec.order_id, 90.0, "DTE_EXIT")

        self.assertEqual(mgr._orders[rec.order_id].status, "EXIT_SUBMITTED")
        from execution_engine.options_order_manager import _BRKST_UNRESOLVED
        self.assertEqual(mgr._orders[rec.order_id].broker_status, _BRKST_UNRESOLVED)


# ---------------------------------------------------------------------------
# N — stays EXIT_SUBMITTED when _place_live_exit_legs returns None
# ---------------------------------------------------------------------------
class TestN_StaysExitSubmittedOnNone(unittest.TestCase):

    def test_n01_no_exit_order_keeps_exit_submitted(self):
        """_close_position stays EXIT_SUBMITTED when _place_live_exit_legs returns None."""
        mock_broker = MagicMock()
        mgr = _make_mgr_live(mock_broker)
        rec = _make_open_rec(legs=[])   # empty legs → _place_live_exit_legs returns None
        mgr._orders[rec.order_id] = rec

        with patch("execution_engine.options_order_manager.OptionsOrderManager._journal_write_close"):
            with self.assertLogs(
                "execution_engine.options_order_manager", level="CRITICAL"
            ):
                mgr._close_position(rec.order_id, 90.0, "STOP_LOSS")

        self.assertEqual(mgr._orders[rec.order_id].status, "EXIT_SUBMITTED")


# ---------------------------------------------------------------------------
# O — marks closed and writes realized_pnl on confirmed fills
# ---------------------------------------------------------------------------
class TestO_ClosedOnConfirmedFills(unittest.TestCase):

    def test_o01_position_closed_with_realized_pnl(self):
        """_close_position marks status=closed and writes realized_pnl on confirmed fills."""
        mock_broker = MagicMock()
        mock_broker.place_order.side_effect = ["EXIT_001", "EXIT_002"]
        mock_broker.get_order_status.return_value = {
            "status": "TRADED", "filled_qty": 75, "avg_fill_price": 80.0,
        }
        mgr = _make_mgr_live(mock_broker)
        rec = _make_open_rec()
        rec.actual_entry_fill_price = 100.0   # simulate entry already reconciled
        mgr._orders[rec.order_id] = rec

        fno_map = MagicMock()
        fno_map.lookup = MagicMock(return_value="99999")

        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map", return_value=fno_map), \
             patch("execution_engine.options_order_manager.OptionsOrderManager._journal_write_close"), \
             patch("learning_system.options_performance_tracker.get_options_performance_tracker") as pt:
            pt.return_value.record_closed_trade = MagicMock()
            mgr._close_position(rec.order_id, 90.0, "TARGET_HIT")

        closed = mgr._orders[rec.order_id]
        self.assertEqual(closed.status, "closed")
        self.assertIsNotNone(closed.actual_exit_fill_price)
        from execution_engine.options_order_manager import _RCON_FULL
        self.assertEqual(closed.reconciliation_status, _RCON_FULL)
        self.assertIsNotNone(closed.realized_pnl)


# ---------------------------------------------------------------------------
# P — knowledge provenance captured in execute()
# ---------------------------------------------------------------------------
class TestP_KnowledgeProvenanceCaptured(unittest.TestCase):

    def test_p01_kda_decision_in_record(self):
        """execute() attaches kda_decision from signal_context to the record."""
        from execution_engine.options_order_manager import OptionsOrderManager
        mgr = _make_mgr_paper()

        meta = {
            "iv_rank": 65.0,
            "spot": 24000.0,
            "dte": 21,
            "regime": "NEUTRAL",
            "strategy_type": "IRON_CONDOR",
            "lots": 1,
            "lot_size": 50,
            "entry_premium": 70.0,
            "max_loss_rs": 3500.0,
            "max_profit_rs": 3500.0,
            "expiry_date": (date.today() + timedelta(days=21)).isoformat(),
            "legs": [],
        }

        mock_signal = MagicMock()
        mock_signal.symbol        = "NIFTY"
        mock_signal.strategy_name = "IRON_CONDOR_AI"
        mock_signal.direction     = MagicMock()
        mock_signal.direction.value = "NEUTRAL"
        mock_signal.entry_price   = 70.0
        mock_signal.stop_loss     = 140.0
        mock_signal.target_price  = 35.0
        mock_signal.min_rr        = 1.5
        mock_signal.notes         = json.dumps(meta)
        from models.trade_signal import SignalType
        mock_signal.signal_type   = SignalType.OPTIONS

        mock_decision = MagicMock()
        mock_decision.score       = 8.0

        signal_context = {
            "kda_decision": "APPROVED_BY_KDA",
            "authorization_source": "OptionsRiskEngine",
            "klp_score": 0.82,
            "kda_evidence_state": "strong",
            "strategylab_result": "converged",
            "final_decision": "EXECUTE",
        }

        with patch.object(mgr, "_journal_write_open"), \
             patch.object(mgr, "_ensure_journal"):
            oid = mgr.execute(mock_signal, mock_decision, signal_context=signal_context)

        self.assertIsNotNone(oid)
        rec = mgr._orders.get(oid.order_id if hasattr(oid, "order_id") else list(mgr._orders.keys())[-1])
        self.assertIsNotNone(rec)
        self.assertEqual(rec.kda_decision, "APPROVED_BY_KDA")
        self.assertEqual(rec.authorization_source, "OptionsRiskEngine")
        self.assertAlmostEqual(rec.klp_score, 0.82)
        self.assertEqual(rec.knowledge_provenance.get("kda_evidence_state"), "strong")
        self.assertAlmostEqual(rec.expected_entry_price, 70.0)


if __name__ == "__main__":
    unittest.main()
