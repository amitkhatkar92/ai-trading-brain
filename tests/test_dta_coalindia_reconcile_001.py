"""
tests/test_dta_coalindia_reconcile_001.py
==========================================
DTA-COALINDIA-RECONCILE-001 — Cross-day broker position reconciliation.

Root cause confirmed via live read-only audit (2026-09-09):
    COALINDIA order_id=34126090853803 was placed 2026-09-08, filled by Dhan
    at 14:01:09 IST, then auto-squared-off by Dhan's own intraday RMS at
    15:11:24 IST the same day (confirmed via get_trade_history()). Our
    internal fill_status stayed "API_ERROR" the whole time because
    get_order_by_id()/get_order_list() are BOTH day-scoped by Dhan and can
    never resolve an order placed on a previous calendar day — so the
    position was retried every 5 minutes indefinitely without ever being
    corrected, continuing to consume capital/exposure budget for a position
    that no longer existed at the broker.

Fix: reconcile_pending_orders() now cross-checks get_positions() (which is
NOT day-scoped) for any order stuck unresolved from a PREVIOUS calendar day.
If the broker confirms no matching open position, internal state is
corrected (no order is ever placed/modified/cancelled).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from execution_engine.order_manager import OrderManager, OrderRecord


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


def _insert_stuck_order(om, placed_at, order_id="ORD-COAL-001", symbol="COALINDIA"):
    rec = OrderRecord(
        order_id=order_id, symbol=symbol, direction="BUY", quantity=5,
        entry_price=419.85, stop_loss=405.45, target=449.33,
        strategy="KDA_AUTHORITY", status="open", fill_status="API_ERROR",
        placed_at=placed_at, initial_stop_loss=405.45,
    )
    om._orders[order_id] = rec
    return rec


_SEC_MAP = {"COALINDIA": {"security_id": "20374", "segment": "NSE_EQ"}}


def _broker_stuck_api_error():
    """Broker whose get_fill_details() never resolves — mirrors real COALINDIA."""
    broker = MagicMock()
    broker.get_fill_details.return_value = {
        "status": "API_ERROR", "broker_order_id": "ORD-COAL-001",
        "actual_fill_price": 0.0, "filled_quantity": 0, "requested_qty": 5,
        "order_status_raw": "API_ERROR", "fill_timestamp": "",
        "reconciliation_source": "DHAN_BROKER",
    }
    return broker


class TestCrossDayBrokerPositionCheck:

    def test_cross_day_stuck_order_confirmed_absent_is_cleaned_up(self):
        """Order from a previous day, broker confirms no open position → removed."""
        broker = _broker_stuck_api_error()
        broker.get_positions.return_value = {"status": "success", "remarks": "", "data": []}
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(om, placed_at=datetime.now() - timedelta(days=1))
            updated = om.reconcile_pending_orders()
        assert "ORD-COAL-001" in updated
        assert "ORD-COAL-001" not in om._orders
        assert "COALINDIA" not in om._portfolio.positions

    def test_cross_day_stuck_order_still_open_at_broker_is_kept(self):
        """Broker confirms a live position still exists → must NOT be removed."""
        broker = _broker_stuck_api_error()
        broker.get_positions.return_value = {
            "status": "success", "remarks": "",
            "data": [{"securityId": "20374", "netQty": 5, "positionType": "LONG"}],
        }
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(om, placed_at=datetime.now() - timedelta(days=1))
            updated = om.reconcile_pending_orders()
        assert "ORD-COAL-001" not in updated
        assert "ORD-COAL-001" in om._orders
        assert om._orders["ORD-COAL-001"].fill_status == "API_ERROR"

    def test_same_day_stuck_order_not_touched_by_cross_day_check(self):
        """An order placed TODAY must never be swept by the cross-day check,
        even if get_positions() would say absent — same-day orders can still
        resolve normally later in the session."""
        broker = _broker_stuck_api_error()
        broker.get_positions.return_value = {"status": "success", "remarks": "", "data": []}
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(om, placed_at=datetime.now())
            updated = om.reconcile_pending_orders()
        assert "ORD-COAL-001" not in updated
        assert "ORD-COAL-001" in om._orders
        broker.get_positions.assert_not_called()

    def test_broker_get_positions_failure_fails_safe(self):
        """get_positions() raising must NOT remove the order (fail safe)."""
        broker = _broker_stuck_api_error()
        broker.get_positions.side_effect = RuntimeError("network error")
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(om, placed_at=datetime.now() - timedelta(days=1))
            updated = om.reconcile_pending_orders()
        assert "ORD-COAL-001" not in updated
        assert "ORD-COAL-001" in om._orders

    def test_broker_get_positions_bad_status_fails_safe(self):
        """A non-'success' status response must NOT remove the order."""
        broker = _broker_stuck_api_error()
        broker.get_positions.return_value = {"status": "failure", "remarks": "err", "data": ""}
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(om, placed_at=datetime.now() - timedelta(days=1))
            updated = om.reconcile_pending_orders()
        assert "ORD-COAL-001" not in updated
        assert "ORD-COAL-001" in om._orders

    def test_unmapped_symbol_fails_safe(self):
        """Symbol missing from DHAN_SECURITY_MAP must not crash and must not
        remove the order (cannot verify without a security_id)."""
        broker = _broker_stuck_api_error()
        broker.get_positions.return_value = {"status": "success", "remarks": "", "data": []}
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", {}):
            om = _make_om_live_with_broker(broker)
            _insert_stuck_order(om, placed_at=datetime.now() - timedelta(days=1))
            updated = om.reconcile_pending_orders()
        assert "ORD-COAL-001" not in updated
        assert "ORD-COAL-001" in om._orders

    def test_no_broker_configured_never_calls_position_check(self):
        """_broker_confirms_no_open_position() must return False safely when
        there is no broker at all (e.g. paper mode short-circuits earlier,
        but the helper itself must also be defensive)."""
        om = _make_om_live_with_broker(MagicMock())
        om._broker = None
        assert om._broker_confirms_no_open_position("COALINDIA") is False
