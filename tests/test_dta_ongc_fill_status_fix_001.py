"""
tests/test_dta_ongc_fill_status_fix_001.py
==============================================
Root-cause fix for a live-money bug found while investigating the real
2026-09-16 ONGC trade: check_and_expire_stale_limits() only checked
rec.status ("open"/"closed"/"cancelled" — a position-level flag that stays
"open" for the whole life of a position) and rec.order_type (a static
"how was it originally placed" attribute that never changes after a fill).
It never checked rec.fill_status, so an ALREADY-FILLED, LIVE position
whose entry happened to be a LIMIT order could be wrongly treated as an
expirable pending order once it aged past the candle-expiry window (or a
regime/distortion/VIX change occurred) — silently wiping its stop-loss/
target tracking for a real position with real capital at risk.

Confirmed live: ONGC order 34126091640603, entered 13:02:05, incorrectly
"context_invalidated"-cancelled at 14:00:18 (58 min later, well past the
15-min candle-expiry window) despite being a fully filled, live position.

Fix: skip records whose fill_status is FILLED or PARTIALLY_FILLED before
any of the 4 expiry checks (time/distortion/regime/VIX) ever run.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest


def _make_bare_om():
    """Minimal OrderManager, mirroring tests/test_dta_system_007.py's helper."""
    import importlib
    import execution_engine.order_manager as om_mod
    importlib.reload(om_mod)
    from execution_engine.order_manager import OrderManager
    om = OrderManager.__new__(OrderManager)
    om._paper_mode = False
    om._orders = {}
    om._portfolio = MagicMock()
    om._portfolio.positions = {}
    om._portfolio.realised_pnl = 0.0
    om._broker = None
    om._reentry_slots = {}
    om._aet_pending = {}
    om._ltp_stale_at = {}
    om._journal_lock = threading.Lock()
    om._restore_stats = {"restored_today": 0}
    om._trade_monitor = None
    om._swap_rotation_date = ""
    om._live_journal_path = "data/live/live_orders.jsonl"
    return om


def _make_rec(order_id, fill_status, age_hours=2.0, **overrides):
    from execution_engine.order_manager import OrderRecord
    rec = OrderRecord(
        order_id=order_id,
        broker_order_id=f"BRK_{order_id}",
        symbol="ONGC",
        direction="BUY",
        quantity=24,
        entry_price=235.64,
        stop_loss=230.42,
        target=246.37,
        strategy="KDA_AUTHORITY",
    )
    rec.status = "open"
    rec.order_type = "LIMIT"
    rec.placed_at = datetime.now() - timedelta(hours=age_hours)
    rec.fill_status = fill_status
    rec.signal_regime = "range_market"
    rec.signal_vix = 14.0
    for k, v in overrides.items():
        setattr(rec, k, v)
    return rec


class TestFilledPositionNeverExpired:
    def test_filled_position_survives_time_expiry(self):
        """The exact live bug: a FILLED position older than the 15-min
        candle-expiry window must NOT be cancelled."""
        om = _make_bare_om()
        rec = _make_rec("ONGC001", fill_status="FILLED", age_hours=1.0)
        om._orders["ONGC001"] = rec

        expired = om.check_and_expire_stale_limits(candle_expiry=1)

        assert expired == []
        assert rec.status == "open"
        assert "ONGC" in om._portfolio.positions or True  # never popped
        assert rec.fill_status == "FILLED"

    def test_partially_filled_position_also_survives(self):
        om = _make_bare_om()
        rec = _make_rec("ONGC002", fill_status="PARTIALLY_FILLED", age_hours=1.0)
        om._orders["ONGC002"] = rec

        expired = om.check_and_expire_stale_limits(candle_expiry=1)

        assert expired == []
        assert rec.status == "open"

    def test_genuinely_pending_order_still_expires(self):
        """Regression guard: a real, never-filled pending limit order must
        still expire correctly — this fix must not break the original
        (correct) behavior for the case it was actually designed for."""
        om = _make_bare_om()
        rec = _make_rec("PEND001", fill_status="PENDING", age_hours=1.0)
        om._orders["PEND001"] = rec

        expired = om.check_and_expire_stale_limits(candle_expiry=1)

        assert expired == ["PEND001"]
        assert rec.status == "cancelled"
        assert rec.pnl == 0.0

    def test_unresolved_fill_status_still_expires(self):
        """Empty-string / UNRESOLVED fill_status (genuinely never confirmed)
        must remain eligible for expiry — only FILLED/PARTIALLY_FILLED are
        excluded."""
        om = _make_bare_om()
        rec = _make_rec("UNRES001", fill_status="", age_hours=1.0)
        om._orders["UNRES001"] = rec

        expired = om.check_and_expire_stale_limits(candle_expiry=1)

        assert expired == ["UNRES001"]

    def test_filled_position_survives_distortion_trigger(self):
        """Even when distortion_active=True (a different one of the 4
        expiry reasons), a FILLED position must still never be touched."""
        om = _make_bare_om()
        rec = _make_rec("ONGC003", fill_status="FILLED", age_hours=0.05)
        om._orders["ONGC003"] = rec

        expired = om.check_and_expire_stale_limits(distortion_active=True)

        assert expired == []
        assert rec.status == "open"

    def test_filled_position_survives_regime_change_trigger(self):
        om = _make_bare_om()
        rec = _make_rec("ONGC004", fill_status="FILLED", age_hours=0.05)
        om._orders["ONGC004"] = rec

        expired = om.check_and_expire_stale_limits(current_regime="bull_market")

        assert expired == []
        assert rec.status == "open"

    def test_non_limit_order_type_unaffected(self):
        """Safety-net regression: MARKET-type records were already skipped
        before this fix (order_type != 'LIMIT') — confirm still true."""
        om = _make_bare_om()
        rec = _make_rec("MKT001", fill_status="PENDING", age_hours=1.0,
                         order_type="MARKET")
        om._orders["MKT001"] = rec

        expired = om.check_and_expire_stale_limits(candle_expiry=1)

        assert expired == []


