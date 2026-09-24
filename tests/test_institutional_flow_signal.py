"""
tests/test_institutional_flow_signal.py
===========================================
Self-learning module #30 (ACQUISITION) -- mechanical institutional-flow
score computed from real OIOS bulk/block-deal + bhav delivery-% data.

T01  No data at all -> None (not a data-quality error)
T02  Bulk/block BUY-dominant deals -> positive bulk signal
T03  Bulk/block SELL-dominant deals -> negative bulk signal
T04  Rising delivery% vs baseline -> positive delivery signal
T05  Falling delivery% vs baseline -> negative delivery signal
T06  Both signals present -> weighted combination
T07  Only one signal present -> that signal alone is returned
T08  Day-scoped cache: second call same day does not re-query the DB
T09  Fail-open: a DB error never raises, returns None
T10  Symbol with .NS suffix is stripped before querying OIOS tables
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, timedelta
from unittest.mock import patch

import pytest

import opportunity_engine.institutional_flow_signal as sig


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_market_behavior.db"
    monkeypatch.setenv("OIOS_DB_PATH", str(db_path))
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE bulk_block_deals (
            deal_id TEXT PRIMARY KEY, trade_date TEXT, symbol TEXT,
            deal_type TEXT, client_name TEXT, buy_sell TEXT,
            quantity REAL, price REAL, sector TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE bhav_daily (
            symbol TEXT, trade_date TEXT, series TEXT,
            traded_quantity REAL, deliverable_qty REAL, delivery_pct REAL,
            PRIMARY KEY (symbol, trade_date)
        )
    """)
    conn.commit()
    conn.close()
    sig._cache.clear()
    yield db_path


def _insert_bulk(db_path, symbol, deals):
    conn = sqlite3.connect(str(db_path))
    for i, (buy_sell, qty, days_ago) in enumerate(deals):
        trade_date = (date.today() - timedelta(days=days_ago)).isoformat()
        conn.execute(
            "INSERT INTO bulk_block_deals VALUES (?,?,?,?,?,?,?,?,?)",
            (f"D{i}", trade_date, symbol, "BULK", "SomeFund", buy_sell, qty, 100.0, "IT"),
        )
    conn.commit()
    conn.close()


def _insert_delivery(db_path, symbol, recent_pcts, baseline_pcts):
    conn = sqlite3.connect(str(db_path))
    for i, pct in enumerate(recent_pcts):
        trade_date = (date.today() - timedelta(days=i + 1)).isoformat()
        conn.execute(
            "INSERT INTO bhav_daily VALUES (?,?,?,?,?,?)",
            (symbol, trade_date, "EQ", 1000.0, 1000.0 * pct, pct),
        )
    for i, pct in enumerate(baseline_pcts):
        trade_date = (date.today() - timedelta(days=15 + i)).isoformat()
        conn.execute(
            "INSERT INTO bhav_daily VALUES (?,?,?,?,?,?)",
            (symbol, trade_date, "EQ", 1000.0, 1000.0 * pct, pct),
        )
    conn.commit()
    conn.close()


def test_t01_no_data_returns_none(_isolated_db):
    assert sig.compute_institutional_flow_score("NODATA") is None


def test_t02_buy_dominant_positive(_isolated_db):
    _insert_bulk(_isolated_db, "BUYCO", [("B", 1000, 5), ("B", 500, 10), ("S", 200, 15)])
    score = sig.compute_institutional_flow_score("BUYCO")
    assert score is not None
    assert score > 0


def test_t03_sell_dominant_negative(_isolated_db):
    _insert_bulk(_isolated_db, "SELLCO", [("S", 1000, 5), ("S", 500, 10), ("B", 200, 15)])
    score = sig.compute_institutional_flow_score("SELLCO")
    assert score is not None
    assert score < 0


def test_t04_rising_delivery_positive(_isolated_db):
    _insert_delivery(_isolated_db, "RISING", recent_pcts=[0.60] * 10, baseline_pcts=[0.40] * 15)
    score = sig.compute_institutional_flow_score("RISING")
    assert score is not None
    assert score > 0


def test_t05_falling_delivery_negative(_isolated_db):
    _insert_delivery(_isolated_db, "FALLING", recent_pcts=[0.30] * 10, baseline_pcts=[0.60] * 15)
    score = sig.compute_institutional_flow_score("FALLING")
    assert score is not None
    assert score < 0


def test_t06_both_signals_weighted_combination(_isolated_db):
    _insert_bulk(_isolated_db, "BOTH", [("B", 1000, 5)])
    _insert_delivery(_isolated_db, "BOTH", recent_pcts=[0.60] * 10, baseline_pcts=[0.40] * 15)
    score = sig.compute_institutional_flow_score("BOTH")
    assert score is not None
    assert score > 0   # both signals positive here


def test_t07_only_one_signal_present(_isolated_db):
    _insert_bulk(_isolated_db, "ONLYBULK", [("B", 1000, 5)])
    score = sig.compute_institutional_flow_score("ONLYBULK")
    assert score == pytest.approx(1.0, abs=1e-6)


def test_t08_day_scoped_cache_avoids_requery(_isolated_db):
    _insert_bulk(_isolated_db, "CACHEME", [("B", 1000, 5)])
    first = sig.compute_institutional_flow_score("CACHEME")
    with patch.object(sig, "_compute_uncached", return_value=999.0) as mocked:
        second = sig.compute_institutional_flow_score("CACHEME")
    mocked.assert_not_called()
    assert second == first


def test_t09_fail_open_never_raises(_isolated_db):
    with patch("opportunity_engine.institutional_flow_signal.get_connection", side_effect=RuntimeError("boom")) if False else patch.object(
        sig, "_compute_uncached", side_effect=RuntimeError("boom")
    ):
        result = sig.compute_institutional_flow_score("CRASHME")
    assert result is None


def test_t10_ns_suffix_stripped(_isolated_db):
    _insert_bulk(_isolated_db, "RELIANCE", [("B", 1000, 5)])
    score = sig.compute_institutional_flow_score("RELIANCE.NS")
    assert score is not None
