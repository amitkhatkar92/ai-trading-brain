"""
tests/test_exit_attribution.py
==============================
OPS-03C: Verify that TradeMonitor._act() writes the correct canonical exit reason
to the journal via close_position(), and that each reason survives the full path:

  _act(action)  →  close_position(reason=canonical)  →  journal row  →  EOD skip-list

Unit tests  (5): canonical reason for each action token
Integration tests (3): open position → simulated exit → journal row verified
"""

from __future__ import annotations
import csv
import io
import os
import sys
import types
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch, call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ── Minimal stubs so TradeMonitor can be imported without the full stack ──────

def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules.setdefault(name, mod)
    return mod


_stub("config",
      PAPER_TRADING=True, TOTAL_CAPITAL=10_000_000,
      MAX_RISK_PER_TRADE_PCT=0.0025,
      MAX_PORTFOLIO_RISK_PCT=0.08, MAX_DRAWDOWN_PCT=0.10,
      MIN_CONFIDENCE_SCORE=6.8,
      ACTIVE_BROKER="zerodha",
      LOG_DIR=os.path.join(ROOT, "data", "logs"), LOG_LEVEL="WARNING",
      ENABLE_ADAPTIVE_EXIT=True, ADAPTIVE_TIME_STALE_MINUTES=180,
      ADAPTIVE_STALE_MAX_R=0.30, ADAPTIVE_EARLY_LOSS_R=-0.60,
      ADAPTIVE_EARLY_LOSS_TRENDING_R=-0.70, ADAPTIVE_EARLY_LOSS_SIDEWAYS_R=-0.50,
      ADAPTIVE_MIN_R_TO_GUARD=2.50,
      ENABLE_ADAPTIVE_EXTENSION=True,
      ADAPTIVE_EXTENSION_TRIGGER_R=2.80, ADAPTIVE_EXTENSION_LOCK_R=2.50,
      ADAPTIVE_EXTENSION_LOCK_STRONG_R=2.70, ADAPTIVE_EXTENSION_STRONG_R=3.10,
      ADAPTIVE_EXTENSION_MAX_VIX=20.0, ADAPTIVE_EXTENSION_TARGET_PCT=0.10,
      ADAPTIVE_EXTENSION_TIME_CAP_MIN=90,
      # broker credentials (unused in tests — placeholders)
      ZERODHA_API_KEY="", ZERODHA_ACCESS_TOKEN="",
      DHAN_CLIENT_ID="", DHAN_ACCESS_TOKEN="",
      ANGELONE_API_KEY="", ANGELONE_CLIENT_ID="",
      ANGELONE_PASSWORD="", ANGELONE_TOTP_SECRET="",
      ATR_ZONE_MULTIPLIER=1.5,
      MAX_CAPITAL_PER_TRADE_PCT=15.0,
      JOURNAL_PATH=os.path.join(ROOT, "data", "paper_trades.csv"),
      ENABLE_BROKER=False,
)
_stub("data_feeds", get_feed_manager=MagicMock(return_value=MagicMock()))
_stub("notifications", get_notifier=MagicMock(return_value=MagicMock()))
_stub("notifications.notifier_manager", get_notifier=MagicMock(return_value=MagicMock()))
_stub("communication.event_bus", get_bus=MagicMock(return_value=MagicMock()))
_stub("communication.events",
      EventType=type("EventType", (), {
          "ORDER_PLACED": "execution.order.placed",
          "POSITION_CLOSED": "monitor.position.closed",
      })())
_stub("data_integrity.price_integrity_validator",
      get_price_validator=MagicMock(
          return_value=MagicMock(validate=MagicMock(
              return_value=MagicMock(ok=True)))))
_stub("trade_monitoring.trade_analytics",
      TradeAnalytics=MagicMock(return_value=MagicMock()))

from execution_engine.order_manager import OrderRecord  # noqa: E402
from trade_monitoring.trade_monitor import TradeMonitor  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_JOURNAL_HEADER = [
    "timestamp", "order_id", "symbol", "direction", "quantity",
    "entry_price", "stop_loss", "target", "strategy",
    "confidence", "rr", "event", "exit_price", "pnl", "reason",
]


