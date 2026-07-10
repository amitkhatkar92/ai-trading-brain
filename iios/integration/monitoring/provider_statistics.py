"""iios/integration/monitoring/provider_statistics.py

Per-provider rolling statistics.
"""
from __future__ import annotations

import time
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderStatistics:
    """Aggregated statistics for a single provider."""

    provider_id:          str   = ""
    total_requests:       int   = 0
    successful_requests:  int   = 0
    failed_requests:      int   = 0
    total_records:        int   = 0
    avg_latency_ms:       float = 0.0
    p95_latency_ms:       float = 0.0
    p99_latency_ms:       float = 0.0
    min_latency_ms:       float = 0.0
    max_latency_ms:       float = 0.0
    availability_pct:     float = 1.0
    failure_rate:         float = 0.0
    last_success_at:      float | None = None
    last_failure_at:      float | None = None
    window_start:         float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id":         self.provider_id,
            "total_requests":      self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests":     self.failed_requests,
            "total_records":       self.total_records,
            "avg_latency_ms":      round(self.avg_latency_ms, 2),
            "p95_latency_ms":      round(self.p95_latency_ms, 2),
            "p99_latency_ms":      round(self.p99_latency_ms, 2),
            "min_latency_ms":      round(self.min_latency_ms, 2),
            "max_latency_ms":      round(self.max_latency_ms, 2),
            "availability_pct":    round(self.availability_pct, 4),
            "failure_rate":        round(self.failure_rate, 4),
            "last_success_at":     self.last_success_at,
            "last_failure_at":     self.last_failure_at,
        }


class RollingProviderStats:
    """
    Maintains a rolling window of request outcomes for one provider.
    Thread-safe.
    """

    def __init__(self, provider_id: str, window_size: int = 200) -> None:
        self.provider_id  = provider_id
        self._window_size = window_size
        self._latencies: deque[float]  = deque(maxlen=window_size)
        self._outcomes:  deque[bool]   = deque(maxlen=window_size)  # True=success
        self._record_counts: deque[int] = deque(maxlen=window_size)
        self._last_success_at: float | None = None
        self._last_failure_at: float | None = None
        self._lock = threading.RLock()

    def record_request(
        self,
        success:      bool,
        latency_ms:   float,
        record_count: int = 0,
    ) -> None:
        with self._lock:
            self._latencies.append(latency_ms)
            self._outcomes.append(success)
            self._record_counts.append(record_count)
            if success:
                self._last_success_at = time.time()
            else:
                self._last_failure_at = time.time()

    def snapshot(self) -> ProviderStatistics:
        with self._lock:
            outcomes  = list(self._outcomes)
            latencies = sorted(self._latencies)
            records   = list(self._record_counts)

        total   = len(outcomes)
        success = sum(1 for o in outcomes if o)
        failed  = total - success

        if latencies:
            avg_lat = sum(latencies) / len(latencies)
            p95_idx = int(len(latencies) * 0.95)
            p99_idx = int(len(latencies) * 0.99)
            p95_lat = latencies[min(p95_idx, len(latencies) - 1)]
            p99_lat = latencies[min(p99_idx, len(latencies) - 1)]
            min_lat = latencies[0]
            max_lat = latencies[-1]
        else:
            avg_lat = p95_lat = p99_lat = min_lat = max_lat = 0.0

        availability = success / total if total > 0 else 1.0
        failure_rate = failed / total if total > 0 else 0.0

        return ProviderStatistics(
            provider_id=self.provider_id,
            total_requests=total,
            successful_requests=success,
            failed_requests=failed,
            total_records=sum(records),
            avg_latency_ms=avg_lat,
            p95_latency_ms=p95_lat,
            p99_latency_ms=p99_lat,
            min_latency_ms=min_lat,
            max_latency_ms=max_lat,
            availability_pct=availability,
            failure_rate=failure_rate,
            last_success_at=self._last_success_at,
            last_failure_at=self._last_failure_at,
        )
