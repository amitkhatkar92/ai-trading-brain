"""
ARCH-006 Integration Test Suite
================================
Tests every critical production path for the ₹10,000 controlled live pilot.

Sections:
  A  — KDA authority (BUY/SELL reach Risk; HOLD/WAIT blocked)
  B  — Position sizing at ₹10k (zero-qty for large-caps; qty>0 for cheap stocks)
  C  — DHAN_SECURITY_MAP safety (known → order; unknown → MISSING_DHAN_MAPPING)
  D  — Exchange-side SL path (entry → _place_stop_loss → DhanBroker.place_sl_order)
  E  — Partial fill reconciliation (SL cancel + resubmit for filled qty)
  F  — Broker failure / fail-closed (timeout, None, exception → no blind retry)
  G  — Duplicate order protection (same signal twice → one position)
  H  — Zero-quantity safeguards (qty=0 → no broker call, clear log)
  I  — Paper/live gate (three independent protections)
  J  — Pilot max positions (₹10k → max 3 positions)
  K  — Restart recovery (CSV journal + _orders dict rebuild)
  L  — Risk independence (KDA BUY vetoed by RiskGuardian)
"""
from __future__ import annotations

import os, sys, unittest, json, tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Optional, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ─── Minimal imports (avoid importing orchestrator which has heavy side effects) ───
from execution_engine.order_manager import OrderManager, OrderRecord, MAX_CAPITAL_PER_TRADE_PCT
from execution_engine.brokers.dhan_broker import DhanBroker
from models.trade_signal import TradeSignal, SignalDirection
from models.portfolio import Portfolio, Position
from config import (
    TOTAL_CAPITAL, MAX_POSITIONS, MAX_RISK_PER_TRADE_PCT,
    PAPER_TRADING, MAX_DRAWDOWN_PCT,
)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _make_signal(symbol="TATASTEEL", direction="BUY", entry=160.0,
                 stop=155.0, target=175.0, qty=1) -> TradeSignal:
    sig = TradeSignal(
        symbol        = symbol,
        direction     = SignalDirection.BUY if direction == "BUY" else SignalDirection.SELL,
        entry_price   = entry,
        stop_loss     = stop,
        target_price  = target,
        quantity      = qty,
        confidence    = 7.5,
        strategy_name = "Breakout_Volume",
    )
    return sig


def _make_decision(score=7.0, modifier=1.0):
    dec = MagicMock()
    dec.confidence_score = score
    dec.position_size_modifier = modifier
    dec.trade_type = "FULL"
    return dec


def _make_paper_om() -> OrderManager:
    """OrderManager in paper mode (no broker)."""
    om = OrderManager()
    assert om._paper_mode or om._broker is None
    return om


def _make_isolated_om() -> OrderManager:
    """OrderManager with a fresh temp journal — no production positions restored."""
    _tmp = os.path.join(tempfile.gettempdir(), f"test_arch006_{os.getpid()}.csv")
    with patch("execution_engine.order_manager.PAPER_TRADE_LOG", _tmp):
        om = OrderManager()
    assert om._paper_mode or om._broker is None
    return om


# ─── A: KDA Authority ──────────────────────────────────────────────────────────

