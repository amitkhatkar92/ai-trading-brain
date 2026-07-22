"""
risk_statistics.py — iios.risk.engine
========================================
Thread-safe atomic counters and derived metrics for the Risk Engine.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class RiskEngineStatistics:
    """
    Thread-safe statistics accumulator for the Risk Engine.

    All ``record_*`` methods are safe to call from any thread.
    :meth:`snapshot` returns a frozen copy.

    Metrics tracked
    ---------------
    - sessions_created
    - sessions_completed
    - sessions_failed
    - requests_submitted
    - requests_completed
    - requests_failed
    - pipelines_started
    - pipelines_completed
    - pipelines_failed
    - snapshots_published
    - avg_assessment_time_s  (running mean)
    - avg_dispatch_time_s    (running mean)
    - throughput_per_min     (approximation over last minute)
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

        # Sessions
        self._sessions_created   = 0
        self._sessions_completed = 0
        self._sessions_failed    = 0

        # Requests
        self._requests_submitted = 0
        self._requests_completed = 0
        self._requests_failed    = 0

        # Pipelines
        self._pipelines_started   = 0
        self._pipelines_completed = 0
        self._pipelines_failed    = 0

        # Snapshots
        self._snapshots_published = 0

        # Timing (Welford online mean)
        self._assess_count = 0
        self._assess_mean  = 0.0
        self._dispatch_count = 0
        self._dispatch_mean  = 0.0

        # Throughput window
        self._throughput_window: list = []   # list of wall-clock completion times
        self._started_at = time.time()

    # ------------------------------------------------------------------
    # Record helpers
    # ------------------------------------------------------------------

    def record_session_created(self) -> None:
        with self._lock:
            self._sessions_created += 1

    def record_session_completed(self) -> None:
        with self._lock:
            self._sessions_completed += 1

    def record_session_failed(self) -> None:
        with self._lock:
            self._sessions_failed += 1

    def record_request_submitted(self) -> None:
        with self._lock:
            self._requests_submitted += 1

    def record_request_completed(self) -> None:
        with self._lock:
            self._requests_completed += 1

    def record_request_failed(self) -> None:
        with self._lock:
            self._requests_failed += 1

    def record_pipeline_started(self) -> None:
        with self._lock:
            self._pipelines_started += 1

    def record_pipeline_completed(self, elapsed_s: float = 0.0) -> None:
        with self._lock:
            self._pipelines_completed += 1
            self._update_assess_mean(elapsed_s)
            now = time.time()
            self._throughput_window.append(now)
            # keep only last 60 s
            cutoff = now - 60.0
            self._throughput_window = [t for t in self._throughput_window if t >= cutoff]

    def record_pipeline_failed(self) -> None:
        with self._lock:
            self._pipelines_failed += 1

    def record_snapshot_published(self) -> None:
        with self._lock:
            self._snapshots_published += 1

    def record_dispatch_time(self, elapsed_s: float) -> None:
        with self._lock:
            self._update_dispatch_mean(elapsed_s)

    # ------------------------------------------------------------------
    # Private online-mean updaters
    # ------------------------------------------------------------------

    def _update_assess_mean(self, elapsed_s: float) -> None:
        self._assess_count += 1
        delta = elapsed_s - self._assess_mean
        self._assess_mean += delta / self._assess_count

    def _update_dispatch_mean(self, elapsed_s: float) -> None:
        self._dispatch_count += 1
        delta = elapsed_s - self._dispatch_mean
        self._dispatch_mean += delta / self._dispatch_count

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            cutoff = now - 60.0
            recent = [t for t in self._throughput_window if t >= cutoff]
            throughput = len(recent)  # completions in last 60 s
            return {
                "sessions_created":     self._sessions_created,
                "sessions_completed":   self._sessions_completed,
                "sessions_failed":      self._sessions_failed,
                "requests_submitted":   self._requests_submitted,
                "requests_completed":   self._requests_completed,
                "requests_failed":      self._requests_failed,
                "pipelines_started":    self._pipelines_started,
                "pipelines_completed":  self._pipelines_completed,
                "pipelines_failed":     self._pipelines_failed,
                "snapshots_published":  self._snapshots_published,
                "avg_assessment_time_s": round(self._assess_mean, 4),
                "avg_dispatch_time_s":   round(self._dispatch_mean, 4),
                "throughput_per_min":    throughput,
            }

    def reset(self) -> None:
        with self._lock:
            self._sessions_created   = 0
            self._sessions_completed = 0
            self._sessions_failed    = 0
            self._requests_submitted = 0
            self._requests_completed = 0
            self._requests_failed    = 0
            self._pipelines_started  = 0
            self._pipelines_completed = 0
            self._pipelines_failed   = 0
            self._snapshots_published = 0
            self._assess_count  = 0
            self._assess_mean   = 0.0
            self._dispatch_count = 0
            self._dispatch_mean  = 0.0
            self._throughput_window = []
