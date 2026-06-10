"""
Data Integrity Tracker
======================
Thread-safe singleton for tracking historical data quality events per symbol.

Emits:
    [HistoricalDataIntegrity]  per corruption event (debug)
    [DataTrustScore]           EOD summary per symbol (info)
    [IndicatorSanityCheck]     when a cached indicator fails bounds validation (debug)

Governance constraint (strictly enforced):
    This module is **observational only**.
    It NEVER blocks execution, NEVER mutates thresholds, NEVER disables strategies.
    The DATA_UNTRUSTED flag is a telemetry label — not an execution gate.
"""
from __future__ import annotations

import threading
import math
from collections import defaultdict
from datetime import date
from typing import Dict, Optional, Set

from utils.logger import get_logger

log = get_logger(__name__)

# Corruption events required before a symbol is labelled DATA_UNTRUSTED
_UNTRUSTED_THRESHOLD: int = 3
# Trust score floor below which a symbol is also labelled DATA_UNTRUSTED
_TRUST_SCORE_FLOOR: float = 0.5
# How much each corruption event reduces the trust score
_CORRUPTION_PENALTY: float = 0.15
# How much each sanity-check failure reduces the trust score
_SANITY_PENALTY: float = 0.10
# How much each successful data refresh restores trust
_REFRESH_RECOVERY: float = 0.05


