"""
decision_statistics.py — iios.decision.lifecycle
==================================================
Thread-safe statistics container for the Decision Lifecycle subsystem.

Tracks the six counters mandated by the specification.

C9 Decision Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class DecisionStatistics:
    """
    Thread-safe statistics for the decision lifecycle subsystem.

    Six tracked metrics
    -------------------
    1. **Decision Sessions Created**    — cumulative sessions created.
    2. **Decision Sessions Completed**  — cumulative successful completions.
    3. **Decision Sessions Failed**     — cumulative failures.
    4. **Decision Sessions Archived**   — cumulative archives.
    5. **Average Session Duration (s)** — EMA of completed session durations.
    6. **Transition Count**             — cumulative state transitions executed.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

        self._sessions_created:   int   = 0
        self._sessions_completed: int   = 0
        self._sessions_failed:    int   = 0
        self._sessions_archived:  int   = 0
        self._transition_count:   int   = 0

        # Exponential moving average for session duration (α = 0.1)
        self._avg_duration_s: float = 0.0
        self._ema_alpha:      float = 0.1

        self._created_at: float = time.time()

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------
    def record_session_created(self) -> None:
        with self._lock:
            self._sessions_created += 1

    def record_session_completed(self, duration_s: float) -> None:
        """Record a completion and update the rolling average duration."""
        with self._lock:
            self._sessions_completed += 1
            if self._avg_duration_s == 0.0:
                self._avg_duration_s = duration_s
            else:
                self._avg_duration_s = (
                    self._ema_alpha * duration_s
                    + (1.0 - self._ema_alpha) * self._avg_duration_s
                )

    def record_session_failed(self) -> None:
        with self._lock:
            self._sessions_failed += 1

    def record_session_archived(self) -> None:
        with self._lock:
            self._sessions_archived += 1

    def record_transition(self) -> None:
        """Increment the transition counter by one."""
        with self._lock:
            self._transition_count += 1

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def sessions_created(self) -> int:
        with self._lock:
            return self._sessions_created

    @property
    def sessions_completed(self) -> int:
        with self._lock:
            return self._sessions_completed

    @property
    def sessions_failed(self) -> int:
        with self._lock:
            return self._sessions_failed

    @property
    def sessions_archived(self) -> int:
        with self._lock:
            return self._sessions_archived

    @property
    def average_session_duration_s(self) -> float:
        """EMA of completed session durations in seconds."""
        with self._lock:
            return self._avg_duration_s

    @property
    def transition_count(self) -> int:
        with self._lock:
            return self._transition_count

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """Return a plain-dict snapshot of all counters."""
        with self._lock:
            return {
                "sessions_created":          self._sessions_created,
                "sessions_completed":        self._sessions_completed,
                "sessions_failed":           self._sessions_failed,
                "sessions_archived":         self._sessions_archived,
                "average_session_duration_s": self._avg_duration_s,
                "transition_count":          self._transition_count,
            }

    def reset(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self._sessions_created   = 0
            self._sessions_completed = 0
            self._sessions_failed    = 0
            self._sessions_archived  = 0
            self._transition_count   = 0
            self._avg_duration_s     = 0.0
            self._created_at         = time.time()

    def __repr__(self) -> str:
        s = self.snapshot()
        return (
            f"DecisionStatistics("
            f"created={s['sessions_created']}, "
            f"completed={s['sessions_completed']}, "
            f"failed={s['sessions_failed']}, "
            f"archived={s['sessions_archived']}, "
            f"transitions={s['transition_count']}, "
            f"avg_duration={s['average_session_duration_s']:.3f}s)"
        )
