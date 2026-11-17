"""Phase 2: entry/stop/target are anchored to the live price before any broker call."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from execution_engine.order_manager import OrderManager, OrderRecord
from models.trade_signal import SignalDirection, TradeSignal

SOURCE = (Path(__file__).resolve().parents[1] / "execution_engine" / "order_manager.py"
          ).read_text(encoding="utf-8")


def _manager(live_price=None, paper=False) -> OrderManager:
    om = OrderManager.__new__(OrderManager)
    om._paper_mode = paper
    om._broker = MagicMock()
    om._entry_quote_provider = (lambda symbol: live_price)
    return om


def _signal(direction="BUY", entry=100.0, stop=97.0, target=108.0, atr=0.0,
            zone_low=0.0, zone_high=0.0) -> TradeSignal:
    return TradeSignal(
        symbol="XYZTEST",
        direction=SignalDirection.BUY if direction == "BUY" else SignalDirection.SELL,
        entry_price=entry, stop_loss=stop, target_price=target, quantity=10,
        atr=atr, entry_zone_low=zone_low, entry_zone_high=zone_high,
    )


def test_buy_is_reanchored_with_distances_preserved():
    signal = _signal()
    assert _manager(99.0)._anchor_entry_to_market(signal) is None
    assert (signal.entry_price, signal.stop_loss, signal.target_price) == (99.0, 96.0, 107.0)
    assert signal.original_entry_price == 100.0
    assert signal.entry_price - signal.stop_loss == pytest.approx(3.0)
    assert signal.target_price - signal.entry_price == pytest.approx(8.0)


def test_sell_is_reanchored_symmetrically():
    signal = _signal("SELL", entry=100.0, stop=103.0, target=92.0)
    assert _manager(101.0)._anchor_entry_to_market(signal) is None
    assert (signal.entry_price, signal.stop_loss, signal.target_price) == (101.0, 104.0, 93.0)
    assert signal.stop_loss - signal.entry_price == pytest.approx(3.0)


def test_entry_zone_bounds_move_with_the_anchor():
    signal = _signal(zone_low=99.0, zone_high=101.0)
    _manager(99.0)._anchor_entry_to_market(signal)
    assert (signal.entry_zone_low, signal.entry_zone_high) == (98.0, 100.0)


def test_signal_beyond_the_staleness_limit_is_rejected_and_left_untouched():
    signal = _signal()
    reason = _manager(97.0)._anchor_entry_to_market(signal)
    assert reason[0] == "STALE_SIGNAL_PRICE_DRIFT"
    assert "drift=-3.00%" in reason[1]
    assert (signal.entry_price, signal.stop_loss, signal.target_price) == (100.0, 97.0, 108.0)
    assert signal.original_entry_price is None


def test_limit_widens_with_the_symbols_own_atr():
    narrow, wide = _signal(atr=0.0), _signal(atr=4.0)
    assert _manager(97.0)._anchor_entry_to_market(narrow) is not None
    assert _manager(97.0)._anchor_entry_to_market(wide) is None
    assert wide.entry_price == 97.0


def test_favourable_drift_is_also_bounded():
    assert _manager(103.0)._anchor_entry_to_market(_signal()) is not None


@pytest.mark.parametrize("live", [None, 0.0, -5.0, float("nan"), "bad"])
def test_unusable_live_price_fails_open(live):
    signal = _signal()
    assert _manager(live)._anchor_entry_to_market(signal) is None
    assert signal.entry_price == 100.0 and signal.original_entry_price is None


def test_a_wildly_different_quote_is_treated_as_bad_data_not_a_stale_signal():
    signal = _signal()
    assert _manager(60.0)._anchor_entry_to_market(signal) is None
    assert signal.entry_price == 100.0


def test_quote_provider_errors_fail_open():
    om = _manager()
    om._entry_quote_provider = MagicMock(side_effect=RuntimeError("feed down"))
    signal = _signal()
    assert om._anchor_entry_to_market(signal) is None
    assert signal.entry_price == 100.0


def test_paper_mode_and_missing_broker_are_untouched():
    signal = _signal()
    assert _manager(99.0, paper=True)._anchor_entry_to_market(signal) is None
    om = _manager(99.0)
    om._broker = None
    assert om._anchor_entry_to_market(signal) is None
    assert signal.entry_price == 100.0


def test_tiny_moves_are_not_worth_reanchoring():
    signal = _signal()
    assert _manager(100.03)._anchor_entry_to_market(signal) is None
    assert signal.entry_price == 100.0 and signal.original_entry_price is None


def test_a_failed_integrity_check_on_the_live_price_leaves_the_signal_alone():
    signal = _signal()
    validator = MagicMock()
    validator.validate.return_value = MagicMock(ok=False)
    with patch("data_integrity.price_integrity_validator.get_price_validator",
               return_value=validator):
        assert _manager(99.0)._anchor_entry_to_market(signal) is None
    assert signal.entry_price == 100.0


def test_reanchoring_twice_keeps_the_original_scanner_price():
    signal = _signal()
    _manager(99.0)._anchor_entry_to_market(signal)
    _manager(98.5)._anchor_entry_to_market(signal)
    assert signal.original_entry_price == 100.0
    assert signal.entry_price == 98.5
    assert signal.entry_price - signal.stop_loss == pytest.approx(3.0)


def test_broker_stop_order_uses_the_anchored_stop():
    om = _manager(99.0)
    signal = _signal()
    om._anchor_entry_to_market(signal)
    om._place_stop_loss(signal, 10, "ORD", product_type="CNC")
    kwargs = om._broker.place_sl_order.call_args.kwargs
    assert kwargs["trigger_price"] == 96.0
    assert kwargs["product_type"] == "CNC"


def test_real_quote_lookup_never_touches_the_network_under_pytest():
    om = OrderManager.__new__(OrderManager)
    assert om._live_reference_price("SBIN") is None


def test_anchoring_runs_before_any_broker_call_on_both_entry_paths():
    execute = SOURCE.index("    def execute(self, signal: TradeSignal,")
    call = SOURCE.index("self._anchor_entry_to_market(signal)", execute)
    assert call < SOURCE.index("self._place_entry_with_retry(signal", execute)
    assert call < SOURCE.index("self._place_stop_loss(signal", execute)
    slot_call = SOURCE.index("self._anchor_entry_to_market(slot.signal)")
    assert slot_call < SOURCE.index("self._broker_place(\n                slot.signal.symbol", slot_call)


def test_record_and_journal_carry_the_original_signal_price(tmp_path):
    assert OrderRecord(order_id="A", symbol="S", direction="BUY", quantity=1,
                       entry_price=1.0, stop_loss=0.5, target=2.0,
                       strategy="x").signal_entry_price == 0.0
    om = _manager()
    record = OrderRecord(order_id="A", symbol="S", direction="BUY", quantity=1,
                         entry_price=99.0, stop_loss=96.0, target=107.0, strategy="x",
                         placed_at=datetime.now(), signal_entry_price=100.0)
    journal = tmp_path / "journal.jsonl"
    with patch("execution_engine.order_manager.LIVE_ORDER_LOG", str(journal)), \
         patch("execution_engine.order_manager._LIVE_DIR", str(tmp_path)):
        om._append_live_journal("OPEN", record)
    assert json.loads(journal.read_text())["signal_entry_price"] == 100.0
