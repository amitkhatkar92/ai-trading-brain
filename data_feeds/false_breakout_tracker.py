"""
False Breakout Learning Memory
================================
Thread-safe in-memory accumulator for breakout failure telemetry.

Tracks:
    • Breakout invalidations per symbol / sector / failure reason
    • Quick breakdowns (invalidation within short window of signal)
    • Sector-level trap frequency

Emits:
    [FalseBreakoutLearning]  EOD summary of failure patterns

Governance constraint (strictly enforced):
    This module is **observational only**.
    It NEVER auto-disables strategies, NEVER mutates thresholds.
    All data is telemetry — not decision input.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import date
from typing import Dict, Optional

from utils.logger import get_logger

log = get_logger(__name__)


class FalseBreakoutTracker:
    """
    Per-session accumulator for breakout failure patterns.

    Thread-safe. Auto-resets at date rollover.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_date: date = date.today()
        self._do_reset(self._reset_date)

    def _do_reset(self, today: date) -> None:
        self._reset_date = today
        # symbol → count of invalidation events
        self._invalidation_count: Dict[str, int] = defaultdict(int)
        # symbol → list of failure reasons
        self._failure_reasons: Dict[str, list] = defaultdict(list)
        # sector → invalidation count
        self._sector_invalidations: Dict[str, int] = defaultdict(int)
        # failure_reason_type → count (e.g. "breakout_rsi_hi" → 12)
        self._reason_type_count: Dict[str, int] = defaultdict(int)
        # total events
        self._total_invalidations: int = 0

    def _ensure_today(self) -> None:
        today = date.today()
        if today != self._reset_date:
            with self._lock:
                if today != self._reset_date:
                    self._do_reset(today)

    def record_invalidation(
        self,
        symbol: str,
        failure_reason: str,
        sector: str = "",
    ) -> None:
        """Record one breakout invalidation event.

        Args:
            symbol:         Equity symbol, e.g. ``"RELIANCE"``
            failure_reason: Reason code from the invalidation engine
            sector:         Sector label if available
        """
        try:
            self._ensure_today()
            with self._lock:
                self._invalidation_count[symbol] += 1
                self._failure_reasons[symbol].append(failure_reason)
                self._reason_type_count[failure_reason] += 1
                self._total_invalidations += 1
                if sector:
                    self._sector_invalidations[sector] += 1
        except Exception:
            pass

    def emit_daily_summary(self) -> None:
        """Emit ``[FalseBreakoutLearning]`` EOD summary.  Called by orchestrator."""
        try:
            self._ensure_today()
            with self._lock:
                total      = self._total_invalidations
                reason_map = dict(self._reason_type_count)
                sector_map = dict(self._sector_invalidations)
                sym_count  = len(self._invalidation_count)

            if total == 0:
                log.info("[FalseBreakoutLearning] no_invalidations today.")
                return

            # Top 3 failure reasons
            top_reasons = sorted(reason_map.items(), key=lambda x: -x[1])[:3]
            top_reason_str = ", ".join(f"{r}:{c}" for r, c in top_reasons)

            # Top 2 sectors
            top_sectors = sorted(sector_map.items(), key=lambda x: -x[1])[:2]
            top_sector_str = ", ".join(f"{s}:{c}" for s, c in top_sectors)

            log.info(
                "[FalseBreakoutLearning] total_invalidations=%d "
                "symbols_affected=%d top_reasons=[%s] top_sectors=[%s]",
                total, sym_count, top_reason_str, top_sector_str,
            )
        except Exception:
            pass


# ── Singleton ────────────────────────────────────────────────────────────────

_FBT_INSTANCE: Optional[FalseBreakoutTracker] = None
_FBT_LOCK = threading.Lock()


def get_false_breakout_tracker() -> FalseBreakoutTracker:
    """Return the process-wide :class:`FalseBreakoutTracker` singleton (DCL)."""
    global _FBT_INSTANCE
    if _FBT_INSTANCE is None:
        with _FBT_LOCK:
            if _FBT_INSTANCE is None:
                _FBT_INSTANCE = FalseBreakoutTracker()
    return _FBT_INSTANCE
