"""
tests/test_dta_broker_map_fallback_001.py
============================================
DTA-BROKER-MAP-FALLBACK-001 — root-cause fix, found while auditing system
health on 2026-09-17: real trade signals for BELRISE (a genuine NSE equity
added to the scanner universe by the earlier universe-expansion work) were
blocked twice today with [MISSING_DHAN_MAPPING], because:

  1. DhanFeed._load_instrument_list() was supposed to auto-extend
     DHAN_SECURITY_MAP via a live call to fetch_security_list("compact"),
     but the dhanhq SDK now returns a pandas DataFrame (207k+ rows) instead
     of a list of dicts. `if not result:` on a DataFrame raises "ambiguous
     truth value", silently caught and leaving _extra_map permanently
     empty (confirmed live: 0 entries loaded).
  2. Separately, execution_engine/order_manager.py::_broker_place() only
     ever checked the static DHAN_SECURITY_MAP, never DhanFeed's own
     _extra_map, so even a correctly populated _extra_map would not have
     helped without this second fix.

This suite covers both halves of the fix.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── Part A: _parse_extra_security_map() row-normalisation ────────────────

class TestParseExtraSecurityMap:
    def test_dataframe_shape_handled(self):
        """The exact live bug: fetch_security_list returns a DataFrame."""
        pd = pytest.importorskip("pandas")
        from data_feeds.dhan_feed import _parse_extra_security_map

        df = pd.DataFrame([
            {"SEM_TRADING_SYMBOL": "BELRISE", "SEM_EXM_EXCH_ID": "NSE",
             "SEM_INSTRUMENT_NAME": "EQUITY", "SEM_SMST_SECURITY_ID": "757102"},
            {"SEM_TRADING_SYMBOL": "BELRISE", "SEM_EXM_EXCH_ID": "BSE",
             "SEM_INSTRUMENT_NAME": "EQUITY", "SEM_SMST_SECURITY_ID": "999999"},
        ])
        result = _parse_extra_security_map(df)
        assert result["BELRISE"] == {
            "security_id": "757102", "segment": "NSE_EQ", "itype": "EQUITY",
        }
        # BSE row must never override/duplicate — only one NSE entry kept
        assert len(result) == 1

    def test_list_of_dicts_shape_still_supported(self):
        """Regression guard: the OLD SDK shape (list of dicts) must still work."""
        from data_feeds.dhan_feed import _parse_extra_security_map

        rows = [
            {"SEM_TRADING_SYMBOL": "NEWSTOCK", "SEM_EXM_EXCH_ID": "NSE",
             "SEM_INSTRUMENT_NAME": "EQUITY", "SEM_SMST_SECURITY_ID": "12345"},
        ]
        result = _parse_extra_security_map(rows)
        assert result["NEWSTOCK"]["security_id"] == "12345"
        assert result["NEWSTOCK"]["segment"] == "NSE_EQ"

    def test_none_result_returns_empty(self):
        from data_feeds.dhan_feed import _parse_extra_security_map
        assert _parse_extra_security_map(None) == {}

    def test_garbage_result_returns_empty_not_raises(self):
        from data_feeds.dhan_feed import _parse_extra_security_map
        assert _parse_extra_security_map("not a valid shape") == {}
        assert _parse_extra_security_map(12345) == {}

    def test_already_in_static_map_never_overridden(self):
        """A symbol already in the hand-curated static map must never be
        shadowed by a (possibly stale) dynamic entry."""
        from data_feeds.dhan_feed import _parse_extra_security_map, DHAN_SECURITY_MAP

        already_mapped_symbol = next(iter(DHAN_SECURITY_MAP))
        rows = [{
            "SEM_TRADING_SYMBOL": already_mapped_symbol, "SEM_EXM_EXCH_ID": "NSE",
            "SEM_INSTRUMENT_NAME": "EQUITY", "SEM_SMST_SECURITY_ID": "999999999",
        }]
        result = _parse_extra_security_map(rows)
        assert already_mapped_symbol not in result

    def test_non_nse_equity_rows_excluded(self):
        """F&O / currency / index / BSE-only rows must never leak into the
        extra map — only real NSE cash-market equities."""
        from data_feeds.dhan_feed import _parse_extra_security_map

        rows = [
            {"SEM_TRADING_SYMBOL": "NIFTY", "SEM_EXM_EXCH_ID": "NSE",
             "SEM_INSTRUMENT_NAME": "OPTIDX", "SEM_SMST_SECURITY_ID": "1"},
            {"SEM_TRADING_SYMBOL": "USDINR", "SEM_EXM_EXCH_ID": "BSE",
             "SEM_INSTRUMENT_NAME": "FUTCUR", "SEM_SMST_SECURITY_ID": "2"},
            {"SEM_TRADING_SYMBOL": "SOMESTOCK", "SEM_EXM_EXCH_ID": "BSE",
             "SEM_INSTRUMENT_NAME": "EQUITY", "SEM_SMST_SECURITY_ID": "3"},
        ]
        assert _parse_extra_security_map(rows) == {}

    def test_missing_symbol_or_security_id_skipped(self):
        from data_feeds.dhan_feed import _parse_extra_security_map
        rows = [
            {"SEM_TRADING_SYMBOL": "", "SEM_EXM_EXCH_ID": "NSE",
             "SEM_INSTRUMENT_NAME": "EQUITY", "SEM_SMST_SECURITY_ID": "1"},
            {"SEM_TRADING_SYMBOL": "NOID", "SEM_EXM_EXCH_ID": "NSE",
             "SEM_INSTRUMENT_NAME": "EQUITY", "SEM_SMST_SECURITY_ID": ""},
        ]
        assert _parse_extra_security_map(rows) == {}

    def test_non_dict_rows_skipped_not_raises(self):
        """DataFrame.to_dict('records') always yields dicts, but a
        malformed/legacy list could contain non-dict rows — must not crash."""
        from data_feeds.dhan_feed import _parse_extra_security_map
        rows = ["not_a_dict", None, 123]
        assert _parse_extra_security_map(rows) == {}


# ── Part B: order_manager._broker_place() dynamic-map fallback ───────────

def _make_bare_om_with_broker():
    import importlib
    import execution_engine.order_manager as om_mod
    importlib.reload(om_mod)
    from execution_engine.order_manager import OrderManager
    om = OrderManager.__new__(OrderManager)
    om._paper_mode = False
    om._broker = MagicMock()
    om._broker.place_order.return_value = "BRK_ORDER_1"
    return om


class TestBrokerPlaceDynamicMapFallback:
    def test_falls_back_to_feed_extra_map_when_static_map_misses(self, monkeypatch):
        om = _make_bare_om_with_broker()

        fake_feed_manager = MagicMock()
        fake_feed_manager.dhan._extra_map = {
            "BELRISE": {"security_id": "757102", "segment": "NSE_EQ", "itype": "EQUITY"},
        }
        import data_feeds
        monkeypatch.setattr(data_feeds, "get_feed_manager", lambda: fake_feed_manager)

        order_id = om._broker_place("BELRISE", "BUY", 10, 100.0, order_type="LIMIT")

        assert order_id == "BRK_ORDER_1"
        om._broker.place_order.assert_called_once_with(
            security_id="757102", exchange_segment="NSE_EQ",
            transaction_type="BUY", quantity=10, price=100.0, order_type="LIMIT",
        )

    def test_still_blocks_when_symbol_in_neither_map(self, monkeypatch, caplog):
        import logging
        om = _make_bare_om_with_broker()

        fake_feed_manager = MagicMock()
        fake_feed_manager.dhan._extra_map = {}
        import data_feeds
        monkeypatch.setattr(data_feeds, "get_feed_manager", lambda: fake_feed_manager)

        with caplog.at_level(logging.ERROR):
            order_id = om._broker_place("TOTALLY_UNKNOWN_XYZ", "BUY", 10, 100.0)

        assert order_id is None
        om._broker.place_order.assert_not_called()
        assert any("MISSING_DHAN_MAPPING" in r.message for r in caplog.records)

    def test_static_map_still_takes_priority(self, monkeypatch):
        """A symbol in the static map must resolve without ever consulting
        the feed manager (defense-in-depth: also protects against feed
        manager construction failures for well-known symbols)."""
        om = _make_bare_om_with_broker()

        def _boom():
            raise AssertionError("get_feed_manager should not be called")
        import data_feeds
        monkeypatch.setattr(data_feeds, "get_feed_manager", lambda: _boom())

        order_id = om._broker_place("RELIANCE", "BUY", 10, 100.0, order_type="LIMIT")
        assert order_id == "BRK_ORDER_1"

    def test_feed_manager_exception_fails_open_to_blocked(self, monkeypatch, caplog):
        """If the feed-manager fallback itself raises, the order must still
        be safely blocked (never place with unresolved security metadata)."""
        import logging
        om = _make_bare_om_with_broker()

        import data_feeds
        monkeypatch.setattr(
            data_feeds, "get_feed_manager",
            lambda: (_ for _ in ()).throw(RuntimeError("feed down")),
        )

        with caplog.at_level(logging.ERROR):
            order_id = om._broker_place("UNMAPPED_XYZ", "BUY", 10, 100.0)

        assert order_id is None
        om._broker.place_order.assert_not_called()
