"""
tests/test_dta_tick_size_001.py
===============================================
DTA-TICK-SIZE-001 — NSE equity order prices must be an exact multiple of
the exchange tick size (0.05), not merely 2-decimal-place rounded.

ROOT CAUSE (found investigating a real, user-reported 20% execution
conversion rate 2026-09-24/25 and Dhan orders shown as immediately failed):
every place computing a LIMIT entry price or a stop-loss trigger/price used
round(x, 2) only — this produces perfectly valid paisa amounts (e.g.
171.84) that are NOT a multiple of 0.05 (171.84 / 0.05 = 3436.8), which
Dhan's exchange-side validation rejects outright with:
  "16283: EXCH:16283:The order price is not multiple of the tick size."
Confirmed live in control_tower.db (ct_events) as the dominant recurring
BROKER_REJECTED_ORDER reason across many days for SBIN, TATACONSUM,
COALINDIA, INDHOTEL.

FIX (part 2, same-day follow-up — found via a real Dhan executed-orders
export showing SBIN's LIMIT price of 979.95 as "Failed" even though 979.95
IS a valid 0.05-multiple): SBIN uses a WIDER tick under SEBI's revised
tick-size framework (confirmed live via order logs: zone=979.95 rejected
with the identical tick-size error). A blanket 0.05 default is unsafe.
_resolve_tick_size() now looks up the REAL, verified per-symbol tick size
from Dhan's own instrument master (SEM_TICK_SIZE, already downloaded daily
by DhanFnOSecurityMap for F&O lot sizes — extended additively, same file,
same download, to also index NSE_EQ tick sizes) and falls back to 0.05
only when the symbol isn't found there.

T01  _round_to_tick rounds a non-tick-aligned price to the nearest 0.05
T02  _round_to_tick leaves an already-aligned price unchanged
T03  _round_to_tick handles the exact real-world failure case (171.84)
T04  _broker_place rounds price to tick when order_type="LIMIT"
T05  _broker_place leaves price untouched when order_type="MARKET"
T06  _place_stop_loss sends tick-rounded trigger_price and price
T07  partial-fill SL resubmission sends tick-rounded trigger_price/price
T08  _resolve_tick_size returns the real per-symbol tick when known
T09  _resolve_tick_size falls back to 0.05 when the symbol is unknown
T10  _resolve_tick_size fails open to 0.05 if the lookup itself raises
T11  _broker_place uses SBIN's real (wider) tick, reproducing the exact
     live bug: 979.95 is a valid 0.05-tick but NOT a valid 0.10-tick
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from execution_engine.order_manager import OrderManager, _round_to_tick, _resolve_tick_size
from models.trade_signal import TradeSignal, SignalDirection


def _make_signal(symbol="SBIN", direction="BUY", entry=171.836,
                  stop=167.73, target=182.12, qty=31) -> TradeSignal:
    return TradeSignal(
        symbol        = symbol,
        direction     = SignalDirection.BUY if direction == "BUY" else SignalDirection.SELL,
        entry_price   = entry,
        stop_loss     = stop,
        target_price  = target,
        quantity      = qty,
        confidence    = 6.5,
        strategy_name = "KDA_AUTHORITY",
    )


class TestRoundToTick:
    def test_t01_rounds_to_nearest_tick(self):
        assert _round_to_tick(171.836) == 171.85
        assert _round_to_tick(171.81) == 171.80

    def test_t02_already_aligned_unchanged(self):
        assert _round_to_tick(171.85) == 171.85
        assert _round_to_tick(100.00) == 100.00

    def test_t03_reproduces_real_failure_case(self):
        # 171.84 is 2dp-valid but NOT a multiple of 0.05 — the real bug.
        rounded = _round_to_tick(171.84)
        assert round(rounded / 0.05, 6) == round(rounded / 0.05)
        assert rounded == 171.85


def _om_with_broker(broker_mock):
    om = OrderManager.__new__(OrderManager)
    om._broker = broker_mock
    return om


class TestBrokerPlaceTickRounding:
    def test_t04_limit_order_rounds_price(self):
        broker = MagicMock()
        broker.place_order.return_value = "OID-1"
        om = _om_with_broker(broker)
        with (
            patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                  {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
            patch("data_feeds.dhan_fno_security_map.get_equity_tick_size", return_value=None),
        ):
            om._broker_place("SBIN", "BUY", 260, 171.84, order_type="LIMIT")
        _, kwargs = broker.place_order.call_args
        assert kwargs["price"] == 171.85

    def test_t05_market_order_price_untouched(self):
        broker = MagicMock()
        broker.place_order.return_value = "OID-2"
        om = _om_with_broker(broker)
        with (
            patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                  {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
            patch("data_feeds.dhan_fno_security_map.get_equity_tick_size", return_value=None),
        ):
            om._broker_place("SBIN", "SELL", 260, 171.84, order_type="MARKET")
        _, kwargs = broker.place_order.call_args
        assert kwargs["price"] == 171.84


class TestStopLossTickRounding:
    def test_t06_trigger_and_price_rounded(self):
        broker = MagicMock()
        broker.place_sl_order.return_value = "SL-1"
        om = _om_with_broker(broker)
        sig = _make_signal(stop=167.731)
        with patch("data_feeds.dhan_fno_security_map.get_equity_tick_size", return_value=None):
            om._place_stop_loss(sig, 31, "OID-1")
        _, kwargs = broker.place_sl_order.call_args
        for val in (kwargs["trigger_price"], kwargs["price"]):
            assert round(val / 0.05, 6) == round(val / 0.05)


class TestPartialFillSlTickRounding:
    def test_t07_resubmitted_sl_is_tick_rounded(self):
        from execution_engine.order_manager import OrderRecord
        from datetime import datetime

        broker = MagicMock()
        broker.get_order_status.return_value = {"status": "PARTIALLY_FILLED", "filled_qty": 15}
        broker.place_sl_order.return_value = "SL-2"
        broker.cancel_order.return_value = True
        om = _om_with_broker(broker)
        om._paper_mode = False
        rec = OrderRecord(
            order_id="OID-1", symbol="SBIN", direction="BUY", quantity=31,
            entry_price=171.84, stop_loss=167.731, target=182.12,
            strategy="KDA_AUTHORITY", status="open", fill_status="PENDING",
            placed_at=datetime.now(), initial_stop_loss=167.731,
            sl_order_id="OLD-SL", order_type="LIMIT",
        )
        om._orders = {"OID-1": rec}
        with patch("data_feeds.dhan_fno_security_map.get_equity_tick_size", return_value=None):
            om.reconcile_partial_fills()
        _, kwargs = broker.place_sl_order.call_args
        for val in (kwargs["trigger_price"], kwargs["price"]):
            assert round(val / 0.05, 6) == round(val / 0.05)


class TestResolveTickSize:
    def test_t08_uses_real_per_symbol_tick(self):
        with patch("data_feeds.dhan_fno_security_map.get_equity_tick_size", return_value=0.10):
            assert _resolve_tick_size("SBIN") == 0.10

    def test_t09_falls_back_to_default_when_unknown(self):
        with patch("data_feeds.dhan_fno_security_map.get_equity_tick_size", return_value=None):
            assert _resolve_tick_size("UNKNOWNSYM") == 0.05

    def test_t10_fails_open_on_lookup_exception(self):
        with patch("data_feeds.dhan_fno_security_map.get_equity_tick_size",
                   side_effect=RuntimeError("boom")):
            assert _resolve_tick_size("SBIN") == 0.05

    def test_t11_reproduces_real_sbin_bug(self):
        # 979.95 is a valid 0.05-tick but genuinely invalid for a 0.10-tick
        # symbol — this is the exact real rejection reproduced end to end.
        broker = MagicMock()
        broker.place_order.return_value = "OID-3"
        om = _om_with_broker(broker)
        with (
            patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                  {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}),
            patch("data_feeds.dhan_fno_security_map.get_equity_tick_size", return_value=0.10),
        ):
            om._broker_place("SBIN", "BUY", 5, 979.95, order_type="LIMIT")
        _, kwargs = broker.place_order.call_args
        sent_price = kwargs["price"]
        assert round(sent_price / 0.10, 6) == round(sent_price / 0.10)
        assert sent_price != 979.95
