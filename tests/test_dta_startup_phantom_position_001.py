"""
tests/test_dta_startup_phantom_position_001.py
================================================
DTA-STARTUP-PHANTOM-POSITION-001 — cross-day broker-position cross-check
extended into reconcile_startup_fills().

Root cause confirmed via live read-only audit (2026-09-17): two ONGC orders
(34126091640603, 23126091548703) restored from the live journal on every
container restart stayed fill_status=API_ERROR forever because
get_order_by_id()/get_order_list() are day-scoped by Dhan and can never
resolve a cross-day order. reconcile_startup_fills() had no fallback for
this (unlike reconcile_pending_orders(), fixed earlier for COALINDIA) — so
a stale prior-day journal-restored position sat as a phantom "open"
position for the whole session, repeatedly failing real exit attempts and
sending real "[ExitFailed] ... Manual intervention may be required" alerts.
Live-verified: get_positions() returned data=[] (broker genuinely holds no
ONGC position) at the time this was found.

Fix: reconcile_startup_fills() now applies the same
_broker_confirms_no_open_position() cross-check (DTA-COALINDIA-RECONCILE-001)
for any restored order still unresolved after the normal per-order
reconcile, placed on a PREVIOUS calendar day. Same-day orders and
already-FILLED/PARTIALLY_FILLED orders are never touched.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from execution_engine.order_manager import OrderManager, OrderRecord

_SEC_MAP = {"ONGC": {"security_id": "2475", "segment": "NSE_EQ"}}


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
    return om


def _insert_stuck_order(om, placed_at, fill_status="JOURNAL_RESTORED",
                         order_id="34126091640603", symbol="ONGC"):
    rec = OrderRecord(
        order_id=order_id, symbol=symbol, direction="BUY", quantity=24,
        entry_price=235.47, stop_loss=230.42, target=246.37,
        strategy="KDA_AUTHORITY", status="open", fill_status=fill_status,
        placed_at=placed_at, initial_stop_loss=230.42,
    )
    om._orders[order_id] = rec
    return rec


def _broker_stuck_api_error():
    broker = MagicMock()
    broker.get_fill_details.return_value = {
        "status": "API_ERROR", "broker_order_id": "34126091640603",
        "actual_fill_price": 0.0, "filled_quantity": 0, "requested_qty": 24,
        "order_status_raw": "API_ERROR", "fill_timestamp": "",
        "reconciliation_source": "DHAN_BROKER",
    }
    return broker


class TestStartupPhantomPositionCleanup:

    def test_cross_day_phantom_position_cleaned_up_at_startup(self):
        broker = _broker_stuck_api_error()
        broker.get_positions.return_value = {"status": "success", "remarks": "", "data": []}
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(om, placed_at=datetime.now() - timedelta(days=1))
            om._trade_monitor = MagicMock()
            reconciled = om.reconcile_startup_fills()
        assert reconciled == 1
        assert "34126091640603" not in om._orders
        assert "ONGC" not in om._portfolio.positions
        om._trade_monitor.deregister.assert_called_once_with("34126091640603")

    def test_cross_day_order_still_open_at_broker_is_kept(self):
        broker = _broker_stuck_api_error()
        broker.get_positions.return_value = {
            "status": "success", "remarks": "",
            "data": [{"securityId": "2475", "netQty": 24, "positionType": "LONG"}],
        }
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(om, placed_at=datetime.now() - timedelta(days=1))
            om.reconcile_startup_fills()
        assert "34126091640603" in om._orders
        assert om._orders["34126091640603"].fill_status == "API_ERROR"

    def test_same_day_order_not_touched(self):
        """An order restored from TODAY's journal must never be swept, even
        if get_positions() would say absent — it may still resolve normally
        later in the session."""
        broker = _broker_stuck_api_error()
        broker.get_positions.return_value = {"status": "success", "remarks": "", "data": []}
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(om, placed_at=datetime.now())
            om.reconcile_startup_fills()
        assert "34126091640603" in om._orders
        broker.get_positions.assert_not_called()

    def test_filled_position_never_touched_even_if_cross_day(self):
        """A genuinely FILLED, live position from a previous day must never
        be cleaned up by this path — only unresolved fill states qualify."""
        broker = MagicMock()
        broker.get_fill_details.return_value = {
            "status": "FILLED", "broker_order_id": "34126091640603",
            "actual_fill_price": 235.47, "filled_quantity": 24, "requested_qty": 24,
            "order_status_raw": "FILLED", "fill_timestamp": "2026-09-16T13:02:05",
            "reconciliation_source": "DHAN_BROKER",
        }
        broker.get_positions.return_value = {"status": "success", "remarks": "", "data": []}
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(
                om, placed_at=datetime.now() - timedelta(days=1),
                fill_status="JOURNAL_RESTORED",
            )
            om.reconcile_startup_fills()
        assert "34126091640603" in om._orders
        assert om._orders["34126091640603"].fill_status == "FILLED"
        broker.get_positions.assert_not_called()

    def test_rejected_still_takes_precedence_over_cross_day_check(self):
        """The existing REJECTED/CANCELLED branch must still fire first and
        the new cross-day check must not double-process it."""
        broker = MagicMock()
        broker.get_fill_details.return_value = {
            "status": "REJECTED", "broker_order_id": "34126091640603",
            "actual_fill_price": 0.0, "filled_quantity": 0, "requested_qty": 24,
            "order_status_raw": "REJECTED", "fill_timestamp": "",
            "reconciliation_source": "DHAN_BROKER",
        }
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(
                om, placed_at=datetime.now() - timedelta(days=1),
                fill_status="JOURNAL_RESTORED",
            )
            om.reconcile_startup_fills()
        assert "34126091640603" not in om._orders
        broker.get_positions.assert_not_called()

    def test_broker_get_positions_failure_fails_safe(self):
        broker = _broker_stuck_api_error()
        broker.get_positions.side_effect = RuntimeError("network error")
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(om, placed_at=datetime.now() - timedelta(days=1))
            om.reconcile_startup_fills()
        assert "34126091640603" in om._orders

    def test_no_trade_monitor_injected_does_not_raise(self):
        broker = _broker_stuck_api_error()
        broker.get_positions.return_value = {"status": "success", "remarks": "", "data": []}
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(om, placed_at=datetime.now() - timedelta(days=1))
            assert om._trade_monitor is None
            reconciled = om.reconcile_startup_fills()  # must not raise
        assert reconciled == 1
        assert "34126091640603" not in om._orders
