"""
opportunity_engine/corporate_event_signal.py
================================================
Self-learning module #32 (ACQUISITION) -- Event Intelligence.

DATA SOURCE DECISION (finalized at implementation time, closing the one
item explicitly left blocked in the original 4-layer plan)
----------------------------------------------------------
No live news feed exists anywhere in this codebase -- confirmed
earlier that even the dormant enterprise_ai_platform package's news
providers (NewsAPI, GDELT) are unimplemented stubs. Rather than add a
new, unverified external dependency (paid API or scraping), this
reuses NSE's own public corporate-announcements endpoint via
nsepython's nsefetch() -- the exact same library + connectivity
pattern data_feeds/nse_feed.py already uses live in production (proven
to get past NSE's anti-bot protection). This is official, free,
real-time, and requires no new dependency.

Unlike company_growth_signal.py's problem (structured growth numbers
aren't available as clean NSE JSON), corporate announcements ARE
returned as clean JSON (symbol, subject/description, date) -- no PDF
parsing needed. What IS avoided, deliberately, is reading the actual
attached PDF/text content: this module only does mechanical KEYWORD
matching on the announcement's short subject/description string
against pre-defined positive/negative category lists (bonus, buyback,
order win, credit downgrade, litigation, etc.) -- deterministic
pattern matching, not text understanding. Routine/neutral
announcement types (board meeting intimation, AGM notice, record date)
are explicitly ignored, never scored.

LATENCY SAFETY: same non-blocking, day-cached, background-worker
pattern as company_growth_signal.py -- a live NSE network call is not
free, and must never block the scanner's live cycle.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

LOOKBACK_DAYS           = 7
WORKER_THROTTLE_SECONDS = 0.30

# Deterministic keyword matching only -- never reads the actual PDF/attachment
# text, only the announcement's own short subject/description string.
_POSITIVE_KEYWORDS = (
    "bonus issue", "buyback", "stock split", "dividend",
    "order win", "order received", "order bagged", "new contract",
    "credit rating upgrade", "rating upgraded", "capacity expansion",
    "acquisition completed", "strategic partnership", "expansion plan",
)
_NEGATIVE_KEYWORDS = (
    "resignation of auditor", "auditor resigned", "credit rating downgrade",
    "rating downgraded", "regulatory action", "penalty imposed",
    "show cause notice", "litigation", "fraud", "investigation",
    "default in payment", "delay in results",
)

_cache: Dict[str, Tuple[str, Optional[float]]] = {}   # symbol -> (date_str, score)
_pending: set = set()
_pending_lock = threading.Lock()
_worker_running = threading.Event()


def _classify_text(text: str) -> int:
    """Return +1 / -1 / 0 for one announcement's subject/description."""
    lowered = text.lower()
    if any(kw in lowered for kw in _NEGATIVE_KEYWORDS):
        return -1
    if any(kw in lowered for kw in _POSITIVE_KEYWORDS):
        return 1
    return 0


def _compute_uncached(symbol: str) -> Optional[float]:
    try:
        import nsepython as nse
    except Exception as exc:
        log.debug("[CorporateEvent] nsepython unavailable: %s", exc)
        return None

    try:
        raw = nse.nsefetch(
            f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={symbol}"
        )
    except Exception as exc:
        log.debug("[CorporateEvent] fetch failed for %s: %s", symbol, exc)
        return None

    if not isinstance(raw, list):
        return None

    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    scores: List[int] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        desc = str(item.get("desc") or item.get("subject") or item.get("attchmntText") or "")
        if not desc:
            continue
        ts_str = str(item.get("an_dt") or item.get("sort_date") or "").strip()
        try:
            ts = datetime.strptime(ts_str.split(" ")[0], "%d-%b-%Y")
        except ValueError:
            try:
                ts = datetime.fromisoformat(ts_str[:19])
            except Exception:
                ts = None
        if ts is not None and ts < cutoff:
            continue
        cls = _classify_text(desc)
        if cls != 0:
            scores.append(cls)

    if not scores:
        return None
    return round(max(-1.0, min(1.0, sum(scores) / len(scores))), 4)


def _worker_loop() -> None:
    try:
        while True:
            with _pending_lock:
                if not _pending:
                    break
                symbol = _pending.pop()
            score = None
            try:
                score = _compute_uncached(symbol)
            except Exception as exc:
                log.debug("[CorporateEvent] worker error for %s: %s", symbol, exc)
            _cache[symbol] = (datetime.now().strftime("%Y-%m-%d"), score)
            time.sleep(WORKER_THROTTLE_SECONDS)
    finally:
        _worker_running.clear()


def _ensure_worker_running() -> None:
    if not _worker_running.is_set():
        _worker_running.set()
        threading.Thread(target=_worker_loop, daemon=True, name="CorporateEventWorker").start()


def compute_corporate_event_score(symbol: str) -> Optional[float]:
    """
    Return a mechanical corporate-event score in [-1, +1] for *symbol*,
    or None if no scoreable announcement exists in the lookback window
    (the normal case most days), or the background fetch hasn't
    completed yet. Never blocks the calling scan cycle. Never raises.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    cached = _cache.get(symbol)
    if cached is not None and cached[0] == today_str:
        return cached[1]
    try:
        with _pending_lock:
            _pending.add(symbol)
        _ensure_worker_running()
    except Exception as exc:
        log.debug("[CorporateEvent] enqueue failed for %s: %s", symbol, exc)
    return None
