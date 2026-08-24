"""
Test Suite: Options Rollback Safety
=====================================
Focused tests for the _rollback_legs() fix (DTA-001 safety blocker).

Test matrix (A-K per spec):
  A. Filled leg + reversal succeeds          → normal rollback, no unresolved
  B. Filled leg + reversal returns None      → ROLLBACK_FAILED persisted
  C. Filled leg + reversal raises exception  → ROLLBACK_FAILED persisted
  D. Status response empty dict              → reconciliation attempted
  E. Reconciliation confirms position live   → UNRESOLVED_LIVE_EXPOSURE visible
  F. Reconciliation confirms position closed → not in unresolved
  G. filled_qty == 0                         → UNRESOLVED_QUANTITY, no reversal
  H. filled_qty > 0                         → reversal uses actual quantity
  I. Multiple filled legs both fail          → each independently recorded
  J. Empty placed list                       → no-op (no duplicate)
  K. Pending cancel succeeds                 → normal path, no unresolved

All tests are pure unit tests with mocked brokers.
No live orders, no network calls, no file I/O (tmp_path).
"""

from __future__ import annotations

import csv
import os
import sys
import threading
import unittest
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, call, patch

# ── Path setup ─────────────────────────────────────────────────────────────
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from execution_engine.options_order_manager import (
    OptionsOrderRecord,
    _RBST_FAILED,
    _RBST_UNRESOLVED,
    _RBST_UNRESOLVED_QTY,
    _RBST_RESOLVED,
    ROLLBACK_FAILURE_COLUMNS,
    ROLLBACK_FAILURES_PATH,
)


# ── Minimal fixtures ───────────────────────────────────────────────────────

def _make_rec(order_id: str = "OPT_NIFTY_BCS_1") -> OptionsOrderRecord:
    return OptionsOrderRecord(
        order_id         = order_id,
        symbol           = "NIFTY",
        strategy         = "BullCallSpread",
        option_type      = "BULL_CALL_SPREAD",
        direction        = "BUY",
        lots             = 1,
        lot_size         = 75,
        entry_premium    = 100.0,
        stop_premium     = 50.0,
        target_premium   = 180.0,
        max_loss_rs      = 7500.0,
        max_profit_rs    = 7500.0,
        expiry_date      = date(2026, 9, 25),
        dte_at_entry     = 30,
        iv_rank_at_entry = 50.0,
        spot_at_entry    = 23000.0,
        regime_at_entry  = "TRENDING_BULLISH",
        placed_at        = datetime(2026, 8, 24, 10, 0, 0),
        legs             = [
            {"direction": "BUY",  "strike": 23000, "type": "CE", "premium": 200},
            {"direction": "SELL", "strike": 23200, "type": "CE", "premium": 100},
        ],
    )


def _make_placed(*items):
    """Each item: (order_id, security_id, tx, leg_dict)."""
    return list(items)


def _build_mgr(tmp_path, mock_broker=None):
    """
    Build an OptionsOrderManager in live mode with mocked broker and temp journal paths.
    Bypasses __init__ to avoid file system / config side-effects.
    """
    import execution_engine.options_order_manager as omod
    real_rbf_path = omod.ROLLBACK_FAILURES_PATH

    rbf_path = str(tmp_path / "options_rollback_failures.csv")
    journal_path = str(tmp_path / "options_trades.csv")

    with patch.object(omod, "ROLLBACK_FAILURES_PATH", rbf_path), \
         patch.object(omod, "JOURNAL_PATH", journal_path):
        from execution_engine.options_order_manager import OptionsOrderManager
        mgr = OptionsOrderManager.__new__(OptionsOrderManager)
        mgr._paper_mode  = False
        mgr._broker      = mock_broker or MagicMock()
        mgr._orders      = {}
        mgr._lock        = threading.Lock()
        mgr._feed        = MagicMock()
        mgr._unresolved  = {}
        # Patch paths onto the instance for the helper methods
        mgr._rbf_path    = rbf_path
        mgr._journal_path = journal_path

    # Monkey-patch the module-level ROLLBACK_FAILURES_PATH for this manager's methods
    # We accomplish this by patching it at the point where it's used in the method body.
    # Simpler: write header and redirect via monkeypatch at module level per test.
    # We use a context-free approach: just write the header to the temp file
    os.makedirs(os.path.dirname(rbf_path) if os.path.dirname(rbf_path) else ".", exist_ok=True)
    with open(rbf_path, "w", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=ROLLBACK_FAILURE_COLUMNS).writeheader()

    return mgr, rbf_path


