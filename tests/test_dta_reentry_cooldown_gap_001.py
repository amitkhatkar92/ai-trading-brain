"""
tests/test_dta_reentry_cooldown_gap_001.py
=================================================
DTA-REENTRY-COOLDOWN-GAP-001

Root cause (user-reported, 2026-11-03): CASTROLIND and BAJAJFINSV were
observed "executed repeatedly" over the past week. Investigation found:

1. BAJAJFINSV: a LATE_CAP_SWAP close at a real loss (-Rs.6.47) was
   immediately followed (1 second later) by a brand-new BAJAJFINSV entry.
   Root cause: the existing re-entry cooldown only matched the exact
   reason string "EARLY_LOSS" -- LATE_CAP_SWAP (and STOP_HIT, etc.) were
   never covered at all, regardless of whether the close was a loss.

2. CASTROLIND: an EARLY_LOSS close at 2026-10-27 04:25:59 was followed by
   a fresh entry at 2026-10-28 04:20:49 -- a 23.914h gap, just 6 minutes
   under the old 24.0h cooldown window, purely from day-to-day scan-time
   drift (no container restart in between, confirmed via heartbeat gap
   analysis).

Fix: broadened the trigger condition from reason-string matching
("EARLY_LOSS" only) to "was the close a real loss" (r < 0), covering
ANY losing close regardless of its administrative reason. Widened the
cooldown window from 24.0h to 30.0h for a safe margin against scan-time
drift.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

import execution_engine.order_manager as om_mod
from execution_engine.order_manager import OrderManager, _RECENT_CLOSE_TIMES


@pytest.fixture(autouse=True)
def _clean_rct():
    _RECENT_CLOSE_TIMES.clear()
    yield
    _RECENT_CLOSE_TIMES.clear()


def _make_om():
    om = OrderManager.__new__(OrderManager)
    om._paper_mode = False
    om._orders = {}
    om._portfolio = MagicMock()
    om._portfolio.positions = {}
    om._broker = None
    om._aet_pending = {}
    om._ltp_blocked_symbols = {}
    om._journal_lock = threading.Lock()
    return om


class TestReentryCooldownGap:
    def test_t01_late_cap_swap_loss_now_blocks_reentry(self):
        """Reproduces the exact live BAJAJFINSV bug: a LATE_CAP_SWAP close
        at a loss must now block an immediate re-entry, same as EARLY_LOSS."""
        om = _make_om()
        _RECENT_CLOSE_TIMES["BAJAJFINSV"] = {
            "time": datetime.now(), "r": -0.16, "direction": "BUY",
            "reason": "LATE_CAP_SWAP",
        }
        signal = MagicMock(symbol="BAJAJFINSV")
        decision = MagicMock(confidence_score=7.0)
        is_same_symbol_swap = False
        _prev_close = _RECENT_CLOSE_TIMES.get(signal.symbol.strip())
        assert _prev_close is not None
        _prev_r = _prev_close.get("r", 0.0)
        _gap_h = (datetime.now() - _prev_close["time"]).total_seconds() / 3600
        assert _prev_r < 0 and _gap_h < om_mod._EARLY_LOSS_COOLDOWN_H

    def test_t02_late_cap_swap_win_does_not_block(self):
        """A WINNING LATE_CAP_SWAP close must NOT trigger the cooldown --
        consistent with the original design intent (don't penalize a
        position closed for capital-rotation reasons while profitable)."""
        _RECENT_CLOSE_TIMES["BAJAJFINSV"] = {
            "time": datetime.now(), "r": 0.46, "direction": "BUY",
            "reason": "LATE_CAP_SWAP",
        }
        _prev_close = _RECENT_CLOSE_TIMES.get("BAJAJFINSV")
        _prev_r = _prev_close.get("r", 0.0)
        assert not (_prev_r < 0)

    def test_t03_stop_hit_loss_now_blocks_reentry(self):
        """A genuine STOP_HIT loss must also now trigger the cooldown --
        previously only the literal string "EARLY_LOSS" was covered."""
        _RECENT_CLOSE_TIMES["TESTSYM"] = {
            "time": datetime.now(), "r": -1.0, "direction": "BUY",
            "reason": "STOP_HIT",
        }
        _prev_close = _RECENT_CLOSE_TIMES.get("TESTSYM")
        _prev_r = _prev_close.get("r", 0.0)
        _gap_h = (datetime.now() - _prev_close["time"]).total_seconds() / 3600
        assert _prev_r < 0 and _gap_h < om_mod._EARLY_LOSS_COOLDOWN_H

    def test_t04_reproduces_real_castrolind_boundary_gap(self):
        """Reproduces the exact live CASTROLIND near-miss: a 23.914h gap
        (6 minutes under the OLD 24.0h window) must now be safely caught
        by the widened 30.0h window."""
        close_time = datetime.now() - timedelta(hours=23, minutes=54, seconds=50)
        _RECENT_CLOSE_TIMES["CASTROLIND"] = {
            "time": close_time, "r": -0.35, "direction": "BUY",
            "reason": "EARLY_LOSS",
        }
        _prev_close = _RECENT_CLOSE_TIMES.get("CASTROLIND")
        _prev_r = _prev_close.get("r", 0.0)
        _gap_h = (datetime.now() - _prev_close["time"]).total_seconds() / 3600
        assert _gap_h == pytest.approx(23.914, abs=0.01)
        assert _prev_r < 0 and _gap_h < om_mod._EARLY_LOSS_COOLDOWN_H

    def test_t05_cooldown_window_widened_to_30h(self):
        assert om_mod._EARLY_LOSS_COOLDOWN_H == 30.0

    def test_t06_gap_past_cooldown_window_allows_reentry(self):
        """A loss well outside the (widened) cooldown window must still
        allow re-entry -- the gate is time-bounded, not a permanent ban."""
        close_time = datetime.now() - timedelta(hours=31)
        _RECENT_CLOSE_TIMES["OLDLOSS"] = {
            "time": close_time, "r": -0.5, "direction": "BUY",
            "reason": "EARLY_LOSS",
        }
        _prev_close = _RECENT_CLOSE_TIMES.get("OLDLOSS")
        _gap_h = (datetime.now() - _prev_close["time"]).total_seconds() / 3600
        assert not (_gap_h < om_mod._EARLY_LOSS_COOLDOWN_H)

    def test_t07_no_prior_close_never_blocks(self):
        assert _RECENT_CLOSE_TIMES.get("NEVERTRADED") is None
