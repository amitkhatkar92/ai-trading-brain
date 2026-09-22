"""
tests/test_dta_phantom_exit_001.py
===============================================
DTA-PHANTOM-EXIT-001 — never fire a reversing (closing) broker order against
a position the broker has already flattened.

ROOT CAUSE (found live 2026-09-22): ANANDRATHI BUY 2 was entered 2026-09-21
before DTA-CARRY-CNC-001 shipped, so it went to Dhan as plain productType=
INTRADAY. Dhan's own MIS auto square-off almost certainly flattened it that
same evening, but our own EOD square-off (DTA-EOD-INTRADAY-SQUAREOFF-001)
hadn't gone live yet at that point in the day, so nothing in this system
ever recorded that close — the position sat "open" in internal state.
The next morning, TradeMonitor's EARLY_LOSS adaptive-exit logic called
close_position(), which blindly sent a SELL 2 "closing" order. Since Dhan
held nothing to net against, that order opened a brand-new, completely
unprotected NAKED SHORT of 2 shares — while this system logged "Trade
Closed (LOSS)" believing it was flat. Confirmed via Dhan's own Open P&L
export: Qty -2.00 @ Avg 2,190.80 (exactly the system's own "exit" price).

FIX: close_position() and check_and_expire_carries()'s CNC exit path both
now call the existing _broker_confirms_no_open_position() check (already
proven in DTA-COALINDIA-RECONCILE-001) before firing any reversing order.
Only ever SKIPS the broker call when the check has POSITIVELY confirmed
absence — any uncertainty (API error, or the broker genuinely still holds
the position) falls through to the normal, unchanged exit path, so this can
never block a real, legitimate close.

T01  close_position(): broker confirms position absent -> no broker order
     placed, position still marked closed (no naked reversing order)
T02  close_position(): broker confirms position still held -> proceeds
     normally, broker.place_order() is called (regression guard)
T03  close_position(): broker check fails/uncertain -> still attempts the
     real close (fail-safe, matches pre-fix behavior exactly)
T04  check_and_expire_carries(): CNC position, broker confirms absent ->
     no broker order placed, position still recorded as closed
T05  check_and_expire_carries(): CNC position, broker still holds it ->
     proceeds normally, broker.place_order() is called (regression guard)
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from execution_engine.order_manager import OrderManager, OrderRecord

_SEC_MAP = {"ANANDRATHI": {"security_id": "7145", "segment": "NSE_EQ"}}


def _make_om_live_with_broker(broker_mock):
    import config as _cfg
    with (
        patch.object(_cfg, "PAPER_TRADING", False),
        patch.dict(os.environ, {"LIVE_TRADING_AUTHORIZED": "true"}),
        patch.object(OrderManager, "_load_broker", return_value=broker_mock),
        patch.object(OrderManager, "_restore_from_live_journal", return_value=None),
        patch.object(OrderManager, "reconcile_startup_fills", return_value=0),
        patch.object(OrderManager, "_reconcile_sim_paper_artifacts", return_value=None),
    ):
        om = OrderManager()
    om._append_live_journal = MagicMock()
    return om


def _insert_open_order(om, order_id="ORD-1", product_type="INTRADAY", **overrides):
    defaults = dict(
        order_id=order_id, symbol="ANANDRATHI", direction="BUY", quantity=2,
        entry_price=2204.8, stop_loss=2177.94, target=2334.18,
        strategy="EDG_COMPOS_69_EE0000", status="open", fill_status="FILLED",
        placed_at=datetime.now(), initial_stop_loss=2177.94,
        product_type=product_type,
    )
    defaults.update(overrides)
    rec = OrderRecord(**defaults)
    om._orders[order_id] = rec
    return rec


_ABSENT_RESP = {"status": "success", "data": []}
_PRESENT_RESP = {"status": "success", "data": [
    {"securityId": "7145", "netQty": 2, "positionType": "LONG"}
]}


class TestClosePositionPhantomGuard:
    def test_t01_skips_broker_order_when_broker_confirms_absent(self):
        broker = MagicMock()
        broker.get_positions.return_value = _ABSENT_RESP
        om = _make_om_live_with_broker(broker)
        _insert_open_order(om)
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            ok = om.close_position("ORD-1", 2190.8, reason="EARLY_LOSS")
        assert ok is True
        broker.place_order.assert_not_called()
        assert om._orders["ORD-1"].status == "closed"

    def test_t02_places_real_order_when_broker_confirms_present(self):
        broker = MagicMock()
        broker.get_positions.return_value = _PRESENT_RESP
        broker.place_order.return_value = "EXIT-OID"
        broker.get_fill_details.return_value = {"status": "FILLED"}
        om = _make_om_live_with_broker(broker)
        _insert_open_order(om)
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            ok = om.close_position("ORD-1", 2190.8, reason="EARLY_LOSS")
        assert ok is True
        broker.place_order.assert_called_once()
        assert om._orders["ORD-1"].status == "closed"

    def test_t03_broker_check_failure_still_attempts_real_close(self):
        broker = MagicMock()
        broker.get_positions.side_effect = RuntimeError("network error")
        broker.place_order.return_value = "EXIT-OID"
        broker.get_fill_details.return_value = {"status": "FILLED"}
        om = _make_om_live_with_broker(broker)
        _insert_open_order(om)
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            ok = om.close_position("ORD-1", 2190.8, reason="EARLY_LOSS")
        assert ok is True
        broker.place_order.assert_called_once()


class TestCarryExpiryPhantomGuard:
    def test_t04_cnc_skips_broker_order_when_absent(self):
        broker = MagicMock()
        broker.get_positions.return_value = _ABSENT_RESP
        om = _make_om_live_with_broker(broker)
        old_placed = datetime.now() - timedelta(days=10)
        _insert_open_order(om, product_type="CNC", placed_at=old_placed)
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP), \
             patch.object(OrderManager, "_review_carry_extension_dryrun", return_value=None):
            expired = om.check_and_expire_carries(live_prices={"ANANDRATHI": 2250.0})
        assert expired == 1
        broker.place_order.assert_not_called()
        assert om._orders["ORD-1"].status == "closed"

    def test_t05_cnc_places_real_order_when_still_held(self):
        broker = MagicMock()
        broker.get_positions.return_value = _PRESENT_RESP
        broker.place_order.return_value = "CARRY-EXIT-OID"
        om = _make_om_live_with_broker(broker)
        old_placed = datetime.now() - timedelta(days=10)
        _insert_open_order(om, product_type="CNC", placed_at=old_placed)
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP), \
             patch.object(OrderManager, "_review_carry_extension_dryrun", return_value=None):
            expired = om.check_and_expire_carries(live_prices={"ANANDRATHI": 2250.0})
        assert expired == 1
        broker.place_order.assert_called_once()
