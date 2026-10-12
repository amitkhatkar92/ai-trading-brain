"""Options-only funds, entry-fill, rollback, and exit-quantity safeguards."""
from __future__ import annotations

import threading
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

from execution_engine.options_order_manager import (
    OptionsOrderManager,
    OptionsOrderRecord,
    ROLLBACK_FAILURE_COLUMNS,
)
from execution_engine.brokers.dhan_broker import DhanBroker


def _manager(broker: MagicMock) -> OptionsOrderManager:
    manager = OptionsOrderManager.__new__(OptionsOrderManager)
    manager._paper_mode = False
    manager._broker = broker
    manager._orders = {}
    manager._unresolved = {}
    manager._feed = MagicMock()
    manager._lock = threading.Lock()
    return manager


def _record(**overrides) -> OptionsOrderRecord:
    fields = dict(
        order_id="OPT_NIFTY_IC_SAFETY",
        symbol="NIFTY",
        strategy="Iron_Condor_Range",
        option_type="IRON_CONDOR",
        direction="SELL",
        lots=1,
        lot_size=65,
        entry_premium=50.0,
        stop_premium=90.0,
        target_premium=10.0,
        max_loss_rs=2600.0,
        max_profit_rs=3250.0,
        expiry_date=date.today() + timedelta(days=20),
        dte_at_entry=20,
        iv_rank_at_entry=50.0,
        spot_at_entry=22000.0,
        regime_at_entry="RANGE_MARKET",
        placed_at=datetime.now(),
        legs=[
            {"direction": "SELL", "strike": 21950, "type": "CE", "premium": 60.0},
            {"direction": "BUY", "strike": 22000, "type": "CE", "premium": 30.0},
        ],
    )
    fields.update(overrides)
    return OptionsOrderRecord(**fields)


def _ready_broker() -> MagicMock:
    broker = MagicMock()
    broker.get_fund_limits.return_value = {
        "status": "success", "data": {"availabelBalance": 100000.0},
    }
    broker.calculate_multi_order_margin.return_value = {
        "status": "success", "data": {"totalMargin": 10000.0},
    }
    return broker


def _security_map():
    fake_map = MagicMock()
    fake_map.lookup.side_effect = ["SEC_BUY", "SEC_SELL"]
    return fake_map


def test_margin_preflight_blocks_before_any_leg_when_funds_are_short():
    broker = _ready_broker()
    broker.get_fund_limits.return_value["data"]["availabelBalance"] = 17394.96
    broker.calculate_multi_order_margin.return_value["data"]["totalMargin"] = 97495.71
    manager = _manager(broker)

    with patch(
        "data_feeds.dhan_fno_security_map.get_fno_security_map",
        return_value=_security_map(),
    ):
        result = manager._place_live_legs(_record(), {"legs": _record().legs})

    assert result is None
    broker.place_order.assert_not_called()
    broker.calculate_multi_order_margin.assert_called_once()


def test_margin_preflight_fails_closed_when_dhan_response_is_unavailable():
    broker = _ready_broker()
    broker.calculate_multi_order_margin.return_value = {}
    manager = _manager(broker)

    with patch(
        "data_feeds.dhan_fno_security_map.get_fno_security_map",
        return_value=_security_map(),
    ):
        result = manager._place_live_legs(_record(), {"legs": _record().legs})

    assert result is None
    broker.place_order.assert_not_called()


def test_rejected_later_leg_reverses_confirmed_fill_and_does_not_accept_spread():
    broker = _ready_broker()
    broker.place_order.side_effect = ["BUY_ENTRY", "SELL_ENTRY", "BUY_REVERSAL"]
    broker.get_order_status.side_effect = [
        {"status": "TRADED", "filled_qty": 65, "avg_fill_price": 30.0},
        {
            "status": "REJECTED", "filled_qty": 0, "avg_fill_price": 0.0,
            "oms_error_detail": "insufficient funds",
        },
        {"status": "REJECTED", "filled_qty": 0},
        {"status": "TRADED", "filled_qty": 65},
    ]
    manager = _manager(broker)
    record = _record()

    with patch(
        "data_feeds.dhan_fno_security_map.get_fno_security_map",
        return_value=_security_map(),
    ):
        result = manager._place_live_legs(record, {"legs": record.legs})

    assert result is None
    assert broker.place_order.call_count == 3
    assert broker.place_order.call_args.kwargs["quantity"] == 65
    assert record.entry_leg_fills[0]["qty_filled"] == 65
    assert record.entry_leg_fills[1]["oms_error_detail"] == "insufficient funds"


