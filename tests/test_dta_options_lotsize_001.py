"""
tests/test_dta_options_lotsize_001.py
========================================
DTA-OPTIONS-LOTSIZE-001: root-cause fix for DH-905 "bad values for
parameters" broker rejections on EVERY options order (confirmed live
2026-10-05, NIFTY/BANKNIFTY Iron_Condor_Range) — the static NSE_LOT_SIZES
fallback dict had drifted stale for ALL SIX index symbols vs the real,
verified Dhan instrument master (SEM_LOT_UNITS), e.g. BANKNIFTY hardcoded
15 vs real 30. Both options_opportunity_ai.py (signal-generation / risk
sizing) and options_order_manager.py (live order placement) now resolve
lot size via the verified instrument-master lookup FIRST, falling back
to the static dict only when the verified lookup is unavailable.

Coverage:
  - Both _resolve_lot_size() helpers prefer the verified lookup over the
    static dict when both are available
  - Both fall back to the static dict when the verified lookup returns
    None (e.g. BSE-listed SENSEX/BANKEX not indexed, or master not loaded)
  - Both fall back to the static dict when the verified lookup raises
  - NSE_LOT_SIZES itself now holds the corrected, verified-as-of-2026-10-05
    values (regression guard against reintroducing stale constants)
  - options_opportunity_ai's 5 signal-builder call sites all route through
    the verified-first helper (source-text guard — no direct
    NSE_LOT_SIZES.get(chain.symbol, ...) call sites remain)
"""
from __future__ import annotations

from unittest.mock import patch

import data_feeds.options_feed as options_feed
import execution_engine.options_order_manager as oom
import opportunity_engine.options_opportunity_ai as ooa


# ── NSE_LOT_SIZES regression guard ──────────────────────────────────────

def test_nse_lot_sizes_corrected_values():
    """Verified against the real Dhan instrument master 2026-10-05 —
    every one of the 6 previously-hardcoded values had drifted stale."""
    assert options_feed.NSE_LOT_SIZES == {
        "NIFTY":      65,
        "BANKNIFTY":  30,
        "FINNIFTY":   60,
        "MIDCPNIFTY": 120,
        "SENSEX":     20,
        "BANKEX":     30,
    }


# ── options_opportunity_ai._resolve_lot_size() ──────────────────────────

class TestOpportunityAIResolveLotSize:
    def test_verified_wins_even_when_static_disagrees(self):
        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map") as _getter:
            _getter.return_value.get_lot_size.return_value = 999
            assert ooa._resolve_lot_size("BANKNIFTY") == 999

    def test_falls_back_to_static_when_verified_returns_none(self):
        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map") as _getter:
            _getter.return_value.get_lot_size.return_value = None
            assert ooa._resolve_lot_size("NIFTY") == 65

    def test_falls_back_to_static_when_verified_raises(self):
        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map",
                   side_effect=RuntimeError("boom")):
            assert ooa._resolve_lot_size("NIFTY") == 65

    def test_unknown_symbol_defaults_to_75_when_neither_resolves(self):
        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map") as _getter:
            _getter.return_value.get_lot_size.return_value = None
            assert ooa._resolve_lot_size("UNKNOWNIDX") == 75

    def test_no_remaining_direct_static_lookups_in_signal_builders(self):
        """Source-text guard: all 5 signal-construction call sites must
        route through _resolve_lot_size(), never the bare static dict."""
        import inspect
        src = inspect.getsource(ooa)
        assert "NSE_LOT_SIZES.get(chain.symbol" not in src
        assert src.count('"lot_size": _resolve_lot_size(chain.symbol)') == 5


# ── options_order_manager._resolve_lot_size() ───────────────────────────

class TestOrderManagerResolveLotSize:
    def test_prefers_verified_over_static(self):
        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map") as _getter:
            _getter.return_value.get_lot_size.return_value = 30
            assert oom._resolve_lot_size("BANKNIFTY") == 30

    def test_falls_back_to_static_when_verified_returns_none(self):
        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map") as _getter:
            _getter.return_value.get_lot_size.return_value = None
            assert oom._resolve_lot_size("BANKNIFTY") == 30  # corrected static value

    def test_falls_back_to_static_when_verified_raises(self):
        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map",
                   side_effect=RuntimeError("boom")):
            assert oom._resolve_lot_size("NIFTY") == 65

    def test_returns_none_when_neither_source_resolves(self):
        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map") as _getter:
            _getter.return_value.get_lot_size.return_value = None
            assert oom._resolve_lot_size("TOTALLYUNKNOWN") is None

    def test_reproduces_the_real_banknifty_bug_scenario(self):
        """Regression guard for the exact confirmed-live failure: before
        this fix, BANKNIFTY resolved to the stale static 15 even when the
        verified master had the real value (30) available — this is the
        root cause of the DH-905 'bad values for parameters' broker
        rejection on every BANKNIFTY options order."""
        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map") as _getter:
            _getter.return_value.get_lot_size.return_value = 30
            resolved = oom._resolve_lot_size("BANKNIFTY")
        assert resolved == 30
        assert resolved != 15  # the old stale hardcoded value

    def test_execute_uses_resolver_not_inline_static_lookup(self):
        """Source-text guard: execute()'s lot-size block must call the
        shared resolver, never a bare NSE_LOT_SIZES.get(signal.symbol)
        checked before the verified lookup (the original bug's exact
        priority-order mistake)."""
        import inspect
        src = inspect.getsource(oom)
        assert "lot_size = _resolve_lot_size(signal.symbol)" in src
