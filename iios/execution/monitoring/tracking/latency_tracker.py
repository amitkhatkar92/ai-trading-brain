"""iios/execution/monitoring/tracking/latency_tracker.py"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.monitoring_constants import (
    LatencyPhase,
    LATENCY_PERCENTILES,
)


@dataclass
class LatencyRecord:
    """Latency measurement for one phase of a single execution."""

    execution_id: str          = ""
    order_id:     str          = ""
    broker_id:    str          = ""
    symbol:       str          = ""
    phase:        LatencyPhase = LatencyPhase.TOTAL
    start_time:   float        = 0.0
    end_time:     float        = 0.0
    latency_ms:   float        = 0.0
    record_id:    str          = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:     dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.latency_ms == 0.0 and self.end_time > self.start_time:
            self.latency_ms = (self.end_time - self.start_time) * 1_000

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":   self.record_id,
            "execution_id": self.execution_id,
            "order_id":    self.order_id,
            "broker_id":   self.broker_id,
            "symbol":      self.symbol,
            "phase":       self.phase.value,
            "latency_ms":  self.latency_ms,
            "start_time":  self.start_time,
            "end_time":    self.end_time,
            "metadata":    self.metadata,
        }


class LatencyTracker:
    """
    Records execution latencies and computes statistical summaries.
    Thread-safe.
    """

    def __init__(self) -> None:
        self._records:            list[LatencyRecord] = []
        self._by_execution:       dict[str, list[LatencyRecord]] = {}
        self._by_phase:           dict[LatencyPhase, list[float]] = {
            p: [] for p in LatencyPhase
        }
        self._lock                = threading.RLock()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record(self, latency: LatencyRecord) -> None:
        with self._lock:
            self._records.append(latency)
            self._by_execution.setdefault(latency.execution_id, []).append(latency)
            self._by_phase[latency.phase].append(latency.latency_ms)

    def record_phase(
        self,
        execution_id: str,
        phase:        LatencyPhase,
        start_time:   float,
        end_time:     float | None = None,
        order_id:     str          = "",
        broker_id:    str          = "",
        symbol:       str          = "",
    ) -> LatencyRecord:
        if end_time is None:
            end_time = time.time()
        rec = LatencyRecord(
            execution_id=execution_id,
            order_id=order_id,
            broker_id=broker_id,
            symbol=symbol,
            phase=phase,
            start_time=start_time,
            end_time=end_time,
        )
        self.record(rec)
        return rec

    # ── Queries ───────────────────────────────────────────────────────────────

    def latencies_for_execution(self, execution_id: str) -> list[LatencyRecord]:
        with self._lock:
            return list(self._by_execution.get(execution_id, []))

    def avg_latency_ms(self, phase: LatencyPhase = LatencyPhase.TOTAL) -> float:
        with self._lock:
            values = self._by_phase.get(phase, [])
        if not values:
            return 0.0
        return sum(values) / len(values)

    def percentile_latency_ms(
        self,
        percentile: int = 95,
        phase: LatencyPhase = LatencyPhase.TOTAL,
    ) -> float:
        with self._lock:
            values = sorted(self._by_phase.get(phase, []))
        if not values:
            return 0.0
        idx = int(len(values) * percentile / 100)
        return values[min(idx, len(values) - 1)]

    def all_latencies(self, phase: LatencyPhase = LatencyPhase.TOTAL) -> list[float]:
        with self._lock:
            return list(self._by_phase.get(phase, []))

    def statistics(self) -> dict[str, Any]:
        return {
            "total_records": len(self._records),
            "avg_total_ms":  round(self.avg_latency_ms(LatencyPhase.TOTAL), 2),
            "p95_total_ms":  round(self.percentile_latency_ms(95, LatencyPhase.TOTAL), 2),
            "p99_total_ms":  round(self.percentile_latency_ms(99, LatencyPhase.TOTAL), 2),
        }
