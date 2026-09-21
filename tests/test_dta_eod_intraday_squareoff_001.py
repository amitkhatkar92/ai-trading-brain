"""
tests/test_dta_eod_intraday_squareoff_001.py
===============================================
DTA-EOD-INTRADAY-SQUAREOFF-001 — system-controlled EOD close for ordinary
(non-CARRY) intraday positions, run ahead of the broker's own auto square-off.

Root cause (found 2026-09-21 investigating a real ANANDRATHI trade): every
order this system places goes to Dhan as productType=INTRADAY
(execution_engine/order_manager.py::_broker_place() never overrides it).
That is a same-day-only broker margin product — Dhan WILL forcibly close it
before close regardless of our own logic, but that forced close bypasses
this system's own order-placement path entirely (confirmed live:
correlationId="NA" on the broker's own closing order, vs a real
correlationId on our own entry order) and is therefore never logged to
live_orders.jsonl or ct_events. A real position was auto-squared by Dhan at
15:11:37, short of its target, with zero record of the exit anywhere in
this system.

Fix: OrderManager.close_all_positions() gained an optional `reason` param
(default "emergency_close", fully backward compatible with the existing
SYSTEM_HALT/DRAWDOWN kill-switch callers). MasterOrchestrator gained
_do_eod_intraday_squareoff(), scheduled at 15:05 IST (ahead of Dhan's own
observed ~15:11 auto square-off window), which closes every still-open,
non-CARRY position through the normal close_position() path -- so the exit
is priced, logged, and fed into learning/risk like any other system-driven
exit. CARRY-tagged (multi-day) positions are never touched.

T01  close_all_positions() default reason is still "emergency_close"
     (backward compatible with SYSTEM_HALT/DRAWDOWN callers)
T02  close_all_positions(reason=...) stamps the custom reason on a
     was-monitored position's close_reason
T03  close_all_positions(reason=...) still uses ORPHAN_CLOSE (not the
     custom reason) for a never-monitored position -- unchanged behavior
T04  _do_eod_intraday_squareoff is scheduled at 15:05, strictly before
     15:30 market close notify
T05  _do_eod_intraday_squareoff source excludes CARRY order_type positions
T06  _do_eod_intraday_squareoff source no-ops when PAPER_TRADING is True
     (paper mode already handled by the separate GAP-007 block)
T07  _do_eod_intraday_squareoff source closes via close_position() with
     reason="EOD_INTRADAY_SQUAREOFF"
T08  _do_eod_intraday_squareoff source respects the NSE holiday guard
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from execution_engine.order_manager import OrderManager, OrderRecord
from models.portfolio import Portfolio, Position

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


def _insert_open_order(om, order_id="ORD-1", symbol="ANANDRATHI"):
    rec = OrderRecord(
        order_id=order_id, symbol=symbol, direction="BUY", quantity=2,
        entry_price=2204.8, stop_loss=2177.94, target=2334.18,
        strategy="EDG_COMPOS_69_EE0000", status="open", fill_status="FILLED",
        placed_at=datetime.now(), initial_stop_loss=2177.94,
    )
    om._orders[order_id] = rec
    return rec


class TestCloseAllPositionsReason:

    def test_t01_default_reason_backward_compatible(self):
        broker = MagicMock()
        broker.place_order.return_value = "EXIT-1"
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            rec = _insert_open_order(om)
            om._portfolio.positions["ANANDRATHI"] = Position(
                symbol="ANANDRATHI", quantity=2, avg_entry_price=2204.8,
                ltp=2210.25, has_live_ltp=True,
            )
            om.close_all_positions()
        assert rec.close_reason == "emergency_close"

    def test_t02_custom_reason_stamped_when_monitored(self):
        broker = MagicMock()
        broker.place_order.return_value = "EXIT-2"
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            rec = _insert_open_order(om)
            om._portfolio.positions["ANANDRATHI"] = Position(
                symbol="ANANDRATHI", quantity=2, avg_entry_price=2204.8,
                ltp=2210.25, has_live_ltp=True,
            )
            om.close_all_positions(reason="EOD_INTRADAY_SQUAREOFF")
        assert rec.close_reason == "EOD_INTRADAY_SQUAREOFF"

    def test_t03_orphan_close_unaffected_by_custom_reason(self):
        broker = MagicMock()
        broker.place_order.return_value = "EXIT-3"
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            rec = _insert_open_order(om)
            # never monitored this session -- no Position / has_live_ltp entry
            om.close_all_positions(reason="EOD_INTRADAY_SQUAREOFF")
        assert rec.close_reason == "ORPHAN_CLOSE"


class TestEodIntradaySquareoffScheduling:

    @staticmethod
    def _orch_source() -> str:
        import inspect
        from orchestrator.master_orchestrator import MasterOrchestrator
        return inspect.getsource(MasterOrchestrator)

    @staticmethod
    def _method_source() -> str:
        import inspect
        from orchestrator.master_orchestrator import MasterOrchestrator
        return inspect.getsource(MasterOrchestrator._do_eod_intraday_squareoff)

    def test_t04_scheduled_at_1505_before_1530_close(self):
        src = self._orch_source()
        sq_idx = src.index('at("15:05").do(self._do_eod_intraday_squareoff)')
        close_idx = src.index('at("15:30").do(self._market_close_notify)')
        assert sq_idx < close_idx, "15:05 square-off must be scheduled before 15:30 close notify"

    def test_t05_excludes_carry_positions(self):
        src = self._method_source()
        assert 'getattr(o, "product_type", "INTRADAY") != "CNC"' in src

    def test_t06_noop_in_paper_mode(self):
        src = self._method_source()
        assert "PAPER_TRADING" in src
        assert re.search(r"if getattr\(_cfg_sq, \"PAPER_TRADING\", False\):\s*\n\s*return", src)

    def test_t07_closes_with_correct_reason(self):
        src = self._method_source()
        assert 'reason="EOD_INTRADAY_SQUAREOFF"' in src
        assert "close_position(" in src

    def test_t08_respects_holiday_guard(self):
        src = self._method_source()
        assert "is_nse_holiday" in src
