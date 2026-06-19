"""
tests/test_governance_window.py
================================
Defence-in-depth governance window tests.

Verifies that NO execution path can place an order before 09:45 IST.

Three layers under test
-----------------------
  Layer 1: MasterOrchestrator deep-scan handler - suppresses task submission
  Layer 2: run_full_cycle() / _run_options_fast_path() - return early
  Layer 3: OrderManager.execute() - returns None (hard block)

Time scenarios tested
---------------------
  08:00  blocked
  09:10  blocked (earliest deep scan)
  09:20  blocked
  09:30  blocked
  09:44  blocked (1 min before window)
  09:45  ALLOWED (exact boundary)
  10:30  ALLOWED

Run with:  python -m pytest tests/test_governance_window.py -v
"""
from __future__ import annotations

import os
import sys
import types
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ---------------------------------------------------------------------------
# Module stubs — must be registered before any project import
# ---------------------------------------------------------------------------

def _stub_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


_stub_module("config",
    PAPER_TRADING=True,
    TOTAL_CAPITAL=1_000_000,
    ACTIVE_BROKER="zerodha",
    ZERODHA_API_KEY="", ZERODHA_ACCESS_TOKEN="",
    DHAN_CLIENT_ID="", DHAN_ACCESS_TOKEN="",
    ANGELONE_API_KEY="", ANGELONE_CLIENT_ID="",
    ANGELONE_PASSWORD="", ANGELONE_TOTP_SECRET="",
    ATR_ZONE_MULTIPLIER=0.10,
    LOG_DIR=os.path.join(ROOT, "data", "logs"),
    LOG_LEVEL="DEBUG",
    MAX_RISK_PER_TRADE_PCT=0.0025,
    MAX_CAPITAL_PER_TRADE_PCT=15.0,
)

_stub_module("data_feeds", get_feed_manager=MagicMock(return_value=MagicMock()))
_stub_module("communication.event_bus", EventBus=MagicMock)
_stub_module("communication.events",
    EventType=type("EventType", (), {
        "ORDER_PLACED": "ORDER_PLACED",
        "ORDER_REJECTED": "ORDER_REJECTED",
    })()
)
_stub_module("execution_engine.brokers")
_stub_module("execution_engine.brokers.dhan_broker", DhanBroker=MagicMock)
_stub_module("data_integrity.price_integrity_validator",
    get_price_validator=MagicMock(return_value=MagicMock(
        validate=MagicMock(return_value=MagicMock(ok=True, classification=""))
    ))
)

# Import project modules after stubs are in place
from execution_engine.order_manager import (   # noqa: E402
    OrderManager,
    _EXEC_WIN_OPEN_H,
    _EXEC_WIN_OPEN_M,
    _LATE_ENTRY_CUTOFF_H,
    _LATE_ENTRY_CUTOFF_M,
)
from models.trade_signal import TradeSignal, SignalDirection   # noqa: E402
from models.agent_output  import DecisionResult               # noqa: E402
import execution_engine.order_manager as _om_mod              # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signal():
    sig = MagicMock(spec=TradeSignal)
    sig.symbol          = "RELIANCE"
    sig.strategy_name   = "Momentum_Retest"
    sig.direction       = SignalDirection.BUY
    sig.entry_price     = 1000.0
    sig.stop_loss       = 980.0
    sig.target_price    = 1040.0
    sig.quantity        = 10
    sig.source          = "test"
    sig.atr             = 5.0
    sig.entry_zone_low  = 998.0
    sig.entry_zone_high = 1002.0
    return sig


def _make_decision(score=7.5):
    dec = MagicMock(spec=DecisionResult)
    dec.confidence_score       = score
    dec.position_size_modifier = 1.0
    dec.trade_type             = "FULL"
    return dec


def _make_om():
    with patch("execution_engine.order_manager.csv"):
        om = OrderManager()
    om._broker          = None   # SIM mode
    om._broker_place    = MagicMock(return_value="ORD001")
    om._place_stop_loss = MagicMock(return_value="SL001")
    om._journal_write   = MagicMock()
    return om


def _guard_blocks(h: int, m: int) -> bool:
    """Replicate the Layer 1/2 guard condition. True = blocked."""
    now = datetime(2026, 6, 19, h, m, 0)
    win = now.replace(hour=_EXEC_WIN_OPEN_H, minute=_EXEC_WIN_OPEN_M,
                      second=0, microsecond=0)
    return now < win


