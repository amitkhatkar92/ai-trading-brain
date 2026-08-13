"""
test_etf_arb_guard.py
ETF-ARB Safety Guard tests (A-J).

Covers:
  A  ETF arb disabled → no opportunity
  B  NIFTYBEES cannot reach execution
  C  BANKBEES cannot reach execution
  D  OrderManager.execute() never called
  E  DhanBroker.place_order() never called
  F  No position created
  G  Equity scanner behaviour unchanged (38 symbols)
  H  Existing 38 Dhan mappings unchanged
  I  Futures arb remains disabled
  J  Guard is idempotent

Run:
    .venv\\Scripts\\python.exe -m pytest test_etf_arb_guard.py -v
"""

import unittest
from unittest.mock import MagicMock, patch

from opportunity_engine.arbitrage_ai import (
    ArbitrageAI,
    ETF_DATA,
    FUTURES_DATA,
    _ETF_ARB_DISABLED,
    _FUTURES_DISABLED,
)
from data_feeds.dhan_feed import DHAN_SECURITY_MAP


class TestEtfArbGuard(unittest.TestCase):

    def setUp(self):
        self.ai = ArbitrageAI()
        self.snapshot = MagicMock()

    # ── A: ETF arb disabled → no opportunity produced ─────────────────────

    def test_A_etf_arb_disabled_returns_empty(self):
        """When _ETF_ARB_DISABLED is True, _etf_nav_arb() must return []."""
        self.assertTrue(_ETF_ARB_DISABLED,
                        "_ETF_ARB_DISABLED must be True (guard not set)")
        result = self.ai._etf_nav_arb()
        self.assertEqual(result, [],
                         "_etf_nav_arb() must return [] when guard is active")

    # ── B: NIFTYBEES cannot reach execution ───────────────────────────────

    def test_B_niftybees_never_in_scan_output(self):
        """NIFTYBEES must not appear in scan() output when guard is active."""
        signals = self.ai.scan(self.snapshot)
        symbols = [s.symbol for s in signals]
        self.assertNotIn("NIFTYBEES", symbols,
                         "NIFTYBEES must not reach the signal pipeline")

    # ── C: BANKBEES cannot reach execution ────────────────────────────────

    def test_C_bankbees_never_in_scan_output(self):
        """BANKBEES must not appear in scan() output when guard is active."""
        signals = self.ai.scan(self.snapshot)
        symbols = [s.symbol for s in signals]
        self.assertNotIn("BANKBEES", symbols,
                         "BANKBEES must not reach the signal pipeline")

    # ── D: OrderManager.execute() never called ────────────────────────────

    def test_D_order_manager_execute_not_called(self):
        """scan() must not call OrderManager.execute() directly."""
        mock_execute = MagicMock()
        with patch("execution_engine.order_manager.OrderManager.execute", mock_execute):
            self.ai.scan(self.snapshot)
        mock_execute.assert_not_called()

    # ── E: DhanBroker.place_order() never called ──────────────────────────

    def test_E_dhan_broker_place_order_not_called(self):
        """scan() must not call DhanBroker.place_order() directly."""
        mock_place = MagicMock()
        with patch("execution_engine.brokers.dhan_broker.DhanBroker.place_order",
                   mock_place):
            self.ai.scan(self.snapshot)
        mock_place.assert_not_called()

    # ── F: No position created ─────────────────────────────────────────────

    def test_F_no_position_created(self):
        """scan() returns an empty list — no TradeSignal objects created."""
        signals = self.ai.scan(self.snapshot)
        self.assertEqual(signals, [],
                         "scan() must return [] (no positions can be created)")

    # ── G: Equity scanner behaviour unchanged ─────────────────────────────

    def test_G_equity_scanner_symbol_count_unchanged(self):
        """
        ArbitrageAI does not touch the equity scanner.
        _BASE_WATCHLIST has 20 symbols, _EXTENDED_WATCHLIST has 18.
        """
        from opportunity_engine.equity_scanner_ai import (
            _BASE_WATCHLIST, _EXTENDED_WATCHLIST,
        )
        self.assertEqual(len(_BASE_WATCHLIST), 20,
                         "_BASE_WATCHLIST must have 20 symbols")
        self.assertEqual(len(_EXTENDED_WATCHLIST), 18,
                         "_EXTENDED_WATCHLIST must have 18 symbols")
        self.assertEqual(len(_BASE_WATCHLIST) + len(_EXTENDED_WATCHLIST), 38)

    # ── H: 38 DHAN mappings unchanged ─────────────────────────────────────

    def test_H_dhan_security_map_38_scanner_symbols(self):
        """All 38 scanner symbols remain in DHAN_SECURITY_MAP."""
        from opportunity_engine.equity_scanner_ai import (
            _BASE_WATCHLIST, _EXTENDED_WATCHLIST,
        )
        scanner_symbols = [
            s["symbol"].strip()
            for s in _BASE_WATCHLIST + _EXTENDED_WATCHLIST
        ]
        missing = [s for s in scanner_symbols if s not in DHAN_SECURITY_MAP]
        self.assertEqual(missing, [],
                         f"Scanner symbols missing from DHAN_SECURITY_MAP: {missing}")
        # ETF symbols must NOT have been added
        self.assertNotIn("NIFTYBEES", DHAN_SECURITY_MAP)
        self.assertNotIn("BANKBEES",  DHAN_SECURITY_MAP)

    # ── I: Futures arb remains disabled ───────────────────────────────────

    def test_I_futures_arb_remains_disabled(self):
        """_FUTURES_DISABLED must still be True — independent of ETF guard."""
        self.assertTrue(_FUTURES_DISABLED,
                        "_FUTURES_DISABLED must remain True")
        result = self.ai._futures_basis_arb()
        self.assertEqual(result, [],
                         "_futures_basis_arb() must return [] when disabled")

    # ── J: Guard is idempotent ─────────────────────────────────────────────

    def test_J_guard_idempotent_across_multiple_calls(self):
        """scan() must return [] on every call while guard is active."""
        for _ in range(5):
            signals = self.ai.scan(self.snapshot)
            self.assertEqual(signals, [],
                             "scan() must consistently return [] (idempotent)")

    # ── Coverage: ETF_DATA still lists symbols (for future enable) ─────────

    def test_etf_data_symbols_not_in_dhan_map(self):
        """ETF_DATA symbols have no DHAN_SECURITY_MAP entry — confirms mapping gap."""
        for item in ETF_DATA:
            self.assertNotIn(
                item["symbol"], DHAN_SECURITY_MAP,
                f"{item['symbol']} must NOT be in DHAN_SECURITY_MAP until "
                "live prices and authoritative IDs are wired",
            )

    # ── Coverage: scan() with ETF guard matches universe coverage expectation ─

    def test_total_executable_symbols_38(self):
        """
        With both guards active, TOTAL_EXECUTABLE_SYMBOLS = 38.
        ArbitrageAI contributes 0.  All 38 are mapped.
        """
        from opportunity_engine.equity_scanner_ai import (
            _BASE_WATCHLIST, _EXTENDED_WATCHLIST,
        )
        scanner_universe = {
            s["symbol"].strip()
            for s in _BASE_WATCHLIST + _EXTENDED_WATCHLIST
        }
        self.assertEqual(len(scanner_universe), 38)
        unmapped = scanner_universe - set(DHAN_SECURITY_MAP.keys())
        self.assertEqual(unmapped, set(),
                         f"Unmapped scanner symbols: {unmapped}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
