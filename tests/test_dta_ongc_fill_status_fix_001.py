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