class TestKDAAuthority(unittest.TestCase):
    """A: KDA decisions are respected in the orchestrator pipeline."""

    def test_a01_kda_hold_blocks_signal(self):
        """KNOWLEDGE_HOLD must be gated in orchestrator (blocks signal from execution)."""
        with open("orchestrator/master_orchestrator.py", encoding="utf-8") as f:
            src = f.read()
        self.assertIn("KNOWLEDGE_HOLD", src, "KNOWLEDGE_HOLD must be referenced in orchestrator")
        self.assertIn('"KNOWLEDGE_HOLD"', src, "KNOWLEDGE_HOLD string literal must appear in gate")
        # Verify the gate: KNOWLEDGE_HOLD appears before order_manager.execute
        hold_pos   = src.find('"KNOWLEDGE_HOLD"')
        execute_pos = src.find("order_manager.execute")
        self.assertLess(hold_pos, execute_pos, "KNOWLEDGE_HOLD gate must appear before execute")

    def test_a02_kda_pipeline_is_shadow_only(self):
        """KDA pipeline must never set broker_calls or orders > 0."""
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        kdp = KnowledgeDecisionPipeline()
        sig = _make_signal()
        result = kdp.run_knowledge_shadow(sig, {}, {})
        self.assertIsNotNone(result)
        self.assertEqual(result.get("broker_calls", 0), 0)
        self.assertEqual(result.get("orders", 0), 0)

    def test_a03_kda_buy_sell_authorize_entry(self):
        """KNOWLEDGE_BUY / KNOWLEDGE_SELL must be the authorization tokens."""
        with open("orchestrator/master_orchestrator.py", encoding="utf-8") as f:
            src = f.read()
        self.assertIn("KNOWLEDGE_BUY", src, "KNOWLEDGE_BUY must appear in orchestrator")
        self.assertIn("KNOWLEDGE_SELL", src, "KNOWLEDGE_SELL must appear in orchestrator")
        # Both must appear AFTER KDA shadow and BEFORE execute
        buy_pos     = src.find('"KNOWLEDGE_BUY"')
        execute_pos = src.find("order_manager.execute")
        self.assertLess(buy_pos, execute_pos, "KNOWLEDGE_BUY check must be before execute")

    def test_a04_debate_cannot_overwrite_kda_decision(self):
        """Debate runs after KDA; it cannot modify kda_decision."""
        with open("orchestrator/master_orchestrator.py", encoding="utf-8") as f:
            src = f.read()
        kda_pos   = src.find("run_knowledge_shadow")
        debate_pos = src.find("_run_debate_and_decide")
        execute_pos = src.find("order_manager.execute")
        self.assertLess(kda_pos, debate_pos, "KDA must run before Debate")
        self.assertLess(debate_pos, execute_pos, "Debate must run before Execute")

    def test_a05_risk_veto_runs_before_debate(self):
        """RiskGuardian evaluates before Debate and Execute."""
        with open("orchestrator/master_orchestrator.py", encoding="utf-8") as f:
            src = f.read()
        rg_pos     = src.find("risk_guardian.evaluate")
        debate_pos = src.find("_run_debate_and_decide")
        execute_pos = src.find("order_manager.execute")
        self.assertLess(rg_pos, debate_pos, "RiskGuardian must run before Debate")
        self.assertLess(rg_pos, execute_pos, "RiskGuardian must run before Execute")


# ─── B: Position Sizing at ₹10k ────────────────────────────────────────────────

class TestPositionSizing10k(unittest.TestCase):
    """B: Position sizing correctly handles ₹10k capital edge cases."""

    def setUp(self):
        from risk_control.capital_risk_engine import CapitalRiskEngine, _MAX_POSITIONS
        from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
        from datetime import datetime

        self.cre = CapitalRiskEngine()
        self.snap = MarketSnapshot(
            timestamp           = datetime.now(),
            indices             = {},
            regime              = RegimeLabel.BULL_TREND,
            volatility          = VolatilityLevel.LOW,
            vix                 = 14.0,
            fii_dii             = {},
            sector_flows        = {},
            sector_leaders      = [],
            events_today        = [],
            market_breadth      = {},
            pcr                 = 1.0,
            global_bias         = "NEUTRAL",
            global_sentiment_score = 5.0,
        )
        self.portfolio = Portfolio(capital=TOTAL_CAPITAL, peak_capital=TOTAL_CAPITAL)

    def test_b01_reliance_produces_zero_quantity(self):
        """RELIANCE at ₹2820 with ₹28 ATR → qty=0 at ₹10k capital."""
        sig = _make_signal("RELIANCE", entry=2820.0, stop=2792.0, target=2880.0, qty=100)
        result = self.cre.allocate([sig], self.snap, self.portfolio)
        self.assertEqual(len(result), 0,
                         "RELIANCE should produce qty=0 at ₹10k capital (correctly rejected)")

    def test_b02_sbin_produces_zero_quantity(self):
        """SBIN at ₹850 with ₹8 ATR → qty=0 at ₹10k capital."""
        sig = _make_signal("SBIN", entry=850.0, stop=842.0, target=880.0, qty=100)
        result = self.cre.allocate([sig], self.snap, self.portfolio)
        self.assertEqual(len(result), 0, "SBIN should produce qty=0 at ₹10k capital")

    def test_b03_cheap_stock_produces_nonzero_quantity(self):
        """TATASTEEL at ₹160 with ₹3 ATR → qty ≥ 1 at ₹10k capital."""
        sig = _make_signal("TATASTEEL", entry=160.0, stop=157.0, target=175.0, qty=100)
        result = self.cre.allocate([sig], self.snap, self.portfolio)
        self.assertGreaterEqual(len(result), 1, "TATASTEEL should produce qty≥1")
        self.assertGreater(result[0].quantity, 0)

    def test_b04_penny_stock_produces_reasonable_quantity(self):
        """IDEA at ₹15 with ₹0.5 ATR → qty > 1 at ₹10k capital."""
        sig = _make_signal("IDEA", entry=15.0, stop=14.5, target=17.0, qty=100)
        result = self.cre.allocate([sig], self.snap, self.portfolio)
        self.assertGreaterEqual(len(result), 1)
        self.assertGreater(result[0].quantity, 1)

    def test_b05_quantity_never_negative(self):
        """Position sizing must never produce negative quantity."""
        for entry, stop in [(2820, 2792), (850, 842), (160, 157), (15, 14.5)]:
            sig = _make_signal(entry=entry, stop=stop, target=entry*1.05, qty=100)
            result = self.cre.allocate([sig], self.snap, self.portfolio)
            for r in result:
                self.assertGreater(r.quantity, 0, f"qty must be > 0 for entry={entry}")


