"""iios/common/logging/performance_logger.py
Performance timing and profiling logger for the IIOS platform.

Tracks:
  • Wall-clock execution time  (time.perf_counter)
  • CPU time                   (time.process_time)
  • Memory allocation delta     (tracemalloc — opt-in, off by default)
  • Per-stage durations         (for pipeline decomposition)
  • Pipeline totals             (sum of stage durations + pipeline overhead)

Usage::

    from iios.common.logging.performance_logger import get_performance_logger

    perf = get_performance_logger("iios.market.integration",
                                   engine_id="iios:market:intelligence:integration")

    # Context-manager usage (most common)
    with perf.measure("fetch_quotes", stage="data_fetch") as timer:
        quotes = feed.get_multiple_quotes(symbols)
    # Automatically logs on exit:
    # elapsed_sec, cpu_time_sec, memory_delta_kb

    # Manual log
    perf.log_execution("build_regime_context", elapsed_sec=0.042)

    # Stage + pipeline summary
    perf.log_stage("normalise", duration_ms=12.4)
    perf.log_pipeline("intelligence_cycle", total_ms=140.0,
                       stage_durations={"fetch": 80.0, "normalise": 12.4})
"""
from __future__ import annotations

import threading
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.structured_logger import StructuredLogger


# ── Performance record ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PerformanceRecord:
    """Immutable snapshot of a single performance observation."""

    name:             str
    elapsed_sec:      float
    cpu_time_sec:     float
    memory_delta_kb:  Optional[float]
    stage:            str
    pipeline:         str
    metadata:         Dict[str, Any]
    timestamp:        datetime


# ── Timer context manager ─────────────────────────────────────────────────────

class _Timer:
    """
    Lightweight timer that captures wall time, CPU time and optional memory.

    Intended to be used via ``PerformanceLogger.measure()``:

    .. code:: python

        with perf.measure("my_op") as t:
            do_work()
        print(t.elapsed_sec)   # wall time in seconds
    """

    def __init__(self, *, track_memory: bool = False) -> None:
        self._track_memory:  bool           = track_memory
        self.elapsed_sec:    float          = 0.0
        self.cpu_time_sec:   float          = 0.0
        self.memory_delta_kb: Optional[float] = None
        self._wall_start:    float          = 0.0
        self._cpu_start:     float          = 0.0

    def start(self) -> None:
        self._wall_start = time.perf_counter()
        self._cpu_start  = time.process_time()
        if self._track_memory:
            if not tracemalloc.is_tracing():
                tracemalloc.start()
            tracemalloc.clear_traces()

    def stop(self) -> None:
        self.elapsed_sec  = time.perf_counter() - self._wall_start
        self.cpu_time_sec = time.process_time() - self._cpu_start
        if self._track_memory and tracemalloc.is_tracing():
            _, peak = tracemalloc.get_traced_memory()
            self.memory_delta_kb = peak / 1024.0

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed_sec * 1000.0


# ── PerformanceLogger ─────────────────────────────────────────────────────────

_MAX_RECENT = 200   # capped ring buffer