class DataIntegrityTracker:
    """
    Per-session accumulator for data quality events.

    Thread-safe. Auto-resets at date rollover (midnight).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_date: date = date.today()
        self._do_reset(self._reset_date)

    # ── Internal lifecycle ───────────────────────────────────────────────────

    def _do_reset(self, today: date) -> None:
        self._reset_date = today
        self._corruption_count: Dict[str, int] = defaultdict(int)
        self._corruption_reasons: Dict[str, list] = defaultdict(list)
        self._scalar_recovery_count: Dict[str, int] = defaultdict(int)
        self._sanity_fail_count: Dict[str, int] = defaultdict(int)
        self._refresh_success: Dict[str, int] = defaultdict(int)
        self._total_scalar_recoveries: int = 0
        self._total_corruptions: int = 0

    def _ensure_today(self) -> None:
        today = date.today()
        if today != self._reset_date:
            with self._lock:
                if today != self._reset_date:
                    self._do_reset(today)

    # ── Public API ───────────────────────────────────────────────────────────

    def record_corruption(
        self,
        symbol: str,
        indicator: str,
        corruption_type: str,
        fallback_used: bool = True,
    ) -> None:
        """Record one data corruption event for *symbol*.

        Args:
            symbol:          Equity symbol, e.g. ``"RELIANCE"``
            indicator:       Which indicator was corrupted, e.g. ``"close_price"``
            corruption_type: Nature of the corruption, e.g. ``"series_coercion"``
            fallback_used:   Whether a fallback value was successfully substituted
        """
        try:
            self._ensure_today()
            with self._lock:
                self._corruption_count[symbol] += 1
                self._corruption_reasons[symbol].append((indicator, corruption_type))
                if fallback_used:
                    self._scalar_recovery_count[symbol] += 1
                    self._total_scalar_recoveries += 1
                self._total_corruptions += 1
            log.debug(
                "[HistoricalDataIntegrity] symbol=%s indicator=%s "
                "corruption_type=%s fallback=%s total_for_symbol=%d",
                symbol, indicator, corruption_type,
                "yes" if fallback_used else "no",
                self._corruption_count[symbol],
            )
        except Exception:
            pass

    def record_sanity_fail(
        self,
        symbol: str,
        indicator: str,
        value: object,
        reason: str,
    ) -> None:
        """Record that a cached indicator value failed sanity bounds validation."""
        try:
            self._ensure_today()
            with self._lock:
                self._sanity_fail_count[symbol] += 1
            log.debug(
                "[IndicatorSanityCheck] symbol=%s indicator=%s value=%s reason=%s",
                symbol, indicator, value, reason,
            )
        except Exception:
            pass

    def record_refresh_success(self, symbol: str) -> None:
        """Record that a fresh data pull succeeded for *symbol*."""
        try:
            self._ensure_today()
            with self._lock:
                self._refresh_success[symbol] += 1
        except Exception:
            pass

    def get_trust_score(self, symbol: str) -> float:
        """Return data trust score ∈ [0.0, 1.0] for *symbol*.

        ``1.0`` = no observed corruption today.
        ``0.0`` = many corruption events — label as DATA_UNTRUSTED.

        Purely informational — does **not** block execution.
        """
        try:
            self._ensure_today()
            corruptions  = self._corruption_count.get(symbol, 0)
            sanity_fails = self._sanity_fail_count.get(symbol, 0)
            refreshes    = self._refresh_success.get(symbol, 0)
            score = 1.0
            score -= corruptions  * _CORRUPTION_PENALTY
            score -= sanity_fails * _SANITY_PENALTY
            score += refreshes    * _REFRESH_RECOVERY
            return max(0.0, min(1.0, score))
        except Exception:
            return 1.0

    def is_data_untrusted(self, symbol: str) -> bool:
        """Return ``True`` if *symbol* is labelled DATA_UNTRUSTED today.

        Governance: informational only — execution is never blocked.
        """
        try:
            self._ensure_today()
            return (
                self._corruption_count.get(symbol, 0) >= _UNTRUSTED_THRESHOLD
                or self.get_trust_score(symbol) < _TRUST_SCORE_FLOOR
            )
        except Exception:
            return False

    def get_untrusted_symbols(self) -> Set[str]:
        """Return the set of all DATA_UNTRUSTED symbols today."""
        try:
            self._ensure_today()
            with self._lock:
                syms = list(self._corruption_count.keys())
            return {s for s in syms if self.is_data_untrusted(s)}
        except Exception:
            return set()

    def get_scalar_recovery_count(self) -> int:
        """Total scalar-coercion recoveries this session."""
        try:
            self._ensure_today()
            return self._total_scalar_recoveries
        except Exception:
            return 0

    def get_total_corruptions(self) -> int:
        """Total corruption events this session."""
        try:
            self._ensure_today()
            return self._total_corruptions
        except Exception:
            return 0

    def emit_daily_summary(self) -> None:
        """Emit ``[DataTrustScore]`` summary.  Called at EOD by orchestrator."""
        try:
            self._ensure_today()
            with self._lock:
                symbols     = list(self._corruption_count.keys())
                total_corr  = self._total_corruptions
                total_rec   = self._total_scalar_recoveries

            if total_corr == 0 and total_rec == 0:
                log.info("[DataTrustScore] session_total: no corruption events observed.")
                return

            untrusted = self.get_untrusted_symbols()
            log.info(
                "[DataTrustScore] session_total: corruptions=%d "
                "scalar_recoveries=%d untrusted_symbols=%d",
                total_corr, total_rec, len(untrusted),
            )
            for sym in sorted(symbols):
                score   = self.get_trust_score(sym)
                corr    = self._corruption_count.get(sym, 0)
                reasons = self._corruption_reasons.get(sym, [])
                reason_str = "; ".join(
                    f"{ind}:{rtype}" for ind, rtype in reasons[:5]
                )
                log.info(
                    "[DataTrustScore] symbol=%s trust=%.2f corruptions=%d "
                    "untrusted=%s reasons=[%s]",
                    sym, score, corr,
                    "YES" if sym in untrusted else "no",
                    reason_str,
                )
        except Exception:
            pass


# ── Singleton ────────────────────────────────────────────────────────────────

_TRACKER_INSTANCE: Optional[DataIntegrityTracker] = None
_TRACKER_LOCK = threading.Lock()


def get_data_integrity_tracker() -> DataIntegrityTracker:
    """Return the process-wide :class:`DataIntegrityTracker` singleton (DCL)."""
    global _TRACKER_INSTANCE
    if _TRACKER_INSTANCE is None:
        with _TRACKER_LOCK:
            if _TRACKER_INSTANCE is None:
                _TRACKER_INSTANCE = DataIntegrityTracker()
    return _TRACKER_INSTANCE