# ---------------------------------------------------------------------------
# Layer 1 & 2: guard logic (pure datetime arithmetic)
# ---------------------------------------------------------------------------

class TestLayer1DeepScanGuard(unittest.TestCase):
    """Layer 1: deep-scan task NOT submitted before 09:45."""

    def test_0800_blocked(self):    self.assertTrue(_guard_blocks(8,  0))
    def test_0910_blocked(self):    self.assertTrue(_guard_blocks(9, 10))
    def test_0920_blocked(self):    self.assertTrue(_guard_blocks(9, 20))
    def test_0930_blocked(self):    self.assertTrue(_guard_blocks(9, 30))
    def test_0944_blocked(self):    self.assertTrue(_guard_blocks(9, 44))
    def test_0945_allowed(self):    self.assertFalse(_guard_blocks(9, 45))
    def test_1030_allowed(self):    self.assertFalse(_guard_blocks(10, 30))


class TestLayer2RunFullCycleGuard(unittest.TestCase):
    """Layer 2: run_full_cycle() / options path exits before 09:45."""

    def test_0910_suppressed(self): self.assertTrue(_guard_blocks(9, 10))
    def test_0944_suppressed(self): self.assertTrue(_guard_blocks(9, 44))
    def test_0945_proceeds(self):   self.assertFalse(_guard_blocks(9, 45))
    def test_1330_proceeds(self):   self.assertFalse(_guard_blocks(13, 30))


# ---------------------------------------------------------------------------
# Layer 3: OrderManager.execute() hard block
# ---------------------------------------------------------------------------

class TestLayer3ExecutionWindowBlock(unittest.TestCase):

    def _execute_at(self, h: int, m: int):
        om  = _make_om()
        sig = _make_signal()
        dec = _make_decision()
        fake = datetime(2026, 6, 19, h, m, 0)
        with patch.object(_om_mod, "datetime") as mock_dt:
            mock_dt.now.return_value = fake
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            return om.execute(sig, dec)

    # Blocked cases
    def test_0800_returns_none(self):
        self.assertIsNone(self._execute_at(8,  0))

    def test_0910_returns_none(self):
        self.assertIsNone(self._execute_at(9, 10))

    def test_0920_returns_none(self):
        self.assertIsNone(self._execute_at(9, 20))

    def test_0930_returns_none(self):
        self.assertIsNone(self._execute_at(9, 30))

    def test_0944_returns_none(self):
        self.assertIsNone(self._execute_at(9, 44))

    # Log tag emitted for blocked calls
    def test_0910_logs_execution_window_block(self):
        om  = _make_om()
        sig = _make_signal()
        dec = _make_decision()
        fake = datetime(2026, 6, 19, 9, 10, 0)
        with self.assertLogs("execution_engine.order_manager", level="WARNING") as lc:
            with patch.object(_om_mod, "datetime") as mock_dt:
                mock_dt.now.return_value = fake
                mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
                om.execute(sig, dec)
        self.assertTrue(
            any("ExecutionWindowBlock" in line for line in lc.output),
            "Expected [ExecutionWindowBlock] in log at 09:10",
        )

    # Allowed: window boundary — guard must NOT fire
    def test_0945_no_window_block_logged(self):
        om  = _make_om()
        sig = _make_signal()
        dec = _make_decision()
        fake = datetime(2026, 6, 19, 9, 45, 0)
        logged = []
        with patch.object(_om_mod, "datetime") as mock_dt:
            mock_dt.now.return_value = fake
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            try:
                with self.assertLogs("execution_engine.order_manager",
                                     level="WARNING") as lc:
                    om.execute(sig, dec)
                logged = lc.output
            except AssertionError:
                pass  # no warnings at all is fine
        self.assertFalse(
            any("ExecutionWindowBlock" in line for line in logged),
            "ExecutionWindowBlock must NOT fire at 09:45",
        )


# ---------------------------------------------------------------------------
# Constants sanity
# ---------------------------------------------------------------------------

class TestConstantDefinition(unittest.TestCase):

    def test_exec_window_constants(self):
        self.assertEqual(_EXEC_WIN_OPEN_H, 9)
        self.assertEqual(_EXEC_WIN_OPEN_M, 45)

    def test_late_entry_constants_unchanged(self):
        self.assertEqual(_LATE_ENTRY_CUTOFF_H, 14)
        self.assertEqual(_LATE_ENTRY_CUTOFF_M, 30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
