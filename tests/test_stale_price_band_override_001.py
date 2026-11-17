"""A stale hand-maintained price band must not block a price the market is trading at."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from data_integrity import instrument_registry as registry_module
from data_integrity import session_close_reference as reference
from data_integrity.instrument_registry import get_instrument_registry


@pytest.fixture
def market(tmp_path, monkeypatch):
    """Market history for RELIANCE trading near 1,345 (its static band is 2,000-3,500)."""
    db = tmp_path / "market.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE ohlcv_daily (symbol TEXT, trade_date TEXT, open REAL, "
                 "high REAL, low REAL, close REAL, volume REAL)")
    last = date.today() - timedelta(days=1)
    for index in range(20):
        day = (last - timedelta(days=19 - index)).isoformat()
        conn.execute("INSERT INTO ohlcv_daily VALUES ('RELIANCE.NS',?,1340,1360,1330,1345,1)", (day,))
    conn.commit()
    conn.close()
    monkeypatch.setattr(reference, "DB_PATH", db)
    reference._cache.clear()
    registry_module._STALE_BAND_LOGGED.clear()
    yield
    reference._cache.clear()
    registry_module._STALE_BAND_LOGGED.clear()


def test_a_price_the_market_is_actually_trading_at_passes_a_stale_static_band(market):
    result = get_instrument_registry().check_price("RELIANCE", 1350.0)
    assert result.ok
    assert result.reason == "STATIC_BAND_STALE_OVERRIDDEN"
    assert result.band_low < 1345 < result.band_high


def test_a_phantom_price_still_fails_both_checks(market):
    # Outside the stale static band AND far from the recent-session history.
    assert not get_instrument_registry().check_price("RELIANCE", 3600.0).ok
    assert not get_instrument_registry().check_price("RELIANCE", 700.0).ok
    assert not get_instrument_registry().check_price("RELIANCE", 1600.0).ok


def test_a_price_inside_the_static_band_is_unchanged(market):
    result = get_instrument_registry().check_price("RELIANCE", 2500.0)
    assert result.ok and result.reason == ""


def test_without_market_history_the_static_band_decides_as_before(tmp_path, monkeypatch):
    monkeypatch.setattr(reference, "DB_PATH", tmp_path / "absent.db")
    reference._cache.clear()
    assert not get_instrument_registry().check_price("RELIANCE", 1350.0).ok
    reference._cache.clear()


def test_the_override_is_reported_once_per_symbol_per_day(market, caplog):
    registry = get_instrument_registry()
    with caplog.at_level("WARNING"):
        for _ in range(5):
            registry.check_price("RELIANCE", 1350.0)
    assert sum("STATIC_BAND_STALE" in r.message for r in caplog.records) == 1