def test_partial_entry_is_cancelled_and_only_confirmed_quantity_reversed():
    broker = _ready_broker()
    broker.cancel_order.return_value = True
    broker.get_order_status.side_effect = [
        {"status": "PARTIALLY_TRADED", "filled_qty": 20, "remaining_qty": 45},
        {"status": "CANCELLED", "filled_qty": 20, "remaining_qty": 0},
    ]
    broker.place_order.return_value = "REVERSAL"
    manager = _manager(broker)
    record = _record()

    manager._rollback_legs(
        [("ENTRY", "SEC_BUY", "BUY", record.legs[1])], record
    )

    broker.cancel_order.assert_called_once_with("ENTRY")
    assert broker.place_order.call_args.kwargs["quantity"] == 20
    assert broker.place_order.call_args.kwargs["transaction_type"] == "SELL"
    assert manager._unresolved == {}


def test_fill_racing_pending_cancel_is_reconciled_and_reversed():
    broker = _ready_broker()
    broker.cancel_order.return_value = True
    broker.get_order_status.side_effect = [
        {"status": "OPEN", "filled_qty": 0, "remaining_qty": 65},
        {"status": "TRADED", "filled_qty": 65, "remaining_qty": 0},
        {"status": "TRADED", "filled_qty": 65, "remaining_qty": 0},
    ]
    broker.place_order.return_value = "REVERSAL"
    manager = _manager(broker)
    record = _record()

    manager._rollback_legs(
        [("ENTRY", "SEC_BUY", "BUY", record.legs[1])], record
    )

    broker.cancel_order.assert_called_once_with("ENTRY")
    assert broker.place_order.call_args.kwargs["quantity"] == 65
    assert broker.place_order.call_args.kwargs["transaction_type"] == "SELL"
    assert manager._unresolved == {}


def test_exit_places_order_only_for_the_leg_and_quantity_actually_filled():
    broker = _ready_broker()
    broker.place_order.return_value = "EXIT_BUY_LEG"
    manager = _manager(broker)
    record = _record(entry_leg_fills=[
        {
            "direction": "BUY", "strike": 22000, "opt_type": "CE",
            "status": "TRADED", "qty_filled": 65, "avg_price": 30.0,
        },
        {
            "direction": "SELL", "strike": 21950, "opt_type": "CE",
            "status": "REJECTED", "qty_filled": 0, "avg_price": 0.0,
        },
    ])

    with patch(
        "data_feeds.dhan_fno_security_map.get_fno_security_map",
        return_value=_security_map(),
    ):
        exit_ids = manager._place_live_exit_legs(record)

    assert exit_ids == ["EXIT_BUY_LEG"]
    broker.place_order.assert_called_once()
    assert broker.place_order.call_args.kwargs["transaction_type"] == "SELL"
    assert broker.place_order.call_args.kwargs["quantity"] == 65


def test_partial_exit_fill_does_not_mark_position_closed():
    broker = _ready_broker()
    manager = _manager(broker)
    record = _record(entry_leg_fills=[
        {
            "direction": "BUY", "strike": 22000, "opt_type": "CE",
            "status": "TRADED", "qty_filled": 65, "avg_price": 30.0,
        },
    ])
    record.status = "open"
    manager._orders[record.order_id] = record
    manager._place_live_exit_legs = MagicMock(return_value=["EXIT_PARTIAL"])
    manager._poll_exit_fills = MagicMock(return_value=[{
        "status": "PARTIALLY_TRADED", "qty_filled": 20,
        "requested_qty": 65, "avg_price": 25.0,
    }])
    manager._journal_write_close = MagicMock()

    manager._close_position(record.order_id, 25.0, "STOP_LOSS")

    assert record.status == "EXIT_SUBMITTED"
    assert record.broker_status == "UNRESOLVED_LIVE_EXPOSURE"
    manager._journal_write_close.assert_not_called()


