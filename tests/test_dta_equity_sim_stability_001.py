"""
tests/test_dta_equity_sim_stability_001.py
=============================================
DTA-EQUITY-SIM-STABILITY-001

Root cause: _estimate_atr()'s 20-day-range proxy (0.40 x (resistance-support))
produced stop distances far wider than a real ATR(14) for many watchlist
symbols, pushing MarketSimulation's stability score below threshold for
essentially every equity candidate on 2026-10-13 (0/408 signals approved
across 6 cycles, confirmed live).

Verifies:
  1. _compute_real_atr14() computes a correct Wilder ATR(14) from real
     ohlcv_daily history, is cached per symbol per day, and fails open
     (returns None) on insufficient history or DB error.
  2. _estimate_atr() prefers the real ATR when available, and falls back
     to the original proxy formula when symbol is omitted/unavailable/
     insufficient — no regression for symbols lacking OHLCV history.
  3. The real-ATR path produces meaningfully tighter stop distances than
     the proxy for a realistic wide-range symbol, directly addressing the
     MarketSimulation stability failure.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import date, timedelta

import pytest

import opportunity_engine.equity_scanner_ai as esa


def _build_temp_db(symbol: str, rows: list) -> str:
    """rows: list of (trade_date, high, low, close) tuples, ascending."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE ohlcv_daily (
            symbol TEXT, trade_date TEXT, open REAL, high REAL, low REAL,
            close REAL, volume REAL
        )
    """)
    for d, h, l, c in rows:
        conn.execute(
            "INSERT INTO ohlcv_daily (symbol, trade_date, open, high, low, close, volume) "
            "VALUES (?,?,?,?,?,?,?)",
            (symbol, d, c, h, l, c, 1_000_000.0),
        )
    conn.commit()
    conn.close()
    return path


def _dates_ending(end: date, n: int):
    return [(end - timedelta(days=n - 1 - i)).isoformat() for i in range(n)]


@pytest.fixture(autouse=True)
def _clear_atr_cache():
    esa._ATR14_CACHE.clear()
    yield
    esa._ATR14_CACHE.clear()


@pytest.fixture
def temp_ohlcv_env(monkeypatch):
    """20 trading days of mildly realistic OHLC for TESTSYM.NS, ~1.2% daily range."""
    dates = _dates_ending(date.today(), 20)
    rows = []
    price = 100.0
    for d in dates:
        high = round(price * 1.012, 2)
        low = round(price * 0.988, 2)
        rows.append((d, high, low, round(price, 2)))
        price *= 1.001
    db_path = _build_temp_db("TESTSYM.NS", rows)
    monkeypatch.setenv("OIOS_DB_PATH", db_path)
    yield db_path
    os.unlink(db_path)


def test_t01_real_atr14_computed_from_history(temp_ohlcv_env):
    atr = esa._compute_real_atr14("TESTSYM")
    assert atr is not None
    # True range per day ≈ 2.4% of price (high-low spread) -> ATR should be
    # a small fraction of price, nowhere near the old proxy's 5-9%+ estimates.
    assert 0 < atr < 3.0


def test_t02_insufficient_history_returns_none(monkeypatch):
    dates = _dates_ending(date.today(), 5)   # below _REAL_ATR14_MIN_ROWS=15
    rows = [(d, 101.0, 99.0, 100.0) for d in dates]
    db_path = _build_temp_db("SHORTHIST.NS", rows)
    monkeypatch.setenv("OIOS_DB_PATH", db_path)
    try:
        assert esa._compute_real_atr14("SHORTHIST") is None
    finally:
        os.unlink(db_path)


def test_t03_missing_symbol_returns_none(temp_ohlcv_env):
    assert esa._compute_real_atr14("NOSUCHSYMBOL") is None


def test_t04_db_error_fails_open(monkeypatch):
    monkeypatch.setenv("OIOS_DB_PATH", "/nonexistent/dir/that/cannot/exist.db")
    assert esa._compute_real_atr14("ANY") is None


def test_t05_cached_per_symbol_per_day(temp_ohlcv_env, monkeypatch):
    first = esa._compute_real_atr14("TESTSYM")
    assert first is not None
    calls = {"n": 0}
    real_get_connection = None
    import oios.db.connection as _conn_mod
    orig = _conn_mod.get_connection

    def counting_get_connection():
        calls["n"] += 1
        return orig()

    monkeypatch.setattr(_conn_mod, "get_connection", counting_get_connection)
    second = esa._compute_real_atr14("TESTSYM")
    assert second == first
    assert calls["n"] == 0   # cache hit — no new DB connection made


def test_t06_estimate_atr_prefers_real_atr_when_available(temp_ohlcv_env):
    # Deliberately wide proxy inputs (would give a huge 20-day-range proxy)
    atr = esa._estimate_atr(100.0, 50.0, 150.0, symbol="TESTSYM")
    assert atr < 3.0   # real ATR used, not the 0.40*(150-50)=40.0 proxy


def test_t07_estimate_atr_falls_back_without_symbol(temp_ohlcv_env):
    atr = esa._estimate_atr(100.0, 50.0, 150.0, symbol=None)
    assert atr == round((150.0 - 50.0) * 0.40, 4)


def test_t08_estimate_atr_falls_back_when_symbol_has_no_history(temp_ohlcv_env):
    atr = esa._estimate_atr(100.0, 50.0, 150.0, symbol="NOSUCHSYMBOL")
    assert atr == round((150.0 - 50.0) * 0.40, 4)


def test_t09_estimate_atr_backward_compatible_default(temp_ohlcv_env):
    # Pre-existing call style (no symbol arg) must behave exactly as before.
    atr = esa._estimate_atr(100.0, 95.0, 105.0)
    assert atr == round((105.0 - 95.0) * 0.40, 4)


def test_t10_real_atr_produces_tighter_stop_than_proxy_for_wide_range_symbol(temp_ohlcv_env):
    """Reproduces the real production scenario: a symbol whose 20-day
    support/resistance spread is wide (would give a ~9% stop via the old
    proxy) but whose real day-to-day ATR is tight — the fix must choose
    the tighter, more accurate real-ATR-based stop."""
    ltp, support, resistance = 100.0, 54.0, 146.0   # proxy would give 0.40*92=36.8 (36.8%!)
    proxy_atr = round((resistance - support) * 0.40, 4)
    real_atr = esa._estimate_atr(ltp, support, resistance, symbol="TESTSYM")
    assert real_atr < proxy_atr
    assert real_atr < 3.0
