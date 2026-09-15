"""
tests/test_trust_score_history.py
====================================
Self-learning module #26 (part 1): ACQUISITION for
data_feeds/trust_score_history.py.

T01  record_daily_trust_snapshot() persists one record per tracked symbol
T02  Same-day re-trigger is a guarded no-op (skipped=already_recorded_today)
T03  get_multi_day_trust_score() returns None below window_days of history
T04  get_multi_day_trust_score() averages correctly once enough history exists
T05  get_history_days_count() counts distinct dates
T06  Fail-open: record_daily_trust_snapshot() never raises
T07  get_all_tracked_symbols_today() on DataIntegrityTracker returns the
     union of corruption/sanity/refresh symbols
T08  Safety-contract source scan
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

import data_feeds.trust_score_history as tsh


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    with patch.object(tsh, "_STORE_DIR", str(tmp_path)), \
         patch.object(tsh, "_HISTORY_PATH", str(tmp_path / "trust_score_history.jsonl")), \
         patch.object(tsh, "_STATE_PATH", str(tmp_path / "snapshot_state.json")):
        yield


def _fake_tracker(symbols, trust=1.0):
    tracker = MagicMock()
    tracker.get_all_tracked_symbols_today.return_value = set(symbols)
    tracker.get_trust_score.return_value = trust
    return tracker


def test_t01_snapshot_persists_one_record_per_symbol():
    with patch("data_feeds.data_integrity_tracker.get_data_integrity_tracker",
               return_value=_fake_tracker(["RELIANCE", "TCS"], trust=0.8)):
        result = tsh.record_daily_trust_snapshot(trade_date="2026-09-01")
    assert result["symbols_recorded"] == 2
    recs = tsh.get_records()
    assert len(recs) == 2
    assert all(r["trust_score"] == 0.8 for r in recs)


def test_t02_same_day_retrigger_is_noop():
    with patch("data_feeds.data_integrity_tracker.get_data_integrity_tracker",
               return_value=_fake_tracker(["RELIANCE"])):
        tsh.record_daily_trust_snapshot(trade_date="2026-09-01")
        result = tsh.record_daily_trust_snapshot(trade_date="2026-09-01")
    assert result["skipped"] == "already_recorded_today"
    assert len(tsh.get_records()) == 1


def test_t03_multi_day_score_none_below_window():
    with patch("data_feeds.data_integrity_tracker.get_data_integrity_tracker",
               return_value=_fake_tracker(["RELIANCE"], trust=0.7)):
        for d in ["2026-09-01", "2026-09-02", "2026-09-03"]:
            tsh.record_daily_trust_snapshot(trade_date=d)
    assert tsh.get_multi_day_trust_score("RELIANCE", window_days=5) is None


def test_t04_multi_day_score_averages_once_enough_history():
    scores = [0.6, 0.7, 0.8, 0.9, 1.0]
    for d, s in zip(["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05"], scores):
        with patch("data_feeds.data_integrity_tracker.get_data_integrity_tracker",
                   return_value=_fake_tracker(["RELIANCE"], trust=s)):
            tsh.record_daily_trust_snapshot(trade_date=d)
    result = tsh.get_multi_day_trust_score("RELIANCE", window_days=5)
    assert result == pytest.approx(sum(scores) / 5)


def test_t05_history_days_count():
    for d in ["2026-09-01", "2026-09-02"]:
        with patch("data_feeds.data_integrity_tracker.get_data_integrity_tracker",
                   return_value=_fake_tracker(["RELIANCE"])):
            tsh.record_daily_trust_snapshot(trade_date=d)
    assert tsh.get_history_days_count() == 2


def test_t06_fail_open_never_raises():
    with patch("data_feeds.data_integrity_tracker.get_data_integrity_tracker",
               side_effect=RuntimeError("boom")):
        result = tsh.record_daily_trust_snapshot(trade_date="2026-09-01")
    assert result["status"] == "ERROR"


def test_t07_tracker_union_accessor():
    from data_feeds.data_integrity_tracker import DataIntegrityTracker
    tracker = DataIntegrityTracker()
    tracker.record_corruption("A", "close_price", "series_coercion")
    tracker.record_sanity_fail("B", "volume", 0, "negative")
    tracker.record_refresh_success("C")
    assert tracker.get_all_tracked_symbols_today() == {"A", "B", "C"}


def test_t08_safety_contract_source_scan():
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data_feeds", "trust_score_history.py",
    )
    src = open(src_path, encoding="utf-8").read()
    for forbidden in ("execution_engine", "order_manager", "dhan_feed", "broker", "risk_control"):
        assert f"import {forbidden}" not in src
        assert f"from {forbidden}" not in src