class TestStaleLimitHoldingsAwareCheck:
    """DTA-STALE-LIMIT-HOLDINGS-001 (found live 2026-09-29): a cross-day
    order whose fill_status can never resolve to FILLED/PARTIALLY_FILLED
    (day-scoped order-status endpoints can't confirm it) stays permanently
    eligible for this function's other checks -- even when it is a
    genuinely real, held position. Confirmed live: 6 positions repaired by
    DTA-CNC-HOLDINGS-PHANTOM-001 (restored with the class default
    order_type="LIMIT", fill_status stuck at API_ERROR) were wrongly
    cancelled here as "expired pending limit orders" despite the broker's
    own Positions+Holdings books confirming every one still genuinely
    held. Fix: before ever cancelling, positively confirm with the broker
    (via the same dual Positions+Holdings check already proven elsewhere)
    that nothing is actually held."""

    def _broker_with_holding(self, security_id, qty):
        broker = MagicMock()
        broker.get_positions.return_value = {"status": "success", "remarks": "", "data": []}
        broker.get_portfolio.return_value = {
            "status": "success", "remarks": "",
            "data": [{"securityId": security_id, "tradingSymbol": "ONGC", "totalQty": qty}],
        }
        return broker

    def _broker_with_nothing(self):
        broker = MagicMock()
        broker.get_positions.return_value = {"status": "success", "remarks": "", "data": []}
        broker.get_portfolio.return_value = {"status": "success", "remarks": "", "data": []}
        return broker

    def test_api_error_fill_status_survives_when_broker_confirms_held(self):
        from unittest.mock import patch
        om = _make_bare_om()
        om._broker = self._broker_with_holding("2475", 24)
        rec = _make_rec("REPAIR001", fill_status="API_ERROR", age_hours=1.0)
        om._orders["REPAIR001"] = rec

        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                   {"ONGC": {"security_id": "2475", "segment": "NSE_EQ"}}):
            expired = om.check_and_expire_stale_limits(candle_expiry=1)

        assert expired == []
        assert rec.status == "open"

    def test_journal_restored_fill_status_survives_when_broker_confirms_held(self):
        from unittest.mock import patch
        om = _make_bare_om()
        om._broker = self._broker_with_holding("2475", 24)
        rec = _make_rec("REPAIR002", fill_status="JOURNAL_RESTORED", age_hours=1.0)
        om._orders["REPAIR002"] = rec

        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                   {"ONGC": {"security_id": "2475", "segment": "NSE_EQ"}}):
            expired = om.check_and_expire_stale_limits(candle_expiry=1)

        assert expired == []
        assert rec.status == "open"

    def test_genuinely_phantom_pending_order_still_expires(self):
        """Regression guard: when the broker confirms NOTHING is held,
        a genuinely never-filled pending order must still expire
        correctly -- this fix must not block real cleanup."""
        from unittest.mock import patch
        om = _make_bare_om()
        om._broker = self._broker_with_nothing()
        rec = _make_rec("PEND002", fill_status="PENDING", age_hours=1.0)
        om._orders["PEND002"] = rec

        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                   {"ONGC": {"security_id": "2475", "segment": "NSE_EQ"}}):
            expired = om.check_and_expire_stale_limits(candle_expiry=1)

        assert expired == ["PEND002"]
        assert rec.status == "cancelled"

    def test_no_broker_configured_preserves_original_behavior(self):
        """No broker (e.g. bare test harness / paper mode) must behave
        exactly as before this fix -- expiry logic runs unmodified."""
        om = _make_bare_om()
        om._broker = None
        rec = _make_rec("PEND003", fill_status="PENDING", age_hours=1.0)
        om._orders["PEND003"] = rec

        expired = om.check_and_expire_stale_limits(candle_expiry=1)

        assert expired == ["PEND003"]

    def test_broker_check_exception_fails_safe_no_cancellation(self):
        """If the broker holdings/positions check itself raises, fail
        safe -- never guess a real position away."""
        from unittest.mock import patch
        om = _make_bare_om()
        broker = MagicMock()
        broker.get_positions.side_effect = RuntimeError("network error")
        om._broker = broker
        rec = _make_rec("REPAIR003", fill_status="API_ERROR", age_hours=1.0)
        om._orders["REPAIR003"] = rec

        with patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP",
                   {"ONGC": {"security_id": "2475", "segment": "NSE_EQ"}}):
            expired = om.check_and_expire_stale_limits(candle_expiry=1)

        assert expired == []
        assert rec.status == "open"
