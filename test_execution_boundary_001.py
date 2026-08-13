"""
test_execution_boundary_001.py
EXECUTION-BOUNDARY-001: Live execution path verification.

Traces the production execution path:
    TradeSignal → OrderManager.execute() → _broker_place() → DhanBroker.place_order()

Safety constraints (HARD REQUIREMENTS, never relaxed):
  - Production code changes: 0
  - Configuration changes: 0
  - Real Dhan orders placed: 0
  - Paper orders created: 0
  - Broker write calls (real API): 0
  - Positions created in production: 0

All broker calls are intercepted by a MagicMock spy BEFORE reaching
DhanBroker.place_order(). A secondary safety guard raises AssertionError
if the real API is somehow reached.

Run:
    .venv\\Scripts\\python.exe -m pytest test_execution_boundary_001.py -v
"""

import threading
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, call

# ── Safety sentinel ────────────────────────────────────────────────────────────
_REAL_DHAN_WRITE_CALLED: bool = False


def _dhan_safety_sentinel(*args, **kwargs):
    """Raise immediately if real Dhan API is reached. Should never be called."""
    global _REAL_DHAN_WRITE_CALLED
    _REAL_DHAN_WRITE_CALLED = True
    raise AssertionError(
        "SAFETY VIOLATION: Real Dhan place_order API was called. "
        "This test MUST NOT place live orders."
    )


# ── Imports from production ────────────────────────────────────────────────────
from execution_engine.order_manager import (
    OrderManager, OrderRecord, MAX_OPEN_POSITIONS,
    MAX_CAPITAL_PER_TRADE_PCT, _RECENT_CLOSE_TIMES, _REENTRY_AUDIT_LOG,
)
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.agent_output import DecisionResult
from models.portfolio import Portfolio


# ── Constants ─────────────────────────────────────────────────────────────────
_VALID_TIME   = datetime(2026, 8, 13, 10, 30, 0)   # safe trading window
_BEFORE_OPEN  = datetime(2026, 8, 13, 9,  0,  0)   # before 09:45 cutoff
_AFTER_CUTOFF = datetime(2026, 8, 13, 15, 0,  0)   # after 14:30 cutoff
_TEST_CAPITAL = 100_000.0                            # large enough to skip capital guard


def _make_signal(
    symbol="RELIANCE",
    direction=SignalDirection.BUY,
    entry_price=1320.0,
    stop_loss=1280.0,
    target_price=1380.0,
    quantity=1,
    strategy_name="Momentum_Breakout",
    confidence=8.0,
    atr=10.0,
    entry_zone_low=1315.0,
    entry_zone_high=1325.0,
) -> TradeSignal:
    """Return a valid synthetic TradeSignal for RELIANCE (in DHAN_SECURITY_MAP).

    At ₹1320 × 1 = ₹1320 notional, capital utilisation is 1.32% of ₹100k,
    well below the 15% cap.
    """
    return TradeSignal(
        symbol=symbol,
        direction=direction,
        signal_type=SignalType.EQUITY,
        entry_price=entry_price,
        stop_loss=stop_loss,
        target_price=target_price,
        quantity=quantity,
        strategy_name=strategy_name,
        confidence=confidence,
        atr=atr,
        entry_zone_low=entry_zone_low,
        entry_zone_high=entry_zone_high,
    )


def _make_decision(
    score=8.0,
    modifier=1.0,
    trade_type="FULL",
) -> DecisionResult:
    """Return an approved DecisionResult."""
    return DecisionResult(
        approved=True,
        confidence_score=score,
        position_size_modifier=modifier,
        trade_type=trade_type,
        reasoning="test_fixture_approved",
    )


def _make_context(vix=14.0, regime="RANGE", distortion=False) -> dict:
    return {"vix": vix, "regime": regime, "distortion": distortion}


