"""
tests/test_dta_carry_cnc_001.py
===============================================
DTA-CARRY-CNC-001 — real overnight carry for BUY equity positions.

ROOT CAUSE (flagged during DTA-EOD-INTRADAY-SQUAREOFF-001, fixed 2026-09-21):
OrderManager._broker_place() never overrode Dhan's default productType=
INTRADAY, so every position this system ever placed — including strategies
whose own carry-days budget (_CARRY_DAYS_BY_TYPE) explicitly assumes 3-7
trading days of holding — was force-flattened by the broker's own same-day
margin rules regardless of internal governance state. The entire
ACTIVE_CARRY/governance_state machinery in this file could never actually
hold a real position past one day.

FIX: BUY entries are now placed as productType=CNC (delivery) — this
system's own position sizing is already capital-independent / no-leverage
(INV-29 "No Leveraged Betting"; see CAPITAL_INDEPENDENCE_AUDIT.md), so CNC's
1x-cash requirement is already what every BUY position is sized for. CNC
lets a position genuinely survive overnight. SELL/SHORT entries remain
INTRADAY (mandatory same-day square-off for cash-segment equity shorting —
a regulatory constraint, not a choice). Exit orders, broker-side stop-loss
orders, and transaction-cost STT/exchange-charge computation all reuse the
position's own entry product_type so they stay consistent with what the
broker actually holds. check_and_expire_carries() — previously CSV-only,
correct only because the broker had already force-closed everything same
day — now places a real broker exit order for CNC positions before
recording the close, since a CNC holding does not auto-close on its own.

T01  _entry_product_type("BUY") == "CNC"
T02  _entry_product_type("SELL") == "INTRADAY"
T03  _broker_place() forwards product_type to broker.place_order()
T04  _broker_place() defaults to INTRADAY when product_type omitted
     (backward compatible with any caller that doesn't pass it)
T05  _place_stop_loss() forwards product_type to broker.place_sl_order()
T06  close_position() reuses the position's own product_type on the exit
     leg (CNC position closes with a CNC exit order)
T07  close_position() computes transaction costs with EQUITY_DELIVERY for
     a CNC position (vs EQUITY_INTRADAY for a plain INTRADAY position)
T08  check_and_expire_carries() places a real CNC broker exit order before
     recording SESSION_EXPIRED for an aged CNC position
T09  check_and_expire_carries() leaves a CNC position OPEN (no CLOSE row,
     governance_state restored to ACTIVE_CARRY) when the broker exit fails
T10  check_and_expire_carries() does NOT attempt a broker call for a
     plain INTRADAY position (legacy/short record) — CSV-only, unchanged
T11  _append_live_journal() persists product_type; _restore_from_live_journal()
     reconstructs it on the restored OrderRecord
T12  OrderRecord.product_type defaults to "INTRADAY" (backward compatible)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from execution_engine.order_manager import OrderManager, OrderRecord
from models.trade_signal import TradeSignal, SignalDirection


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


def _make_signal(symbol="ANANDRATHI", direction="BUY", entry=2204.8,
                  stop=2177.94, target=2334.18, qty=2) -> TradeSignal:
    return TradeSignal(
        symbol        = symbol,
        direction     = SignalDirection.BUY if direction == "BUY" else SignalDirection.SELL,
        entry_price   = entry,
        stop_loss     = stop,
        target_price  = target,
        quantity      = qty,
        confidence    = 7.5,
        strategy_name = "EDG_COMPOS_69_EE0000",
    )


def _insert_open_order(om, order_id="ORD-1", symbol="ANANDRATHI",
                        direction="BUY", product_type="CNC", **overrides):
    defaults = dict(
        order_id=order_id, symbol=symbol, direction=direction, quantity=2,
        entry_price=2204.8, stop_loss=2177.94, target=2334.18,
        strategy="EDG_COMPOS_69_EE0000", status="open", fill_status="FILLED",
        placed_at=datetime.now(), initial_stop_loss=2177.94,
        product_type=product_type,
    )
    defaults.update(overrides)
    rec = OrderRecord(**defaults)
    om._orders[order_id] = rec
    return rec


class TestEntryProductType:
    def test_t01_buy_is_cnc(self):
        om = OrderManager.__new__(OrderManager)
        assert om._entry_product_type("BUY") == "CNC"

    def test_t02_sell_is_intraday(self):
        om = OrderManager.__new__(OrderManager)
        assert om._entry_product_type("SELL") == "INTRADAY"


class TestBrokerPlaceForwarding:
    def test_t03_forwards_product_type(self):
        broker = MagicMock()
        broker.place_order.return_value = "OID-1"
        om = _make_om_live_with_broker(broker)
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                   {"ANANDRATHI": {"security_id": "7145", "segment": "NSE_EQ"}}):
            oid = om._broker_place("ANANDRATHI", "BUY", 2, 2204.8,
                                    order_type="LIMIT", product_type="CNC")
        assert oid == "OID-1"
        _, kwargs = broker.place_order.call_args
        assert kwargs["product_type"] == "CNC"

    def test_t04_defaults_to_intraday(self):
        broker = MagicMock()
        broker.place_order.return_value = "OID-2"
        om = _make_om_live_with_broker(broker)
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                   {"ANANDRATHI": {"security_id": "7145", "segment": "NSE_EQ"}}):
            om._broker_place("ANANDRATHI", "SELL", 2, 2204.8, order_type="MARKET")
        _, kwargs = broker.place_order.call_args
        assert kwargs["product_type"] == "INTRADAY"


class TestStopLossProductType:
    def test_t05_forwards_product_type(self):
        broker = MagicMock()
        broker.place_sl_order.return_value = "SL-1"
        om = _make_om_live_with_broker(broker)
        sig = _make_signal()
        sl_id = om._place_stop_loss(sig, 2, "OID-1", product_type="CNC")
        assert sl_id == "SL-1"
        _, kwargs = broker.place_sl_order.call_args
        assert kwargs["product_type"] == "CNC"


class TestClosePositionProductType:
    def test_t06_exit_reuses_entry_product_type(self):
        broker = MagicMock()
        broker.place_order.return_value = "EXIT-OID"
        broker.get_fill_details.return_value = {"status": "FILLED"}
        om = _make_om_live_with_broker(broker)
        _insert_open_order(om, product_type="CNC")
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                   {"ANANDRATHI": {"security_id": "7145", "segment": "NSE_EQ"}}):
            ok = om.close_position("ORD-1", 2250.0, reason="manual")
        assert ok is True
        _, kwargs = broker.place_order.call_args
        assert kwargs["product_type"] == "CNC"

    def test_t07_cnc_uses_delivery_cost_model(self):
        broker = MagicMock()
        broker.place_order.return_value = "EXIT-OID"
        broker.get_fill_details.return_value = {"status": "FILLED"}
        om = _make_om_live_with_broker(broker)
        _insert_open_order(om, order_id="ORD-CNC", product_type="CNC")
        _insert_open_order(om, order_id="ORD-INTRADAY", product_type="INTRADAY")
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                   {"ANANDRATHI": {"security_id": "7145", "segment": "NSE_EQ"}}), \
             patch("models.transaction_costs.get_cost_model") as _gcm:
            _model = MagicMock()
            _model.compute.return_value = MagicMock(total_cost=10.0)
            _gcm.return_value = _model
            om.close_position("ORD-CNC", 2250.0, reason="manual")
            _cnc_kwargs = _model.compute.call_args.kwargs
            om.close_position("ORD-INTRADAY", 2250.0, reason="manual")
            _intraday_kwargs = _model.compute.call_args.kwargs
        from models.transaction_costs import InstrumentType
        assert _cnc_kwargs["instrument_type"] == InstrumentType.EQUITY_DELIVERY
        assert _intraday_kwargs["instrument_type"] == InstrumentType.EQUITY_INTRADAY


class TestCarryExpiryBrokerExecution:
    def test_t08_places_real_cnc_exit_before_recording_close(self):
        broker = MagicMock()
        broker.place_order.return_value = "CARRY-EXIT-OID"
        om = _make_om_live_with_broker(broker)
        old_placed = datetime.now() - timedelta(days=10)
        _insert_open_order(om, product_type="CNC", placed_at=old_placed)
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                   {"ANANDRATHI": {"security_id": "7145", "segment": "NSE_EQ"}}), \
             patch.object(OrderManager, "_review_carry_extension_dryrun", return_value=None):
            expired = om.check_and_expire_carries(live_prices={"ANANDRATHI": 2250.0})
        assert expired == 1
        broker.place_order.assert_called_once()
        _, kwargs = broker.place_order.call_args
        assert kwargs["product_type"] == "CNC"
        assert om._orders["ORD-1"].status == "closed"

    def test_t09_broker_failure_keeps_position_open(self):
        broker = MagicMock()
        broker.place_order.return_value = None  # simulate broker rejection
        om = _make_om_live_with_broker(broker)
        old_placed = datetime.now() - timedelta(days=10)
        _insert_open_order(om, product_type="CNC", placed_at=old_placed)
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                   {"ANANDRATHI": {"security_id": "7145", "segment": "NSE_EQ"}}), \
             patch.object(OrderManager, "_review_carry_extension_dryrun", return_value=None):
            expired = om.check_and_expire_carries(live_prices={"ANANDRATHI": 2250.0})
        assert expired == 0
        rec = om._orders["ORD-1"]
        assert rec.status == "open"
        assert rec.governance_state == "ACTIVE_CARRY"

    def test_t10_intraday_position_never_calls_broker(self):
        broker = MagicMock()
        om = _make_om_live_with_broker(broker)
        old_placed = datetime.now() - timedelta(days=10)
        _insert_open_order(om, product_type="INTRADAY", placed_at=old_placed)
        with patch.object(OrderManager, "_review_carry_extension_dryrun", return_value=None):
            expired = om.check_and_expire_carries(live_prices={"ANANDRATHI": 2250.0})
        assert expired == 1
        broker.place_order.assert_not_called()
        assert om._orders["ORD-1"].status == "closed"


class TestJournalRoundTrip:
    def test_t11_product_type_persisted_and_restored(self, tmp_path):
        om = OrderManager.__new__(OrderManager)
        rec = OrderRecord(
            order_id="ORD-J1", symbol="ANANDRATHI", direction="BUY", quantity=2,
            entry_price=2204.8, stop_loss=2177.94, target=2334.18,
            strategy="EDG_COMPOS_69_EE0000", broker_order_id="ORD-J1",
            fill_status="FILLED", actual_fill_price=2204.8,
            product_type="CNC",
        )
        journal_path = tmp_path / "live_orders.jsonl"
        with patch("execution_engine.order_manager.LIVE_ORDER_LOG", str(journal_path)), \
             patch("execution_engine.order_manager._LIVE_DIR", str(tmp_path)):
            OrderManager._append_live_journal(om, "OPEN", rec)
        line = json.loads(journal_path.read_text().strip().splitlines()[0])
        assert line["product_type"] == "CNC"

        # Reconstruct like _restore_from_live_journal does
        restored = OrderRecord(
            order_id=line["order_id"], symbol=line["symbol"],
            direction=line["direction"], quantity=int(line["quantity"]),
            entry_price=float(line["entry_price"]), stop_loss=float(line["stop_loss"]),
            target=float(line["target_price"]), strategy=line["strategy"],
            fill_status="JOURNAL_RESTORED",
            actual_fill_price=float(line["actual_fill_price"] or line["entry_price"]),
            product_type=line.get("product_type") or "INTRADAY",
        )
        assert restored.product_type == "CNC"


class TestOrderRecordDefault:
    def test_t12_defaults_to_intraday(self):
        rec = OrderRecord(
            order_id="X", symbol="Y", direction="BUY", quantity=1,
            entry_price=1.0, stop_loss=0.9, target=1.2, strategy="s",
        )
        assert rec.product_type == "INTRADAY"
