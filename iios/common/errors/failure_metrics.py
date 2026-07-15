"""iios/common/errors/failure_metrics.py
Failure and recovery metrics tracking for the IIOS platform.

Tracks per-engine and platform-wide:
  • Failure count
  • Recovery count (and success/failure split)
  • Retry count
  • Recovery success rate
  • Mean Time To Recovery (MTTR)
  • Sliding-window failure trends

Thread-safe via RLock.

Usage::

    from iios.common.errors.failure_metrics import FailureTracker, get_failure_tracker

    tracker = get_failure_tracker()
    tracker.record_failure("iios:market:integration", ValueError)
    tracker.record_retry("iios:market:integration")
    tracker.record_recovery("iios:market:integration", recovery_time_sec=1.2, succeeded=True)

    snap = tracker.snapshot()
    print(snap.recovery_success_rate)   # e.g. 0.92
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional, Tuple, Type


# ── Per-engine counters ───────────────────────────────────────────────────────

@dataclass
class _EngineCounters:
    """Mutable per-engine metric accumulators."""

    failures:         int       = 0
    recoveries:       int       = 0
    recovery_successes: int     = 0
    retries:          int       = 0
    total_recovery_sec: float   = 0.0
    # Ring buffer of (epoch_float, failure) tuples for trend analysis
    failure_timestamps: Deque[float] = field(default_factory=lambda: deque(maxlen=1000))


# ── Snapshots ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EngineMetricsSnapshot:
    """Immutable point-in-time metrics snapshot for one engine."""

    engine_id:             str
    failures:              int
    recoveries:            int
    recovery_successes:    int
    recovery_failures:     int
    retries:               int
    recovery_success_rate: float    # 0.0 – 1.0
    mean_time_to_recovery: float    # seconds; 0.0 if no recoveries
    snapshot_time:         datetime


@dataclass(frozen=True)
class FailureMetricsSnapshot:
    """Immutable platform-wide metrics snapshot."""

    total_failures:              int
    total_recoveries:            int
    total_recovery_successes:    int
    total_recovery_failures:     int
    total_retries:               int
    recovery_success_rate:       float
    mean_time_to_recovery:       float
    engines:                     Dict[str, EngineMetricsSnapshot]
    snapshot_time:               datetime


# ── Failure trend entry ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class FailureTrendEntry:
    """A single bucket in a failure trend time-series."""

    window_start: datetime
    window_end:   datetime
    failure_count: int
    engine_id:    str = ""   # empty = platform-wide


# ── FailureTracker ────────────────────────────────────────────────────────────

class FailureTracker:
    """
    Thread-safe failure and recovery metrics tracker.

    Maintains per-engine counters and a platform-wide aggregate.
    All mutation is serialized with an RLock to guarantee consistency
    across threads.
    """

    def __init__(self) -> None:
        self._lock:    threading.RLock                 = threading.RLock()
        self._engines: Dict[str, _EngineCounters]      = defaultdict(_EngineCounters)

    # ── Recording API ─────────────────────────────────────────────────────────

    def record_failure(
        self,
        engine_id: str,
        exc_type:  Optional[Type[BaseException]] = None,
    ) -> None:
        """
        Record that an error occurred in *engine_id*.

        :param engine_id: Identifies the reporting engine.
        :param exc_type:  Optional exception class for future categorization.
        """
        with self._lock:
            c = self._engines[engine_id]
            c.failures += 1
            c.failure_timestamps.append(time.time())

    def record_recovery(
        self,
        engine_id:          str,
        recovery_time_sec:  float,
        *,
        succeeded:          bool = True,
    ) -> None:
        """
        Record a recovery attempt for *engine_id*.

        :param recovery_time_sec: Wall time spent in the recovery operation.
        :param succeeded:         Whether recovery ultimately succeeded.
        """
        with self._lock:
            c = self._engines[engine_id]
            c.recoveries += 1
            if succeeded:
                c.recovery_successes += 1
                c.total_recovery_sec += recovery_time_sec

    def record_retry(self, engine_id: str) -> None:
        """Record a single retry attempt for *engine_id*."""
        with self._lock:
            self._engines[engine_id].retries += 1

    # ── Snapshot API ──────────────────────────────────────────────────────────

    def snapshot(self) -> FailureMetricsSnapshot:
        """Return an immutable platform-wide metrics snapshot."""
        with self._lock:
            engine_snaps: Dict[str, EngineMetricsSnapshot] = {}
            for eng_id, c in self._engines.items():
                engine_snaps[eng_id] = self._engine_snapshot(eng_id, c)

            total_failures   = sum(c.failures         for c in self._engines.values())
            total_recoveries = sum(c.recoveries        for c in self._engines.values())
            total_successes  = sum(c.recovery_successes for c in self._engines.values())
            total_retries    = sum(c.retries           for c in self._engines.values())
            total_rec_sec    = sum(c.total_recovery_sec for c in self._engines.values())

            rate = total_successes / total_recoveries if total_recoveries > 0 else 0.0
            mttr = total_rec_sec / total_successes    if total_successes > 0   else 0.0

            return FailureMetricsSnapshot(
                total_failures           = total_failures,
                total_recoveries         = total_recoveries,
                total_recovery_successes = total_successes,
                total_recovery_failures  = total_recoveries - total_successes,
                total_retries            = total_retries,
                recovery_success_rate    = round(rate, 4),
                mean_time_to_recovery    = round(mttr, 4),
                engines                  = engine_snaps,
                snapshot_time            = datetime.now(timezone.utc),
            )

    def engine_snapshot(self, engine_id: str) -> Optional[EngineMetricsSnapshot]:
        """Return a metrics snapshot for a specific engine, or None if unknown."""
        with self._lock:
            if engine_id not in self._engines:
                return None
            return self._engine_snapshot(engine_id, self._engines[engine_id])

    def failure_trend(
        self,
        engine_id:  str = "",
        window_sec: float = 60.0,
        buckets:    int = 10,
    ) -> List[FailureTrendEntry]:
        """
        Return a bucketed failure trend over the last *window_sec* seconds.

        :param engine_id:  If non-empty, filter to a specific engine.
                           If empty, aggregate all engines.
        :param window_sec: Total time window in seconds.
        :param buckets:    Number of equal-width time buckets.
        :returns:          List of FailureTrendEntry, oldest first.
        """
        now = time.time()
        bucket_size = window_sec / max(buckets, 1)
        window_start = now - window_sec

        # Collect relevant timestamps
        with self._lock:
            if engine_id:
                if engine_id not in self._engines:
                    return []
                all_ts = [ts for ts in self._engines[engine_id].failure_timestamps
                          if ts >= window_start]
                tag = engine_id
            else:
                all_ts = [
                    ts
                    for c in self._engines.values()
                    for ts in c.failure_timestamps
                    if ts >= window_start
                ]
                tag = ""

        counts: List[int] = [0] * buckets
        for ts in all_ts:
            bucket_idx = min(int((ts - window_start) / bucket_size), buckets - 1)
            counts[bucket_idx] += 1

        trend: List[FailureTrendEntry] = []
        for i, cnt in enumerate(counts):
            b_start = window_start + i * bucket_size
            b_end   = b_start + bucket_size
            trend.append(FailureTrendEntry(
                window_start  = datetime.fromtimestamp(b_start, tz=timezone.utc),
                window_end    = datetime.fromtimestamp(b_end,   tz=timezone.utc),
                failure_count = cnt,
                engine_id     = tag,
            ))
        return trend

    def reset(self, engine_id: str = "") -> None:
        """
        Reset counters.

        :param engine_id: If non-empty, reset only that engine.
                          If empty, reset the entire platform.
        """
        with self._lock:
            if engine_id:
                if engine_id in self._engines:
                    self._engines[engine_id] = _EngineCounters()
            else:
                self._engines.clear()

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _engine_snapshot(self, eng_id: str, c: _EngineCounters) -> EngineMetricsSnapshot:
        recovery_failures = c.recoveries - c.recovery_successes
        rate = c.recovery_successes / c.recoveries if c.recoveries > 0 else 0.0
        mttr = c.total_recovery_sec / c.recovery_successes if c.recovery_successes > 0 else 0.0
        return EngineMetricsSnapshot(
            engine_id             = eng_id,
            failures              = c.failures,
            recoveries            = c.recoveries,
            recovery_successes    = c.recovery_successes,
            recovery_failures     = recovery_failures,
            retries               = c.retries,
            recovery_success_rate = round(rate, 4),
            mean_time_to_recovery = round(mttr, 4),
            snapshot_time         = datetime.now(timezone.utc),
        )


# ── Module-level singleton ────────────────────────────────────────────────────

_singleton_lock:   threading.Lock     = threading.Lock()
_singleton:        Optional[FailureTracker] = None


def get_failure_tracker() -> FailureTracker:
    """
    Return the platform-wide singleton FailureTracker.

    Thread-safe; creates on first call.
    """
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = FailureTracker()
    return _singleton


def reset_failure_tracker() -> None:
    """
    Replace the singleton with a fresh instance.

    Intended for test isolation only — never call in production.
    """
    global _singleton
    with _singleton_lock:
        _singleton = FailureTracker()