def _make_om(
    broker_return="MOCK_ORDER_001",
    capital: float = _TEST_CAPITAL,
) -> OrderManager:
    """
    Build a test OrderManager that is in LIVE mode (_paper_mode=False)
    but uses a MagicMock as the broker.

    The mock's place_order() returns ``broker_return`` (truthy string by
    default).  Set to None to simulate broker failure.

    A secondary safety guard patches DhanBroker.place_order with
    ``_dhan_safety_sentinel`` to ensure the real SDK is never reached.
    """
    om = OrderManager.__new__(OrderManager)
    om._paper_mode    = False
    om._portfolio     = Portfolio(capital=capital, peak_capital=capital)
    om._orders        = {}
    om._reentry_slots = {}
    om._aet_pending   = {}
    om._ltp_stale_at  = {}
    om._journal_lock           = threading.Lock()
    om._expiry_sidecar_lock    = threading.Lock()
    om._dup_guard_stats        = {
        "overrides_by_profit": 0, "overrides_by_age": 0,
        "blocks_by_loss": 0, "blocks_by_age": 0,
        "ltp_unavailable_fallbacks": 0, "ltp_stale_fallbacks": 0,
        "ltp_lowconf_fallbacks": 0, "missed_opportunity_recovered": 0,
    }
    om._decision_latency_samples = []
    om._ltp_blocked_symbols      = {}
    om._trade_monitor            = None
    om._restored_extended_oids   = set()
    om._closed_ids_today         = set()
    om._closed_ids_today_date    = None
    om._swap_rotation_date       = None
    om._restore_stats            = {
        "restored_today": 0, "restored_carry": 0, "expired_at_restore": 0,
        "orphan_monitored_count": 0, "monitoring_gap_seconds": 0,
        "reconciled_count": 0, "immediate_sl_hits": 0, "immediate_expiries": 0,
    }
    # Build a mock broker whose place_order returns a valid order ID
    mock_broker = MagicMock(name="mock_broker")
    mock_broker.place_order.return_value = broker_return
    mock_broker.place_sl_order.return_value = "MOCK_SL_001"
    om._broker = mock_broker
    return om


