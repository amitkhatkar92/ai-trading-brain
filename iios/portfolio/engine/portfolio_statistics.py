"""
portfolio_statistics.py — iios.portfolio.engine
================================================
Thread-safe accumulation of Portfolio Engine statistics.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict

_EMA_ALPHA = 0.1


class PortfolioEngineStatistics:
    """
    Thread-safe accumulator for Portfolio Engine statistics.

    All counters start at zero and increment monotonically.
    Duration statistics are maintained via an exponential moving average.

    Tracked statistics
    ------------------
    portfolio_sessions :           Total portfolio sessions created.
    portfolio_requests :           Total requests submitted per workflow type.
    portfolio_pipelines :          Total pipelines started.
    portfolio_pipelines_completed: Total pipelines completed successfully.
    portfolio_pipelines_failed :   Total pipelines that failed.
    portfolio_snapshots_published: Total portfolio snapshots published.
    average_portfolio_time_s :     Arithmetic mean pipeline duration.
    average_dispatch_time_s :      Arithmetic mean dispatch duration.
    subsystem_availability :       Rolling availability rate (0.0–1.0).
    portfolio_throughput :         Pipelines completed per minute.
    """

    def __init__(self) -> None:
        self._lock               = threading.Lock()
        self._sessions:    int   = 0
        self._requests:    int   = 0
        self._requests_by_type: Dict[str, int] = {}
        self._pipelines:   int   = 0
        self._completed:   int   = 0
        self._failed:      int   = 0
        self._snapshots:   int   = 0
        self._total_pipeline_s: float = 0.0
        self._pipeline_dur_count: int = 0
        self._ema_pipeline_s: float   = 0.0
        self._total_dispatch_s: float = 0.0
        self._dispatch_count:   int   = 0
        self._ema_dispatch_s:   float = 0.0
        self._avail_samples:    int   = 0
        self._avail_sum:        float = 0.0
        self._started_at: float       = time.time()
        # Rolling throughput window (last 60s)
        self._window_start: float     = time.time()
        self._window_count: int       = 0
        self._throughput_per_min: float = 0.0

    # ------------------------------------------------------------------
    # Recorders
    # ------------------------------------------------------------------

    def record_session_created(self) -> None:
        with self._lock:
            self._sessions += 1

    def record_request(self, workflow_type: object = None) -> None:
        with self._lock:
            self._requests += 1
            if workflow_type is not None:
                key = getattr(workflow_type, "value", str(workflow_type))
                self._requests_by_type[key] = self._requests_by_type.get(key, 0) + 1

    def record_pipeline_started(self) -> None:
        with self._lock:
            self._pipelines += 1

    def record_pipeline_completed(self, elapsed_s: float = 0.0) -> None:
        with self._lock:
            self._completed += 1
            self._window_count += 1
            if elapsed_s > 0.0:
                self._total_pipeline_s  += elapsed_s
                self._pipeline_dur_count += 1
                self._ema_pipeline_s = (
                    _EMA_ALPHA * elapsed_s
                    + (1.0 - _EMA_ALPHA) * self._ema_pipeline_s
                ) if self._ema_pipeline_s > 0 else elapsed_s
            # Update rolling throughput
            now = time.time()
            window = now - self._window_start
            if window >= 60.0:
                self._throughput_per_min = self._window_count / (window / 60.0)
                self._window_start = now
                self._window_count = 0

    def record_pipeline_failed(self) -> None:
        with self._lock:
            self._failed += 1

    def record_snapshot_published(self) -> None:
        with self._lock:
            self._snapshots += 1

    def record_dispatch(self, elapsed_s: float = 0.0) -> None:
        with self._lock:
            self._dispatch_count += 1
            if elapsed_s > 0.0:
                self._total_dispatch_s += elapsed_s
                self._ema_dispatch_s = (
                    _EMA_ALPHA * elapsed_s
                    + (1.0 - _EMA_ALPHA) * self._ema_dispatch_s
                ) if self._ema_dispatch_s > 0 else elapsed_s

    def record_subsystem_availability(self, available: bool) -> None:
        with self._lock:
            self._avail_samples += 1
            self._avail_sum     += 1.0 if available else 0.0

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg_pipeline = (
                self._total_pipeline_s / self._pipeline_dur_count
                if self._pipeline_dur_count > 0 else 0.0
            )
            avg_dispatch = (
                self._total_dispatch_s / self._dispatch_count
                if self._dispatch_count > 0 else 0.0
            )
            avail = (
                self._avail_sum / self._avail_samples
                if self._avail_samples > 0 else 1.0
            )
            return {
                "portfolio_sessions":            self._sessions,
                "portfolio_requests":            self._requests,
                "portfolio_requests_by_type":    dict(self._requests_by_type),
                "portfolio_pipelines":           self._pipelines,
                "portfolio_pipelines_completed": self._completed,
                "portfolio_pipelines_failed":    self._failed,
                "portfolio_snapshots_published": self._snapshots,
                "average_portfolio_time_s":      avg_pipeline,
                "ema_portfolio_time_s":          self._ema_pipeline_s,
                "average_dispatch_time_s":       avg_dispatch,
                "ema_dispatch_time_s":           self._ema_dispatch_s,
                "subsystem_availability":        avail,
                "portfolio_throughput":          self._throughput_per_min,
                "uptime_s":                      time.time() - self._started_at,
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._sessions           = 0
            self._requests           = 0
            self._requests_by_type   = {}
            self._pipelines          = 0
            self._completed          = 0
            self._failed             = 0
            self._snapshots          = 0
            self._total_pipeline_s   = 0.0
            self._pipeline_dur_count = 0
            self._ema_pipeline_s     = 0.0
            self._total_dispatch_s   = 0.0
            self._dispatch_count     = 0
            self._ema_dispatch_s     = 0.0
            self._avail_samples      = 0
            self._avail_sum          = 0.0
            self._started_at         = time.time()
            self._window_start       = time.time()
            self._window_count       = 0
            self._throughput_per_min = 0.0
