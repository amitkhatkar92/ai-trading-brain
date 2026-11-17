"""Daily bars are fetched the same evening once the session is final, never intraday."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from oios.data import ohlcv_fetcher as fetcher

IST = fetcher._IST


def _at(text: str):
    return patch.object(fetcher, "_now_ist", return_value=datetime.fromisoformat(text).replace(tzinfo=IST))


@pytest.mark.parametrize("now,today,expected", [
    ("2026-11-17 16:47", "2026-11-17", "2026-11-18"),   # Tuesday after the final-bar time
    ("2026-11-17 16:00", "2026-11-17", "2026-11-18"),   # exactly at the boundary
    ("2026-11-17 15:59", "2026-11-17", "2026-11-17"),   # not final yet
    ("2026-11-17 14:00", "2026-11-17", "2026-11-17"),   # intraday: a partial bar must never be stored
    ("2026-11-17 08:03", "2026-11-17", "2026-11-17"),   # pre-market refresh, today's bar cannot exist
])
def test_today_is_included_only_after_the_session_is_final(now, today, expected):
    with _at(now):
        assert fetcher._fetch_end_date(today) == expected


def test_weekend_and_holiday_are_never_extended():
    with _at("2026-11-14 17:00"):                       # Saturday
        assert fetcher._fetch_end_date("2026-11-14") == "2026-11-14"
    with _at("2026-11-10 17:00"), patch("config.is_nse_holiday", return_value=True):
        assert fetcher._fetch_end_date("2026-11-10") == "2026-11-10"


def test_explicit_past_dates_keep_their_existing_behaviour():
    with _at("2026-11-17 17:00"):
        assert fetcher._fetch_end_date("2026-11-13") == "2026-11-13"
        assert fetcher._fetch_end_date("2026-11-18") == "2026-11-18"


def _run(now: str):
    conn = MagicMock()
    rows = [("SBIN.NS", "2026-11-17", 1.0, 2.0, 0.5, 1.5, 10.0, 1.5, "YFINANCE")]
    with _at(now), \
         patch.object(fetcher, "get_latest_date", return_value="2026-11-16"), \
         patch.object(fetcher, "fetch_symbol_ohlcv", return_value=rows) as fetch, \
         patch.object(fetcher, "upsert_ohlcv_rows", return_value=1), \
         patch.object(fetcher, "find_gaps", return_value=[]):
        result = fetcher.run_daily_fetch(conn, ["SBIN.NS"], "2026-11-17", inter_symbol_delay_s=0)
    return fetch, result


def test_post_close_refresh_asks_for_todays_bar():
    fetch, result = _run("2026-11-17 16:47")
    fetch.assert_called_once_with("SBIN.NS", "2026-11-17", "2026-11-18")
    assert result.symbols_ok == ["SBIN.NS"] and result.symbols_failed == []


def test_morning_and_intraday_refresh_are_unchanged():
    for now in ("2026-11-17 08:03", "2026-11-17 11:00"):
        fetch, _ = _run(now)
        fetch.assert_called_once_with("SBIN.NS", "2026-11-17", "2026-11-17")


def test_symbol_already_current_is_skipped_without_a_network_call():
    conn = MagicMock()
    with _at("2026-11-17 16:47"), \
         patch.object(fetcher, "get_latest_date", return_value="2026-11-17"), \
         patch.object(fetcher, "fetch_symbol_ohlcv") as fetch:
        result = fetcher.run_daily_fetch(conn, ["SBIN.NS"], "2026-11-17", inter_symbol_delay_s=0)
    fetch.assert_not_called()
    assert result.symbols_ok == ["SBIN.NS"]