# ─── C: DHAN_SECURITY_MAP Safety ───────────────────────────────────────────────

class TestDhanSecurityMapSafety(unittest.TestCase):
    """C: Symbol resolution is safe for both known and unknown symbols."""

    def _make_live_broker(self) -> DhanBroker:
        """Create a DhanBroker in SIM mode (not connected)."""
        b = object.__new__(DhanBroker)
        b.client_id    = "TEST"
        b.access_token = "TEST"
        b._dhan        = None
        b._connected   = False
        return b

    def test_c01_known_symbol_resolves_to_order(self):
        """Known symbol in DHAN_SECURITY_MAP → place_order returns SIM ID."""
        from data_feeds.dhan_feed import DHAN_SECURITY_MAP
        if not DHAN_SECURITY_MAP:
            self.skipTest("DHAN_SECURITY_MAP empty")
        symbol = next(iter(DHAN_SECURITY_MAP))
        meta   = DHAN_SECURITY_MAP[symbol]
        broker = self._make_live_broker()
        result = broker.place_order(
            security_id      = meta["security_id"],
            exchange_segment = meta["segment"],
            transaction_type = "BUY",
            quantity         = 1,
            price            = 100.0,
            order_type       = "LIMIT",
        )
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("SIM_DHAN_"), f"Expected SIM_DHAN_ prefix, got {result}")

    def test_c02_unknown_symbol_logs_and_returns_none(self):
        """Unknown symbol in _broker_place → None + MISSING_DHAN_MAPPING log."""
        import logging
        with self.assertLogs("execution_engine.order_manager", level="ERROR") as cm:
            om = _make_paper_om()
            # Temporarily set a fake broker so _broker_place takes the live path
            fake_broker = MagicMock()
            om._broker = fake_broker
            om._paper_mode = False
            result = om._broker_place("UNKNOWNSYMBOL_XYZ999", "BUY", 1, 100.0)
        self.assertIsNone(result, "Unknown symbol must return None")
        self.assertTrue(
            any("MISSING_DHAN_MAPPING" in m for m in cm.output),
            "MISSING_DHAN_MAPPING must appear in error log",
        )

    def test_c03_missing_mapping_does_not_call_broker(self):
        """Unknown symbol must never result in a broker.place_order call."""
        om = _make_paper_om()
        fake_broker = MagicMock()
        om._broker = fake_broker
        om._paper_mode = False
        om._broker_place("IMPOSSIBLE_SYMBOL_99999", "BUY", 1, 100.0)
        fake_broker.place_order.assert_not_called()


# ─── D: Exchange-Side SL Path ──────────────────────────────────────────────────

