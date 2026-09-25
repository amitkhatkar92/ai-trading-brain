"""
tests/test_dta_tick_size_002_equity_index.py
===============================================
DTA-TICK-SIZE-001 (part 2) — DhanFnOSecurityMap additive NSE cash-equity
tick-size index, built from the same already-downloaded instrument master
used for F&O lot sizes (no second live download).

Confirmed against the REAL, freshly-downloaded 2026-09-25 production
instrument master: SEM_TICK_SIZE is stored in PAISA, not rupees (e.g.
SBIN/TATACONSUM = "10" -> Rs 0.10, COALINDIA/RECLTD/INDHOTEL = "5" ->
Rs 0.05, GAIL/IOC = "1" -> Rs 0.01) — must be divided by 100.

T01  EQUITY row with a sane paisa tick value is indexed and correctly
     converted to rupees
T02  EQUITY row with an implausible converted tick (>Rs 2.00) is rejected,
     falls back to None
T03  Non-NSE / non-EQUITY rows never populate the equity index
T04  get_equity_tick_size() is case-insensitive on the symbol
T05  get_equity_tick_size() returns None for a genuinely unknown symbol
T06  module-level get_equity_tick_size() wrapper delegates to the singleton
     and fails open (returns None) if the singleton raises
T07  F&O index (lot sizes, contract lookup) is completely unaffected by
     the additive equity-tick pass (regression guard)
"""
from __future__ import annotations

import threading
from datetime import date
from unittest.mock import patch

from data_feeds.dhan_fno_security_map import DhanFnOSecurityMap


def _make_map_from_rows(rows):
    m = DhanFnOSecurityMap.__new__(DhanFnOSecurityMap)
    m._index              = {}
    m._lot_sizes           = {}
    m._equity_tick_sizes   = {}
    m._loaded_date         = date.today()
    m._lock                = threading.Lock()
    m._build_index(rows)
    return m


def _equity_row(symbol, tick_size_paisa):
    """Real Dhan master stores SEM_TICK_SIZE in paisa (e.g. "10" -> Rs 0.10)."""
    return {
        "SEM_EXM_EXCH_ID":     "NSE",
        "SEM_INSTRUMENT_NAME": "EQUITY",
        "SEM_TRADING_SYMBOL":  symbol,
        "SEM_TICK_SIZE":       str(tick_size_paisa),
    }


def _fno_row(underlying, strike, opt_type, sid):
    return {
        "SEM_EXM_EXCH_ID":      "NSE",
        "SEM_INSTRUMENT_NAME":  "OPTIDX",
        "SEM_TRADING_SYMBOL":   f"{underlying}-Sep2026-{int(strike)}-{opt_type}",
        "SEM_SMST_SECURITY_ID": str(sid),
        "SEM_EXPIRY_DATE":      "2026-09-25 14:30:00",
        "SEM_STRIKE_PRICE":     f"{strike:.5f}",
        "SEM_OPTION_TYPE":      opt_type,
        "SEM_LOT_UNITS":        "75.0",
    }


class TestEquityTickIndex:
    def test_t01_sane_tick_indexed(self):
        # Real production data: SBIN's raw SEM_TICK_SIZE is "10" (paisa).
        m = _make_map_from_rows([_equity_row("SBIN", "10")])
        assert m.get_equity_tick_size("SBIN") == 0.10

    def test_t02_implausible_tick_rejected(self):
        # A raw paisa value of 1000 would convert to Rs 10.00 -- implausible
        # for cash equity, must be rejected rather than silently trusted.
        m = _make_map_from_rows([_equity_row("SBIN", "1000")])
        assert m.get_equity_tick_size("SBIN") is None

    def test_t03_non_equity_rows_never_populate_index(self):
        m = _make_map_from_rows([
            _fno_row("NIFTY", 24500.0, "CE", "100001"),
            {"SEM_EXM_EXCH_ID": "BSE", "SEM_INSTRUMENT_NAME": "EQUITY",
             "SEM_TRADING_SYMBOL": "SBIN", "SEM_TICK_SIZE": "5"},
        ])
        assert m.get_equity_tick_size("SBIN") is None
        assert m.get_equity_tick_size("NIFTY") is None

    def test_t04_case_insensitive(self):
        m = _make_map_from_rows([_equity_row("TATACONSUM", "5")])
        assert m.get_equity_tick_size("tataconsum") == 0.05

    def test_t05_unknown_symbol_none(self):
        m = _make_map_from_rows([_equity_row("SBIN", "10")])
        assert m.get_equity_tick_size("UNKNOWNXYZ") is None

    def test_t06_module_wrapper_delegates_and_fails_open(self):
        from data_feeds.dhan_fno_security_map import get_equity_tick_size as _wrapper

        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map") as _getter:
            _getter.return_value.get_equity_tick_size.return_value = 0.10
            assert _wrapper("SBIN") == 0.10

        with patch("data_feeds.dhan_fno_security_map.get_fno_security_map",
                   side_effect=RuntimeError("boom")):
            assert _wrapper("SBIN") is None

    def test_t07_fno_index_unaffected(self):
        m = _make_map_from_rows([
            _fno_row("NIFTY", 24500.0, "CE", "100001"),
            _equity_row("SBIN", "10"),
        ])
        assert m.lookup("NIFTY", "2026-09-25", 24500.0, "CE") == "100001"
        assert m.get_lot_size("NIFTY") == 75
        assert m.get_equity_tick_size("SBIN") == 0.10