class PerformanceLogger:
    """
    Thread-safe performance measurement logger for one component/engine.

    All timings are logged via the ``StructuredLogger`` as INFO-level records
    with ``context`` dicts containing the performance data.
    """

    def __init__(
        self,
        name:       str,
        *,
        engine_id:  str = "",
        component:  str = "",
    ) -> None:
        self._name:      str = name
        self._engine_id: str = engine_id
        self._component: str = component
        self._log:       StructuredLogger = get_logger(
            name, engine_id=engine_id, component=component
        )
        self._lock:      threading.Lock   = threading.Lock()
        self._recent:    List[PerformanceRecord] = []

    # ── Context manager ───────────────────────────────────────────────────────

    @contextmanager
    def measure(
        self,
        name:          str,
        *,
        stage:         str = "",
        pipeline:      str = "",
        track_memory:  bool = False,
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> Generator[_Timer, None, None]:
        """
        Time a block of code, log the result, and store the record.

        Example::

            with perf.measure("fetch_quotes", stage="data_fetch") as t:
                quotes = feed.get_multiple_quotes(symbols)
            # t.elapsed_sec is available after the block

        :param name:         Metric name / operation identifier.
        :param stage:        Optional pipeline stage name.
        :param pipeline:     Optional pipeline name.
        :param track_memory: If True, uses tracemalloc to measure memory
                             allocation delta (adds overhead — use sparingly).
        :param metadata:     Additional key-value pairs to include in the record.
        """
        timer = _Timer(track_memory=track_memory)
        timer.start()
        try:
            yield timer
        finally:
            timer.stop()
            self._record_and_log(
                name         = name,
                elapsed_sec  = timer.elapsed_sec,
                cpu_time_sec = timer.cpu_time_sec,
                memory_kb    = timer.memory_delta_kb,
                stage        = stage,
                pipeline     = pipeline,
                metadata     = metadata or {},
            )

    # ── Manual log methods ────────────────────────────────────────────────────

    def log_execution(
        self,
        name:        str,
        elapsed_sec: float,
        *,
        cpu_time_sec: float             = 0.0,
        memory_kb:    Optional[float]   = None,
        stage:        str               = "",
        pipeline:     str               = "",
        **kwargs:     Any,
    ) -> None:
        """Log a single execution measurement (wall time in seconds)."""
        self._record_and_log(
            name         = name,
            elapsed_sec  = elapsed_sec,
            cpu_time_sec = cpu_time_sec,
            memory_kb    = memory_kb,
            stage        = stage,
            pipeline     = pipeline,
            metadata     = kwargs,
        )

    def log_stage(
        self,
        stage_name:  str,
        duration_ms: float,
        *,
        pipeline:    str = "",
        **kwargs:    Any,
    ) -> None:
        """Log a single pipeline stage duration (in milliseconds)."""
        self._record_and_log(
            name         = stage_name,
            elapsed_sec  = duration_ms / 1000.0,
            cpu_time_sec = 0.0,
            memory_kb    = None,
            stage        = stage_name,
            pipeline     = pipeline,
            metadata     = kwargs,
        )

    def log_pipeline(
        self,
        pipeline_name:   str,
        total_ms:        float,
        stage_durations: Dict[str, float],
        **kwargs:        Any,
    ) -> None:
        """
        Log an entire pipeline summary with per-stage breakdown.

        :param pipeline_name:    Identifier for the pipeline.
        :param total_ms:         Total elapsed time in milliseconds.
        :param stage_durations:  Mapping of stage_name → duration_ms.
        """
        meta: Dict[str, Any] = {
            "stage_durations_ms": stage_durations,
            **kwargs,
        }
        self._record_and_log(
            name         = pipeline_name,
            elapsed_sec  = total_ms / 1000.0,
            cpu_time_sec = 0.0,
            memory_kb    = None,
            stage        = "",
            pipeline     = pipeline_name,
            metadata     = meta,
        )

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary(self) -> List[PerformanceRecord]:
        """Return a copy of the most recent performance records."""
        with self._lock:
            return list(self._recent)

    def clear(self) -> None:
        """Clear the recent records buffer."""
        with self._lock:
            self._recent.clear()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _record_and_log(
        self,
        *,
        name:         str,
        elapsed_sec:  float,
        cpu_time_sec: float,
        memory_kb:    Optional[float],
        stage:        str,
        pipeline:     str,
        metadata:     Dict[str, Any],
    ) -> None:
        record = PerformanceRecord(
            name             = name,
            elapsed_sec      = elapsed_sec,
            cpu_time_sec     = cpu_time_sec,
            memory_delta_kb  = memory_kb,
            stage            = stage,
            pipeline         = pipeline,
            metadata         = metadata,
            timestamp        = datetime.now(timezone.utc),
        )

        ctx: Dict[str, Any] = {
            "perf_name":       name,
            "elapsed_ms":      round(elapsed_sec * 1000, 3),
            "cpu_ms":          round(cpu_time_sec * 1000, 3),
        }
        if memory_kb is not None:
            ctx["memory_delta_kb"] = round(memory_kb, 2)
        if stage:
            ctx["stage"] = stage
        if pipeline:
            ctx["pipeline"] = pipeline
        if metadata:
            ctx.update(metadata)

        self._log.structured(
            20,  # logging.INFO
            f"Perf: {name} elapsed={ctx['elapsed_ms']}ms",
            elapsed_ms = ctx["elapsed_ms"],
            context    = ctx,
        )

        with self._lock:
            self._recent.append(record)
            if len(self._recent) > _MAX_RECENT:
                self._recent.pop(0)


# ── Registry ──────────────────────────────────────────────────────────────────

_registry_lock:  threading.Lock                     = threading.Lock()
_perf_registry:  Dict[str, PerformanceLogger]       = {}


def get_performance_logger(
    name:       str,
    *,
    engine_id:  str = "",
    component:  str = "",
) -> PerformanceLogger:
    """
    Return or create a ``PerformanceLogger`` for the given name.

    Cached per ``(name, engine_id)`` pair.

    Example::

        perf = get_performance_logger("iios.market.integration",
                                       engine_id="iios:market:intelligence:integration")
    """
    key = f"{name}:{engine_id}"
    with _registry_lock:
        if key not in _perf_registry:
            _perf_registry[key] = PerformanceLogger(
                name, engine_id=engine_id, component=component
            )
        return _perf_registry[key]
