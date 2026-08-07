"""
production_readiness/ph3_signal_freshness.py — Phase 3: Signal Freshness.

Assigns freshness status to every TradeSignal based on its age in trading days.

Thresholds:
    0–5  trading days → FRESH (no restriction)
    6–15 trading days → WEAKENING (warn but allow)
    15+  trading days → EXPIRED (must not enter execution)

Trading days ≈ calendar days × 5/7 (ignoring bank holidays — conservative).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

from .prr_config import (
    FRESHNESS_FRESH_MAX_DAYS,
    FRESHNESS_STATUS_EXPIRED,
    FRESHNESS_STATUS_FRESH,
    FRESHNESS_STATUS_WEAKENING,
    FRESHNESS_WEAKENING_MAX_DAYS,
)
from .prr_models import FreshnessResult, SignalFreshnessReport

if TYPE_CHECKING:
    from models.trade_signal import TradeSignal

log = logging.getLogger(__name__)

_CALENDAR_TO_TRADING = 5.0 / 7.0


def calendar_days_to_trading(calendar_days: float) -> float:
    """Approximate calendar days → trading days conversion."""
    return calendar_days * _CALENDAR_TO_TRADING


def compute_freshness(
    signal_ts: datetime,
    symbol: str = "",
    now: Optional[datetime] = None,
) -> FreshnessResult:
    """
    Compute freshness status for a signal created at signal_ts.
    Uses UTC-aware comparison when signal_ts is timezone-aware.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Make both timestamps comparable
    if signal_ts.tzinfo is None:
        signal_ts = signal_ts.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    calendar_days = (now - signal_ts).total_seconds() / 86400.0
    trading_days  = calendar_days_to_trading(calendar_days)

    if trading_days <= FRESHNESS_FRESH_MAX_DAYS:
        status     = FRESHNESS_STATUS_FRESH
        score      = 1.0 - (trading_days / FRESHNESS_FRESH_MAX_DAYS) * 0.20
        is_expired = False
        reason     = f"Signal is {trading_days:.1f} trading days old — FRESH"
    elif trading_days <= FRESHNESS_WEAKENING_MAX_DAYS:
        status     = FRESHNESS_STATUS_WEAKENING
        progress   = (trading_days - FRESHNESS_FRESH_MAX_DAYS) / (
            FRESHNESS_WEAKENING_MAX_DAYS - FRESHNESS_FRESH_MAX_DAYS
        )
        score      = 0.80 - progress * 0.40    # 0.80 → 0.40 over WEAKENING range
        is_expired = False
        reason     = (
            f"Signal is {trading_days:.1f} trading days old — WEAKENING, "
            f"entry thesis may have changed"
        )
    else:
        status     = FRESHNESS_STATUS_EXPIRED
        score      = 0.0
        is_expired = True
        reason     = (
            f"Signal is {trading_days:.1f} trading days old — EXPIRED. "
            f"Blocked from execution per PRR-001 Phase 3 rule."
        )

    return FreshnessResult(
        symbol=symbol,
        signal_ts=signal_ts.isoformat(),
        age_trading_days=round(trading_days, 2),
        freshness_score=round(score, 3),
        freshness_status=status,
        is_expired=is_expired,
        reason=reason,
    )


def is_signal_expired(signal: "TradeSignal") -> bool:
    """
    Gate function called by OrderManager before placing any order.
    Returns True if the signal must NOT be executed.
    """
    ts = getattr(signal, "timestamp", None)
    if ts is None:
        return False    # no timestamp — do not block (safe default)
    try:
        result = compute_freshness(ts, symbol=getattr(signal, "symbol", ""))
        if result.is_expired:
            log.warning(
                "[SignalFreshness] BLOCKING execution for %s — signal age=%.1f trading days "
                "(status=%s): %s",
                result.symbol, result.age_trading_days, result.freshness_status, result.reason,
            )
            return True
        if result.freshness_status == FRESHNESS_STATUS_WEAKENING:
            log.info(
                "[SignalFreshness] WEAKENING signal %s — age=%.1f trading days (not blocked)",
                result.symbol, result.age_trading_days,
            )
        return False
    except Exception as e:
        log.debug("[SignalFreshness] Cannot evaluate signal freshness: %s", e)
        return False


def build_freshness_report(
    signals: list,
    today: Optional[str] = None,
) -> SignalFreshnessReport:
    """Build an aggregated freshness report from a list of TradeSignal objects."""
    today = today or datetime.now().date().isoformat()
    details: list = []
    fresh_n = weakening_n = expired_n = blocked_n = 0
    oldest_blocked = 0.0

    for sig in signals:
        ts = getattr(sig, "timestamp", None)
        if ts is None:
            continue
        result = compute_freshness(ts, symbol=getattr(sig, "symbol", ""))
        details.append(result)
        if result.freshness_status == FRESHNESS_STATUS_FRESH:
            fresh_n += 1
        elif result.freshness_status == FRESHNESS_STATUS_WEAKENING:
            weakening_n += 1
        else:
            expired_n += 1
            blocked_n += 1
            oldest_blocked = max(oldest_blocked, result.age_trading_days)

    return SignalFreshnessReport(
        date=today,
        signals_checked=len(details),
        fresh=fresh_n,
        weakening=weakening_n,
        expired=expired_n,
        blocked_for_execution=blocked_n,
        oldest_blocked_days=oldest_blocked,
        details=details,
    )
