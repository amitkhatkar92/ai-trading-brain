"""
tests/test_dta_gap_continuation_001.py
========================================
DTA-GAP-CONTINUATION-001

Addresses the user's "Case 1" (gap-up/gap-down stocks) using real,
already-fetched feed data (TickerQuote.open / .close) instead of touching
the Protected ExecutionWindowBlock (execution_engine/order_manager.py).

A new "Setup 0: Gap Continuation" in EquityScannerAI._identify_setup()
fires ONLY when a real, large, volume-confirmed gap is STILL HOLDING by
the time the (already-scheduled) scan runs -- evidence-aligned with
EMP-001's own 60-day finding that the opening-window context is what makes
a gap predictive, not the raw gap tick alone. Dormant (falls through to the
existing setups, byte-identical behavior) whenever gap_pct is absent or
below threshold -- which is the overwhelming majority of symbols/days.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from models.trade_signal import SignalDirection
from opportunity_engine.equity_scanner_ai import (
    EquityScannerAI,
    GAP_CONTINUATION_MIN_PCT,
    GAP_CONTINUATION_MIN_VOLUME,
    RR_GAP_CONTINUATION,
)
from strategy_lab.strategy_generator_ai import STRATEGY_PARAMS


def _snapshot(regime=RegimeLabel.RANGE_MARKET) -> MarketSnapshot:
    return MarketSnapshot(timestamp=datetime.now(), indices={}, regime=regime,
                           volatility=VolatilityLevel.MEDIUM)


def _stock(gap_pct=None, gap_day_open=None, ltp=510.0, volume_ratio=1.0, **overrides):
    base = {
        "symbol": "TESTSTOCK",
        "ltp": ltp,
        "resistance": 520.0,    # tight, realistic range -> ATR% stays under the guard
        "support": 480.0,
        "rsi": 55.0,            # neutral -- falls to "rsi_neutral" if Setup 0 skipped
        "volume_ratio": volume_ratio,
        "adv_crore": 50.0,
        "price_is_live": True,
        "gap_pct": gap_pct,
        "gap_day_open": gap_day_open,
    }
    base.update(overrides)
    return base


@pytest.fixture()
def scanner() -> EquityScannerAI:
    return EquityScannerAI()


def test_t01_no_gap_data_falls_through_unchanged(scanner):
    """No gap_pct (the common case) -> Setup 0 never fires; existing
    rsi_neutral knowledge_referred fallback behavior is unaffected."""
    stock = _stock(gap_pct=None, gap_day_open=None)
    sig, reason = scanner._identify_setup(stock, _snapshot())
    assert reason == "knowledge_referred"
    assert sig.strategy_name == "knowledge_referred"


def test_t02_gap_up_held_and_volume_confirmed_fires(scanner):
    """Real 3% gap up, held above open, volume confirmed -> Gap_Continuation BUY."""
    day_open = 500.0
    ltp = 510.0  # held comfortably above open
    stock = _stock(gap_pct=3.0, gap_day_open=day_open, ltp=ltp,
                    volume_ratio=GAP_CONTINUATION_MIN_VOLUME + 0.5)
    sig, reason = scanner._identify_setup(stock, _snapshot())
    assert reason == "signal_found"
    assert sig.strategy_name == "Gap_Continuation"
    assert sig.direction == SignalDirection.BUY
    assert sig.gap_pct == 3.0
    assert sig.stop_loss < ltp
    assert sig.target_price > ltp
    assert sig.risk_reward_ratio >= RR_GAP_CONTINUATION - 0.01


def test_t03_gap_down_held_and_volume_confirmed_fires_short(scanner):
    """Real 3% gap down, held below open, volume confirmed -> Gap_Continuation SHORT."""
    day_open = 500.0
    ltp = 490.0  # held comfortably below open
    stock = _stock(gap_pct=-3.0, gap_day_open=day_open, ltp=ltp,
                    volume_ratio=GAP_CONTINUATION_MIN_VOLUME + 0.5)
    sig, reason = scanner._identify_setup(stock, _snapshot())
    assert reason == "signal_found"
    assert sig.strategy_name == "Gap_Continuation"
    assert sig.direction == SignalDirection.SHORT
    assert sig.gap_pct == -3.0
    assert sig.stop_loss > ltp
    assert sig.target_price < ltp


def test_t04_gap_up_but_filled_back_through_open_does_not_fire(scanner):
    """Gap present but price has fallen back through the open -- not a genuine
    continuation -- falls through to the existing setup chain instead."""
    stock = _stock(gap_pct=3.0, gap_day_open=500.0, ltp=495.0,  # below day_open
                    volume_ratio=GAP_CONTINUATION_MIN_VOLUME + 0.5)
    sig, reason = scanner._identify_setup(stock, _snapshot())
    assert sig.strategy_name != "Gap_Continuation"


def test_t05_gap_below_threshold_does_not_fire(scanner):
    stock = _stock(gap_pct=GAP_CONTINUATION_MIN_PCT - 0.5, gap_day_open=500.0,
                    ltp=510.0, volume_ratio=GAP_CONTINUATION_MIN_VOLUME + 0.5)
    sig, reason = scanner._identify_setup(stock, _snapshot())
    assert sig.strategy_name != "Gap_Continuation"


def test_t06_volume_not_confirmed_does_not_fire(scanner):
    stock = _stock(gap_pct=3.0, gap_day_open=500.0, ltp=510.0,
                    volume_ratio=GAP_CONTINUATION_MIN_VOLUME - 0.5)
    sig, reason = scanner._identify_setup(stock, _snapshot())
    assert sig.strategy_name != "Gap_Continuation"


def test_t07_bear_market_guard_still_fires_first(scanner):
    """Existing hard safety gate (bear market) must still pre-empt Setup 0."""
    stock = _stock(gap_pct=5.0, gap_day_open=500.0, ltp=520.0,
                    volume_ratio=GAP_CONTINUATION_MIN_VOLUME + 1.0)
    sig, reason = scanner._identify_setup(stock, _snapshot(regime=RegimeLabel.BEAR_MARKET))
    assert sig is None
    assert reason == "bear_market"


def test_t08_registered_in_strategy_params_so_identity_is_preserved():
    """Without this registration, StrategyGeneratorAI._assign() would silently
    relabel the signal via auto-assign (same bug class as the historical
    Bear_Put_Spread missing-entry issue)."""
    assert "Gap_Continuation" in STRATEGY_PARAMS
    assert STRATEGY_PARAMS["Gap_Continuation"]["min_rr"] <= RR_GAP_CONTINUATION


def test_t09_execution_window_guard_untouched():
    """Regression guard: this change must never touch the Protected
    ExecutionWindowBlock in order_manager.py."""
    om_path = ROOT / "execution_engine" / "order_manager.py"
    src = om_path.read_text(encoding="utf-8")
    assert "_EXEC_WIN_OPEN_H, _EXEC_WIN_OPEN_M = 9, 45" in src
    assert "Gap_Continuation" not in src


def test_t10_do_fetch_prices_populates_gap_cache():
    """_do_fetch_prices() extracts open/close from the already-returned
    TickerQuote and computes gap_pct -- no new network call."""
    import opportunity_engine.equity_scanner_ai as esa

    fake_quote = MagicMock()
    fake_quote.ltp = 103.0
    fake_quote.open = 103.0
    fake_quote.close = 100.0
    fake_quote.feed_source = "DHAN"

    fake_feed = MagicMock()
    fake_feed.get_multiple_quotes.return_value = {"TESTSTOCK.NS": fake_quote}

    with patch("data_feeds.data_feed_manager.get_feed_manager", return_value=fake_feed):
        prices = esa._do_fetch_prices(["TESTSTOCK"])

    assert prices.get("TESTSTOCK") == 103.0
    gap_pct, day_open = esa._GAP_CACHE.get("TESTSTOCK", (None, None))
    assert gap_pct == pytest.approx(3.0)
    assert day_open == 103.0


def test_t11_no_open_close_data_leaves_gap_cache_entry_absent():
    """Fail-open: a quote missing open/close never fabricates a gap."""
    import opportunity_engine.equity_scanner_ai as esa
    esa._GAP_CACHE = {}

    fake_quote = MagicMock()
    fake_quote.ltp = 103.0
    fake_quote.open = 0.0
    fake_quote.close = 0.0
    fake_quote.feed_source = "DHAN"

    fake_feed = MagicMock()
    fake_feed.get_multiple_quotes.return_value = {"TESTSTOCK.NS": fake_quote}

    with patch("data_feeds.data_feed_manager.get_feed_manager", return_value=fake_feed):
        esa._do_fetch_prices(["TESTSTOCK"])

    assert "TESTSTOCK" not in esa._GAP_CACHE