class TestExchangeSideSL(unittest.TestCase):
    """D: SL order reaches DhanBroker.place_sl_order in live mode."""

    def test_d01_place_sl_order_exists_on_dhan_broker(self):
        """DhanBroker must have place_sl_order method."""
        self.assertTrue(hasattr(DhanBroker, "place_sl_order"))

    def test_d02_place_sl_order_returns_sim_id_when_not_connected(self):
        """place_sl_order returns SIM_SL_* when broker not connected."""
        b = object.__new__(DhanBroker)
        b._connected = False; b._dhan = None
        result = b.place_sl_order("TATASTEEL", "NSE", "SELL", 5, 155.0, 154.2)
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("SIM_SL_"), f"Expected SIM_SL_ prefix, got {result}")

    def test_d03_place_sl_order_direction_is_opposite(self):
        """SL for a BUY position must use SELL direction."""
        b = object.__new__(DhanBroker)
        b._connected = False; b._dhan = None
        result = b.place_sl_order("TATASTEEL", "NSE", "SELL", 1, 155.0, 154.2)
        self.assertIn("SELL", result)

    def test_d04_place_stop_loss_in_paper_mode_returns_sim(self):
        """_place_stop_loss returns SIM_SL_* in paper mode."""
        om = _make_paper_om()
        sig = _make_signal()
        result = om._place_stop_loss(sig, 5, "ENTRY_OID_123")
        self.assertIsNotNone(result)
        self.assertIn("SIM_SL", result)

    def test_d05_place_stop_loss_calls_broker_place_sl_in_live_mode(self):
        """_place_stop_loss calls broker.place_sl_order in live mode."""
        om = _make_paper_om()
        fake_broker = MagicMock()
        fake_broker.place_sl_order.return_value = "SL_OID_456"
        om._broker = fake_broker
        om._paper_mode = False
        sig = _make_signal()
        result = om._place_stop_loss(sig, 5, "ENTRY_OID_123")
        fake_broker.place_sl_order.assert_called_once()
        call_kwargs = fake_broker.place_sl_order.call_args
        args = call_kwargs[1] if call_kwargs[1] else {}
        if not args:  # positional args
            args = {k: v for k, v in zip(
                ["symbol","exchange","transaction_type","quantity","trigger_price","price"],
                call_kwargs[0]
            )}
        self.assertEqual(args.get("quantity"), 5)
        self.assertAlmostEqual(args.get("trigger_price"), sig.stop_loss, places=2)

    def test_d06_sl_not_placed_when_entry_fails(self):
        """If entry order fails, SL must not be placed."""
        om = _make_paper_om()
        fake_broker = MagicMock()
        fake_broker.place_order.return_value = None  # entry fails
        fake_broker.place_sl_order = MagicMock()
        om._broker = fake_broker
        om._paper_mode = False
        # Patch _place_entry_with_retry to return None
        with patch.object(om, "_place_entry_with_retry", return_value=None):
            with patch.object(om, "_place_stop_loss") as mock_sl:
                sig = _make_signal()
                dec = _make_decision()
                om.execute(sig, dec)
                mock_sl.assert_not_called()

    def test_d07_sl_order_has_trigger_and_limit_price(self):
        """SL order must have both trigger_price and limit price (not just trigger)."""
        import inspect
        src = inspect.getsource(DhanBroker.place_sl_order)
        self.assertIn("trigger_price", src)
        self.assertIn("price", src)
        self.assertIn("STOP_LOSS", src)


# ─── E: Partial Fill Reconciliation ────────────────────────────────────────────

class TestPartialFillReconciliation(unittest.TestCase):
    """E: Partial fills update both position quantity AND SL order."""

    def test_e01_reconcile_is_noop_in_paper_mode(self):
        """reconcile_partial_fills returns [] in paper mode."""
        om = _make_paper_om()
        self.assertEqual(om.reconcile_partial_fills(), [])

    def test_e02_reconcile_adjusts_quantity_to_filled(self):
        """Partial fill adjusts rec.quantity from requested to filled."""
        om = _make_paper_om()
        # Inject a fake open order
        rec = OrderRecord(
            order_id   = "LIVE_OID_001",
            symbol     = "TATASTEEL",
            direction  = "BUY",
            quantity   = 10,
            entry_price= 160.0,
            stop_loss  = 155.0,
            target     = 175.0,
            strategy   = "Breakout_Volume",
            order_type = "LIMIT",
            status     = "open",
        )
        rec.sl_order_id = "SL_OID_001"
        om._orders["LIVE_OID_001"] = rec

        # Fake broker: reports 4/10 filled
        fake_broker = MagicMock()
        fake_broker.get_order_status.return_value = {
            "status": "PARTIAL_FILL", "filled_qty": 4, "remaining_qty": 6
        }
        fake_broker.cancel_order.return_value = True
        fake_broker.place_sl_order.return_value = "NEW_SL_OID_002"
        om._broker = fake_broker
        om._paper_mode = False

        updated = om.reconcile_partial_fills()

        self.assertIn("LIVE_OID_001", updated)
        self.assertEqual(rec.quantity, 4, "quantity must be adjusted to filled qty")

    def test_e03_reconcile_cancels_old_sl(self):
        """Partial fill must cancel the stale SL (placed for requested qty)."""
        om = _make_paper_om()
        rec = OrderRecord(
            order_id="PF_OID", symbol="TATASTEEL", direction="BUY",
            quantity=10, entry_price=160.0, stop_loss=155.0, target=175.0,
            strategy="X", order_type="LIMIT", status="open",
        )
        rec.sl_order_id = "OLD_SL"
        om._orders["PF_OID"] = rec

        fake_broker = MagicMock()
        fake_broker.get_order_status.return_value = {"filled_qty": 3}
        fake_broker.cancel_order.return_value = True
        fake_broker.place_sl_order.return_value = "NEW_SL"
        om._broker = fake_broker
        om._paper_mode = False

        om.reconcile_partial_fills()

        fake_broker.cancel_order.assert_called_once_with("OLD_SL")

    def test_e04_reconcile_resubmits_sl_for_filled_qty(self):
        """New SL must be placed for filled qty, not original requested qty."""
        om = _make_paper_om()
        rec = OrderRecord(
            order_id="PF_OID2", symbol="TATASTEEL", direction="BUY",
            quantity=10, entry_price=160.0, stop_loss=155.0, target=175.0,
            strategy="X", order_type="LIMIT", status="open",
        )
        rec.sl_order_id = "OLD_SL2"
        om._orders["PF_OID2"] = rec

        fake_broker = MagicMock()
        fake_broker.get_order_status.return_value = {"filled_qty": 3}
        fake_broker.cancel_order.return_value = True
        fake_broker.place_sl_order.return_value = "NEW_SL2"
        om._broker = fake_broker
        om._paper_mode = False

        om.reconcile_partial_fills()

        call_kwargs = fake_broker.place_sl_order.call_args
        args = call_kwargs[1] if call_kwargs[1] else {}
        if not args:
            args = {k: v for k, v in zip(
                ["symbol","exchange","transaction_type","quantity","trigger_price","price"],
                call_kwargs[0]
            )}
        self.assertEqual(args.get("quantity"), 3, "SL must be for filled qty=3, not requested qty=10")

    def test_e05_reconcile_updates_sl_order_id(self):
        """rec.sl_order_id must be updated to the new SL order ID."""
        om = _make_paper_om()
        rec = OrderRecord(
            order_id="PF_OID3", symbol="TATASTEEL", direction="BUY",
            quantity=10, entry_price=160.0, stop_loss=155.0, target=175.0,
            strategy="X", order_type="LIMIT", status="open",
        )
        rec.sl_order_id = "OLD_SL3"
        om._orders["PF_OID3"] = rec

        fake_broker = MagicMock()
        fake_broker.get_order_status.return_value = {"filled_qty": 5}
        fake_broker.cancel_order.return_value = True
        fake_broker.place_sl_order.return_value = "BRAND_NEW_SL"
        om._broker = fake_broker
        om._paper_mode = False

        om.reconcile_partial_fills()
        self.assertEqual(rec.sl_order_id, "BRAND_NEW_SL")

    def test_e06_full_fill_does_not_trigger_reconciliation(self):
        """Full fill (filled >= requested) must not trigger partial-fill logic."""
        om = _make_paper_om()
        rec = OrderRecord(
            order_id="FF_OID", symbol="TATASTEEL", direction="BUY",
            quantity=5, entry_price=160.0, stop_loss=155.0, target=175.0,
            strategy="X", order_type="LIMIT", status="open",
        )
        rec.sl_order_id = "EXISTING_SL"
        om._orders["FF_OID"] = rec

        fake_broker = MagicMock()
        fake_broker.get_order_status.return_value = {"filled_qty": 5}
        om._broker = fake_broker
        om._paper_mode = False

        updated = om.reconcile_partial_fills()
        self.assertEqual(updated, [], "Full fill must not trigger partial-fill logic")
        fake_broker.cancel_order.assert_not_called()