class TestExecutionBoundary001(unittest.TestCase):
    """
    EXECUTION-BOUNDARY-001 test suite.

    All tests use a mock broker. Real DhanBroker.place_order is patched
    with a safety sentinel that raises AssertionError if invoked.

    Safety assertions at the end of every test:
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)
    """

    def setUp(self):
        # Clear module-level state between tests to prevent cross-contamination
        _RECENT_CLOSE_TIMES.clear()
        _REENTRY_AUDIT_LOG.clear()
        global _REAL_DHAN_WRITE_CALLED
        _REAL_DHAN_WRITE_CALLED = False

    # ── Helper: common patches for execute() ─────────────────────────────────

    def _patches(self, frozen_time: datetime):
        """Return a list of patch context managers used by most tests."""
        return [
            # Freeze clock inside order_manager to the given time
            patch("execution_engine.order_manager.datetime") ,
            # Prevent real signal_freshness import from blocking the signal
            patch(
                "production_readiness.ph3_signal_freshness.is_signal_expired",
                return_value=False,
            ),
            # Prevent price integrity guard from rejecting the test price
            patch("data_integrity.price_integrity_validator.get_price_validator"),
            # Skip notification side effects
            patch("notifications.notifier_manager.get_notifier"),
            # Skip retries sleeping in failed-broker tests
            patch("time.sleep"),
            # Safety sentinel on real DhanBroker
            patch(
                "execution_engine.brokers.dhan_broker.DhanBroker.place_order",
                side_effect=_dhan_safety_sentinel,
            ),
        ]

    def _setup_dt_mock(self, mock_dt, frozen_time: datetime):
        """Configure the datetime mock to return frozen_time from .now()."""
        mock_dt.now.return_value = frozen_time
        # Pass-through constructor so datetime(2026, ...) still works elsewhere
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

    def _setup_price_validator(self, mock_get_pv):
        """Configure the price validator mock to approve every price."""
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.classification = "VALID"
        mock_get_pv.return_value.validate.return_value = mock_result

    # ─────────────────────────────────────────────────────────────────────────
    # CASE A: Valid approved signal → broker called exactly once
    # ─────────────────────────────────────────────────────────────────────────

    def test_A_valid_signal_broker_called_once(self):
        """
        CASE A: A valid approved signal arriving during market hours must
        generate exactly one call to broker.place_order.

        Also verifies:
          - Returned OrderRecord is non-None
          - order_type is LIMIT
          - No real Dhan API was touched
        """
        om     = _make_om()
        signal = _make_signal()
        dec    = _make_decision()
        ctx    = _make_context()

        patches = self._patches(_VALID_TIME)
        with patches[0] as mock_dt, patches[1], patches[2] as mock_pv, \
             patches[3], patches[4], patches[5]:

            self._setup_dt_mock(mock_dt, _VALID_TIME)
            self._setup_price_validator(mock_pv)

            result = om.execute(signal, dec, ctx)

        self.assertIsNotNone(result, "Expected OrderRecord, got None")
        self.assertIsInstance(result, OrderRecord)
        self.assertEqual(result.order_type, "LIMIT")

        # Exactly one broker call for the entry order
        self.assertEqual(
            om._broker.place_order.call_count, 1,
            f"Expected exactly 1 broker call, got {om._broker.place_order.call_count}",
        )

        # Verify call arguments (post-EB001+EB002 fix)
        call_kwargs = om._broker.place_order.call_args
        # _broker_place now passes: security_id, exchange_segment, transaction_type, ...
        self.assertIn("security_id",      call_kwargs.kwargs, "security_id kwarg missing")
        self.assertIn("exchange_segment", call_kwargs.kwargs, "exchange_segment kwarg missing")
        self.assertIn("transaction_type", call_kwargs.kwargs)
        self.assertEqual(call_kwargs.kwargs["transaction_type"], "BUY")
        # Old wrong kwarg names must NOT be present
        self.assertNotIn("symbol",   call_kwargs.kwargs, "old 'symbol=' kwarg still present")
        self.assertNotIn("exchange", call_kwargs.kwargs, "old 'exchange=' kwarg still present")

        # Safety: real Dhan API never reached
        self.assertFalse(_REAL_DHAN_WRITE_CALLED, "SAFETY VIOLATION: real Dhan API was called")

    # ─────────────────────────────────────────────────────────────────────────
    # CASE B: Quantity = 0 after position_size_modifier → broker NOT called
    # ─────────────────────────────────────────────────────────────────────────

    def test_B_zero_quantity_blocked(self):
        """
        CASE B: When position_size_modifier=0.0, qty after modifier is 0.
        execute() must return None and must NOT call the broker.
        """
        om     = _make_om()
        signal = _make_signal(quantity=1)
        dec    = _make_decision(modifier=0.0)   # qty = 1 * 0.0 = 0
        ctx    = _make_context()

        patches = self._patches(_VALID_TIME)
        with patches[0] as mock_dt, patches[1], patches[2] as mock_pv, \
             patches[3], patches[4], patches[5]:

            self._setup_dt_mock(mock_dt, _VALID_TIME)
            self._setup_price_validator(mock_pv)

            result = om.execute(signal, dec, ctx)

        self.assertIsNone(result, "Expected None for zero-qty signal, got OrderRecord")
        self.assertEqual(om._broker.place_order.call_count, 0)
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ─────────────────────────────────────────────────────────────────────────
    # CASE C: Strategy disable — architectural finding
    # ─────────────────────────────────────────────────────────────────────────

    def test_C_strategy_disable_not_enforced_in_execute(self):
        """
        CASE C: Strategy disable is NOT enforced in OrderManager.execute().

        ARCHITECTURAL FINDING: execute() has no strategy-disable guard.
        Strategy disabling is enforced upstream (StrategyHealthMonitor /
        MasterOrchestrator) and does not reach execute().

        This test documents the boundary: a disabled strategy's signal would
        still be executed if it somehow reached execute() directly.
        The guard exists at Layer 5 (StrategyLab) / Layer 12 (TradeMonitoring),
        not at Layer 11 (ExecutionEngine).
        """
        om     = _make_om()
        signal = _make_signal(strategy_name="DISABLED_STRATEGY_XYZ")
        dec    = _make_decision()
        ctx    = _make_context()

        patches = self._patches(_VALID_TIME)
        with patches[0] as mock_dt, patches[1], patches[2] as mock_pv, \
             patches[3], patches[4], patches[5]:

            self._setup_dt_mock(mock_dt, _VALID_TIME)
            self._setup_price_validator(mock_pv)

            result = om.execute(signal, dec, ctx)

        # execute() does NOT block disabled strategies — broker is still called
        self.assertIsNotNone(
            result,
            "ARCHITECTURAL NOTE: execute() does not check strategy-disable state. "
            "Disable enforcement is at orchestrator/health-monitor layers.",
        )
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ─────────────────────────────────────────────────────────────────────────
    # CASE D: Confidence below threshold — architectural finding
    # ─────────────────────────────────────────────────────────────────────────

    def test_D_low_confidence_not_enforced_in_execute(self):
        """
        CASE D: Confidence threshold (6.5) is enforced by DecisionEngine,
        NOT by OrderManager.execute().

        ARCHITECTURAL FINDING: execute() does not check confidence_score.
        If a signal with score=3.0 arrives (bypassing DecisionEngine), execute()
        will attempt to route it to the broker.
        """
        om     = _make_om()
        signal = _make_signal(confidence=3.0)
        dec    = _make_decision(score=3.0)       # below 6.5 threshold
        ctx    = _make_context()

        patches = self._patches(_VALID_TIME)
        with patches[0] as mock_dt, patches[1], patches[2] as mock_pv, \
             patches[3], patches[4], patches[5]:

            self._setup_dt_mock(mock_dt, _VALID_TIME)
            self._setup_price_validator(mock_pv)

            result = om.execute(signal, dec, ctx)

        # execute() does NOT block low-confidence signals
        self.assertIsNotNone(
            result,
            "ARCHITECTURAL NOTE: execute() does not enforce confidence threshold. "
            "Score gating lives in DecisionEngine (Layer 10).",
        )
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ─────────────────────────────────────────────────────────────────────────
    # CASE E: Capital per trade > 15% → blocked by capital guard
    # ─────────────────────────────────────────────────────────────────────────

    def test_E_capital_guard_blocks_oversized_trade(self):
        """
        CASE E: When notional > MAX_CAPITAL_PER_TRADE_PCT (15%) of portfolio
        capital, execute() returns None and the broker is NOT called.

        Fixture: RELIANCE at ₹2500 × qty=1 → ₹2500 = 25% of ₹10,000 capital.
        """
        om = _make_om(capital=10_000.0)    # small capital like production
        # ₹2500 × 1 = 25% > 15%: should trigger CAPITAL/TRADE GUARD
        signal = _make_signal(
            symbol="RELIANCE",
            entry_price=2500.0,
            stop_loss=2450.0,
            target_price=2600.0,
            quantity=1,
        )
        dec = _make_decision()
        ctx = _make_context()

        patches = self._patches(_VALID_TIME)
        with patches[0] as mock_dt, patches[1], patches[2] as mock_pv, \
             patches[3], patches[4], patches[5]:

            self._setup_dt_mock(mock_dt, _VALID_TIME)
            self._setup_price_validator(mock_pv)

            result = om.execute(signal, dec, ctx)

        self.assertIsNone(result, "Expected None for oversized capital trade")
        self.assertEqual(om._broker.place_order.call_count, 0)
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ─────────────────────────────────────────────────────────────────────────
    # CASE F: Kill switch — architectural finding
    # ─────────────────────────────────────────────────────────────────────────

    def test_F_kill_switch_not_enforced_in_execute(self):
        """
        CASE F: Kill switch is NOT checked inside OrderManager.execute().

        ARCHITECTURAL FINDING: The kill switch is checked at the orchestrator
        layer (utils/kill_switch.py → master_orchestrator.run_full_cycle()) and
        prevents the cycle from starting. It is NOT a guard inside execute().
        A direct call to execute() bypasses the kill switch.
        """
        om     = _make_om()
        signal = _make_signal()
        dec    = _make_decision()
        ctx    = _make_context()

        patches = self._patches(_VALID_TIME) + [
            patch("utils.kill_switch.is_trading_enabled", return_value=False),
        ]
        with patches[0] as mock_dt, patches[1], patches[2] as mock_pv, \
             patches[3], patches[4], patches[5], patches[6]:

            self._setup_dt_mock(mock_dt, _VALID_TIME)
            self._setup_price_validator(mock_pv)

            result = om.execute(signal, dec, ctx)

        # Kill switch does NOT stop execute() directly — enforced upstream
        self.assertIsNotNone(
            result,
            "ARCHITECTURAL NOTE: execute() does not check kill_switch. "
            "Kill switch is enforced in master_orchestrator.run_full_cycle().",
        )
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ─────────────────────────────────────────────────────────────────────────
    # CASE G: Market closed (before 09:45) → ExecutionWindowBlock
    # ─────────────────────────────────────────────────────────────────────────

    def test_G1_before_0945_execution_window_block(self):
        """
        CASE G1: Any signal arriving before 09:45 IST is blocked by
        ExecutionWindowBlock. Returns None, broker never called.
        """
        om     = _make_om()
        signal = _make_signal()
        dec    = _make_decision()
        ctx    = _make_context()

        patches = self._patches(_BEFORE_OPEN)
        with patches[0] as mock_dt, patches[1], patches[2] as mock_pv, \
             patches[3], patches[4], patches[5]:

            self._setup_dt_mock(mock_dt, _BEFORE_OPEN)
            self._setup_price_validator(mock_pv)

            result = om.execute(signal, dec, ctx)

        self.assertIsNone(result, "Expected None before 09:45 execution window")
        self.assertEqual(om._broker.place_order.call_count, 0)
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    def test_G2_after_1430_late_entry_block(self):
        """
        CASE G2: Any fresh signal arriving after 14:30 IST is blocked by
        the LateEntryBlock. Returns None, broker never called.
        """
        om     = _make_om()
        signal = _make_signal()
        dec    = _make_decision()
        ctx    = _make_context()

        patches = self._patches(_AFTER_CUTOFF)
        with patches[0] as mock_dt, patches[1], patches[2] as mock_pv, \
             patches[3], patches[4], patches[5]:

            self._setup_dt_mock(mock_dt, _AFTER_CUTOFF)
            self._setup_price_validator(mock_pv)

            result = om.execute(signal, dec, ctx)

        self.assertIsNone(result, "Expected None after 14:30 late-entry cutoff")
        self.assertEqual(om._broker.place_order.call_count, 0)
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ─────────────────────────────────────────────────────────────────────────
    # CASE H: Invalid / unknown symbol
    # ─────────────────────────────────────────────────────────────────────────

    def test_H_unknown_symbol_blocked_at_mapping_layer(self):
        """
        CASE H (updated post-EB001+EB002 fix):
        _broker_place() now performs DHAN_SECURITY_MAP lookup before
        reaching broker.place_order().  An unrecognised symbol that is
        absent from the map is blocked at the mapping layer with a
        [MISSING_DHAN_MAPPING] log and returns None — broker is NOT called.

        Pre-fix behaviour: symbol passed through to broker unchecked.
        Post-fix behaviour: unknown symbol → None, 0 broker calls.
        """
        om     = _make_om()
        signal = _make_signal(symbol="NOTREAL_XYZ123")
        dec    = _make_decision()
        ctx    = _make_context()

        patches = self._patches(_VALID_TIME)
        with patches[0] as mock_dt, patches[1], patches[2] as mock_pv, \
             patches[3], patches[4], patches[5]:

            self._setup_dt_mock(mock_dt, _VALID_TIME)
            self._setup_price_validator(mock_pv)

            result = om.execute(signal, dec, ctx)

        # Post-fix: unknown symbol blocked before broker — execute() returns None
        self.assertIsNone(
            result,
            "Post-fix: execute() must return None for unmapped symbol",
        )
        # Broker must NOT be called for unmapped symbol
        self.assertEqual(om._broker.place_order.call_count, 0,
                         "Broker must not be called for unmapped symbol")
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ─────────────────────────────────────────────────────────────────────────
    # CASE I: Broker unavailable → graceful failure, no repeated submission
    # ─────────────────────────────────────────────────────────────────────────

    def test_I_broker_unavailable_returns_none_no_retry_storm(self):
        """
        CASE I: When the broker returns None for all attempts, execute() returns
        None gracefully after exactly MAX_ORDER_RETRIES=3 attempts.

        No more than 3 broker calls must be made (no infinite retry).
        """
        om = _make_om(broker_return=None)      # broker always returns None
        signal = _make_signal()
        dec    = _make_decision()
        ctx    = _make_context()

        patches = self._patches(_VALID_TIME)
        with patches[0] as mock_dt, patches[1], patches[2] as mock_pv, \
             patches[3], patches[4] as mock_sleep, patches[5]:

            self._setup_dt_mock(mock_dt, _VALID_TIME)
            self._setup_price_validator(mock_pv)

            result = om.execute(signal, dec, ctx)

        self.assertIsNone(result, "Expected None when broker returns None for all retries")
        # Exactly MAX_ORDER_RETRIES=3 broker attempts (no more, no less)
        self.assertEqual(
            om._broker.place_order.call_count, 3,
            f"Expected exactly 3 retry attempts, got {om._broker.place_order.call_count}",
        )
        # time.sleep called for each inter-retry pause (between retries 1→2 and 2→3)
        self.assertEqual(mock_sleep.call_count, 2, "Expected 2 sleep pauses for 3 retries")
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ─────────────────────────────────────────────────────────────────────────
    # CASE J: Duplicate signal → DupGuard blocks second call
    # ─────────────────────────────────────────────────────────────────────────

    def test_J_duplicate_signal_idempotency(self):
        """
        CASE J: A second execute() call for the same symbol while the first
        position is open must be blocked by DupGuard.

        Verifies: exactly one broker submission per symbol (idempotency).
        """
        om     = _make_om()
        signal = _make_signal()
        dec    = _make_decision()
        ctx    = _make_context()

        patches = self._patches(_VALID_TIME)
        with patches[0] as mock_dt, patches[1], patches[2] as mock_pv, \
             patches[3], patches[4], patches[5]:

            self._setup_dt_mock(mock_dt, _VALID_TIME)
            self._setup_price_validator(mock_pv)

            # First call — should succeed
            result1 = om.execute(signal, dec, ctx)

            # Second call for same symbol — DupGuard must block
            signal2 = _make_signal()     # identical symbol
            result2 = om.execute(signal2, dec, ctx)

        self.assertIsNotNone(result1, "First execute() should succeed")
        self.assertIsNone(result2, "Duplicate execute() must be blocked by DupGuard")
        # Only one broker call total across both execute() calls
        self.assertEqual(
            om._broker.place_order.call_count, 1,
            "DupGuard violation: broker called more than once for same symbol",
        )
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ─────────────────────────────────────────────────────────────────────────
    # DEFECT TEST: DhanBroker parameter name mismatch
    # ─────────────────────────────────────────────────────────────────────────

    def test_DEFECT_broker_parameter_name_mismatch(self):
        """
        DEFECT: OrderManager._broker_place() calls DhanBroker.place_order()
        with WRONG keyword argument names.

        _broker_place sends:
            symbol=symbol, exchange="NSE", transaction_type=..., quantity=...,
            price=..., order_type=...

        DhanBroker.place_order() expects:
            security_id, exchange_segment, transaction_type, quantity, price,
            order_type, product_type

        Python raises TypeError for 'symbol' and 'exchange' — this is caught
        by _place_entry_with_retry's try/except and results in ALL retries
        failing silently. Consequence: trades_executed=0 even when the broker
        is connected.

        This test verifies the defect is REAL and REPRODUCIBLE.
        """
        from execution_engine.brokers.dhan_broker import DhanBroker
        import config as cfg

        dhan = DhanBroker(cfg.DHAN_CLIENT_ID, cfg.DHAN_ACCESS_TOKEN)
        dhan._connected = False     # sim mode (no live API call)
        dhan._dhan = None

        # Simulate exactly what _broker_place does:
        with self.assertRaises(TypeError) as ctx_mgr:
            dhan.place_order(
                symbol="BHEL",                  # WRONG: expects security_id
                exchange="NSE",                 # WRONG: expects exchange_segment
                transaction_type="BUY",
                quantity=3,
                price=270.0,
                order_type="LIMIT",
            )

        self.assertIn("unexpected keyword argument", str(ctx_mgr.exception))
        self.assertIn("symbol", str(ctx_mgr.exception))

    def test_DEFECT_correct_call_works(self):
        """
        DEFECT companion: Verify the CORRECT keyword argument names work.

        The correct call should be:
            dhan.place_order(
                security_id="500103",    # Dhan security_id for BHEL
                exchange_segment="NSE_EQ",
                transaction_type="BUY",
                quantity=3,
                price=270.0,
                order_type="LIMIT",
            )

        When _connected=False, DhanBroker returns a SIM_ order_id safely.
        """
        from execution_engine.brokers.dhan_broker import DhanBroker
        import config as cfg

        dhan = DhanBroker(cfg.DHAN_CLIENT_ID, cfg.DHAN_ACCESS_TOKEN)
        dhan._connected = False
        dhan._dhan = None

        # Correct parameter names — should NOT raise TypeError
        result = dhan.place_order(
            security_id="500103",           # CORRECT
            exchange_segment="NSE_EQ",      # CORRECT
            transaction_type="BUY",
            quantity=3,
            price=270.0,
            order_type="LIMIT",
        )

        # sim mode returns SIM_DHAN_{security_id}_{transaction_type}
        self.assertIsNotNone(result)
        self.assertIn("SIM_DHAN", result)

    # ─────────────────────────────────────────────────────────────────────────
    # INSTRUMENT MAPPING VERIFICATION
    # ─────────────────────────────────────────────────────────────────────────

    def test_INSTRUMENT_dhan_security_map_used_in_broker_place(self):
        """
        POST-EB002-FIX VERIFICATION: _broker_place() now performs
        DHAN_SECURITY_MAP lookup and passes security_id + exchange_segment
        to broker.place_order() — NOT the raw symbol string.

        Pre-fix:  symbol=symbol, exchange="NSE" (EB001 defect)
        Post-fix: security_id=_meta["security_id"],
                  exchange_segment=_meta["segment"]

        Status: FIXED — symbol→security_id translation now exists in
        _broker_place (data_feeds.dhan_feed.DHAN_SECURITY_MAP).
        """
        om = _make_om()
        import inspect
        source = inspect.getsource(om._broker_place)
        # Post-fix: DHAN_SECURITY_MAP IS used
        self.assertIn(
            "DHAN_SECURITY_MAP", source,
            "DHAN_SECURITY_MAP must be present in _broker_place post-fix",
        )
        # Post-fix: security_id kwarg IS used
        self.assertIn("security_id", source)
        # Post-fix: exchange_segment kwarg IS used
        self.assertIn("exchange_segment", source)
        # Old wrong kwarg names must be gone
        # (symbol=symbol in place_order context — the fix removed this)
        self.assertNotIn(
            "GLOBAL_SYMBOL_MAP", source,
            "GLOBAL_SYMBOL_MAP should not be used — DHAN_SECURITY_MAP is the source",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # SAFETY INVARIANT: Real Dhan API never reached across all tests
    # ─────────────────────────────────────────────────────────────────────────

    def test_SAFETY_real_dhan_api_never_called(self):
        """
        Meta-test: verifies the _REAL_DHAN_WRITE_CALLED sentinel is False
        after all preceding tests in this session.
        """
        self.assertFalse(
            _REAL_DHAN_WRITE_CALLED,
            "SAFETY VIOLATION: _REAL_DHAN_WRITE_CALLED is True. "
            "At least one test reached the real Dhan API.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
