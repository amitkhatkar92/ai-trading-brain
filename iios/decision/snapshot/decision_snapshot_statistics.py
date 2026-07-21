"""
decision_snapshot_statistics.py — iios.decision.snapshot
=========================================================
Thread-safe runtime statistics for the Decision Snapshot subsystem.

Seven counters (matching the spec)
-----------------------------------
1. snapshots_created    — total snapshots built
2. snapshots_published  — total snapshots published
3. snapshots_archived   — total snapshots archived
4. validation_success   — total passed validations
5. validation_failure   — total failed validations
6. average_build_time_s — EMA of build wall-clock time
7. average_snapshot_size— EMA of serialized snapshot byte size

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque

from .constants import EMA_ALPHA, THROUGHPUT_WINDOW_S


class DecisionSnapshotStatistics:
    """Thread-safe runtime statistics for the snapshot subsystem."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

        self._created    = 0
        self._published  = 0
        self._archived   = 0
        self._val_ok     = 0
        self._val_fail   = 0

        self._avg_build  = 0.0
        self._avg_size   = 0.0

        self._window: Deque[float] = deque()

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def record_snapshot_created(
        self,
        *,
        build_time_s:    float = 0.0,
        snapshot_size:   int   = 0,
    ) -> None:
        with self._lock:
            self._created   += 1
            self._avg_build  = EMA_ALPHA * build_time_s  + (1.0 - EMA_ALPHA) * self._avg_build
            self._avg_size   = EMA_ALPHA * snapshot_size + (1.0 - EMA_ALPHA) * self._avg_size
            now = time.monotonic()
            self._window.append(now)
            cutoff = now - THROUGHPUT_WINDOW_S
            while self._window and self._window[0] < cutoff:
                self._window.popleft()

    def record_snapshot_validated(self, *, success: bool) -> None:
        with self._lock:
            if success:
                self._val_ok += 1
            else:
                self._val_fail += 1

    def record_snapshot_published(self) -> None:
        with self._lock:
            self._published += 1

    def record_snapshot_archived(self) -> None:
        with self._lock:
            self._archived += 1

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        with self._lock:
            total_val = self._val_ok + self._val_fail
            return {
                "snapshots_created":     self._created,
                "snapshots_published":   self._published,
                "snapshots_archived":    self._archived,
                "validation_success":    self._val_ok,
                "validation_failure":    self._val_fail,
                "validation_success_rate": (
                    self._val_ok / total_val if total_val else 0.0
                ),
                "average_build_time_s":  self._avg_build,
                "average_snapshot_size": self._avg_size,
                "snapshot_throughput":   len(self._window),
            }

    def reset(self) -> None:
        with self._lock:
            self._created   = 0
            self._published = 0
            self._archived  = 0
            self._val_ok    = 0
            self._val_fail  = 0
            self._avg_build = 0.0
            self._avg_size  = 0.0
            self._window.clear()