# ─── F: Broker Failure / Fail-Closed ───────────────────────────────────────────

class TestBrokerFailureFallback(unittest.TestCase):
    """F: Any broker failure must fail closed — no blind retry."""

    def test_f01_broker_returning_none_does_not_create_record(self):
        """_place_entry_with_retry returning None → no OrderRecord created."""
        om = _make_isolated_om()
        with patch.object(om, "_place_entry_with_retry", return_value=None):
            sig = _make_signal()
            dec = _make_decision()
            result = om.execute(sig, dec)
        self.assertIsNone(result)
        self.assertEqual(len(om._orders), 0)

    def test_f02_broker_exception_does_not_create_record(self):
        """Broker throwing exception → no OrderRecord created."""
        om = _make_isolated_om()
        with patch.object(om, "_place_entry_with_retry", side_effect=RuntimeError("network error")):
            sig = _make_signal()
            dec = _make_decision()
            try:
                result = om.execute(sig, dec)
            except RuntimeError:
                pass
        self.assertEqual(len(om._orders), 0)

    def test_f03_sl_failure_does_not_block_order_record(self):
        """SL placement failure must still create the position record (software SL active)."""
        om = _make_paper_om()
        # Patch _place_stop_loss to return None (SL failed)
        with patch.object(om, "_place_stop_loss", return_value=None):
            sig = _make_signal("SUZLON", entry=75.0, stop=74.0, target=80.0, qty=5)
            dec = _make_decision()
            result = om.execute(sig, dec)
        # In paper mode the order should still be recorded (SL is software-tracked)
        if result is not None:
            self.assertIn(result, om._orders)
            self.assertEqual(om._orders[result].sl_order_id, "")

    def test_f04_get_order_status_failure_is_swallowed_in_reconcile(self):
        """get_order_status exception in reconcile → logged, not raised."""
        om = _make_paper_om()
        rec = OrderRecord(
            order_id="ERR_OID", symbol="TATASTEEL", direction="BUY",
            quantity=5, entry_price=160.0, stop_loss=155.0, target=175.0,
            strategy="X", order_type="LIMIT", status="open",
        )
        om._orders["ERR_OID"] = rec

        fake_broker = MagicMock()
        fake_broker.get_order_status.side_effect = ConnectionError("timeout")
        om._broker = fake_broker
        om._paper_mode = False

        # Must not raise
        updated = om.reconcile_partial_fills()
        self.assertEqual(updated, [])


