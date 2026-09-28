"""
tests/test_dta_cnc_holdings_phantom_001.py
=============================================
DTA-CNC-HOLDINGS-PHANTOM-001 — settled CNC (delivery) holdings must never
be treated as a "phantom" (already-flattened) position.

ROOT CAUSE (found live 2026-09-28, via the user's own broker Portfolio.csv
export): _broker_confirms_no_open_position() only ever checked
get_positions() -- Dhan's INTRADAY/unsettled book. A CNC BUY that has gone
through normal T+1 settlement moves OUT of Positions and INTO Holdings, even
though the broker still genuinely holds the shares. Confirmed live: 6 real,
currently-held CNC positions (SBIN, GAIL, TATACONSUM, IOC, SETFGOLD,
TATAGOLD -- ~Rs 24,265 combined) were silently wiped from internal tracking
by this exact gap -- some mislabeled CANCELLED (via reconcile_startup_fills/
reconcile_pending_orders, GAIL/IOC on 2026-09-25) and some mislabeled CLOSED
via close_position()'s own PhantomExitGuard (SBIN/TATACONSUM/TATAGOLD/
SETFGOLD on 2026-09-28) -- while the shares themselves sat completely
unmanaged (no further stop-loss/target monitoring) at the broker.

FIX: _broker_confirms_no_open_position() now ALSO checks get_portfolio()
(settled Holdings) and only concludes "no position" when the symbol is
absent/zero-qty in BOTH the Positions and Holdings books.

T01  Positions absent + Holdings shows a real qty -> NOT phantom (False)
     -- reproduces the exact live SBIN bug scenario.
T02  Positions absent + Holdings absent too -> genuinely phantom (True)
T03  Holdings check raises/unreachable (no get_portfolio attr) -> fails
     safe (False), never guesses a position away.
T04  Holdings response has bad status -> fails safe (False).
T05  Holdings shows the symbol with totalQty=0 -> correctly still phantom
     (True) -- a fully sold-down holding row can legitimately have zero qty.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from execution_engine.order_manager import OrderManager

_SEC_MAP = {"SBIN": {"security_id": "3045", "segment": "NSE_EQ"}}

_POSITIONS_ABSENT = {"status": "success", "remarks": "", "data": []}


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


class TestSettledHoldingsNeverTreatedAsPhantom:

    def test_t01_settled_cnc_holding_is_not_phantom(self):
        """Reproduces the exact live bug: get_positions() says absent
        (already settled out of the intraday book) but get_portfolio()
        shows the real, currently-held SBIN shares -- must return False."""
        broker = MagicMock()
        broker.get_positions.return_value = _POSITIONS_ABSENT
        broker.get_portfolio.return_value = {
            "status": "success", "remarks": "",
            "data": [{"securityId": "3045", "tradingSymbol": "SBIN", "totalQty": 5}],
        }
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            result = om._broker_confirms_no_open_position("SBIN")
        assert result is False

    def test_t02_absent_from_both_books_is_genuinely_phantom(self):
        broker = MagicMock()
        broker.get_positions.return_value = _POSITIONS_ABSENT
        broker.get_portfolio.return_value = {"status": "success", "remarks": "", "data": []}
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            result = om._broker_confirms_no_open_position("SBIN")
        assert result is True

    def test_t03_broker_missing_get_portfolio_fails_safe(self):
        broker = MagicMock(spec=["get_positions"])
        broker.get_positions.return_value = _POSITIONS_ABSENT
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            result = om._broker_confirms_no_open_position("SBIN")
        assert result is False

    def test_t04_holdings_bad_status_fails_safe(self):
        broker = MagicMock()
        broker.get_positions.return_value = _POSITIONS_ABSENT
        broker.get_portfolio.return_value = {"status": "failure", "remarks": "err", "data": ""}
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            result = om._broker_confirms_no_open_position("SBIN")
        assert result is False

    def test_t05_holdings_row_present_but_zero_qty_still_phantom(self):
        broker = MagicMock()
        broker.get_positions.return_value = _POSITIONS_ABSENT
        broker.get_portfolio.return_value = {
            "status": "success", "remarks": "",
            "data": [{"securityId": "3045", "tradingSymbol": "SBIN", "totalQty": 0}],
        }
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            result = om._broker_confirms_no_open_position("SBIN")
        assert result is True

    def test_t06_holdings_check_exception_fails_safe(self):
        broker = MagicMock()
        broker.get_positions.return_value = _POSITIONS_ABSENT
        broker.get_portfolio.side_effect = RuntimeError("network error")
        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", _SEC_MAP):
            om = _make_om_live_with_broker(broker)
            result = om._broker_confirms_no_open_position("SBIN")
        assert result is False
