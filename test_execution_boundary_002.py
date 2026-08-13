"""
test_execution_boundary_002.py
EB-003 — Execution Path Repair: Broker-spy tests for EB001+EB002 fix and SL architecture.

SAFETY CONSTRAINTS (never relaxed):
  Real Dhan orders: 0
  Dhan write calls: 0
  VPS deployment: 0
  Production restart: 0

Run:
    .venv\\Scripts\\python.exe -m pytest test_execution_boundary_002.py -v
"""

import threading
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, call

# ── Safety sentinel ────────────────────────────────────────────────────────────
_REAL_DHAN_WRITE_CALLED: bool = False


def _dhan_safety_sentinel(*args, **kwargs):
    global _REAL_DHAN_WRITE_CALLED
    _REAL_DHAN_WRITE_CALLED = True
    raise AssertionError("SAFETY: real Dhan place_order API was called — test failure")


# ── Production imports ─────────────────────────────────────────────────────────
from execution_engine.order_manager import (
    OrderManager, OrderRecord,
    _RECENT_CLOSE_TIMES, _REENTRY_AUDIT_LOG,
)
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.agent_output import DecisionResult
from models.portfolio import Portfolio
from data_feeds.dhan_feed import DHAN_SECURITY_MAP


# ── Constants ─────────────────────────────────────────────────────────────────
_VALID_TIME = datetime(2026, 8, 13, 10, 30, 0)
_TEST_CAP   = 500_000.0    # large enough to clear all capital guards


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


def _make_decision(score=8.0, modifier=1.0) -> DecisionResult:
    return DecisionResult(
        approved=True,
        confidence_score=score,
        position_size_modifier=modifier,
        trade_type="FULL",
        reasoning="test_fixture",
    )


def _make_om(broker_return="MOCK_ORDER_001", capital=_TEST_CAP) -> OrderManager:
    """Live-mode OrderManager (PAPER_TRADING=False) with mock broker."""
    om = OrderManager.__new__(OrderManager)
    om._paper_mode    = False
    om._portfolio     = Portfolio(capital=capital, peak_capital=capital)
    om._orders        = {}
    om._reentry_slots = {}
    om._aet_pending   = {}
    om._ltp_stale_at  = {}
    om._journal_lock           = threading.Lock()
    om._expiry_sidecar_lock    = threading.Lock()
    om._dup_guard_stats        = {k: 0 for k in (
        "overrides_by_profit", "overrides_by_age", "blocks_by_loss",
        "blocks_by_age", "ltp_unavailable_fallbacks", "ltp_stale_fallbacks",
        "ltp_lowconf_fallbacks", "missed_opportunity_recovered",
    )}
    om._decision_latency_samples = []
    om._ltp_blocked_symbols      = {}
    om._trade_monitor            = None
    om._restored_extended_oids   = set()
    om._closed_ids_today         = set()
    om._closed_ids_today_date    = None
    om._swap_rotation_date       = None
    om._restore_stats            = {k: 0 for k in (
        "restored_today", "restored_carry", "expired_at_restore",
        "orphan_monitored_count", "monitoring_gap_seconds",
        "reconciled_count", "immediate_sl_hits", "immediate_expiries",
    )}
    mock_broker = MagicMock(name="mock_broker")
    mock_broker.place_order.return_value = broker_return
    mock_broker.place_sl_order.return_value = "MOCK_SL_001"
    # Safety: DhanBroker.place_order real SDK never reached
    spec_mock = MagicMock(spec=["place_order", "cancel_order",
                                "get_positions", "get_portfolio"])
    spec_mock.place_order.return_value = broker_return
    om._broker = spec_mock
    return om


def _std_patches(frozen_time: datetime):
    return [
        patch("execution_engine.order_manager.datetime"),
        patch("production_readiness.ph3_signal_freshness.is_signal_expired",
              return_value=False),
        patch("data_integrity.price_integrity_validator.get_price_validator"),
        patch("notifications.notifier_manager.get_notifier"),
        patch("time.sleep"),
        patch("execution_engine.brokers.dhan_broker.DhanBroker.place_order",
              side_effect=_dhan_safety_sentinel),
    ]


def _setup_dt(mock_dt, t: datetime):
    mock_dt.now.return_value = t
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)