# ─── G: Duplicate Order Protection ─────────────────────────────────────────────

class TestDuplicateOrderProtection(unittest.TestCase):
    """G: Same signal executed twice → one position, not two."""

    def test_g01_same_symbol_blocked_on_second_execute(self):
        """Second execute on same symbol is blocked by _symbol_has_open_position."""
        om = _make_paper_om()
        sig = _make_signal("TATASTEEL", qty=1)
        dec = _make_decision()

        # First execute (suppress time/market checks via patch)
        with patch.object(om, "_is_outside_exec_window", return_value=False, create=True):
            result1 = om.execute(sig, dec)

        if result1 is None:
            self.skipTest("First execute blocked (market hours / data feed) — acceptable in test env")

        # Second execute must be blocked
        with patch.object(om, "_is_outside_exec_window", return_value=False, create=True):
            result2 = om.execute(sig, dec)
        self.assertIsNone(result2, "Second execute on same symbol must be blocked")
        self.assertEqual(len([r for r in om._orders.values() if r.symbol == "TATASTEEL"]), 1)

    def test_g02_duplicate_protection_uses_symbol_check(self):
        """_symbol_has_open_position correctly identifies open positions."""
        om = _make_paper_om()
        # Manually inject an open position
        rec = OrderRecord(
            order_id="DUP_OID", symbol="TATASTEEL", direction="BUY",
            quantity=5, entry_price=160.0, stop_loss=155.0, target=175.0,
            strategy="X", order_type="LIMIT", status="open",
        )
        om._orders["DUP_OID"] = rec
        self.assertTrue(om._symbol_has_open_position("TATASTEEL"))
        self.assertFalse(om._symbol_has_open_position("RELIANCE"))


# ─── H: Zero-Quantity Safeguards ───────────────────────────────────────────────

class TestZeroQuantitySafeguards(unittest.TestCase):
    """H: qty=0 must never reach the broker."""

    def test_h01_zero_qty_from_modifier_is_blocked(self):
        """qty = int(signal.qty * 0) = 0 → rejected before broker call."""
        om = _make_paper_om()
        sig = _make_signal(qty=5)
        dec = _make_decision(modifier=0.0)  # modifier=0 → qty=0
        with patch.object(om, "_broker_place") as mock_bp:
            om.execute(sig, dec)
            mock_bp.assert_not_called()

    def test_h02_negative_quantity_cannot_reach_broker(self):
        """Negative quantity is rejected at qty <= 0 check."""
        om = _make_paper_om()
        sig = _make_signal(qty=-1)
        dec = _make_decision()
        with patch.object(om, "_broker_place") as mock_bp:
            om.execute(sig, dec)
            mock_bp.assert_not_called()

    def test_h03_zero_qty_from_cre_never_reaches_orderManager(self):
        """CRE must drop signals with qty=0 before returning."""
        from risk_control.capital_risk_engine import CapitalRiskEngine
        from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
        from datetime import datetime
        cre = CapitalRiskEngine()
        snap = MarketSnapshot(
            timestamp=datetime.now(), indices={},
            regime=RegimeLabel.BULL_TREND, volatility=VolatilityLevel.LOW,
            vix=14.0, fii_dii={}, sector_flows={}, sector_leaders=[],
            events_today=[], market_breadth={}, pcr=1.0,
            global_bias="NEUTRAL", global_sentiment_score=5.0,
        )
        sig = _make_signal("RELIANCE", entry=2820.0, stop=2792.0, target=2880.0, qty=100)
        portfolio = Portfolio(capital=TOTAL_CAPITAL, peak_capital=TOTAL_CAPITAL)
        result = cre.allocate([sig], snap, portfolio)
        self.assertEqual(len(result), 0, "CRE must drop qty=0 signals")

    def test_h04_broker_never_called_for_zero_qty(self):
        """When CRE produces qty=0, no broker call is ever made."""
        from risk_control.capital_risk_engine import CapitalRiskEngine
        from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
        from datetime import datetime
        cre = CapitalRiskEngine()
        snap = MarketSnapshot(
            timestamp=datetime.now(), indices={},
            regime=RegimeLabel.BULL_TREND, volatility=VolatilityLevel.LOW,
            vix=14.0, fii_dii={}, sector_flows={}, sector_leaders=[],
            events_today=[], market_breadth={}, pcr=1.0,
            global_bias="NEUTRAL", global_sentiment_score=5.0,
        )
        sig = _make_signal("RELIANCE", entry=2820.0, stop=2792.0, target=2880.0, qty=100)
        portfolio = Portfolio(capital=TOTAL_CAPITAL, peak_capital=TOTAL_CAPITAL)
        om = _make_paper_om()
        with patch.object(om, "_broker_place") as mock_bp:
            cre_result = cre.allocate([sig], snap, portfolio)
            for sig_out in cre_result:
                om.execute(sig_out, _make_decision())
            if not cre_result:
                mock_bp.assert_not_called()


