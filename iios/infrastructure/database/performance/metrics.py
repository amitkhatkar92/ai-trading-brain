"""
iios/infrastructure/database/performance/metrics.py
====================================================
Database performance metrics collector.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

__all__ = ["DatabaseMetrics", "QueryMetric"]


@dataclass
class QueryMetric:
    """Record of a single query execution."""
    sql: str
    duration_ms: float
    rows_affected: int
    timestamp: float = field(default_factory=time.time)
    error: bool = False


class DatabaseMetrics:
    """Collects and aggregates database performance metrics.

    Usage::

        metrics = DatabaseMetrics()
        with metrics.measure("SELECT * FROM trades") as m:
            rows = db.query(...)
            m.rows = len(rows)

        report = metrics.report()
    """

    def __init__(self, history_size: int = 1000) -> None:
        self._history: deque[QueryMetric] = deque(maxlen=history_size)
        self._per_table: dict[str, list[float]] = defaultdict(list)
        self._total_queries = 0
        self._total_errors = 0
        self._total_rows_read = 0
        self._total_rows_written = 0
        self._total_duration_ms = 0.0
        self._session_count = 0
        self._lock = threading.Lock()

    def record(
        self,
        sql: str,
        duration_ms: float,
        rows_affected: int = 0,
        error: bool = False,
        table: str = "",
    ) -> None:
        metric = QueryMetric(
            sql=sql[:500],
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            error=error,
        )
        with self._lock:
            self._history.append(metric)
            self._total_queries += 1
            self._total_duration_ms += duration_ms
            if error:
                self._total_errors += 1
            else:
                sql_upper = sql.strip().upper()
                if sql_upper.startswith("SELECT"):
                    self._total_rows_read += rows_affected
                else:
                    self._total_rows_written += rows_affected
            if table:
                self._per_table[table].append(duration_ms)

    def record_session(self) -> None:
        with self._lock:
            self._session_count += 1

    def report(self) -> dict[str, Any]:
        with self._lock:
            history = list(self._history)
        durations = [m.duration_ms for m in history]
        p50 = _percentile(durations, 50)
        p95 = _percentile(durations, 95)
        p99 = _percentile(durations, 99)
        slow = [m for m in history if m.duration_ms > 100]
        return {
            "total_queries": self._total_queries,
            "total_errors": self._total_errors,
            "error_rate": self._total_errors / max(self._total_queries, 1),
            "total_rows_read": self._total_rows_read,
            "total_rows_written": self._total_rows_written,
            "total_duration_ms": self._total_duration_ms,
            "avg_duration_ms": self._total_duration_ms / max(self._total_queries, 1),
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "slow_queries": len(slow),
            "sessions_created": self._session_count,
            "recent_queries": len(history),
        }

    def slow_queries(self, threshold_ms: float = 100.0) -> list[QueryMetric]:
        with self._lock:
            return [m for m in self._history if m.duration_ms >= threshold_ms]

    def reset(self) -> None:
        with self._lock:
            self._history.clear()
            self._per_table.clear()
            self._total_queries = 0
            self._total_errors = 0
            self._total_rows_read = 0
            self._total_rows_written = 0
            self._total_duration_ms = 0.0

    def measure(self, sql: str, table: str = "") -> "_MeasureContext":
        return _MeasureContext(self, sql, table)


class _MeasureContext:
    def __init__(self, metrics: DatabaseMetrics, sql: str, table: str) -> None:
        self._metrics = metrics
        self._sql = sql
        self._table = table
        self._t0 = 0.0
        self.rows = 0
        self.error = False

    def __enter__(self) -> "_MeasureContext":
        self._t0 = time.monotonic()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        duration_ms = (time.monotonic() - self._t0) * 1000
        self._metrics.record(
            sql=self._sql,
            duration_ms=duration_ms,
            rows_affected=self.rows,
            error=exc_type is not None,
            table=self._table,
        )
        return False


def _percentile(data: list[float], p: int) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (k - lo)
