"""
opportunity_engine/company_growth_signal.py
===============================================
Self-learning module #31 (ACQUISITION) -- Company Intelligence
(growth-screen half only -- see report to user: management-quality/
"story" judgement is deliberately NOT attempted here, it is not
something this system can do reliably).

Computes a mechanical growth score per symbol from REAL, filed
quarterly financial data (revenue growth, earnings growth) -- no
judgement, no text/concall reading, purely arithmetic on structured
numbers already reported by the company.

DATA SOURCE DECISION (finalized at implementation time)
----------------------------------------------------------
The originally-proposed "NSE primary" source does not expose
structured quarterly revenue/earnings growth as clean, queryable JSON
the way OIOS's bulk_block_deals/delivery_pct endpoints did for
Positioning Intelligence -- NSE's public corporate-financial-results
endpoint mainly links to filed PDFs, not parsed numbers. yfinance is
used instead: it is the only source in this stack with a stable,
already-proven Python API (yf.Ticker already used in data_feeds/
yahoo_feed.py, dhan_feed.py, options_feed.py) that also exposes
`.info["revenueGrowth"]` / `.info["earningsGrowth"]` for many NSE
tickers. Coverage/reliability is honestly inconsistent for smaller,
less-followed names -- callers MUST treat None as "no data today",
never as a red flag.

LATENCY SAFETY
----------------
`Ticker(...).info` is a real network call (0.5-2s) -- calling it
synchronously for every scanner candidate would risk blowing
OpportunityEngine's own latency budget (this codebase already runs
close to its CRIT threshold on yfinance batch calls elsewhere).
compute_company_growth_score() is therefore NON-BLOCKING: a cache miss
enqueues the symbol for a background worker (mirrors the existing
_RSI_REFRESH_RUNNING / price-refresh thread pattern already used
elsewhere in equity_scanner_ai.py) and returns None immediately for
THIS cycle; the score becomes available on a later cycle once fetched.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

GROWTH_FULL_SCORE_THRESHOLD = 0.50   # 50%+ growth -> score saturates at +/-1.0
WORKER_THROTTLE_SECONDS     = 0.30   # be gentle on the Yahoo endpoint

_cache: Dict[str, Tuple[str, Optional[float]]] = {}   # symbol -> (date_str, score)
_pending: set = set()
_pending_lock = threading.Lock()
_worker_running = threading.Event()


def _ns_ticker(symbol: str) -> str:
    return symbol if symbol.endswith(".NS") else f"{symbol}.NS"


def _compute_uncached(symbol: str) -> Optional[float]:
    try:
        import yfinance as yf
    except Exception as exc:
        log.debug("[CompanyGrowth] yfinance unavailable: %s", exc)
        return None
    try:
        info = yf.Ticker(_ns_ticker(symbol)).info
    except Exception as exc:
        log.debug("[CompanyGrowth] fetch failed for %s: %s", symbol, exc)
        return None
    if not isinstance(info, dict):
        return None

    values = [
        v for v in (info.get("revenueGrowth"), info.get("earningsGrowth"))
        if isinstance(v, (int, float))
    ]
    if not values:
        return None
    avg = sum(values) / len(values)
    return round(max(-1.0, min(1.0, avg / GROWTH_FULL_SCORE_THRESHOLD)), 4)


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
                log.debug("[CompanyGrowth] worker error for %s: %s", symbol, exc)
            _cache[symbol] = (datetime.now().strftime("%Y-%m-%d"), score)
            time.sleep(WORKER_THROTTLE_SECONDS)
    finally:
        _worker_running.clear()


def _ensure_worker_running() -> None:
    if not _worker_running.is_set():
        _worker_running.set()
        threading.Thread(target=_worker_loop, daemon=True, name="CompanyGrowthWorker").start()


def compute_company_growth_score(symbol: str) -> Optional[float]:
    """
    Return a mechanical growth score in [-1, +1] for *symbol*, or None
    if not yet available (either no real growth data exists, or the
    background fetch hasn't completed yet -- never a red flag; the
    normal state for a freshly-seen symbol on its first cycle).
    Never blocks the calling scan cycle. Never raises.
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
        log.debug("[CompanyGrowth] enqueue failed for %s: %s", symbol, exc)
    return None