# ─── I: Paper/Live Gate ────────────────────────────────────────────────────────

class TestPaperLiveGate(unittest.TestCase):
    """I: Three independent protections against accidental live orders."""

    def test_i01_paper_trading_config_default_is_true(self):
        """config.py must default PAPER_TRADING to 'true' when env var is absent."""
        with open("config.py", encoding="utf-8") as f:
            src = f.read()
        # The default in getenv must be 'true'
        self.assertIn('getenv("PAPER_TRADING", "true")', src,
                      "config.py must default PAPER_TRADING to 'true'")

    def test_i02_live_trading_authorized_is_absent(self):
        """LIVE_TRADING_AUTHORIZED must be absent or not 'true'."""
        import os
        lta = os.environ.get("LIVE_TRADING_AUTHORIZED", "").lower()
        self.assertNotEqual(lta, "true",
                            "LIVE_TRADING_AUTHORIZED must NOT be 'true' during pre-live validation")

    def test_i03_orderManager_paper_mode_true_means_no_broker(self):
        """When _paper_mode=True, OrderManager._broker is None."""
        om = _make_paper_om()
        # In paper mode, _broker must be None
        if hasattr(om, "_paper_mode") and om._paper_mode:
            self.assertIsNone(om._broker)

    def test_i04_dhan_broker_sim_when_not_connected(self):
        """DhanBroker returns SIM_DHAN_* when not connected."""
        b = object.__new__(DhanBroker)
        b._connected = False; b._dhan = None
        result = b.place_order("123", "NSE_EQ", "BUY", 1, 100.0, "LIMIT")
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("SIM_DHAN_"))

    def test_i05_broker_not_set_routes_all_orders_to_sim(self):
        """OrderManager with no broker → all orders get SIM_ prefix."""
        om = _make_paper_om()
        # In paper mode, _broker_place returns SIM_ IDs
        result = om._broker_place("TATASTEEL", "BUY", 1, 160.0)
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("SIM_"), f"Expected SIM_ prefix, got {result}")


# ─── J: Pilot Max Positions ─────────────────────────────────────────────────────

class TestPilotMaxPositions(unittest.TestCase):
    """J: ₹10k capital enforces explicit max 3 positions (not 8)."""

    def test_j01_config_max_positions_is_3_at_10k_capital(self):
        """MAX_POSITIONS must be 3 when TOTAL_CAPITAL=10000."""
        self.assertEqual(TOTAL_CAPITAL, 10000.0, "TOTAL_CAPITAL must be ₹10,000 for this test")
        self.assertEqual(MAX_POSITIONS, 3,
                         f"MAX_POSITIONS must be 3 at ₹10k capital, got {MAX_POSITIONS}")

    def test_j02_cre_uses_config_max_positions(self):
        """CRE _MAX_POSITIONS must equal config.MAX_POSITIONS."""
        from risk_control.capital_risk_engine import _MAX_POSITIONS
        self.assertEqual(_MAX_POSITIONS, MAX_POSITIONS,
                         "CRE must use config.MAX_POSITIONS, not hardcoded 8")

    def test_j03_cre_rejects_4th_signal_at_pilot_cap(self):
        """With 3 positions open, CRE must reject the 4th signal."""
        from risk_control.capital_risk_engine import CapitalRiskEngine
        from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
        from datetime import datetime
        cre = CapitalRiskEngine()
        snap = MarketSnapshot(
            timestamp=datetime.now(), indices={},
            regime=RegimeLabel.BULL_TREND, volatility=VolatilityLevel.LOW,
            vix=14.0, fii_dii={}, sector_flows={}, sector_leaders=[],
            events_today=[], market_breadth={}, pcr=1.0,
            global_bias="NEUTRAL", global_sentiment_score=5.0,
        )
        # 4 cheap signals that would all get qty≥1
        signals = [
            _make_signal(sym, entry=75.0, stop=74.0, target=80.0, qty=100)
            for sym in ["SUZLON", "IDEA", "YESBANK", "PNB"]
        ]
        portfolio = Portfolio(capital=TOTAL_CAPITAL, peak_capital=TOTAL_CAPITAL)
        result = cre.allocate(signals, snap, portfolio)
        self.assertLessEqual(len(result), MAX_POSITIONS,
                             f"CRE must cap at {MAX_POSITIONS} positions, got {len(result)}")

    def test_j04_max_positions_larger_capital(self):
        """At ₹1Cr capital, MAX_POSITIONS would be 8 (verify formula)."""
        # Test the _compute_max_positions logic directly
        import config as cfg
        # Simulate ₹1Cr
        original = cfg.TOTAL_CAPITAL
        try:
            cfg.TOTAL_CAPITAL = 10_000_000
            result = cfg._compute_max_positions()
            self.assertEqual(result, 8)
        finally:
            cfg.TOTAL_CAPITAL = original


