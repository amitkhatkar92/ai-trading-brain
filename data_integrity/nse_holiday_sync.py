"""
Automatic NSE trading-holiday sync.

config.NSE_HOLIDAYS is a hand-verified static list for 2026. When it runs out the OIOS
trading calendar ends (ages and expiries stop advancing) and weekday holidays look like
trading days. NSE publishes the next year's list late in the year; this fetches it from
NSE's own holiday master and stores it in data/nse_holidays_synced.json, which config
merges for calendar years the static list does not cover. It never overrides or removes a
static date, and a list that is clearly partial is rejected rather than stored.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC_FILE = os.path.join(_ROOT, "data", "nse_holidays_synced.json")
_PAGE = "https://www.nseindia.com/resources/exchange-communication-holidays"
_API = "https://www.nseindia.com/api/holiday-master?type=trading"
_SEGMENT = "CM"                    # capital-market (equities) segment
MIN_WEEKDAY_HOLIDAYS = 8           # NSE years have 14-18; fewer means a partial publication
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "application/json,text/html", "Accept-Language": "en-US,en;q=0.9",
}


def parse_holiday_master(payload: dict, segment: str = _SEGMENT) -> dict[int, list[dt.date]]:
    """Weekday holidays per calendar year from NSE's holiday-master JSON."""
    by_year: dict[int, set[dt.date]] = {}
    for row in payload.get(segment, []) or []:
        try:
            day = dt.datetime.strptime(str(row["tradingDate"]).strip(), "%d-%b-%Y").date()
        except (KeyError, ValueError):
            continue
        if day.weekday() < 5:
            by_year.setdefault(day.year, set()).add(day)
    return {year: sorted(days) for year, days in by_year.items()}


def fetch_holiday_master() -> Optional[dict]:
    try:
        import requests
        session = requests.Session()
        session.get(_PAGE, headers=_HEADERS, timeout=20)        # primes the cookies NSE requires
        response = session.get(_API, headers={**_HEADERS, "Referer": _PAGE}, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        log.warning("[NSEHolidays] fetch failed: %s", exc)
        return None


def load_synced(path: str = SYNC_FILE) -> dict[int, list[dt.date]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle).get("years", {})
        return {int(y): [dt.date.fromisoformat(d) for d in days] for y, days in raw.items()}
    except Exception:
        return {}


def needs_sync(today: dt.date, covered_years: set[int]) -> bool:
    """Next year's list is wanted from October on, until it is covered."""
    return today.month >= 10 and (today.year + 1) not in covered_years


def sync_nse_holidays(today: Optional[dt.date] = None, payload: Optional[dict] = None,
                      path: str = SYNC_FILE) -> dict:
    """Fetch and store holidays for years the static list lacks. Never raises."""
    try:
        import config
        today = today or dt.date.today()
        static_years = {d.year for d in config.NSE_HOLIDAYS if d.year not in load_synced(path)}
        synced = load_synced(path)
        covered = static_years | set(synced)
        if payload is None:
            if not needs_sync(today, covered):
                return {"status": "NOT_NEEDED", "covered_years": sorted(covered)}
            payload = fetch_holiday_master()
            if payload is None:
                return {"status": "FETCH_FAILED"}
        added: dict[int, list[dt.date]] = {}
        for year, days in parse_holiday_master(payload).items():
            if year in static_years:
                continue                                    # the verified static list always wins
            if len(days) < MIN_WEEKDAY_HOLIDAYS:
                log.warning("[NSEHolidays] %s list looks partial (%d weekday holidays) - ignored", year, len(days))
                continue
            added[year] = days
        if not added:
            return {"status": "NOTHING_NEW", "covered_years": sorted(covered)}
        synced.update(added)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"fetched_on": today.isoformat(),
                       "years": {str(y): [d.isoformat() for d in days] for y, days in sorted(synced.items())}},
                      handle, indent=1)
        config.NSE_HOLIDAYS = frozenset(config.NSE_HOLIDAYS | {d for days in added.values() for d in days})
        log.info("[NSEHolidays] stored holidays for %s", sorted(added))
        return {"status": "UPDATED", "years": sorted(added)}
    except Exception as exc:
        log.warning("[NSEHolidays] sync failed: %s", exc)
        return {"status": "ERROR", "error": str(exc)}
