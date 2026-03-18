"""
Unit tests for Adaptive Entry Timing (AET) — Phase 4.

Tests:
  1. IMMEDIATE mode → order placed immediately, aet_mode=="IMMEDIATE"
  2. PULLBACK mode (BULL regime) → zone price shifted deeper (BUY cheaper)
  3. PULLBACK mode SELL → zone price shifted higher
  4. CONFIRMATION mode (VIX >= 18) → no order from execute(), slot in _aet_pending
  5. CONFIRMATION mode (distortion) → slot deferred
  6. attempt_aet_confirmations: VIX drops → order placed
  7. attempt_aet_confirmations: max_wait exceeded → slot abandoned, returns []
  8. attempt_aet_confirmations: regime changed → slot invalidated, returns []

Run with:  python -m pytest tests/test_aet.py -v
"""
import sys
import os
import types
import importlib
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# Minimal stubs so order_manager can be imported without the full stack
# ──────────────────────────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

def _stub_module(name, **attrs):
    """Create and register a minimal stub module."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod

# Stubs for heavy dependencies
class _FakeEnum:
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"

_stub_module("config",
    PAPER_TRADING=True, MAX_POSITION_SIZE=100_000,
    RISK_PER_TRADE_PCT=1.0, INITIAL_CAPITAL=1_000_000,
    TOTAL_CAPITAL=1_000_000,
    ACTIVE_BROKER="dhan",
    ZERODHA_API_KEY="", ZERODHA_ACCESS_TOKEN="",
    DHAN_CLIENT_ID="", DHAN_ACCESS_TOKEN="",
    ANGELONE_API_KEY="", ANGELONE_CLIENT_ID="",
    ANGELONE_PASSWORD="", ANGELONE_TOTP_SECRET="",
    LOG_DIR=os.path.join(ROOT, "data", "logs"),
    LOG_LEVEL="DEBUG",
)

# Broker stub
_broker_mod = _stub_module("execution_engine.brokers")
_dhan_mod   = _stub_module("execution_engine.brokers.dhan_broker",
                            DhanBroker=MagicMock)
_broker_mod.dhan_broker = _dhan_mod

_stub_module("data_feeds",
    get_feed_manager=MagicMock(return_value=MagicMock()))

_stub_module("communication.event_bus", EventBus=MagicMock)
_stub_module("communication.events")
_stub_module("communication.events",
    EventType=type("EventType", (), {"ORDER_PLACED": "ORDER_PLACED",
                                     "ORDER_REJECTED": "ORDER_REJECTED"})())

from execution_engine.order_manager import (
    OrderManager,
    AdaptiveTimingMode,
    AetPendingSlot,
    OrderRecord,
    AET_VIX_CONFIRM_THRESHOLD,
    AET_PULLBACK_DIP_PCT,
    AET_MAX_WAIT_CANDLES,
    ZONE_BASE_PCT,
    ZONE_VIX_NORMAL,
)
from models.trade_signal import TradeSignal, SignalDirection
from models.agent_output import DecisionResult


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_signal(direction=SignalDirection.BUY, price=1000.0):
    sig = MagicMock(spec=TradeSignal)
    sig.symbol        = "NIFTY"
    sig.direction     = direction
    sig.entry_price   = price
    sig.stop_loss     = price * 0.99
    sig.target_price  = price * 1.02
    sig.strategy_name = "test_strat"
    return sig

def _make_decision(confidence=7.0):
    dec = MagicMock(spec=DecisionResult)
    dec.confidence_score = confidence
    dec.position_size    = 5
    return dec

def _make_om():
    with patch("execution_engine.order_manager.csv"):
        om = OrderManager()
    om._broker_place      = MagicMock(return_value="ORD001")
    om._place_stop_loss   = MagicMock(return_value="SL001")
    om._journal_write            = MagicMock()
    om._journal_write_reentry    = MagicMock()
    om._journal_write_aet_confirmed = MagicMock()
    om._journal_cancel           = MagicMock()
    return om


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestDetermineAetMode(unittest.TestCase):
    def setUp(self):\
            self.om = _make_om()

    def test_immediate_mode(self):
        m = self.om._determine_aet_mode(vix=12.0, regime="RANGING")
        self.assertEqual(m, AdaptiveTimingMode.IMMEDIATE)

    def test_pullback_mode_bull(self):
        for regime in ("BULL", "BULLISH", "TREND", "BULL_MARKET"):
            with self.subTest(regime=regime):
                m = self.om._determine_aet_mode(vix=10.0, regime=regime)
                self.assertEqual(m, AdaptiveTimingMode.PULLBACK)

    def test_confirmation_high_vix(self):
        m = self.om._determine_aet_mode(vix=AET_VIX_CONFIRM_THRESHOLD, regime="BULL")
        self.assertEqual(m, AdaptiveTimingMode.CONFIRMATION)

    def test_confirmation_distortion(self):
        m = self.om._determine_aet_mode(vix=10.0, regime="BULL", distortion_active=True)
        self.assertEqual(m, AdaptiveTimingMode.CONFIRMATION)


class TestApplyAetPrice(unittest.TestCase):
    def setUp(self):
        self.om = _make_om()

    def test_immediate_unchanged(self):
        p = self.om._apply_aet_price(1000.0, "BUY", AdaptiveTimingMode.IMMEDIATE)
        self.assertAlmostEqual(p, 1000.0)

    def test_pullback_buy_cheaper(self):
        p = self.om._apply_aet_price(1000.0, "BUY", AdaptiveTimingMode.PULLBACK)
        expected = round(1000.0 * (1.0 - AET_PULLBACK_DIP_PCT / 100.0), 2)
        self.assertAlmostEqual(p, expected)
        self.assertLess(p, 1000.0)

    def test_pullback_sell_higher(self):
        p = self.om._apply_aet_price(1000.0, "SELL", AdaptiveTimingMode.PULLBACK)
        expected = round(1000.0 * (1.0 + AET_PULLBACK_DIP_PCT / 100.0), 2)
        self.assertAlmostEqual(p, expected)
        self.assertGreater(p, 1000.0)

    def test_confirmation_passthrough(self):
        p = self.om._apply_aet_price(555.0, "BUY", AdaptiveTimingMode.CONFIRMATION)
        self.assertAlmostEqual(p, 555.0)


class TestExecuteAetIntegration(unittest.TestCase):
    def setUp(self):
        self.om = _make_om()

    def _ctx(self, vix=10.0, regime="RANGING", distortion=False):
        return {"vix": vix, "regime": regime, "distortion": distortion}

    # Test 1 — IMMEDIATE mode places order immediately
    def test_immediate_places_order(self):
        sig = _make_signal(SignalDirection.BUY)
        dec = _make_decision()
        rec = self.om.execute(sig, dec, signal_context=self._ctx(vix=10.0, regime="RANGING"))
        self.assertIsNotNone(rec)
        self.assertEqual(rec.aet_mode, AdaptiveTimingMode.IMMEDIATE.value)
        self.om._broker_place.assert_called()

    # Test 2 — PULLBACK mode: BUY limit cheaper than zone
    def test_pullback_buy_price_deeper(self):
        sig = _make_signal(SignalDirection.BUY, price=2000.0)
        dec = _make_decision()
        rec = self.om.execute(sig, dec, signal_context=self._ctx(vix=10.0, regime="BULL"))
        self.assertIsNotNone(rec)
        self.assertEqual(rec.aet_mode, AdaptiveTimingMode.PULLBACK.value)
        # zone_price (which IS the limit) should be < zone without pullback
        base_zone = self.om._calc_entry_zone_price(2000.0, "BUY", 10.0)
        pullback_zone = round(base_zone * (1.0 - AET_PULLBACK_DIP_PCT / 100.0), 2)
        self.assertAlmostEqual(rec.zone_price, pullback_zone, places=2)

    # Test 3 — CONFIRMATION (VIX high): returns None, slot registered
    def test_confirmation_vix_defers(self):
        sig = _make_signal(SignalDirection.BUY)
        dec = _make_decision()
        result = self.om.execute(sig, dec, signal_context=self._ctx(vix=AET_VIX_CONFIRM_THRESHOLD + 1))
        self.assertIsNone(result)
        self.assertEqual(len(self.om._aet_pending), 1)
        slot = next(iter(self.om._aet_pending.values()))
        self.assertEqual(slot.signal_vix, AET_VIX_CONFIRM_THRESHOLD + 1)

    # Test 4 — CONFIRMATION (distortion): returns None, slot registered
    def test_confirmation_distortion_defers(self):
        sig = _make_signal(SignalDirection.BUY)
        dec = _make_decision()
        result = self.om.execute(sig, dec, signal_context=self._ctx(vix=10.0, distortion=True))
        self.assertIsNone(result)
        self.assertEqual(len(self.om._aet_pending), 1)


class TestAttemptAetConfirmations(unittest.TestCase):
    def setUp(self):
        self.om = _make_om()

    def _add_slot(self, vix=25.0, regime="RANGING", candles_waited=0):
        sig = _make_signal()
        dec = _make_decision()
        slot_id = f"AET_TEST_{int(datetime.now().timestamp())}"
        self.om._aet_pending[slot_id] = AetPendingSlot(
            slot_id       = slot_id,
            signal        = sig,
            decision      = dec,
            qty           = 5,
            zone_price    = self.om._calc_entry_zone_price(1000.0, "BUY", vix),
            signal_regime = regime,
            signal_vix    = vix,
            created_at    = datetime.now(),
            candles_waited= candles_waited,
            max_wait      = AET_MAX_WAIT_CANDLES,
        )
        return slot_id

    # Test 5 — VIX drops: confirmation clears, order placed
    def test_confirmation_clears_places_order(self):
        self._add_slot(vix=25.0, regime="RANGING")
        records = self.om.attempt_aet_confirmations(
            current_vix=10.0, current_regime="RANGING", distortion_active=False)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].aet_mode, AdaptiveTimingMode.CONFIRMATION.value)
        self.assertEqual(len(self.om._aet_pending), 0)

    # Test 6 — max_wait exceeded: slot abandoned
    def test_max_wait_expires_slot(self):
        self._add_slot(vix=25.0, candles_waited=AET_MAX_WAIT_CANDLES)
        records = self.om.attempt_aet_confirmations(
            current_vix=10.0, current_regime="RANGING", distortion_active=False)
        self.assertEqual(records, [])
        self.assertEqual(len(self.om._aet_pending), 0)

    # Test 7 — regime changed: slot invalidated
    def test_regime_change_invalidates_slot(self):
        self._add_slot(vix=25.0, regime="BULL")
        records = self.om.attempt_aet_confirmations(
            current_vix=10.0, current_regime="BEAR", distortion_active=False)
        self.assertEqual(records, [])
        self.assertEqual(len(self.om._aet_pending), 0)

    # Test 8 — high VIX still active: slot kept, no order
    def test_high_vix_keeps_slot(self):
        self._add_slot(vix=25.0)
        records = self.om.attempt_aet_confirmations(
            current_vix=AET_VIX_CONFIRM_THRESHOLD + 1, current_regime="RANGING",
            distortion_active=False)
        self.assertEqual(records, [])
        self.assertEqual(len(self.om._aet_pending), 1)
        # candles_waited must have incremented
        slot = next(iter(self.om._aet_pending.values()))
        self.assertEqual(slot.candles_waited, 1)


if __name__ == "__main__":
    unittest.main()
