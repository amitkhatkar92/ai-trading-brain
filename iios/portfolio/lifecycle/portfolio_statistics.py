"""
portfolio_statistics.py — iios.portfolio.lifecycle
====================================================
Thread-safe accumulation of portfolio lifecycle statistics.

C10 Portfolio Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict

# EMA smoothing factor — lower = smoother
_EMA_ALPHA = 0.1


class PortfolioStatistics:
    """
    Thread-safe accumulator for portfolio lifecycle statistics.

    All counters start at zero and increment monotonically.
    Duration statistics are maintained via an exponential moving average.

    Usage
    -----
    ::

        stats = PortfolioStatistics()
        stats.record_session_created()
        stats.record_session_completed(duration_s=120.0)
        snap = stats.snapshot()
    """

    def __init__(self) -> None:
        self._lock              = threading.Lock()
        self._created:   int    = 0
        self._completed: int    = 0
        self._failed:    int    = 0
        self._archived:  int    = 0
        self._transitions: int  = 0
        self._total_duration: float    = 0.0
        self._completed_with_dur: int  = 0
        self._ema_duration: float      = 0.0
        self._started_at: float        = time.time()

    # ------------------------------------------------------------------
    # Recorders
    # ------------------------------------------------------------------

    def record_session_created(self) -> None:
        with self._lock:
            self._created += 1

    def record_session_completed(self, duration_s: float = 0.0) -> None:
        with self._lock:
            self._completed += 1
            if duration_s > 0.0:
                self._total_duration      += duration_s
                self._completed_with_dur  += 1
                if self._ema_duration == 0.0:
                    self._ema_duration = duration_s
                else:
                    self._ema_duration = (
                        _EMA_ALPHA * duration_s
                        + (1.0 - _EMA_ALPHA) * self._ema_duration
                    )

    def record_session_failed(self) -> None:
        with self._lock:
            self._failed += 1

    def record_session_archived(self) -> None:
        with self._lock:
            self._archived += 1

    def record_transition(self) -> None:
        with self._lock:
            self._transitions += 1

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """
        Return an immutable snapshot of all current statistics.

        Keys
        ----
        portfolio_sessions_created :    Total sessions created.
        portfolio_sessions_completed :  Total sessions completed.
        portfolio_sessions_failed :     Total sessions failed.
        portfolio_sessions_archived :   Total sessions archived.
        transition_count :              Total state transitions applied.
        average_session_duration_s :    Arithmetic mean (0.0 if none).
        ema_session_duration_s :        EMA-smoothed session duration.
        uptime_s :                      Service uptime in seconds.
        """
        with self._lock:
            avg = (
                self._total_duration / self._completed_with_dur
                if self._completed_with_dur > 0
                else 0.0
            )
            return {
                "portfolio_sessions_created":    self._created,
                "portfolio_sessions_completed":  self._completed,
                "portfolio_sessions_failed":     self._failed,
                "portfolio_sessions_archived":   self._archived,
                "transition_count":              self._transitions,
                "average_session_duration_s":    avg,
                "ema_session_duration_s":        self._ema_duration,
                "uptime_s":                      time.time() - self._started_at,
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._created            = 0
            self._completed          = 0
            self._failed             = 0
            self._archived           = 0
            self._transitions        = 0
            self._total_duration     = 0.0
            self._completed_with_dur = 0
            self._ema_duration       = 0.0
            self._started_at         = time.time()