def test_dhan_adapter_uses_read_only_multi_order_margin_endpoint():
    broker = DhanBroker.__new__(DhanBroker)
    broker._connected = True
    broker.client_id = "test-client"
    broker._dhan = MagicMock()
    broker._dhan.dhan_http.post.return_value = {
        "status": "success", "data": {"totalMargin": 1234.0},
    }
    orders = [{
        "exchangeSegment": "NSE_FNO",
        "transactionType": "BUY",
        "quantity": 65,
        "productType": "MARGIN",
        "securityId": "12345",
        "price": 100.0,
    }]

    result = broker.calculate_multi_order_margin(orders)

    assert result["data"]["totalMargin"] == 1234.0
    broker._dhan.dhan_http.post.assert_called_once_with(
        "/margincalculator/multi",
        {
            "includePosition": False,
            "includeOrders": False,
            "dhanClientId": "test-client",
            "scripList": orders,
        },
    )


def test_dhan_adapter_funds_lookup_fails_closed_when_disconnected():
    broker = DhanBroker.__new__(DhanBroker)
    broker._connected = False
    broker._dhan = None

    assert broker.get_fund_limits() == {}


def test_unresolved_filled_long_leg_counts_premium_at_risk(tmp_path):
    import csv

    journal = tmp_path / "rollback.csv"
    with journal.open("w", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=ROLLBACK_FAILURE_COLUMNS).writeheader()
    manager = _manager(MagicMock())
    record = _record()
    leg = {"direction": "BUY", "strike": 22000, "type": "CE", "premium": 282.55}

    with patch(
        "execution_engine.options_order_manager.ROLLBACK_FAILURES_PATH",
        str(journal),
    ):
        manager._record_rollback_failure(
            original_order_id="ENTRY",
            security_id="SEC_BUY",
            leg=leg,
            rec=record,
            original_tx="BUY",
            filled_qty_raw=65,
            reversal_tx="SELL",
            reversal_order_id=None,
            status="UNRESOLVED_LIVE_EXPOSURE",
            reason="reversal rejected",
            per_leg_max_loss=100.0,
        )

    assert manager.get_total_options_exposure_rs() == 282.55 * 65


def test_unresolved_short_leg_blocks_new_options_exposure(tmp_path):
    import csv
    import math

    journal = tmp_path / "rollback.csv"
    with journal.open("w", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=ROLLBACK_FAILURE_COLUMNS).writeheader()
    manager = _manager(MagicMock())
    record = _record()
    with patch(
        "execution_engine.options_order_manager.ROLLBACK_FAILURES_PATH",
        str(journal),
    ):
        manager._record_rollback_failure(
            original_order_id="ENTRY",
            security_id="SEC_SELL",
            leg={"direction": "SELL", "strike": 21950, "type": "CE", "premium": 60.0},
            rec=record,
            original_tx="SELL",
            filled_qty_raw=65,
            reversal_tx="BUY",
            reversal_order_id=None,
            status="UNRESOLVED_LIVE_EXPOSURE",
            reason="reversal not confirmed",
            per_leg_max_loss=100.0,
        )

    assert math.isinf(manager.get_total_options_exposure_rs())


def test_partial_structure_realized_pnl_uses_actual_leg_cashflows():
    manager = _manager(MagicMock())
    record = _record(
        entry_leg_fills=[{
            "direction": "BUY", "strike": 22000, "opt_type": "CE",
            "status": "TRADED", "qty_filled": 65, "avg_price": 282.55,
        }],
        exit_leg_fills=[{
            "direction": "SELL", "strike": 22000, "opt_type": "CE",
            "status": "TRADED", "qty_filled": 65, "avg_price": 250.0,
        }],
    )

    assert manager._compute_realized_pnl(record) == -2115.75