def _read_rbf_rows(rbf_path: str) -> List[dict]:
    """Read all data rows from the rollback failures CSV."""
    with open(rbf_path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ── Test class ─────────────────────────────────────────────────────────────

class TestOptionsRollbackSafety(unittest.TestCase):
    """
    All tests patch ROLLBACK_FAILURES_PATH at the module level for the duration
    of each test so that file writes go to a temp directory.
    """

    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        self._rbf_path = os.path.join(self._tmpdir, "options_rollback_failures.csv")
        with open(self._rbf_path, "w", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=ROLLBACK_FAILURE_COLUMNS).writeheader()
        self._patcher = patch(
            "execution_engine.options_order_manager.ROLLBACK_FAILURES_PATH",
            self._rbf_path,
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def _make_mgr(self, broker=None):
        from execution_engine.options_order_manager import OptionsOrderManager
        mgr = OptionsOrderManager.__new__(OptionsOrderManager)
        mgr._paper_mode = False
        mgr._broker     = broker or MagicMock()
        mgr._orders     = {}
        mgr._lock       = threading.Lock()
        mgr._feed       = MagicMock()
        mgr._unresolved = {}
        return mgr

    # ── A. Filled leg + reversal succeeds ──────────────────────────────────

    def test_a_reversal_succeeds_no_unresolved(self):
        """Normal rollback: reversal is placed, nothing enters unresolved."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.return_value = {"status": "TRADED", "filled_qty": 75}
        mgr._broker.place_order.return_value = "REV_001"

        rec = _make_rec()
        leg = rec.legs[0]
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", leg))

        mgr._rollback_legs(placed, rec)

        self.assertEqual(len(mgr._unresolved), 0)
        # Verify exactly one reversal was attempted
        mgr._broker.place_order.assert_called_once()
        # Verify actual filled_qty was passed (not a substitute)
        call_kwargs = mgr._broker.place_order.call_args.kwargs
        self.assertEqual(call_kwargs["quantity"], 75)
        self.assertEqual(call_kwargs["transaction_type"], "SELL")

    # ── B. Filled leg + reversal returns None ──────────────────────────────

    def test_b_reversal_returns_none_persisted(self):
        """rev_id=None must write ROLLBACK_FAILED and add to _unresolved."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.return_value = {"status": "TRADED", "filled_qty": 75}
        mgr._broker.place_order.return_value = None

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))

        mgr._rollback_legs(placed, rec)

        self.assertEqual(len(mgr._unresolved), 1)
        exposure = list(mgr._unresolved.values())[0]
        self.assertEqual(exposure["status"], _RBST_UNRESOLVED)
        self.assertEqual(exposure["order_id"], "ORD_001")

        rows = _read_rbf_rows(self._rbf_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], _RBST_UNRESOLVED)
        self.assertEqual(rows[0]["original_order_id"], "ORD_001")
        self.assertIn("reversal returned", rows[0]["reason"])

    # ── C. Filled leg + reversal raises exception ──────────────────────────

    def test_c_reversal_raises_exception_persisted(self):
        """Exception during place_order(reversal) must write ROLLBACK_FAILED."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.return_value = {"status": "TRADED", "filled_qty": 75}
        mgr._broker.place_order.side_effect = Exception("network timeout")

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))

        mgr._rollback_legs(placed, rec)

        self.assertEqual(len(mgr._unresolved), 1)
        exposure = list(mgr._unresolved.values())[0]
        self.assertEqual(exposure["status"], _RBST_UNRESOLVED)

        rows = _read_rbf_rows(self._rbf_path)
        self.assertEqual(len(rows), 1)
        self.assertIn("network timeout", rows[0]["reason"])

    # ── D. Status response is empty dict → reconciliation attempted ────────

    def test_d_empty_status_triggers_reconciliation(self):
        """Empty get_order_status dict must trigger a second reconciliation call."""
        mgr = self._make_mgr()
        # First call: ambiguous; second call (reconcile): confirmed CANCELLED
        mgr._broker.get_order_status.side_effect = [
            {},
            {"status": "CANCELLED"},
        ]

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))

        mgr._rollback_legs(placed, rec)

        self.assertEqual(mgr._broker.get_order_status.call_count, 2)

    # ── E. Reconciliation confirms position live → exposure visible ────────

    def test_e_reconcile_confirms_traded_exposure_visible(self):
        """If reconciliation confirms TRADED, exposure enters _unresolved."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.side_effect = [
            {},                                            # initial: ambiguous
            {"status": "TRADED", "filled_qty": 75},       # reconcile: confirmed
        ]

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))

        mgr._rollback_legs(placed, rec)

        self.assertEqual(len(mgr._unresolved), 1)
        # get_total_options_exposure_rs must reflect the unresolved position
        self.assertGreater(mgr.get_total_options_exposure_rs(), 0.0)
        rows = _read_rbf_rows(self._rbf_path)
        self.assertEqual(rows[0]["status"], _RBST_UNRESOLVED)

    # ── F. Reconciliation confirms closed → not in unresolved ─────────────

    def test_f_reconcile_confirms_closed_not_unresolved(self):
        """cancel_order=False + reconcile=CANCELLED → exposure is resolved, not persisted."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.side_effect = [
            {"status": "OPEN"},    # initial: pending
            {"status": "CANCELLED"},  # reconcile after cancel failure
        ]
        mgr._broker.cancel_order.return_value = False

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))

        mgr._rollback_legs(placed, rec)

        self.assertEqual(len(mgr._unresolved), 0)
        rows = _read_rbf_rows(self._rbf_path)
        self.assertEqual(len(rows), 0)

    # ── G. filled_qty == 0 → UNRESOLVED_QUANTITY, no reversal ────────────

    def test_g_zero_filled_qty_no_reversal(self):
        """TRADED with filled_qty=0 must NOT substitute 1 or attempt reversal."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.return_value = {"status": "TRADED", "filled_qty": 0}

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))

        mgr._rollback_legs(placed, rec)

        mgr._broker.place_order.assert_not_called()
        self.assertEqual(len(mgr._unresolved), 1)
        exposure = list(mgr._unresolved.values())[0]
        self.assertEqual(exposure["status"], _RBST_UNRESOLVED_QTY)

        rows = _read_rbf_rows(self._rbf_path)
        self.assertEqual(rows[0]["status"], _RBST_UNRESOLVED_QTY)
        self.assertEqual(rows[0]["filled_qty_raw"], "0")

    # ── H. filled_qty > 0 → reversal uses actual quantity ─────────────────

    def test_h_actual_quantity_used_for_reversal(self):
        """Reversal must use the broker-reported filled_qty, not a default."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.return_value = {"status": "TRADED", "filled_qty": 150}
        mgr._broker.place_order.return_value = "REV_150"

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))

        mgr._rollback_legs(placed, rec)

        call_kwargs = mgr._broker.place_order.call_args.kwargs
        self.assertEqual(call_kwargs["quantity"], 150)
        self.assertEqual(len(mgr._unresolved), 0)

    # ── I. Multiple filled legs → each independently recorded ─────────────

    def test_i_multiple_legs_each_unresolved(self):
        """Each leg with a failed reversal must produce its own unresolved record."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.return_value = {"status": "TRADED", "filled_qty": 75}
        mgr._broker.place_order.return_value = None  # all reversals fail

        rec = _make_rec()
        placed = _make_placed(
            ("ORD_001", "SEC_001", "BUY",  rec.legs[0]),
            ("ORD_002", "SEC_002", "SELL", rec.legs[1]),
        )

        mgr._rollback_legs(placed, rec)

        self.assertEqual(len(mgr._unresolved), 2)
        rows = _read_rbf_rows(self._rbf_path)
        self.assertEqual(len(rows), 2)
        order_ids = {r["original_order_id"] for r in rows}
        self.assertIn("ORD_001", order_ids)
        self.assertIn("ORD_002", order_ids)

    # ── J. Empty placed list → no-op, no duplicate reversal ───────────────

    def test_j_empty_placed_is_noop(self):
        """_rollback_legs([]) must do nothing — no broker calls, no unresolved."""
        mgr = self._make_mgr()

        rec = _make_rec()
        mgr._rollback_legs([], rec)

        mgr._broker.get_order_status.assert_not_called()
        mgr._broker.place_order.assert_not_called()
        self.assertEqual(len(mgr._unresolved), 0)

    # ── K. Pending cancel succeeds → normal path, no unresolved ───────────

    def test_k_cancel_pending_succeeds_no_unresolved(self):
        """A PENDING order successfully cancelled must leave no unresolved state."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.return_value = {"status": "PENDING"}
        mgr._broker.cancel_order.return_value = True

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))

        mgr._rollback_legs(placed, rec)

        mgr._broker.cancel_order.assert_called_once_with("ORD_001")
        mgr._broker.place_order.assert_not_called()
        self.assertEqual(len(mgr._unresolved), 0)
        rows = _read_rbf_rows(self._rbf_path)
        self.assertEqual(len(rows), 0)

    # ── Extra: get_order_status raises → UNRESOLVED_LIVE_EXPOSURE ─────────

    def test_status_query_raises_persisted(self):
        """Exception from get_order_status must produce UNRESOLVED_LIVE_EXPOSURE."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.side_effect = Exception("broker timeout")

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))

        mgr._rollback_legs(placed, rec)

        self.assertEqual(len(mgr._unresolved), 1)
        exposure = list(mgr._unresolved.values())[0]
        self.assertEqual(exposure["status"], _RBST_UNRESOLVED)

    # ── Extra: CANCELLED status → skip, no action ─────────────────────────

    def test_already_cancelled_no_action(self):
        """A CANCELLED leg must be skipped — no reversal, no cancel, no unresolved."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.return_value = {"status": "CANCELLED"}

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))

        mgr._rollback_legs(placed, rec)

        mgr._broker.cancel_order.assert_not_called()
        mgr._broker.place_order.assert_not_called()
        self.assertEqual(len(mgr._unresolved), 0)

    # ── Extra: SIM reversal order ID → UNRESOLVED_LIVE_EXPOSURE ──────────

    def test_sim_reversal_id_treated_as_failure(self):
        """A SIM_ prefixed reversal order ID must be treated as a failed reversal."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.return_value = {"status": "TRADED", "filled_qty": 75}
        mgr._broker.place_order.return_value = "SIM_REV_001"

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))

        mgr._rollback_legs(placed, rec)

        self.assertEqual(len(mgr._unresolved), 1)
        rows = _read_rbf_rows(self._rbf_path)
        self.assertEqual(rows[0]["status"], _RBST_UNRESOLVED)

    # ── Extra: cancel raises exception → UNRESOLVED_LIVE_EXPOSURE ─────────

    def test_cancel_raises_exception_persisted(self):
        """Exception from cancel_order must produce UNRESOLVED_LIVE_EXPOSURE."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.return_value = {"status": "OPEN"}
        mgr._broker.cancel_order.side_effect = Exception("broker disconnected")

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))

        mgr._rollback_legs(placed, rec)

        self.assertEqual(len(mgr._unresolved), 1)
        rows = _read_rbf_rows(self._rbf_path)
        self.assertEqual(rows[0]["status"], _RBST_UNRESOLVED)
        self.assertIn("cancel_order exception", rows[0]["reason"])

    # ── Extra: get_unresolved_exposures public API ─────────────────────────

    def test_get_unresolved_exposures_returns_list(self):
        """get_unresolved_exposures() must reflect _unresolved dict contents."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.return_value = {"status": "TRADED", "filled_qty": 75}
        mgr._broker.place_order.return_value = None

        rec = _make_rec()
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))
        mgr._rollback_legs(placed, rec)

        exposures = mgr.get_unresolved_exposures()
        self.assertEqual(len(exposures), 1)
        self.assertIn("exposure_id", exposures[0])
        self.assertIn("security_id", exposures[0])

    # ── Extra: exposure included in total options exposure ─────────────────

    def test_exposure_included_in_total_rs(self):
        """get_total_options_exposure_rs must include unresolved legs."""
        mgr = self._make_mgr()
        mgr._broker.get_order_status.return_value = {"status": "TRADED", "filled_qty": 75}
        mgr._broker.place_order.return_value = None

        rec = _make_rec()  # max_loss_rs=7500, 2 legs → 3750 per leg estimate
        placed = _make_placed(("ORD_001", "SEC_001", "BUY", rec.legs[0]))
        mgr._rollback_legs(placed, rec)

        total = mgr.get_total_options_exposure_rs()
        # No open _orders, but one unresolved leg with per-leg estimate
        self.assertGreater(total, 0.0)
        self.assertAlmostEqual(total, 7500.0 / 2, places=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