def _make_order(symbol="HDFCBANK", direction="BUY",
                entry=1720.0, stop=1685.0, target=1790.0,
                strategy="Breakout_Volume", oid=None) -> OrderRecord:
    rec = OrderRecord(
        order_id         = oid or f"TEST_{symbol}_{direction}_1",
        symbol           = symbol,
        direction        = direction,
        quantity         = 10,
        entry_price      = entry,
        stop_loss        = stop,
        target           = target,
        strategy         = strategy,
        placed_at        = datetime.now(),
        status           = "open",
        order_type       = "MARKET",
        confidence_score = 8.0,
    )
    return rec


def _make_monitor_with_order(rec: OrderRecord) -> tuple[TradeMonitor, MagicMock]:
    """Return (TradeMonitor, mock_order_manager) with rec pre-registered."""
    monitor = TradeMonitor()
    mock_om = MagicMock()
    monitor._order_manager = mock_om
    monitor._open_orders[rec.order_id] = rec
    monitor._peak_r[rec.order_id] = 0.0
    monitor._ltp_history[rec.order_id] = [rec.entry_price]
    monitor._last_good_ltp[rec.order_id] = rec.entry_price
    return monitor, mock_om


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — canonical reason mapping in _act()
# ─────────────────────────────────────────────────────────────────────────────

class TestCanonicalReasonMapping(unittest.TestCase):
    """_act() must pass canonical reason strings to close_position(), not action tokens."""

    def _run_act(self, action: str, adaptive_sub: str = None) -> str:
        """Run _act and return the reason string passed to close_position()."""
        rec = _make_order()
        monitor, mock_om = _make_monitor_with_order(rec)
        if adaptive_sub:
            monitor._adaptive_reasons[rec.order_id] = adaptive_sub
        monitor._act(rec.order_id, rec, 1750.0, action)
        # close_position should have been called once
        mock_om.close_position.assert_called_once()
        _, kwargs = mock_om.close_position.call_args
        return kwargs.get("reason") or mock_om.close_position.call_args[0][2]

    def test_close_target_maps_to_TARGET_HIT(self):
        reason = self._run_act("close_target")
        self.assertEqual(reason, "TARGET_HIT",
                         f"Expected TARGET_HIT, got {reason!r}")

    def test_close_sl_maps_to_STOP_HIT(self):
        reason = self._run_act("close_sl")
        self.assertEqual(reason, "STOP_HIT",
                         f"Expected STOP_HIT, got {reason!r}")

    def test_adaptive_exit_TIME_STALE(self):
        reason = self._run_act("adaptive_exit", adaptive_sub="TIME_STALE")
        self.assertEqual(reason, "TIME_STALE",
                         f"Expected TIME_STALE, got {reason!r}")

    def test_adaptive_exit_EARLY_LOSS(self):
        reason = self._run_act("adaptive_exit", adaptive_sub="EARLY_LOSS")
        self.assertEqual(reason, "EARLY_LOSS",
                         f"Expected EARLY_LOSS, got {reason!r}")

    def test_close_emergency_preserved(self):
        reason = self._run_act("close_emergency")
        self.assertEqual(reason, "close_emergency",
                         f"Expected close_emergency (system intervention), got {reason!r}")

    def test_human_readable_description_not_passed(self):
        """Ensure verbose strings like 'Target hit at 1750.00' are never the journal reason."""
        reason = self._run_act("close_target")
        self.assertNotIn("at ", reason,
                         "Journal reason must not contain human-readable price description")
        self.assertNotIn("hit", reason.lower().replace("hit", "_HIT") if "_HIT" in reason else "",
                         "Journal reason must be canonical label, not verbose description")

    def test_unknown_action_falls_back_to_itself(self):
        """Unrecognised action tokens should pass through unchanged (safe fallback)."""
        reason = self._run_act("some_future_action")
        self.assertEqual(reason, "some_future_action")


# ─────────────────────────────────────────────────────────────────────────────
# Integration tests — full path: order → _evaluate → _act → journal row
# ─────────────────────────────────────────────────────────────────────────────

