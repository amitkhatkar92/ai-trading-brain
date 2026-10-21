"""
tests/test_dta_nse_holiday_calendar_001.py
=============================================
DTA-NSE-HOLIDAY-CALENDAR-001

Root cause: config.py's hardcoded NSE_HOLIDAYS for 2026 placed
Diwali-Balipratipada on Oct 20/21 -- the real NSE/BSE date is 10-Nov-2026
(confirmed live against nseindia.com and bseindia.com official holiday
pages on 2026-10-21, both showing the market open that day). This caused
the system to silently skip a real trading day (2026-10-21).

Verifies the corrected 2026 calendar matches the authoritative NSE/BSE
equities-segment list exactly, and that the previously-wrong dates are
no longer flagged as holidays.
"""
from __future__ import annotations

import datetime as dt

import config


def test_oct_21_2026_is_not_a_holiday():
    """Regression guard for the found-and-fixed bug: 2026-10-21 is a real
    trading day (Wednesday), not Diwali."""
    assert not config.is_nse_holiday(dt.date(2026, 10, 21))


def test_oct_20_2026_is_dussehra_holiday():
    """2026-10-20 is correctly a holiday (Dussehra), date unchanged."""
    assert config.is_nse_holiday(dt.date(2026, 10, 20))


def test_real_diwali_balipratipada_nov_10_2026_is_a_holiday():
    assert dt.date(2026, 11, 10) in config.NSE_HOLIDAYS


def test_nov_5_2026_is_no_longer_misflagged():
    """Old (wrong) Guru Nanak Jayanti date must no longer be a holiday
    unless it happens to fall on a weekend anyway."""
    d = dt.date(2026, 11, 5)
    if d.weekday() < 5:
        assert not config.is_nse_holiday(d)


def test_guru_nanak_jayanti_correct_date():
    assert dt.date(2026, 11, 24) in config.NSE_HOLIDAYS


def test_full_2026_calendar_matches_authoritative_nse_bse_list():
    """Cross-checked against nseindia.com/resources/exchange-communication-
    holidays and bseindia.com/static/markets/marketinfo/listholi.aspx
    (both equities-segment lists, identical), fetched 2026-10-21."""
    expected = {
        dt.date(2026, 1, 15),   # MCGM Election Day
        dt.date(2026, 1, 26),   # Republic Day
        dt.date(2026, 3, 3),    # Holi
        dt.date(2026, 3, 26),   # Shri Ram Navami
        dt.date(2026, 3, 31),   # Shri Mahavir Jayanti
        dt.date(2026, 4, 3),    # Good Friday
        dt.date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
        dt.date(2026, 5, 1),    # Maharashtra Day
        dt.date(2026, 5, 28),   # Bakri Id
        dt.date(2026, 6, 26),   # Muharram
        dt.date(2026, 9, 14),   # Ganesh Chaturthi
        dt.date(2026, 10, 2),   # Mahatma Gandhi Jayanti
        dt.date(2026, 10, 20),  # Dussehra
        dt.date(2026, 11, 10),  # Diwali - Balipratipada
        dt.date(2026, 11, 24),  # Prakash Gurpurb Sri Guru Nanak Dev
        dt.date(2026, 12, 25),  # Christmas
    }
    actual_2026 = {d for d in config.NSE_HOLIDAYS if d.year == 2026}
    assert actual_2026 == expected


def test_weekend_detection_unaffected():
    """is_nse_holiday()'s weekend short-circuit must still work regardless
    of the holiday-list content."""
    saturday = dt.date(2026, 10, 24)
    sunday = dt.date(2026, 10, 25)
    assert saturday.weekday() == 5
    assert sunday.weekday() == 6
    assert config.is_nse_holiday(saturday)
    assert config.is_nse_holiday(sunday)
