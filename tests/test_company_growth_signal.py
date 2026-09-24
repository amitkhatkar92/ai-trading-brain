"""
tests/test_company_growth_signal.py
=======================================
Self-learning module #31 (ACQUISITION) -- mechanical company-growth
score computed from real yfinance revenue/earnings growth data.
Non-blocking: a cache miss enqueues a background fetch and returns
None immediately for the current cycle.

T01  Cache miss returns None immediately (never blocks)
T02  Cache hit (same day) returns the cached score without recomputing
T03  _compute_uncached(): both growth fields present -> weighted average,
     scaled so 50%+ growth saturates near +/-1.0
T04  _compute_uncached(): only one field present -> that field alone
T05  _compute_uncached(): neither field present -> None
T06  _compute_uncached(): yfinance import failure -> None, never raises
T07  _compute_uncached(): Ticker().info raising -> None, never raises
T08  Background worker populates the cache; a later call returns the
     real (non-None) score without blocking
T09  Symbol without .NS suffix gets it appended before the yfinance call
T10  compute_company_growth_score() never raises even if the pending
     set/lock machinery itself fails
"""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

import opportunity_engine.company_growth_signal as sig


@pytest.fixture(autouse=True)
def _reset_state():
    sig._cache.clear()
    with sig._pending_lock:
        sig._pending.clear()
    sig._worker_running.clear()
    yield
    sig._cache.clear()
    with sig._pending_lock:
        sig._pending.clear()
    sig._worker_running.clear()


def test_t01_cache_miss_returns_none_immediately():
    with patch.object(sig, "_ensure_worker_running"):
        result = sig.compute_company_growth_score("FRESH")
    assert result is None


def test_t02_cache_hit_returns_cached_without_recompute():
    today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    sig._cache["CACHED"] = (today, 0.75)
    with patch.object(sig, "_ensure_worker_running") as mocked:
        result = sig.compute_company_growth_score("CACHED")
    mocked.assert_not_called()
    assert result == 0.75


def test_t03_both_fields_weighted_average_scaled():
    fake_ticker = MagicMock()
    fake_ticker.info = {"revenueGrowth": 0.50, "earningsGrowth": 0.50}
    with patch("yfinance.Ticker", return_value=fake_ticker):
        score = sig._compute_uncached("GROWTHCO")
    assert score == pytest.approx(1.0, abs=1e-6)


def test_t04_only_one_field_present():
    fake_ticker = MagicMock()
    fake_ticker.info = {"revenueGrowth": 0.25, "earningsGrowth": None}
    with patch("yfinance.Ticker", return_value=fake_ticker):
        score = sig._compute_uncached("HALFDATA")
    assert score == pytest.approx(0.5, abs=1e-6)


def test_t05_neither_field_present_returns_none():
    fake_ticker = MagicMock()
    fake_ticker.info = {"someOtherField": 123}
    with patch("yfinance.Ticker", return_value=fake_ticker):
        score = sig._compute_uncached("NODATA")
    assert score is None


def test_t06_yfinance_import_failure_returns_none(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "yfinance":
            raise ImportError("no yfinance")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    assert sig._compute_uncached("ANY") is None


def test_t07_ticker_info_raising_returns_none():
    with patch("yfinance.Ticker", side_effect=RuntimeError("boom")):
        assert sig._compute_uncached("CRASHY") is None


def test_t08_background_worker_populates_cache():
    fake_ticker = MagicMock()
    fake_ticker.info = {"revenueGrowth": 0.40, "earningsGrowth": 0.40}
    with patch("yfinance.Ticker", return_value=fake_ticker), \
         patch.object(sig, "WORKER_THROTTLE_SECONDS", 0.0):
        first = sig.compute_company_growth_score("WORKERTEST")
        assert first is None
        # Wait for the background worker thread to finish (bounded).
        for _ in range(50):
            if "WORKERTEST" in sig._cache:
                break
            time.sleep(0.05)
        second = sig.compute_company_growth_score("WORKERTEST")
    assert second == pytest.approx(0.8, abs=1e-6)


def test_t09_ns_suffix_appended():
    fake_ticker = MagicMock()
    fake_ticker.info = {"revenueGrowth": 0.10, "earningsGrowth": 0.10}
    with patch("yfinance.Ticker", return_value=fake_ticker) as mocked:
        sig._compute_uncached("RELIANCE")
    mocked.assert_called_once_with("RELIANCE.NS")


def test_t10_enqueue_failure_never_raises():
    with patch.object(sig, "_ensure_worker_running", side_effect=RuntimeError("boom")):
        result = sig.compute_company_growth_score("WHATEVER")
    assert result is None