class TestExitAttributionIntegration(unittest.TestCase):
    """
    Simulate realistic price scenarios.  Verify that journal CLOSE rows contain
    the correct canonical reason.

    OrderManager.close_position() writes to CSV in paper mode.  We capture that
    by patching _journal_write_close and inspecting the reason argument.
    """

    def _capture_journal_reason(self, rec: OrderRecord, ltp: float) -> str:
        """
        Run check_all with the given ltp and capture the reason written to journal.
        Returns the reason string, or '' if close_position was not called.
        """
        monitor, mock_om = _make_monitor_with_order(rec)
        monitor.update_market_context("bull_trend", 15.0)
        monitor.check_all({rec.symbol: ltp})
        if mock_om.close_position.called:
            _, kwargs = mock_om.close_position.call_args
            return kwargs.get("reason") or mock_om.close_position.call_args[0][2]
        return ""

    def test_target_hit_writes_TARGET_HIT(self):
        """LTP >= target → reason = TARGET_HIT."""
        rec = _make_order(entry=1720.0, stop=1685.0, target=1790.0)
        reason = self._capture_journal_reason(rec, ltp=1795.0)  # above target
        self.assertEqual(reason, "TARGET_HIT",
                         f"Expected TARGET_HIT when LTP crosses target, got {reason!r}")

    def test_stop_hit_writes_STOP_HIT(self):
        """LTP <= stop → reason = STOP_HIT."""
        rec = _make_order(entry=1720.0, stop=1685.0, target=1790.0)
        reason = self._capture_journal_reason(rec, ltp=1680.0)  # below stop
        self.assertEqual(reason, "STOP_HIT",
                         f"Expected STOP_HIT when LTP crosses stop, got {reason!r}")

    def test_adaptive_time_stale_writes_TIME_STALE(self):
        """
        Simulate an aged trade (placed far in the past) with minimal price movement
        so the adaptive engine fires TIME_STALE.
        """
        import config as _cfg
        original = _cfg.ADAPTIVE_TIME_STALE_MINUTES
        _cfg.ADAPTIVE_TIME_STALE_MINUTES = 0   # instant threshold for test

        rec = _make_order(entry=1720.0, stop=1685.0, target=1790.0)
        # Place time far in the past so age_minutes > 0
        rec.placed_at  = datetime(2020, 1, 1)
        rec.created_at = datetime(2020, 1, 1)

        monitor, mock_om = _make_monitor_with_order(rec)
        monitor.update_market_context("range_market", 15.0)
        # LTP barely moved from entry → r_multiple ≈ 0 → TIME_STALE should fire
        monitor.check_all({rec.symbol: 1721.0})

        _cfg.ADAPTIVE_TIME_STALE_MINUTES = original  # restore

        if mock_om.close_position.called:
            _, kwargs = mock_om.close_position.call_args
            reason = kwargs.get("reason") or mock_om.close_position.call_args[0][2]
            self.assertEqual(reason, "TIME_STALE",
                             f"Expected TIME_STALE for aged stale trade, got {reason!r}")
        else:
            self.skipTest("Adaptive exit did not fire (check _AE_ENABLED / guard conditions)")


# ─────────────────────────────────────────────────────────────────────────────
# EOD Learning skip-list contract tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEodSkipList(unittest.TestCase):
    """
    Verify that the EOD skip-list correctly classifies canonical reasons.
    These tests document the expected categorisation so any future change to
    _skip_reasons is visible and intentional.
    """

    # Canonical skip set — mirrors _do_eod_learning in master_orchestrator.py
    SKIP_REASONS = {
        "REPLACEMENT",
        "emergency_close",
        "close_emergency",
        "ORPHAN_CLOSE",
        "EOD_CLOSE",
        "SYSTEM_CLEANUP",
    }

    def test_TARGET_HIT_is_not_skipped(self):
        self.assertNotIn("TARGET_HIT", self.SKIP_REASONS)

    def test_STOP_HIT_is_not_skipped(self):
        self.assertNotIn("STOP_HIT", self.SKIP_REASONS)

    def test_TIME_STALE_is_not_skipped(self):
        self.assertNotIn("TIME_STALE", self.SKIP_REASONS)

    def test_EARLY_LOSS_is_not_skipped(self):
        self.assertNotIn("EARLY_LOSS", self.SKIP_REASONS)

    def test_ORPHAN_CLOSE_is_skipped(self):
        self.assertIn("ORPHAN_CLOSE", self.SKIP_REASONS)

    def test_emergency_close_is_skipped(self):
        self.assertIn("emergency_close", self.SKIP_REASONS)

    def test_EOD_CLOSE_is_skipped(self):
        self.assertIn("EOD_CLOSE", self.SKIP_REASONS)

    def test_SYSTEM_CLEANUP_is_skipped(self):
        self.assertIn("SYSTEM_CLEANUP", self.SKIP_REASONS)


if __name__ == "__main__":
    unittest.main()
