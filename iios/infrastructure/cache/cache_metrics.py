"""
iios/infrastructure/cache/cache_metrics.py
==========================================
Cache performance metrics with rolling percentile tracking.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

from .cache_constants import METRICS_WINDOW_SIZE

__all__ = ["CacheMetrics", "RegionMetrics", "LatencyTracker"]


class LatencyTracker:
    """Rolling window of latency samples for percentile computation."""

    def __init__(self, window: int = METRICS_WINDOW_SIZE) -> None:
        self._samples: deque[float] = deque(maxlen=window)
        self._lock = threading.Lock()

    def record(self, ms: float) -> None:
        with self._lock:
            self._samples.append(ms)

    def percentile(self, pct: float) -> float:
        """Return the *pct*-th percentile latency in milliseconds (0–100)."""
        with self._lock:
            if not self._samples:
                return 0.0
            sorted_s = sorted(self._samples)
            idx = max(0, int(len(sorted_s) * pct / 100) - 1)
            return sorted_s[idx]

    @property
    def p50(self) -> float:
        return self.percentile(50)

    @property
    def p95(self) -> float:
        return self.percentile(95)

    @property
    def p99(self) -> float:
        return self.percentile(99)

    @property
    def avg(self) -> float:
        with self._lock:
            if not self._samples:
                return 0.0
            return sum(self._samples) / len(self._samples)

    def reset(self) -> None:
        with self._lock:
            self._samples.clear()


@dataclass
class RegionMetrics:
    """Per-region cache statistics."""
    region: str
    hits: int = 0
    misses: int = 0
    writes: int = 0
    deletes: int = 0
    evictions: int = 0
    expirations: int = 0
    invalidations: int = 0
    errors: int = 0
    sync_failures: int = 0
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    current_size: int = 0
    total_bytes: int = 0

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    @property
    def miss_ratio(self) -> float:
        return 1.0 - self.hit_ratio

    def to_dict(self) -> dict[str, Any]:
        return {
            "region": self.region,
            "hits": self.hits,
            "misses": self.misses,
            "writes": self.writes,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "invalidations": self.invalidations,
            "errors": self.errors,
            "hit_ratio": round(self.hit_ratio, 4),
            "l1_hits": self.l1_hits,
            "l2_hits": self.l2_hits,
            "l3_hits": self.l3_hits,
            "current_size": self.current_size,
            "total_bytes": self.total_bytes,
        }


class CacheMetrics:
    """Thread-safe metrics collector for a cache engine instance."""

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self._hits = 0
        self._misses = 0
        self._writes = 0
        self._deletes = 0
        self._evictions = 0
        self._expirations = 0
        self._invalidations = 0
        self._errors = 0
        self._l1_hits = 0
        self._l2_hits = 0
        self._l3_hits = 0
        self._sync_failures = 0
        self._latency = LatencyTracker()
        self._write_latency = LatencyTracker()
        self._region_metrics: dict[str, RegionMetrics] = {}
        self._lock = threading.RLock()

    # ── Record operations ────────────────────────────────────────────────────

    def record_hit(self, ms: float = 0.0, level: str = "l1", region: str = "") -> None:
        with self._lock:
            self._hits += 1
            if level == "l1":
                self._l1_hits += 1
            elif level == "l2":
                self._l2_hits += 1
            elif level == "l3":
                self._l3_hits += 1
            if region:
                rm = self._get_or_create_region(region)
                rm.hits += 1
                if level == "l1":
                    rm.l1_hits += 1
                elif level == "l2":
                    rm.l2_hits += 1
                elif level == "l3":
                    rm.l3_hits += 1
        self._latency.record(ms)

    def record_miss(self, region: str = "") -> None:
        with self._lock:
            self._misses += 1
            if region:
                self._get_or_create_region(region).misses += 1

    def record_write(self, ms: float = 0.0, region: str = "") -> None:
        with self._lock:
            self._writes += 1
            if region:
                self._get_or_create_region(region).writes += 1
        self._write_latency.record(ms)

    def record_delete(self, region: str = "") -> None:
        with self._lock:
            self._deletes += 1
            if region:
                self._get_or_create_region(region).deletes += 1

    def record_eviction(self, count: int = 1, region: str = "") -> None:
        with self._lock:
            self._evictions += count
            if region:
                self._get_or_create_region(region).evictions += count

    def record_expiration(self, region: str = "") -> None:
        with self._lock:
            self._expirations += 1
            if region:
                self._get_or_create_region(region).expirations += 1

    def record_invalidation(self, count: int = 1, region: str = "") -> None:
        with self._lock:
            self._invalidations += count
            if region:
                self._get_or_create_region(region).invalidations += count

    def record_error(self, region: str = "") -> None:
        with self._lock:
            self._errors += 1
            if region:
                self._get_or_create_region(region).errors += 1

    def record_sync_failure(self) -> None:
        with self._lock:
            self._sync_failures += 1

    def _get_or_create_region(self, region: str) -> RegionMetrics:
        if region not in self._region_metrics:
            self._region_metrics[region] = RegionMetrics(region=region)
        return self._region_metrics[region]

    # ── Aggregates ───────────────────────────────────────────────────────────

    @property
    def hit_ratio(self) -> float:
        with self._lock:
            total = self._hits + self._misses
            return self._hits / total if total else 0.0

    @property
    def miss_ratio(self) -> float:
        return 1.0 - self.hit_ratio

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "hits": self._hits,
                "misses": self._misses,
                "writes": self._writes,
                "deletes": self._deletes,
                "evictions": self._evictions,
                "expirations": self._expirations,
                "invalidations": self._invalidations,
                "errors": self._errors,
                "sync_failures": self._sync_failures,
                "l1_hits": self._l1_hits,
                "l2_hits": self._l2_hits,
                "l3_hits": self._l3_hits,
                "hit_ratio": round(self.hit_ratio, 4),
                "miss_ratio": round(self.miss_ratio, 4),
                "latency_p50_ms": round(self._latency.p50, 3),
                "latency_p95_ms": round(self._latency.p95, 3),
                "latency_p99_ms": round(self._latency.p99, 3),
                "write_latency_p50_ms": round(self._write_latency.p50, 3),
            }

    def region_snapshot(self, region: str) -> Optional[dict[str, Any]]:
        with self._lock:
            rm = self._region_metrics.get(region)
            return rm.to_dict() if rm else None

    def all_regions(self) -> list[str]:
        with self._lock:
            return list(self._region_metrics.keys())

    def reset(self) -> None:
        with self._lock:
            self._hits = self._misses = self._writes = self._deletes = 0
            self._evictions = self._expirations = self._invalidations = 0
            self._errors = self._sync_failures = 0
            self._l1_hits = self._l2_hits = self._l3_hits = 0
            self._region_metrics.clear()
        self._latency.reset()
        self._write_latency.reset()
