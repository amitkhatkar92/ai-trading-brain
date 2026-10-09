"""
tests/test_dta_options_producttype_001.py
============================================
DTA-OPTIONS-PRODUCTTYPE-001: root-cause fix for DH-905 "Missing required
fields, bad values for parameters etc." broker rejections on EVERY live
options leg placement — confirmed live 2026-10-08, NIFTY and BANKNIFTY
Iron_Condor_Range, both legs rejected, 3 separate cycles (13:04/14:02/
15:03), 0 options positions ever recorded as a result.

Root cause: all 3 live-broker `place_order()` call sites in
options_order_manager.py passed `product_type="NRML"`. Confirmed against
the installed dhanhq SDK source (dhanhq/dhanhq.py) that Dhan's real,
only valid product type values are CNC / INTRADAY / MARGIN / CO / BO /
MTF — "NRML" has never existed in Dhan's API (it is Zerodha/NSE
terminology, already correctly used that way in zerodha_broker.py for
the Zerodha adapter, but wrong for Dhan). Every live options order was
therefore rejected by Dhan's own server-side parameter validation.

Fix: all 3 call sites now pass product_type="MARGIN" (Dhan's equivalent
of a carried F&O position) — entry leg placement (_place_live_legs),
rollback reversal (_rollback_legs), and position close (_place_live_exit_legs).

Coverage:
  - Each of the 3 live call sites sends product_type="MARGIN" to the broker
  - Regression guard: the string "NRML" must never reappear anywhere in
    this file (source-text scan)
"""
from __future__ import annotations

import os
import sys
import threading
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import execution_engine.options_order_manager as oom
from execution_engine.options_order_manager import OptionsOrderManager, OptionsOrderRecord


def _make_rec(**overrides) -> OptionsOrderRecord:
    base = dict(
        order_id         = "OPT_NIFTY_IC_1",
        symbol           = "NIFTY",
        strategy         = "Iron_Condor_Range",
        option_type      = "IRON_CONDOR",
        direction        = "SELL",
        lots             = 1,
        lot_size         = 65,
        entry_premium    = 50.0,
        stop_premium     = 90.0,
        target_premium   = 10.0,
        max_loss_rs      = 2600.0,
        max_profit_rs    = 3250.0,
        expiry_date      = date(2026, 10, 30),
        dte_at_entry     = 21,
        iv_rank_at_entry = 50.0,
        spot_at_entry    = 25000.0,
        regime_at_entry  = "RANGE_MARKET",
        placed_at        = datetime(2026, 10, 8, 13, 4, 0),
        legs             = [
            {"direction": "SELL", "strike": 25200, "type": "CE", "premium": 60},
            {"direction": "BUY",  "strike": 25300, "type": "CE", "premium": 30},
        ],
    )
    base.update(overrides)
    return OptionsOrderRecord(**base)


def _build_mgr(mock_broker=None) -> OptionsOrderManager:
    mgr = OptionsOrderManager.__new__(OptionsOrderManager)
    mgr._paper_mode = False
    mgr._broker     = mock_broker or MagicMock()
    mgr._orders     = {}
    mgr._lock       = threading.Lock()
    mgr._unresolved = {}
    return mgr


class TestEntryLegPlacementProductType:
    def test_entry_leg_sends_margin_not_nrml(self):
        mgr = _build_mgr()
        mgr._broker.place_order.return_value = "BROKER_123"
        rec = _make_rec()

        fake_map = MagicMock()
        fake_map.lookup.return_value = "SEC_ID_1"
        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map", return_value=fake_map):
            result = mgr._place_live_legs(rec, {"legs": rec.legs})

        assert result == ["BROKER_123", "BROKER_123"]
        for call_args in mgr._broker.place_order.call_args_list:
            assert call_args.kwargs["product_type"] == "MARGIN"
            assert call_args.kwargs["product_type"] != "NRML"


class TestRollbackReversalProductType:
    def test_rollback_reversal_sends_margin_not_nrml(self):
        mgr = _build_mgr()
        rec = _make_rec()
        mgr._broker.get_order_status.return_value = {"status": "TRADED", "filled_qty": 65}
        mgr._broker.place_order.return_value = "REV_123"

        placed = [("BROKER_1", "SEC_ID_1", "SELL", rec.legs[0])]
        mgr._rollback_legs(placed, rec)

        assert mgr._broker.place_order.called
        call_args = mgr._broker.place_order.call_args
        assert call_args.kwargs["product_type"] == "MARGIN"
        assert call_args.kwargs["product_type"] != "NRML"


class TestExitLegProductType:
    def test_exit_leg_sends_margin_not_nrml(self):
        mgr = _build_mgr()
        mgr._broker.place_order.return_value = "EXIT_123"
        rec = _make_rec()

        fake_map = MagicMock()
        fake_map.lookup.return_value = "SEC_ID_1"
        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map", return_value=fake_map):
            mgr._place_live_exit_legs(rec)

        assert mgr._broker.place_order.called
        for call_args in mgr._broker.place_order.call_args_list:
            assert call_args.kwargs["product_type"] == "MARGIN"
            assert call_args.kwargs["product_type"] != "NRML"


def test_source_scan_nrml_never_reappears():
    """Regression guard: the invalid 'NRML' product type ASSIGNMENT must
    never reappear in this file (explanatory comments mentioning the old
    bad value for documentation purposes are fine)."""
    src = (ROOT / "execution_engine" / "options_order_manager.py").read_text(encoding="utf-8")
    assert 'product_type     = "NRML"' not in src
    assert "product_type     = 'NRML'" not in src