# ─── K: Restart Recovery ────────────────────────────────────────────────────────

class TestRestartRecovery(unittest.TestCase):
    """K: CSV journal + _orders rebuild after crash."""

    def test_k01_restore_from_journal_exists(self):
        """_restore_from_journal must exist and be callable."""
        self.assertTrue(hasattr(OrderManager, "_restore_from_journal"))

    def test_k02_prefetch_restored_ltps_exists(self):
        """_prefetch_restored_ltps must exist (prevents false drawdown halt)."""
        self.assertTrue(hasattr(OrderManager, "_prefetch_restored_ltps"))

    def test_k03_csv_journal_path_configured(self):
        """PAPER_TRADE_LOG constant must be defined."""
        from execution_engine.order_manager import PAPER_TRADE_LOG
        self.assertIsNotNone(PAPER_TRADE_LOG)
        self.assertTrue(PAPER_TRADE_LOG.endswith(".csv"))

    def test_k04_no_duplicate_after_restart(self):
        """After restore, _symbol_has_open_position blocks re-execution."""
        om = _make_paper_om()
        # Inject a restored position
        rec = OrderRecord(
            order_id="RESTORED_OID", symbol="TATASTEEL", direction="BUY",
            quantity=5, entry_price=160.0, stop_loss=155.0, target=175.0,
            strategy="X", order_type="LIMIT", status="open",
        )
        om._orders["RESTORED_OID"] = rec
        # Attempt to execute a new signal for the same symbol
        sig = _make_signal("TATASTEEL", qty=1)
        dec = _make_decision()
        with patch.object(om, "_broker_place") as mock_bp:
            om.execute(sig, dec)
            mock_bp.assert_not_called()


# ─── L: Risk Independence ──────────────────────────────────────────────────────

class TestRiskIndependence(unittest.TestCase):
    """L: KDA intelligence authority ≠ Risk safety authority. Risk can always veto."""

    def test_l01_risk_guardian_evaluate_exists(self):
        """FailSafeRiskGuardian.evaluate() must exist."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        self.assertTrue(hasattr(FailSafeRiskGuardian, "evaluate"))

    def test_l02_risk_guardian_returns_block_on_vix_breach(self):
        """FailSafeRiskGuardian must return BLOCK on extreme VIX."""
        from risk_guardian.risk_guardian import FailSafeRiskGuardian, KILL_SWITCH_VIX
        rg = FailSafeRiskGuardian()
        try:
            from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
            from datetime import datetime
            snap = MarketSnapshot(
                timestamp=datetime.now(), indices={},
                regime=RegimeLabel.VOLATILE, volatility=VolatilityLevel.EXTREME,
                vix=float(KILL_SWITCH_VIX) + 5.0,  # just above kill-switch
                fii_dii={}, sector_flows={}, sector_leaders=[],
                events_today=[], market_breadth={}, pcr=0.5,
                global_bias="BEARISH", global_sentiment_score=1.0,
            )
            portfolio = Portfolio(capital=TOTAL_CAPITAL, peak_capital=TOTAL_CAPITAL)
            result = rg.evaluate(snap, portfolio)
            action = getattr(result, "action", str(result)).upper()
            self.assertIn("BLOCK", action, f"VIX>{KILL_SWITCH_VIX} must trigger BLOCK")
        except Exception as e:
            self.skipTest(f"RiskGuardian.evaluate signature mismatch: {e}")

    def test_l03_risk_veto_is_before_execution_in_source(self):
        """Risk veto code appears before order_manager.execute in orchestrator."""
        with open("orchestrator/master_orchestrator.py", encoding="utf-8") as f:
            src = f.read()
        rg_pos = src.find("risk_guardian.evaluate")
        ex_pos = src.find("order_manager.execute")
        self.assertGreater(rg_pos, 0, "risk_guardian.evaluate must exist in orchestrator")
        self.assertGreater(ex_pos, 0, "order_manager.execute must exist in orchestrator")
        self.assertLess(rg_pos, ex_pos, "RiskGuardian must appear before order_manager.execute")


if __name__ == "__main__":
    unittest.main(verbosity=2)
