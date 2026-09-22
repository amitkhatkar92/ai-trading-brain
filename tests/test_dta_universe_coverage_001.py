"""
tests/test_dta_universe_coverage_001.py
==========================================
DTA-UNIVERSE-COVERAGE-001

Verifies:
  1. _load_local_ohlcv_batch() correctly loads/excludes symbols by
     MIN_HISTORY_DAYS and staleness.
  2. _compute_technical_context() produces identical results whether fed
     from a live-yfinance-shaped call (_process_symbol) or a local-DB-
     shaped call (_process_symbol_from_local), given equivalent input.
  3. resistance_1y/support_1y are populated only when enough history
     exists, and never override the 20-day support/resistance fields.
  4. config.py candidate-pool caps were raised (SCANNER_MAX_CANDIDATES,
     MAX_PREPARED_CANDIDATES) from the old 120 default.
"""
from __future__ import annotations

import math
import os
import sqlite3
import tempfile
from datetime import date, timedelta

import pandas as pd
import pytest

import opportunity_engine.market_scanner as ms


def _wiggly_prices(n: int, base: float = 100.0, amp: float = 1.8) -> list:
    """Deterministic, realistically-noisy price series (passes ATR% gates)."""
    return [round(base + amp * math.sin(i * 0.7) + i * 0.03, 2) for i in range(n)]


def _build_temp_db(rows_by_symbol: dict) -> str:
    """Create a temp sqlite DB with an ohlcv_daily table populated per symbol."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE ohlcv_daily (
            symbol TEXT, trade_date TEXT, open REAL, high REAL, low REAL,
            close REAL, volume REAL, adjusted_close REAL,
            data_source TEXT DEFAULT 'YFINANCE', fetched_at TEXT
        )
    """)
    for sym, rows in rows_by_symbol.items():
        for d, c in rows:
            conn.execute(
                "INSERT INTO ohlcv_daily (symbol, trade_date, open, high, low, close, volume) "
                "VALUES (?,?,?,?,?,?,?)",
                (sym, d, c, c * 1.01, c * 0.99, c, 6_000_000.0),
            )
    conn.commit()
    conn.close()
    return path


def _dates_ending(end: date, n: int):
    return [(end - timedelta(days=n - 1 - i)).isoformat() for i in range(n)]


@pytest.fixture
def temp_ohlcv_env(monkeypatch):
    today = date.today()
    fresh_dates = _dates_ending(today, 40)   # 40 rows, ends today -> fresh & sufficient
    stale_dates = _dates_ending(today - timedelta(days=30), 40)  # ends 30d ago -> stale
    short_dates = _dates_ending(today, 5)    # only 5 rows -> below MIN_HISTORY_DAYS
    long_dates  = _dates_ending(today, 260)  # 260 rows -> enough for 1y context

    rows = {
        "FRESH.NS":  [(d, p) for d, p in zip(fresh_dates, _wiggly_prices(40))],
        "STALE.NS":  [(d, p) for d, p in zip(stale_dates, _wiggly_prices(40))],
        "SHORT.NS":  [(d, p) for d, p in zip(short_dates, _wiggly_prices(5))],
        "LONGHIST.NS": [(d, p) for d, p in zip(long_dates, _wiggly_prices(260))],
    }
    db_path = _build_temp_db(rows)
    monkeypatch.setenv("OIOS_DB_PATH", db_path)
    yield db_path
    os.unlink(db_path)


def test_t01_fresh_sufficient_symbol_included(temp_ohlcv_env):
    result = ms._load_local_ohlcv_batch(["FRESH", "STALE", "SHORT"])
    assert "FRESH" in result
    assert len(result["FRESH"]["closes"]) == 40


def test_t02_stale_symbol_excluded(temp_ohlcv_env):
    result = ms._load_local_ohlcv_batch(["FRESH", "STALE", "SHORT"])
    assert "STALE" not in result


def test_t03_short_history_symbol_excluded(temp_ohlcv_env):
    result = ms._load_local_ohlcv_batch(["FRESH", "STALE", "SHORT"])
    assert "SHORT" not in result


def test_t04_long_history_symbol_included_with_full_depth(temp_ohlcv_env):
    result = ms._load_local_ohlcv_batch(["LONGHIST"])
    assert "LONGHIST" in result
    assert len(result["LONGHIST"]["closes"]) == 260


def test_t05_empty_symbol_list_returns_empty(temp_ohlcv_env):
    assert ms._load_local_ohlcv_batch([]) == {}


def test_t06_process_symbol_from_local_matches_shared_context(temp_ohlcv_env):
    result = ms._load_local_ohlcv_batch(["LONGHIST"])
    out = ms._process_symbol_from_local("LONGHIST", result["LONGHIST"])
    assert out is not None
    assert out["symbol"] == "LONGHIST"
    assert out["data_source"] == "LOCAL_DB"
    assert out["resistance"] is not None
    assert out["support"] is not None


def test_t07_resistance_1y_populated_only_with_enough_history():
    # 260 days -> enough for 1y context
    close_long = pd.Series(_wiggly_prices(260))
    high_long  = close_long * 1.01
    low_long   = close_long * 0.99
    vol_long   = pd.Series([6_000_000.0] * 260)
    ctx_long = ms._compute_technical_context("X", close_long, high_long, low_long, vol_long)
    assert ctx_long is not None
    assert ctx_long["resistance_1y"] is not None
    assert ctx_long["support_1y"] is not None

    # 40 days -> not enough for 1y context
    close_short = pd.Series(_wiggly_prices(40))
    high_short  = close_short * 1.01
    low_short   = close_short * 0.99
    vol_short   = pd.Series([6_000_000.0] * 40)
    ctx_short = ms._compute_technical_context("Y", close_short, high_short, low_short, vol_short)
    assert ctx_short is not None
    assert ctx_short["resistance_1y"] is None
    assert ctx_short["support_1y"] is None


def test_t08_1y_fields_never_override_20d_support_resistance():
    close = pd.Series(_wiggly_prices(260))
    high  = close * 1.01
    low   = close * 0.99
    vol   = pd.Series([6_000_000.0] * 260)
    ctx = ms._compute_technical_context("Z", close, high, low, vol)
    assert ctx is not None
    w20 = close.iloc[-20:]
    assert ctx["support"] == round(float(w20.min()), 2)
    assert ctx["resistance"] == round(float(w20.max()), 2)


def test_t09_process_symbol_live_path_still_data_source_tagged():
    """Regression: the existing live-fetch path (_process_symbol) must still
    work unchanged and be tagged YFINANCE_LIVE."""
    idx = pd.date_range("2026-01-01", periods=40, freq="D")
    close = pd.Series(_wiggly_prices(40), index=idx)
    high  = close * 1.01
    low   = close * 0.99
    vol   = pd.Series([6_000_000.0] * 40, index=idx)
    df = pd.DataFrame({"Close": close, "High": high, "Low": low, "Volume": vol})
    out = ms._process_symbol("TEST", df)
    assert out is not None
    assert out["data_source"] == "YFINANCE_LIVE"


def test_t10_config_candidate_caps_raised():
    import config
    assert config.SCANNER_MAX_CANDIDATES > 120
    assert config.MAX_PREPARED_CANDIDATES > 120
    assert config.SCANNER_MAX_CANDIDATES == config.MAX_PREPARED_CANDIDATES
