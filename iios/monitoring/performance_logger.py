"""
iios/monitoring/performance_logger.py
=======================================
Performance timing and latency tracking for IIOS subsystems.

Provides:
  - ``PerformanceLogger.time()`` — context manager for measuring operations
  - Layer-level SLA enforcement (WARN/CRIT thresholds)
  - In-memory rolling statistics (min/max/avg/p95/p99)
  - Integration with the IIOS 17-layer SLA constants

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import logging
import statistics
import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Any, Generator, Optional

from .monitoring_constants import LATENCY_WARN_MS, LATENCY_CRIT_MS, IIOS_LAYER_NAMES
from .monitoring_models import PerformanceRecord

__all__ = [
    "PerformanceLogger",
    "TimingResult",
    "get_performance_logger",
]

_LOG = logging.getLogger("iios.monitoring.performance")
_instance_lock = threading.Lock()
_instance: Optional["PerformanceLogger"] = None


class TimingResult:
    """Result of a single timed operation."""

    def __init__(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self.operation = operation
        self.duration_ms = duration_ms
        self.success = success
        self.error = error
        self.metadata = metadata or {}

    @property
    def is_slow(self) -> bool:
        return self.duration_ms > LATENCY_WARN_MS

    @property
    def is_critical(self) -> bool:
        return self.duration_ms > LATENCY_CRIT_MS

    def __repr__(self) -> str:
        return f"TimingResult({self.operation!r}, {self.duration_ms:.1f}ms, ok={self.success})"


class _OperationStats:
    """Rolling statistics for one named operation."""

    def __init__(self, max_history: int = 1000) -> None:
        self._samples: deque[float] = deque(maxlen=max_history)
        self._count = 0
        self._total = 0.0
        self._min = float("inf")
        self._max = float("-inf")
        self._errors = 0

    def record(self, duration_ms: float, success: bool = True) -> None:
        self._samples.append(duration_ms)
        self._count += 1
        self._total += duration_ms
        self._min = min(self._min, duration_ms)
        self._max = max(self._max, duration_ms)
        if not success:
            self._errors += 1

    @property
    def count(self) -> int:
        return self._count

    @property
    def error_count(self) -> int:
        return self._errors

    @property
    def mean_ms(self) -> float:
        return self._total / self._count if self._count else 0.0

    @property
    def min_ms(self) -> float:
        return self._min if self._count else 0.0

    @property
    def max_ms(self) -> float:
        return self._max if self._count else 0.0

    @property
    def p95_ms(self) -> float:
        samples = sorted(self._samples)
        if not samples:
            return 0.0
        idx = int(len(samples) * 0.95)
        return samples[min(idx, len(samples) - 1)]

    @property
    def p99_ms(self) -> float:
        samples = sorted(self._samples)
        if not samples:
            return 0.0
        idx = int(len(samples) * 0.99)
        return samples[min(idx, len(samples) - 1)]

    @property
    def success_rate(self) -> float:
        return (self._count - self._errors) / self._count if self._count else 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "error_count": self.error_count,
            "mean_ms": round(self.mean_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "success_rate": round(self.success_rate, 4),
        }


class PerformanceLogger:
    """Measures and tracks execution timing for IIOS operations.

    Usage::

        perf = get_performance_logger()
        with perf.time("GlobalIntelligence.fetch") as t:
            result = await fetch()
        # t.duration_ms, t.is_slow, t.is_critical available here
    """

    # Per-layer SLA overrides (ms)
    _WARN_OVERRIDES: dict[str, int] = {
        "GlobalIntelligence": 5_000,
    }
    _CRIT_OVERRIDES: dict[str, int] = {
        "GlobalIntelligence": 12_000,
    }

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stats: dict[str, _OperationStats] = {}
        self._recent: deque[PerformanceRecord] = deque(maxlen=5000)
        self._record_count = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @contextmanager
    def time(
        self,
        operation: str,
        component: str = "",
        layer: str = "",
        warn_ms: Optional[int] = None,
        crit_ms: Optional[int] = None,
        **metadata: Any,
    ) -> Generator[TimingResult, None, None]:
        """Context manager that measures execution time of the block.

        Usage::

            with perf.time("RiskGuardian.evaluate", layer="RiskGuardian") as t:
                # ... code ...
            print(t.duration_ms)
        """
        layer_name = layer or operation.split(".")[0]
        w_ms = warn_ms or self._WARN_OVERRIDES.get(layer_name, LATENCY_WARN_MS)
        c_ms = crit_ms or self._CRIT_OVERRIDES.get(layer_name, LATENCY_CRIT_MS)

        result = TimingResult(operation=operation, duration_ms=0.0)
        t_start = time.monotonic()
        error: Optional[str] = None
        try:
            yield result
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            result.success = False
            result.error = error
            raise
        finally:
            duration_ms = (time.monotonic() - t_start) * 1000
            result.duration_ms = duration_ms

            # SLA checks
            if duration_ms >= c_ms:
                _LOG.critical(
                    "LATENCY CRITICAL: %s took %.1fms (threshold=%dms)",
                    operation, duration_ms, c_ms,
                )
            elif duration_ms >= w_ms:
                _LOG.warning(
                    "LATENCY WARN: %s took %.1fms (threshold=%dms)",
                    operation, duration_ms, w_ms,
                )
            else:
                _LOG.debug("%s completed in %.1fms", operation, duration_ms)

            self._record(operation, component, layer, duration_ms, result.success, error, metadata)

    def record(
        self,
        operation: str,
        duration_ms: float,
        component: str = "",
        layer: str = "",
        success: bool = True,
        error: Optional[str] = None,
        **metadata: Any,
    ) -> PerformanceRecord:
        """Record a timing measurement directly (without context manager)."""
        return self._record(operation, component, layer, duration_ms, success, error, metadata)

    def get_stats(self, operation: str) -> Optional[dict[str, Any]]:
        """Return aggregated statistics for *operation*."""
        with self._lock:
            stats = self._stats.get(operation)
        return stats.to_dict() if stats else None

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Return statistics for all tracked operations."""
        with self._lock:
            return {op: s.to_dict() for op, s in self._stats.items()}

    def recent_records(self, n: int = 50, operation: Optional[str] = None) -> list[PerformanceRecord]:
        """Return recent performance records."""
        with self._lock:
            records = list(reversed(list(self._recent)))
        if operation:
            records = [r for r in records if r.operation == operation]
        return records[:n]

    def layer_summary(self) -> dict[str, dict[str, Any]]:
        """Return a summary of performance per IIOS layer."""
        with self._lock:
            result = {}
            for layer in IIOS_LAYER_NAMES:
                # Find all ops with this layer prefix
                ops = {k: v for k, v in self._stats.items() if k.startswith(layer)}
                if ops:
                    all_means = [v.mean_ms for v in ops.values() if v.count > 0]
                    result[layer] = {
                        "operation_count": len(ops),
                        "avg_ms": round(sum(all_means) / len(all_means), 2) if all_means else 0.0,
                    }
        return result

    @property
    def record_count(self) -> int:
        return self._record_count

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _record(
        self,
        operation: str,
        component: str,
        layer: str,
        duration_ms: float,
        success: bool,
        error: Optional[str],
        metadata: dict,
    ) -> PerformanceRecord:
        rec = PerformanceRecord(
            operation=operation,
            duration_ms=duration_ms,
            component=component,
            layer=layer,
            success=success,
            error=error,
            metadata=metadata,
        )
        with self._lock:
            if operation not in self._stats:
                self._stats[operation] = _OperationStats()
            self._stats[operation].record(duration_ms, success)
            self._recent.append(rec)
            self._record_count += 1
        return rec


def get_performance_logger() -> PerformanceLogger:
    """Return (or create) the global ``PerformanceLogger`` singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = PerformanceLogger()
        return _instance


def _reset_performance_logger() -> None:
    global _instance
    with _instance_lock:
        _instance = None
