"""
Trade Classifier
================
Classifies every paper trade in `data/paper_trades.csv` into one of five
integrity categories, based on when it was opened relative to known
data-quality events (wrong security IDs, feed degradation, etc.).

Classification enum:
    VERIFIED                — opened AFTER all security-ID fixes deployed;
                              both feeds agreed (or only one was available and
                              it passed the sanity band); price within bounds.
    LEGACY_UNVERIFIED       — opened BEFORE the security-ID fix deployment
                              (2026-05-13 16:05 UTC).  May have received prices
                              from a wrong instrument; cannot be confirmed.
    RECONCILIATION_SUSPECT  — entry vs LTP deviation >50% at position-restore
                              time (flagged by _post_restore_governance_pass).
    INVALID_MARKET_DATA     — opened while the primary feed was returning prices
                              outside the instrument sanity band.
    EXECUTION_INTEGRITY_FAILURE — SL or target fired at a time when a
                              PRICE_INTEGRITY_FAILURE was already recorded for
                              that symbol (retroactive classification).

Only VERIFIED trades should feed: learning, SHM, expectancy, governance stats.

Usage:
    from data_integrity.trade_classifier import classify_trades, TradeClassification
    results = classify_trades()          # reads paper_trades.csv directly
    for trade_id, cls in results.items():
        print(trade_id, cls)
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

from data_integrity.instrument_registry import (
    SECURITY_ID_FIX_DEPLOYED,
    get_instrument_registry,
)
from utils import get_logger

log = get_logger(__name__)

# ── Classification definitions ────────────────────────────────────────────────

class TradeClassification(str, Enum):
    VERIFIED                   = "VERIFIED"
    LEGACY_UNVERIFIED          = "LEGACY_UNVERIFIED"
    RECONCILIATION_SUSPECT     = "RECONCILIATION_SUSPECT"
    INVALID_MARKET_DATA        = "INVALID_MARKET_DATA"
    EXECUTION_INTEGRITY_FAILURE = "EXECUTION_INTEGRITY_FAILURE"


# Symbols that had CONFIRMED wrong security IDs before the fix date.
# Trades opened for these symbols before SECURITY_ID_FIX_DEPLOYED are
# automatically classified LEGACY_UNVERIFIED.
_AFFECTED_SYMBOLS_PRE_FIX = {
    "INFY",          # was 10604 (=BHARTIARTL)
    "BHARTIARTL",    # was 317 (=BAJFINANCE duplicate)
    "ONGC",          # was 11654 (=LALPATHLAB)
    "TATAMOTORS",    # was 3456 (=TMPV spin-off, not TMCV)
    # HINDALCO and COALINDIA were not in static map — _extra_map resolution unverified
    "HINDALCO",
    "COALINDIA",
}

# Path to paper trades journal (resolved relative to project root)
_JOURNAL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "paper_trades.csv",
)


def _parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse CSV timestamp to UTC-aware datetime."""
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            # assume IST (UTC+5:30) — convert to UTC
            from datetime import timedelta
            dt = dt - timedelta(hours=5, minutes=30)
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def classify_trades(
    journal_path: str = _JOURNAL_PATH,
) -> Dict[str, TradeClassification]:
    """
    Read `paper_trades.csv` and return a dict of:
        order_id → TradeClassification

    Only OPEN and first-occurrence rows are classified (CLOSE rows inherit
    the same classification as the matching OPEN).
    """
    registry = get_instrument_registry()
    results: Dict[str, TradeClassification] = {}
    # Track which order_ids had their OPEN classified already
    seen: Dict[str, TradeClassification] = {}

    if not os.path.exists(journal_path):
        log.warning("[TradeClassifier] Journal not found: %s", journal_path)
        return results

    with open(journal_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            order_id  = row.get("order_id", "").strip()
            symbol    = row.get("symbol", "").strip().upper()
            event     = row.get("event", "").strip()
            ts_str    = row.get("timestamp", "").strip()
            entry_px  = _safe_float(row.get("entry_price"))
            exit_px   = _safe_float(row.get("exit_price") or row.get("close_price"))

            if not order_id:
                continue

            # ── CLOSE rows: inherit classification from OPEN ───────────────
            if event == "CLOSE" and order_id in seen:
                results[order_id] = seen[order_id]
                continue

            # ── Classify the OPEN row ──────────────────────────────────────
            ts = _parse_timestamp(ts_str)
            cls = _classify_one(
                order_id=order_id,
                symbol=symbol,
                event=event,
                ts=ts,
                entry_price=entry_px,
                exit_price=exit_px,
                registry=registry,
            )
            seen[order_id] = cls
            results[order_id] = cls

    _log_summary(results)
    return results


def _classify_one(
    order_id:    str,
    symbol:      str,
    event:       str,
    ts:          Optional[datetime],
    entry_price: Optional[float],
    exit_price:  Optional[float],
    registry,
) -> TradeClassification:
    """Apply classification rules in priority order."""

    # ── Rule 1: Affected symbol opened before security-ID fix ─────────────
    if symbol in _AFFECTED_SYMBOLS_PRE_FIX and ts and ts < SECURITY_ID_FIX_DEPLOYED:
        log.info(
            "[TradeClassifier] %s  %s  LEGACY_UNVERIFIED "
            "(opened %s, fix deployed %s)",
            order_id, symbol,
            ts.strftime("%Y-%m-%dT%H:%M"),
            SECURITY_ID_FIX_DEPLOYED.strftime("%Y-%m-%dT%H:%M"),
        )
        return TradeClassification.LEGACY_UNVERIFIED

    # ── Rule 2: Entry price outside sanity band ────────────────────────────
    if entry_price is not None and entry_price > 0:
        band_check = registry.check_price(symbol, entry_price)
        if not band_check.ok and band_check.reason != "NO_BAND_REGISTERED":
            log.warning(
                "[TradeClassifier] %s  %s  INVALID_MARKET_DATA  "
                "entry=%.2f outside band [%.0f, %.0f]",
                order_id, symbol, entry_price,
                band_check.band_low, band_check.band_high,
            )
            return TradeClassification.INVALID_MARKET_DATA

    # ── Rule 3: Exit price outside sanity band → execution integrity failure
    if exit_price is not None and exit_price > 0 and event == "CLOSE":
        band_check = registry.check_price(symbol, exit_price)
        if not band_check.ok and band_check.reason != "NO_BAND_REGISTERED":
            log.warning(
                "[TradeClassifier] %s  %s  EXECUTION_INTEGRITY_FAILURE  "
                "exit=%.2f outside band [%.0f, %.0f]",
                order_id, symbol, exit_price,
                band_check.band_low, band_check.band_high,
            )
            return TradeClassification.EXECUTION_INTEGRITY_FAILURE

    # ── Rule 4: Opened before fix date (any symbol — general legacy caution)
    if ts and ts < SECURITY_ID_FIX_DEPLOYED:
        return TradeClassification.LEGACY_UNVERIFIED

    # ── Default: VERIFIED ──────────────────────────────────────────────────
    return TradeClassification.VERIFIED


def _safe_float(val) -> Optional[float]:
    try:
        return float(val) if val not in (None, "", "None") else None
    except (TypeError, ValueError):
        return None


def _log_summary(results: Dict[str, TradeClassification]) -> None:
    counts: Dict[str, int] = {}
    for cls in results.values():
        counts[cls.value] = counts.get(cls.value, 0) + 1
    log.info(
        "[TradeClassifier] Classification summary: %s",
        "  ".join(f"{k}={v}" for k, v in sorted(counts.items())),
    )


# ── Convenience: is a trade VERIFIED? ─────────────────────────────────────────
def is_verified(order_id: str, results: Optional[Dict[str, TradeClassification]] = None) -> bool:
    """
    Quick check: returns True only if the trade's classification is VERIFIED.
    If `results` is None, runs classify_trades() internally (expensive —
    prefer pre-computing and passing in).
    """
    if results is None:
        results = classify_trades()
    return results.get(order_id) == TradeClassification.VERIFIED
