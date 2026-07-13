"""iios/investment/strategy/lifecycle/runtime_statistics.py
Rolling runtime statistics for the lifecycle engine.
"""
from __future__ import annotations

import math
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, List, Optional


@dataclass
class CycleSample:
    """Timing record for a single completed execution cycle."""

    cycle_id: str
    strategy_count: int
    duration_ms: float
    success_count: int
    failure_count: int
    completed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def cycle_success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 1.0


class RuntimeStatistics:
    """
    Thread-safe rolling statistics for the lifecycle engine.

    Keeps the last ``window`` cycle samples and computes derived metrics
    on demand (no caching — always computed from live samples).
    """

    def __init__(self, window: int = 200) -> None:
        self.window = window
        self._lock: threading.Lock = threading.Lock()
        self._samples: Deque[CycleSample] = deque(maxlen=window)
        self._total_cycles: int = 0
        self._total_failures: int = 0
        self._total_strategies_run: int = 0
        self._started_at: datetime = datetime.now(timezone.utc)

    # ── Write ─────────────────────────────────────────────────────────────────

    def record(self, sample: CycleSample) -> None:
        with self._lock:
            self._samples.append(sample)
            self._total_cycles += 1
            self._total_failures += sample.failure_count
            self._total_strategies_run += sample.strategy_count

    # ── Reads ─────────────────────────────────────────────────────────────────

    @property
    def total_cycles(self) -> int:
        with self._lock:
            return self._total_cycles

    @property
    def total_failures(self) -> int:
        with self._lock:
            return self._total_failures

    @property
    def total_strategies_run(self) -> int:
        with self._lock:
            return self._total_strategies_run

    @property
    def uptime_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self._started_at).total_seconds()

    def success_rate(self) -> float:
        with self._lock:
            if self._total_cycles == 0:
                return 1.0
            return (self._total_cycles - self._total_failures) / self._total_cycles

    def p50_latency_ms(self) -> float:
        return self._percentile(50)

    def p95_latency_ms(self) -> float:
        return self._percentile(95)

    def p99_latency_ms(self) -> float:
        return self._percentile(99)

    def recent_samples(self, n: int = 50) -> List[CycleSample]:
        with self._lock:
            return list(self._samples)[-n:]

    def to_dict(self) -> dict:
        return {
            "total_cycles": self.total_cycles,
            "total_failures": self.total_failures,
            "total_strategies_run": self.total_strategies_run,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "p50_latency_ms": round(self.p50_latency_ms(), 2),
            "p95_latency_ms": round(self.p95_latency_ms(), 2),
            "p99_latency_ms": round(self.p99_latency_ms(), 2),
            "success_rate": round(self.success_rate(), 4),
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _percentile(self, pct: int) -> float:
        with self._lock:
            if not self._samples:
                return 0.0
            sorted_ms = sorted(s.duration_ms for s in self._samples)
        idx = max(0, math.ceil(len(sorted_ms) * pct / 100) - 1)
        return sorted_ms[idx]
