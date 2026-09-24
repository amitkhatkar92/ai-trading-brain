"""
tests/test_corporate_event_signal.py
========================================
Self-learning module #32 (ACQUISITION) -- mechanical corporate-event
score computed from real NSE corporate announcements (keyword-matched
only, never reads actual PDF/attachment text). Non-blocking: a cache
miss enqueues a background fetch and returns None immediately.

T01  Cache miss returns None immediately (never blocks)
T02  Cache hit (same day) returns the cached score without recomputing
T03  _classify_text(): positive keyword -> +1
T04  _classify_text(): negative keyword -> -1
T05  _classify_text(): routine/neutral text -> 0
T06  _compute_uncached(): announcements outside the lookback window are
     excluded
T07  _compute_uncached(): all-neutral / no announcements -> None
T08  _compute_uncached(): nsepython import failure -> None, never raises
T09  _compute_uncached(): nsefetch raising -> None, never raises
T10  _compute_uncached(): non-list response -> None (fail-open on
     unexpected shape)
T11  Background worker populates the cache; a later call returns the
     real (non-None) score without blocking
T12  compute_corporate_event_score() never raises even if the pending
     set/lock machinery itself fails
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

import opportunity_engine.corporate_event_signal as sig


def _patched_nsefetch(return_value=None, side_effect=None):
    """Inject a fake nsepython module into sys.modules for the duration of
    the context -- nsepython is a real production dependency (Docker image
    only) but is not installed in this local dev venv."""
    fake_module = ModuleType("nsepython")
    if side_effect is not None:
        fake_module.nsefetch = MagicMock(side_effect=side_effect)
    else:
        fake_module.nsefetch = MagicMock(return_value=return_value)
    return patch.dict(sys.modules, {"nsepython": fake_module})


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
        result = sig.compute_corporate_event_score("FRESH")
    assert result is None


def test_t02_cache_hit_returns_cached_without_recompute():
    today = datetime.now().strftime("%Y-%m-%d")
    sig._cache["CACHED"] = (today, 0.5)
    with patch.object(sig, "_ensure_worker_running") as mocked:
        result = sig.compute_corporate_event_score("CACHED")
    mocked.assert_not_called()
    assert result == 0.5


def test_t03_positive_keyword_classified_plus_one():
    assert sig._classify_text("Company announces Bonus Issue of shares") == 1


def test_t04_negative_keyword_classified_minus_one():
    assert sig._classify_text("Resignation of Auditor with immediate effect") == -1


def test_t05_neutral_text_classified_zero():
    assert sig._classify_text("Intimation of Board Meeting for routine matters") == 0


def test_t06_old_announcements_excluded():
    old_date = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
    items = [{"desc": "Bonus Issue approved", "an_dt": old_date}]
    with _patched_nsefetch(return_value=items):
        score = sig._compute_uncached("OLDNEWS")
    assert score is None


def test_t07_all_neutral_returns_none():
    recent = datetime.now().strftime("%d-%b-%Y")
    items = [{"desc": "Intimation of Board Meeting", "an_dt": recent}]
    with _patched_nsefetch(return_value=items):
        score = sig._compute_uncached("NEUTRALCO")
    assert score is None


def test_t08_nsepython_import_failure_returns_none(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "nsepython":
            raise ImportError("no nsepython")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    assert sig._compute_uncached("ANY") is None


def test_t09_nsefetch_raising_returns_none():
    with _patched_nsefetch(side_effect=RuntimeError("boom")):
        assert sig._compute_uncached("CRASHY") is None


def test_t10_non_list_response_returns_none():
    with _patched_nsefetch(return_value={"unexpected": "shape"}):
        assert sig._compute_uncached("WEIRD") is None


def test_t11_background_worker_populates_cache():
    recent = datetime.now().strftime("%d-%b-%Y")
    items = [
        {"desc": "Order Win from major client", "an_dt": recent},
        {"desc": "Order Bagged for new project", "an_dt": recent},
    ]
    with _patched_nsefetch(return_value=items), \
         patch.object(sig, "WORKER_THROTTLE_SECONDS", 0.0):
        first = sig.compute_corporate_event_score("WORKERTEST")
        assert first is None
        for _ in range(50):
            if "WORKERTEST" in sig._cache:
                break
            time.sleep(0.05)
        second = sig.compute_corporate_event_score("WORKERTEST")
    assert second == pytest.approx(1.0, abs=1e-6)


def test_t12_enqueue_failure_never_raises():
    with patch.object(sig, "_ensure_worker_running", side_effect=RuntimeError("boom")):
        result = sig.compute_corporate_event_score("WHATEVER")
    assert result is None
