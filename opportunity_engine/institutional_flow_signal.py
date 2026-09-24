"""
opportunity_engine/institutional_flow_signal.py
===================================================
Self-learning module #30 (ACQUISITION) -- Positioning Intelligence.

Computes a per-symbol "institutional flow" score from REAL data already
collected by OIOS (never simulated -- confirmed during audit that
market_intelligence/market_data_ai.py's own FII/DII numbers are
`random.uniform(...)` placeholders, while OIOS's bulk_block_deals and
bhav_daily(delivery_pct) tables are populated from genuine NSE bulk/
block-deal filings and delivery data):

  bulk_signal      : net (BUY - SELL) bulk/block deal quantity over the
                      lookback window, normalised to [-1, +1] by total
                      deal quantity. Positive = net institutional
                      accumulation; negative = net distribution.
  delivery_signal   : recent average delivery_pct vs. the prior baseline
                      average, normalised to [-1, +1]. Rising delivery %
                      is a classic "genuine holding, not day-trading"
                      accumulation proxy.

Both are purely mechanical (no ML, no judgement) and computed from data
this system already owns -- no new external dependency. Returns None
whenever a symbol has no bulk/block deals AND no bhav delivery history
in the lookback window (the normal case for most symbols on most days
-- NOT a data-quality problem, so callers must treat None as "no
signal today", never as a red flag).

Zero effect on any live decision by itself. The value is attached to
TradeSignal as an OBSERVATIONAL field (institutional_flow_score /
institutional_flow_available, mirroring the existing price_is_live
pattern) and only ever influences KDA's authority score once
learning_system/institutional_flow_refinement_engine.py has validated
it against enough real trade outcomes -- fully automatic, no human
step, exactly like every other self-learning module built this
session.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

BULK_LOOKBACK_DAYS       = 30
DELIVERY_RECENT_DAYS     = 10
DELIVERY_BASELINE_DAYS   = 30
BULK_WEIGHT              = 0.6
DELIVERY_WEIGHT          = 0.4

# Day-scoped in-memory cache -- avoids hitting the OIOS SQLite DB on every
# single candidate evaluation within the same scan cycle/day. Cleared
# automatically once the date rolls over.
_cache: Dict[str, Tuple[str, Optional[float]]] = {}   # symbol -> (date_str, score)


def _strip_suffix(symbol: str) -> str:
    return symbol[:-3] if symbol.endswith(".NS") else symbol


def _bulk_signal(conn, symbol: str) -> Optional[float]:
    cutoff = (date.today() - timedelta(days=BULK_LOOKBACK_DAYS)).isoformat()
    try:
        rows = conn.execute(
            "SELECT buy_sell, quantity FROM bulk_block_deals "
            "WHERE symbol = ? AND trade_date >= ?",
            (symbol, cutoff),
        ).fetchall()
    except Exception as exc:
        log.debug("[InstitutionalFlow] bulk_block_deals query failed for %s: %s", symbol, exc)
        return None
    if not rows:
        return None
    net = 0.0
    total = 0.0
    for row in rows:
        qty = float(row["quantity"] or 0.0)
        total += qty
        if row["buy_sell"] == "B":
            net += qty
        elif row["buy_sell"] == "S":
            net -= qty
    if total <= 0:
        return None
    return max(-1.0, min(1.0, net / total))


def _delivery_signal(conn, symbol: str) -> Optional[float]:
    recent_cutoff = (date.today() - timedelta(days=DELIVERY_RECENT_DAYS)).isoformat()
    baseline_cutoff = (date.today() - timedelta(days=DELIVERY_BASELINE_DAYS)).isoformat()
    try:
        recent_rows = conn.execute(
            "SELECT delivery_pct FROM bhav_daily "
            "WHERE symbol = ? AND trade_date >= ? AND delivery_pct IS NOT NULL",
            (symbol, recent_cutoff),
        ).fetchall()
        baseline_rows = conn.execute(
            "SELECT delivery_pct FROM bhav_daily "
            "WHERE symbol = ? AND trade_date >= ? AND trade_date < ? AND delivery_pct IS NOT NULL",
            (symbol, baseline_cutoff, recent_cutoff),
        ).fetchall()
    except Exception as exc:
        log.debug("[InstitutionalFlow] bhav_daily query failed for %s: %s", symbol, exc)
        return None
    if not recent_rows or not baseline_rows:
        return None
    recent_avg = sum(float(r["delivery_pct"]) for r in recent_rows) / len(recent_rows)
    baseline_avg = sum(float(r["delivery_pct"]) for r in baseline_rows) / len(baseline_rows)
    if baseline_avg <= 0:
        return None
    diff = (recent_avg - baseline_avg) / baseline_avg
    return max(-1.0, min(1.0, diff))


def _compute_uncached(symbol: str) -> Optional[float]:
    try:
        from oios.db.connection import get_connection
    except Exception as exc:
        log.debug("[InstitutionalFlow] OIOS db unavailable: %s", exc)
        return None

    bare_symbol = _strip_suffix(symbol)
    conn = None
    try:
        conn = get_connection()
        bulk = _bulk_signal(conn, bare_symbol)
        delivery = _delivery_signal(conn, bare_symbol)
    except Exception as exc:
        log.debug("[InstitutionalFlow] compute failed for %s: %s", symbol, exc)
        return None
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    if bulk is None and delivery is None:
        return None
    if bulk is not None and delivery is not None:
        return round(BULK_WEIGHT * bulk + DELIVERY_WEIGHT * delivery, 4)
    if bulk is not None:
        return round(bulk, 4)
    return round(delivery, 4)


def compute_institutional_flow_score(symbol: str) -> Optional[float]:
    """
    Return a mechanical institutional-flow score in [-1, +1] for *symbol*,
    or None if neither bulk/block deal data nor bhav delivery-% history
    exists for it in the lookback window (the normal case for most
    symbols most days). Day-scoped cached -- computed at most once per
    symbol per calendar day. Never raises.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    cached = _cache.get(symbol)
    if cached is not None and cached[0] == today_str:
        return cached[1]
    try:
        score = _compute_uncached(symbol)
    except Exception as exc:
        log.debug("[InstitutionalFlow] unexpected error for %s: %s", symbol, exc)
        score = None
    _cache[symbol] = (today_str, score)
    return score
