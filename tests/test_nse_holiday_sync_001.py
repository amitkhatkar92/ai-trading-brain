"""NSE holiday list ran out at 2026-12-31 and had to be extended by hand. It is now synced from NSE."""
from __future__ import annotations

import datetime as dt
import json

import pytest

import config
from data_integrity import nse_holiday_sync as sync


def _payload(year, count, weekend=True):
    days, day = [], dt.date(year, 1, 4)                  # a Monday in 2027
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day += dt.timedelta(days=1)
    rows = [{"tradingDate": d.strftime("%d-%b-%Y"), "description": "x"} for d in days]
    if weekend:
        rows.append({"tradingDate": dt.date(year, 1, 2).strftime("%d-%b-%Y"), "description": "Saturday"})
    return {"CM": rows, "FO": rows[:1]}


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "NSE_HOLIDAYS", frozenset(config.NSE_HOLIDAYS))
    return str(tmp_path / "synced.json")


def test_parse_keeps_weekday_holidays_of_the_equity_segment_only():
    parsed = sync.parse_holiday_master(_payload(2027, 10))
    assert list(parsed) == [2027] and len(parsed[2027]) == 10
    assert all(d.weekday() < 5 for d in parsed[2027])          # the Saturday row is dropped


def test_next_year_is_stored_and_applied_to_the_running_process(isolated):
    assert dt.date(2027, 1, 7) not in config.NSE_HOLIDAYS
    result = sync.sync_nse_holidays(dt.date(2026, 12, 1), _payload(2027, 12), isolated)
    assert result == {"status": "UPDATED", "years": [2027]}
    assert dt.date(2027, 1, 7) in config.NSE_HOLIDAYS and config.is_nse_holiday(dt.date(2027, 1, 7))
    assert sync.load_synced(isolated)[2027]
    assert dt.date(2026, 11, 10) in config.NSE_HOLIDAYS           # static dates untouched


def test_a_partial_list_is_rejected(isolated):
    assert sync.sync_nse_holidays(dt.date(2026, 12, 1), _payload(2027, 3), isolated)["status"] == "NOTHING_NEW"
    assert sync.load_synced(isolated) == {}


def test_the_verified_static_year_is_never_overridden(isolated):
    before = frozenset(config.NSE_HOLIDAYS)
    assert sync.sync_nse_holidays(dt.date(2026, 12, 1), _payload(2026, 12), isolated)["status"] == "NOTHING_NEW"
    assert config.NSE_HOLIDAYS == before


def test_no_request_is_made_before_october_or_once_covered(isolated, monkeypatch):
    monkeypatch.setattr(sync, "fetch_holiday_master", lambda: pytest.fail("must not fetch"))
    assert sync.sync_nse_holidays(dt.date(2026, 6, 1), None, isolated)["status"] == "NOT_NEEDED"
    sync.sync_nse_holidays(dt.date(2026, 12, 1), _payload(2027, 12), isolated)
    assert sync.sync_nse_holidays(dt.date(2026, 12, 2), None, isolated)["status"] == "NOT_NEEDED"


def test_a_failed_fetch_is_harmless(isolated, monkeypatch):
    monkeypatch.setattr(sync, "fetch_holiday_master", lambda: None)
    assert sync.sync_nse_holidays(dt.date(2026, 12, 1), None, isolated)["status"] == "FETCH_FAILED"


def test_config_merges_synced_years_but_never_a_static_year(tmp_path, monkeypatch):
    path = tmp_path / "data"
    path.mkdir()
    (path / "nse_holidays_synced.json").write_text(json.dumps(
        {"years": {"2027": ["2027-01-26"], "2026": ["2026-02-02"]}}), encoding="utf-8")
    import types
    fake = types.ModuleType("fake_config")
    fake.__file__ = str(tmp_path / "config.py")
    fake._dt = dt
    source = config._merge_synced_nse_holidays.__code__
    merged = types.FunctionType(source, {"_dt": dt, "__file__": str(tmp_path / "config.py")})(frozenset({dt.date(2026, 1, 26)}))
    assert dt.date(2027, 1, 26) in merged and dt.date(2026, 2, 2) not in merged


def test_the_calendar_covers_a_synced_year(isolated):
    import sqlite3
    from oios.db.calendar import ensure_trading_calendar
    from oios.db.migrations import apply_phase_c
    sync.sync_nse_holidays(dt.date(2026, 12, 1), _payload(2027, 12), isolated)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_phase_c(conn=conn)
    assert ensure_trading_calendar(conn)["to"] == "2027-12-31"