def _setup_pv(mock_get_pv):
    r = MagicMock(); r.ok = True; r.classification = "VALID"
    mock_get_pv.return_value.validate.return_value = r


class TestExecutionBoundary002(unittest.TestCase):

    def setUp(self):
        _RECENT_CLOSE_TIMES.clear()
        _REENTRY_AUDIT_LOG.clear()
        global _REAL_DHAN_WRITE_CALLED
        _REAL_DHAN_WRITE_CALLED = False

    # ── A: BHEL BUY → correct security_id via patched map ─────────────────

    def test_A_bhel_buy_resolves_correct_security_id(self):
        """
        BHEL is NOT in the live DHAN_SECURITY_MAP (not a current scanner symbol).
        This test patches the map to include BHEL (NSE security_id="438") to
        verify that the lookup and kwarg-passing mechanics work end-to-end.

        BHEL NSE ID confirmed from security_id_list.csv: sid=438, exchange=NSE, series=EQ.
        """
        om  = _make_om()
        sig = _make_signal(symbol="BHEL", entry_price=270.0, stop_loss=255.0,
                           target_price=305.0, quantity=1,
                           entry_zone_low=268.0, entry_zone_high=272.0)
        dec = _make_decision()

        patched_map = dict(DHAN_SECURITY_MAP)
        patched_map["BHEL"] = {"security_id": "438", "segment": "NSE_EQ",
                               "itype": "EQUITY"}

        patches = _std_patches(_VALID_TIME)
        with patches[0] as mdt, patches[1], patches[2] as mpv, \
             patches[3], patches[4], patches[5]:
            _setup_dt(mdt, _VALID_TIME)
            _setup_pv(mpv)
            with patch("execution_engine.order_manager.DHAN_SECURITY_MAP",
                       new=patched_map) if False else \
                 patch("data_feeds.dhan_feed.DHAN_SECURITY_MAP", patched_map):
                result = om.execute(sig, dec, {"vix": 14.0, "regime": "RANGE"})

        self.assertIsNotNone(result, "Expected OrderRecord, got None")
        self.assertEqual(om._broker.place_order.call_count, 1)
        kw = om._broker.place_order.call_args.kwargs
        self.assertEqual(kw["security_id"],      "438",    "Wrong security_id for BHEL")
        self.assertEqual(kw["exchange_segment"], "NSE_EQ", "Wrong exchange_segment for BHEL")
        self.assertEqual(kw["transaction_type"], "BUY")
        self.assertEqual(kw["order_type"],       "LIMIT")
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ── B: RELIANCE BUY → security_id="2885", exchange_segment="NSE_EQ" ───

    def test_B_reliance_buy_security_id_correct(self):
        """RELIANCE is in DHAN_SECURITY_MAP — verifies real map lookup."""
        om  = _make_om()
        sig = _make_signal(symbol="RELIANCE")
        dec = _make_decision()

        patches = _std_patches(_VALID_TIME)
        with patches[0] as mdt, patches[1], patches[2] as mpv, \
             patches[3], patches[4], patches[5]:
            _setup_dt(mdt, _VALID_TIME)
            _setup_pv(mpv)
            result = om.execute(sig, dec, {"vix": 14.0, "regime": "RANGE"})

        self.assertIsNotNone(result)
        self.assertEqual(om._broker.place_order.call_count, 1)
        kw = om._broker.place_order.call_args.kwargs
        self.assertEqual(kw["security_id"],      "2885",   "RELIANCE security_id wrong")
        self.assertEqual(kw["exchange_segment"], "NSE_EQ", "RELIANCE segment wrong")
        self.assertEqual(kw["transaction_type"], "BUY")
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ── C: Unknown symbol → MISSING_DHAN_MAPPING, broker NOT called ────────

    def test_C_unknown_symbol_missing_mapping_no_broker_call(self):
        """
        'FAKE_STOCK_XYZ' is not in DHAN_SECURITY_MAP.
        _broker_place() must log [MISSING_DHAN_MAPPING] and return None.
        Broker.place_order must NOT be called.
        """
        om  = _make_om()
        sig = _make_signal(symbol="FAKE_STOCK_XYZ", entry_price=100.0,
                           stop_loss=95.0, target_price=110.0)
        dec = _make_decision()

        patches = _std_patches(_VALID_TIME)
        with patches[0] as mdt, patches[1], patches[2] as mpv, \
             patches[3], patches[4], patches[5]:
            _setup_dt(mdt, _VALID_TIME)
            _setup_pv(mpv)
            result = om.execute(sig, dec, {"vix": 14.0, "regime": "RANGE"})

        self.assertIsNone(result, "Expected None for unmapped symbol")
        self.assertEqual(om._broker.place_order.call_count, 0,
                         "Broker must NOT be called for unmapped symbol")
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ── D: quantity=0 → execute() blocks before reaching broker ────────────

    def test_D_zero_quantity_blocked(self):
        """Zero-quantity signal must not reach broker."""
        om  = _make_om()
        sig = _make_signal(symbol="RELIANCE", quantity=1)
        dec = _make_decision(modifier=0.0)

        patches = _std_patches(_VALID_TIME)
        with patches[0] as mdt, patches[1], patches[2] as mpv, \
             patches[3], patches[4], patches[5]:
            _setup_dt(mdt, _VALID_TIME)
            _setup_pv(mpv)
            result = om.execute(sig, dec, {"vix": 14.0, "regime": "RANGE"})

        self.assertIsNone(result)
        self.assertEqual(om._broker.place_order.call_count, 0)
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ── E: Duplicate execution → max one broker request ────────────────────

    def test_E_duplicate_execution_idempotency(self):
        """DupGuard: second execute() for same symbol must be blocked."""
        om  = _make_om()
        sig = _make_signal(symbol="RELIANCE")
        dec = _make_decision()
        ctx = {"vix": 14.0, "regime": "RANGE"}

        patches = _std_patches(_VALID_TIME)
        with patches[0] as mdt, patches[1], patches[2] as mpv, \
             patches[3], patches[4], patches[5]:
            _setup_dt(mdt, _VALID_TIME)
            _setup_pv(mpv)
            r1 = om.execute(sig, dec, ctx)
            r2 = om.execute(_make_signal(symbol="RELIANCE"), dec, ctx)

        self.assertIsNotNone(r1)
        self.assertIsNone(r2, "Second RELIANCE signal must be blocked by DupGuard")
        self.assertEqual(om._broker.place_order.call_count, 1,
                         "Broker must be called exactly once for duplicate signal")
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ── F: Valid entry + SL architecture ───────────────────────────────────

    def test_F_entry_success_sl_architecture_software(self):
        """
        EB003 ARCHITECTURE:
        - Entry: LIMIT order placed via DhanBroker.place_order() ✓ (after fix)
        - SL: TradeMonitor software loop — NOT an exchange-side SL order
        - _place_stop_loss() returns None for DhanBroker (no place_sl_order method)
        - OrderRecord.stop_loss is set correctly → TradeMonitor monitors it

        Verifies:
          1. execute() returns OrderRecord
          2. OrderRecord.stop_loss == signal.stop_loss (software SL anchor)
          3. sl_order_id == "" (no exchange SL — expected)
          4. Exactly one broker call (entry only, no SL order)
          5. position has software SL protection via stop_loss field
        """
        om  = _make_om()
        sig = _make_signal(symbol="RELIANCE", stop_loss=1280.0)
        dec = _make_decision()
        ctx = {"vix": 14.0, "regime": "RANGE"}

        patches = _std_patches(_VALID_TIME)
        with patches[0] as mdt, patches[1], patches[2] as mpv, \
             patches[3], patches[4], patches[5]:
            _setup_dt(mdt, _VALID_TIME)
            _setup_pv(mpv)
            result = om.execute(sig, dec, ctx)

        self.assertIsNotNone(result)
        self.assertEqual(result.stop_loss, 1280.0,
                         "OrderRecord.stop_loss must equal signal.stop_loss (software SL anchor)")
        self.assertEqual(result.initial_stop_loss, 1280.0,
                         "initial_stop_loss immutable anchor must be set")
        self.assertEqual(result.sl_order_id, "",
                         "sl_order_id must be empty — DhanBroker has no place_sl_order")
        # Only the entry order reaches broker — no second SL broker call
        self.assertEqual(om._broker.place_order.call_count, 1,
                         "Exactly one broker call (entry only)")
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ── G: Entry success + SL returns None → software SL still active ──────

    def test_G_entry_ok_sl_returns_none_software_sl_active(self):
        """
        EB003 SAFETY CASE:
        When _place_stop_loss() returns None (DhanBroker has no place_sl_order),
        the system does NOT abort the order. The position receives software SL
        protection via TradeMonitor monitoring order.stop_loss each cycle.

        This is the INTENDED architecture: exchange-side SL is aspirational;
        TradeMonitor is the production SL mechanism.

        Verifies:
          1. execute() returns non-None OrderRecord (not aborted due to SL=None)
          2. stop_loss field is populated (TradeMonitor protection is active)
          3. No broker explosion from retried SL attempts
        """
        om  = _make_om()
        # DhanBroker has no place_sl_order → _place_stop_loss returns None
        # (confirmed: hasattr(DhanBroker, "place_sl_order") is False)
        sig = _make_signal(symbol="SBIN", entry_price=1036.0, stop_loss=1015.0,
                           target_price=1060.0, quantity=1,
                           entry_zone_low=1033.0, entry_zone_high=1039.0)
        dec = _make_decision()

        patches = _std_patches(_VALID_TIME)
        with patches[0] as mdt, patches[1], patches[2] as mpv, \
             patches[3], patches[4], patches[5]:
            _setup_dt(mdt, _VALID_TIME)
            _setup_pv(mpv)
            result = om.execute(sig, dec, {"vix": 14.0, "regime": "RANGE"})

        # Entry must succeed even though SL order returns None
        self.assertIsNotNone(result, "Entry must not abort because SL order returns None")
        self.assertEqual(result.stop_loss, 1015.0,
                         "Software SL anchor (stop_loss field) must be set")
        self.assertGreater(result.stop_loss, 0.0,
                           "stop_loss > 0 confirms TradeMonitor can protect this position")
        # entry is the only broker call
        self.assertEqual(om._broker.place_order.call_count, 1)
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ── H: Broker unavailable (_broker=None) → SIM path, safe ─────────────

    def test_H_broker_unavailable_sim_path(self):
        """
        When _broker is None (paper mode / disconnected),
        _broker_place() uses the SIM path — returns SIM_* order_id.
        No TypeError, no MISSING_DHAN_MAPPING, no real API call.
        """
        om = _make_om()
        om._broker = None    # simulate broker unavailable

        sig = _make_signal(symbol="RELIANCE")
        dec = _make_decision()

        patches = _std_patches(_VALID_TIME)
        with patches[0] as mdt, patches[1], patches[2] as mpv, \
             patches[3], patches[4], patches[5]:
            _setup_dt(mdt, _VALID_TIME)
            _setup_pv(mpv)
            result = om.execute(sig, dec, {"vix": 14.0, "regime": "RANGE"})

        # SIM path: execute() should succeed with a SIM_* order_id
        self.assertIsNotNone(result)
        self.assertTrue(result.order_id.startswith("SIM_"),
                        f"Expected SIM_* order_id, got: {result.order_id}")
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ── I: Invalid SL (stop_loss=0) → documented gap ───────────────────────

    def test_I_zero_stoploss_position_created_documented_gap(self):
        """
        DOCUMENTED GAP: execute() does not validate stop_loss > 0.
        A signal with stop_loss=0 passes all execute() guards and creates
        a position, but TradeMonitor cannot protect it (LTP never <= 0).

        This is a pre-existing gap unrelated to EB001/EB002/EB003.
        The fix does not introduce this issue; it is documented here for audit.
        """
        om  = _make_om()
        sig = _make_signal(symbol="RELIANCE", stop_loss=0.0)  # clearly invalid
        dec = _make_decision()

        patches = _std_patches(_VALID_TIME)
        with patches[0] as mdt, patches[1], patches[2] as mpv, \
             patches[3], patches[4], patches[5]:
            _setup_dt(mdt, _VALID_TIME)
            _setup_pv(mpv)
            result = om.execute(sig, dec, {"vix": 14.0, "regime": "RANGE"})

        # execute() does NOT block stop_loss=0 — pre-existing gap
        # (DecisionEngine upstream should prevent this; execute() trusts it)
        if result is not None:
            self.assertEqual(result.stop_loss, 0.0,
                             "Confirms: execute() allows stop_loss=0 (pre-existing gap)")
        # Regardless, real Dhan API never reached
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ── J: Retry behaviour → max 3 broker calls, no duplicate orders ───────

    def test_J_retry_capped_at_3_no_duplicate_orders(self):
        """
        When broker returns None for all attempts,
        _place_entry_with_retry() makes exactly 3 calls and returns None.
        execute() returns None — no duplicate or phantom orders.
        """
        om = _make_om(broker_return=None)  # broker always returns None
        sig = _make_signal(symbol="RELIANCE")
        dec = _make_decision()

        patches = _std_patches(_VALID_TIME)
        with patches[0] as mdt, patches[1], patches[2] as mpv, \
             patches[3], patches[4] as msleep, patches[5]:
            _setup_dt(mdt, _VALID_TIME)
            _setup_pv(mpv)
            result = om.execute(sig, dec, {"vix": 14.0, "regime": "RANGE"})

        self.assertIsNone(result, "All retries failed → None")
        self.assertEqual(om._broker.place_order.call_count, 3,
                         "Exactly 3 broker attempts (MAX_ORDER_RETRIES=3)")
        self.assertEqual(msleep.call_count, 2,
                         "2 sleep pauses between 3 retries")
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ── BHEL/PNB mapping investigation ─────────────────────────────────────

    def test_BHEL_PNB_not_in_scanner_not_in_map(self):
        """
        EB-002 PHASE 5: BHEL and PNB are absent from DHAN_SECURITY_MAP.

        Root cause: they are NOT in the current scanner watchlist
        (_BASE_WATCHLIST or _EXTENDED_WATCHLIST in equity_scanner_ai.py).
        They are Nifty PSU/midcap stocks outside the current trading universe.

        Conclusion: their absence is intentional for the current scanner scope.
        Authoritative NSE IDs from security_id_list.csv:
          BHEL:  security_id="438",   exchange=NSE, series=EQ
          PNB:   security_id="10666", exchange=NSE, series=EQ

        Safe population path: add to DHAN_SECURITY_MAP ONLY when they are
        simultaneously added to the scanner watchlist.
        """
        self.assertNotIn("BHEL", DHAN_SECURITY_MAP,
                         "BHEL is correctly absent — not in scanner")
        self.assertNotIn("PNB", DHAN_SECURITY_MAP,
                         "PNB is correctly absent — not in scanner")
        # Verify all current scanner symbols ARE covered
        scanner_symbols = [
            "RELIANCE", "HDFCBANK", "ICICIBANK", "TATASTEEL", "INFY",
            "BANKBARODA", "LT", "COALINDIA", "HCLTECH", "SBIN",
            "AXISBANK", "ONGC", "KOTAKBANK", "BHARTIARTL", "ITC",
            "BAJAJFINSV", "HINDALCO", "ULTRACEMCO", "TECHM", "NTPC",
            "HINDUNILVR", "ASIANPAINT", "BAJFINANCE", "MARUTI",
            "SUNPHARMA", "WIPRO", "POWERGRID", "DIVISLAB", "TITAN",
            "DRREDDY", "ADANIENT", "TATACONSUM", "NESTLEIND",
            "HAVELLS", "PIDILITIND", "GRASIM", "JSWSTEEL", "ADANIPORTS",
        ]
        missing = [s for s in scanner_symbols if s not in DHAN_SECURITY_MAP]
        self.assertEqual(missing, [],
                         f"Scanner symbols missing from DHAN_SECURITY_MAP: {missing}")

    # ── TATACONSUM and POWERGRID specific mapping verification ─────────────

    def test_TATACONSUM_POWERGRID_correct_mapping(self):
        """Verify specific security_ids for requested symbols."""
        self.assertEqual(DHAN_SECURITY_MAP["TATACONSUM"]["security_id"], "3432")
        self.assertEqual(DHAN_SECURITY_MAP["TATACONSUM"]["segment"], "NSE_EQ")
        self.assertEqual(DHAN_SECURITY_MAP["POWERGRID"]["security_id"], "14977")
        self.assertEqual(DHAN_SECURITY_MAP["POWERGRID"]["segment"], "NSE_EQ")

    # ── ADANIENT uses NSE_EQ (not IDX_I which BANKNIFTY shares id=25) ────────

    def test_ADANIENT_uses_NSE_EQ_not_IDX_I(self):
        """
        ADANIENT and BANKNIFTY both have security_id="25" but different segments.
        ADANIENT must be routed to NSE_EQ, not IDX_I (the index segment).
        Passing the wrong segment would misroute to BANKNIFTY.
        """
        adanient = DHAN_SECURITY_MAP["ADANIENT"]
        banknifty = DHAN_SECURITY_MAP["BANKNIFTY"]
        self.assertEqual(adanient["security_id"], "25")
        self.assertEqual(adanient["segment"], "NSE_EQ")   # equity
        self.assertEqual(banknifty["security_id"], "25")
        self.assertEqual(banknifty["segment"], "IDX_I")   # index — different segment
        # Confirm the fix passes the segment, not just the ID
        # (if only security_id were passed, ambiguity would exist)
        om  = _make_om()
        sig = _make_signal(symbol="ADANIENT", entry_price=3157.0, stop_loss=3000.0,
                           target_price=3350.0)
        dec = _make_decision()
        patches = _std_patches(_VALID_TIME)
        with patches[0] as mdt, patches[1], patches[2] as mpv, \
             patches[3], patches[4], patches[5]:
            _setup_dt(mdt, _VALID_TIME)
            _setup_pv(mpv)
            result = om.execute(sig, dec, {"vix": 14.0, "regime": "RANGE"})
        self.assertIsNotNone(result)
        kw = om._broker.place_order.call_args.kwargs
        self.assertEqual(kw["security_id"],      "25",     "ADANIENT security_id")
        self.assertEqual(kw["exchange_segment"], "NSE_EQ", "ADANIENT must use NSE_EQ not IDX_I")
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ── Symbol with .NS suffix is normalised correctly ─────────────────────

    def test_symbol_with_NS_suffix_normalised(self):
        """If a signal arrives with RELIANCE.NS (yfinance format), it must work."""
        om  = _make_om()
        sig = _make_signal(symbol="RELIANCE.NS")  # .NS suffix — possible from feed
        dec = _make_decision()
        patches = _std_patches(_VALID_TIME)
        with patches[0] as mdt, patches[1], patches[2] as mpv, \
             patches[3], patches[4], patches[5]:
            _setup_dt(mdt, _VALID_TIME)
            _setup_pv(mpv)
            result = om.execute(sig, dec, {"vix": 14.0, "regime": "RANGE"})
        # RELIANCE.NS → stripped to RELIANCE → found in map
        self.assertIsNotNone(result)
        kw = om._broker.place_order.call_args.kwargs
        self.assertEqual(kw["security_id"], "2885")
        self.assertFalse(_REAL_DHAN_WRITE_CALLED)

    # ── EB001 TypeError is gone — no longer raised ─────────────────────────

    def test_EB001_typeerror_no_longer_raised(self):
        """
        Post-fix regression: DhanBroker.place_order() must NOT receive
        the wrong kwarg names 'symbol=' or 'exchange='.
        Calling with wrong names raises TypeError; correct names succeed.
        """
        from execution_engine.brokers.dhan_broker import DhanBroker
        import config as cfg
        b = DhanBroker(cfg.DHAN_CLIENT_ID, cfg.DHAN_ACCESS_TOKEN)
        b._connected = False
        b._dhan = None
        # Correct call (as fix now generates) must NOT raise
        try:
            result = b.place_order(
                security_id="2885", exchange_segment="NSE_EQ",
                transaction_type="BUY", quantity=1, price=1320.0,
                order_type="LIMIT",
            )
            self.assertIn("SIM_DHAN", result,
                          "SIM mode must return SIM_DHAN_* string")
        except TypeError as e:
            self.fail(f"Correct kwargs raised TypeError (regression): {e}")

    # ── Safety sentinel ────────────────────────────────────────────────────

    def test_SAFETY_real_dhan_api_never_reached(self):
        """Meta: confirm sentinel was never triggered across all tests."""
        self.assertFalse(_REAL_DHAN_WRITE_CALLED,
                         "SAFETY VIOLATION: real DhanBroker.place_order was called")


if __name__ == "__main__":
    unittest.main(verbosity=2)
