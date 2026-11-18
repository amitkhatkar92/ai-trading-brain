"""
oios/data/corporate_announcement_fetcher.py

Layer 0 — NSE corporate-announcement pipeline (feeds ``daily_events``).

``daily_events`` had no live writer anywhere: ``ingest_event`` was only ever called from
tests, so every consumer (cause intelligence, propagation, data-health reports, and the
mover cause attribution) read an empty table. This module is that missing writer.

Source: NSE's public corporate-announcements API, which returns every announcement filed on
a date (about 500-1,100 a day) with symbol, category, short text and an exchange timestamp
(verified reachable from the VPS; it serves history, so recent days can be backfilled).

Classification is a fixed lookup on NSE's own ``desc`` category, never free-text guessing:
  * material categories are stored with an event type, a magnitude and a direction;
    direction is set only where the category itself implies one (an order win, an
    insolvency filing); everything else is NEUTRAL;
  * routine filings (investor meets, newspaper copies, shareholder meetings, ESOPs,
    appointments, ...) are skipped and counted;
  * exchange *queries* triggered by a move (volume spike, price movement, news
    verification) are skipped on purpose: they are reactions to the move, not causes.

Rows carry a deterministic id from NSE's own sequence id, so re-fetching a day is a no-op.
Timestamps are stored in IST as ``announced_at`` in ``raw_data`` so a consumer can tell
whether a filing was public before the next open. Never raises.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from datetime import date, datetime, timedelta
from typing import Any

log = logging.getLogger(__name__)

_API = ("https://www.nseindia.com/api/corporate-announcements"
        "?index=equities&from_date={d}&to_date={d}")
_HOME = "https://www.nseindia.com/"
_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
SOURCE = "NSE_ANNOUNCEMENT"
CONFIDENCE = 0.95            # exchange filing
DEFAULT_DAYS_BACK = 3
REQUEST_PAUSE_S = 1.0

# category (lower-case NSE ``desc``) -> (event_type, direction, magnitude)
_CATEGORY_RULES: dict[str, tuple[str, str, str]] = {
    "bagging/receiving of orders/contracts": ("ORDER_WIN", "POSITIVE", "HIGH"),
    "awarding of order(s)/contract(s)": ("ORDER_WIN", "POSITIVE", "HIGH"),
    "acquisition": ("OTHER", "NEUTRAL", "HIGH"),
    "amalgamation/merger": ("OTHER", "NEUTRAL", "HIGH"),
    "scheme of arrangement": ("OTHER", "NEUTRAL", "HIGH"),
    "demerger": ("OTHER", "NEUTRAL", "HIGH"),
    "stock split": ("OTHER", "NEUTRAL", "HIGH"),
    "buyback": ("OTHER", "NEUTRAL", "HIGH"),
    "public announcement - buyback of shares": ("OTHER", "NEUTRAL", "HIGH"),
    "public announcement-open offer": ("OTHER", "NEUTRAL", "HIGH"),
    "rights issue": ("OTHER", "NEUTRAL", "MEDIUM"),
    "preferential issue": ("OTHER", "NEUTRAL", "MEDIUM"),
    "qualified institutional placement": ("OTHER", "NEUTRAL", "MEDIUM"),
    "issue of securities": ("OTHER", "NEUTRAL", "MEDIUM"),
    "dividend": ("OTHER", "NEUTRAL", "MEDIUM"),
    "agreements": ("OTHER", "NEUTRAL", "MEDIUM"),
    "disclosure of material issue": ("OTHER", "NEUTRAL", "MEDIUM"),
    "granting/withdrawal/surrender/cancellation/suspension of key licenses/ regulatory approvals":
        ("OTHER", "NEUTRAL", "MEDIUM"),
    "capacity addition": ("CAPEX", "POSITIVE", "MEDIUM"),
    "commencement of commercial production/operations": ("CAPEX", "POSITIVE", "MEDIUM"),
    "integrated filing- financial": ("EARNINGS", "NEUTRAL", "MEDIUM"),
    "monthly business updates": ("EARNINGS", "NEUTRAL", "LOW"),
    "disclosure under sebi takeover regulations": ("PROMOTER", "NEUTRAL", "MEDIUM"),
    "credit rating": ("OTHER", "NEUTRAL", "MEDIUM"),
    "credit rating- revision": ("OTHER", "NEUTRAL", "MEDIUM"),
    "credit rating- new": ("OTHER", "NEUTRAL", "MEDIUM"),
    "credit rating- others": ("OTHER", "NEUTRAL", "MEDIUM"),
    "corporate insolvency resolution process": ("OTHER", "NEGATIVE", "HIGH"),
    "fraud/default/arrest": ("OTHER", "NEGATIVE", "HIGH"),
    "suspension of trading": ("OTHER", "NEGATIVE", "HIGH"),
    "action(s) taken or orders passed": ("OTHER", "NEGATIVE", "MEDIUM"),
    "action(s) initiated or orders passed": ("OTHER", "NEGATIVE", "MEDIUM"),
    "pendency of litigation(s)/dispute(s) or the outcome impacting the company":
        ("OTHER", "NEGATIVE", "MEDIUM"),
    "strikes/lockouts/disturbances": ("OTHER", "NEGATIVE", "MEDIUM"),
    "reasons for delayed/non-submission of financial results": ("EARNINGS", "NEGATIVE", "MEDIUM"),
    "resignation of statutory auditor": ("OTHER", "NEGATIVE", "MEDIUM"),
    "change in auditors": ("OTHER", "NEUTRAL", "LOW"),
    "change in management": ("OTHER", "NEUTRAL", "LOW"),
    "resignation of director/kmp/smp": ("OTHER", "NEUTRAL", "LOW"),
}
_BOARD_OUTCOME = "outcome of board meeting"      # results, dividend, fund raise: decided by text
_REACTIONS = frozenset({"spurt in volume", "price movement", "news verification",
                        "clarification - financial results"})


def classify_announcement(item: dict[str, Any]) -> tuple[str, str, str] | None:
    """(event_type, direction, magnitude) for a material announcement, else ``None``."""
    category = str(item.get("desc") or "").strip().lower()
    text = str(item.get("attchmntText") or "").lower()
    if not category or category in _REACTIONS:
        return None
    if category == _BOARD_OUTCOME:
        return ("EARNINGS", "NEUTRAL", "MEDIUM") if "result" in text else ("OTHER", "NEUTRAL", "LOW")
    rule = _CATEGORY_RULES.get(category)
    if rule is None:
        return None
    event_type, direction, magnitude = rule
    if category.startswith("credit rating"):
        if "downgrade" in text:
            direction = "NEGATIVE"
        elif "upgrade" in text:
            direction = "POSITIVE"
    return event_type, direction, magnitude


def _announced_at(item: dict[str, Any]) -> str | None:
    raw = str(item.get("an_dt") or item.get("exchdisstime") or "").strip()
    for fmt in ("%d-%b-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).isoformat(timespec="seconds")
        except ValueError:
            continue
    return None


def _event_id(item: dict[str, Any], symbol: str, announced: str) -> str:
    seq = str(item.get("seq_id") or "").strip()
    key = f"NSE_ANN|{seq}" if seq else f"NSE_ANN|{symbol}|{announced}|{item.get('desc')}"
    return hashlib.sha1(key.encode()).hexdigest()


def build_event_rows(items: list[dict[str, Any]]) -> tuple[list[tuple], dict[str, int]]:
    """Turn raw API items into ``daily_events`` rows; also count what was skipped."""
    now = datetime.now().isoformat(timespec="seconds")
    rows: list[tuple] = []
    stats = {"fetched": len(items), "material": 0, "skipped_routine": 0, "skipped_invalid": 0}
    for item in items:
        if not isinstance(item, dict):
            stats["skipped_invalid"] += 1
            continue
        symbol = str(item.get("symbol") or "").strip().upper()
        announced = _announced_at(item)
        verdict = classify_announcement(item)
        if not symbol or not announced:
            stats["skipped_invalid"] += 1
            continue
        if verdict is None:
            stats["skipped_routine"] += 1
            continue
        event_type, direction, magnitude = verdict
        category = str(item.get("desc") or "").strip()
        text = str(item.get("attchmntText") or "").strip()
        rows.append((
            _event_id(item, symbol, announced),
            symbol if symbol.endswith(".NS") else symbol + ".NS",
            announced[:10], event_type, f"{category}: {text}"[:300], magnitude, direction,
            SOURCE, CONFIDENCE,
            json.dumps({"announced_at": announced, "timezone": "IST", "category": category,
                        "text": text[:500], "seq_id": item.get("seq_id"),
                        "attachment": item.get("attchmntFile")}),
            now,
        ))
        stats["material"] += 1
    return rows, stats


def _insert_events(conn: sqlite3.Connection, rows: list[tuple]) -> int:
    before = conn.total_changes
    with conn:
        conn.executemany("""
            INSERT OR IGNORE INTO daily_events
                (event_id, symbol, event_date, event_type, headline, magnitude, direction,
                 source, confidence, raw_data, normalized_at, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
        """, rows)
    return conn.total_changes - before


def _fetch_day(session: Any, day: date) -> list[dict[str, Any]] | None:
    url = _API.format(d=day.strftime("%d-%m-%Y"))
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        log.warning("[Announcements] fetch failed for %s: %s", day, exc)
        return None
    return data if isinstance(data, list) else None


def run_announcement_fetch(
    conn: sqlite3.Connection, today: date | None = None, days_back: int = DEFAULT_DAYS_BACK,
    session: Any = None,
) -> dict[str, Any]:
    """Fetch and store material announcements for the last ``days_back`` days. Never raises."""
    summary: dict[str, Any] = {"days": 0, "fetched": 0, "material": 0, "stored": 0,
                               "skipped_routine": 0, "failed_days": 0}
    try:
        if session is None:
            import requests
            session = requests.Session()
            session.headers.update(_HEADERS)
            try:
                session.get(_HOME, timeout=15)      # prime the cookies NSE expects
            except Exception:
                log.debug("[Announcements] cookie priming failed", exc_info=True)
        end = today or date.today()
        for offset in range(max(0, days_back) + 1):
            day = end - timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            items = _fetch_day(session, day)
            if items is None:
                summary["failed_days"] += 1
                continue
            rows, stats = build_event_rows(items)
            summary["days"] += 1
            summary["fetched"] += stats["fetched"]
            summary["material"] += stats["material"]
            summary["skipped_routine"] += stats["skipped_routine"]
            if rows:
                summary["stored"] += _insert_events(conn, rows)
            if offset < days_back:
                time.sleep(REQUEST_PAUSE_S)
    except Exception as exc:
        log.warning("[Announcements] run failed (non-critical): %s", exc, exc_info=True)
        summary["error"] = str(exc)
    return summary
