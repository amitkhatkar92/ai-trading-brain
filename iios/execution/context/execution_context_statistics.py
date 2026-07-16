"""iios/execution/context/execution_context_statistics.py
==================================================
Statistics dataclasses for the Execution Context package.

ContextBuildStatistics — per-build timing and outcome.
RegistryContextStatistics — aggregate across all registered contexts.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextBuildStatistics:
    """
    Mutable statistics for one execution context build.

    Records builder duration, validation outcome, and context size.
    """
    context_id:         str
    execution_id:       str
    built_at:           float = field(default_factory=time.time)
    builder_time_ms:    float = 0.0
    validation_passed:  bool  = False
    validation_time_ms: float = 0.0
    context_size_bytes: int   = 0
    snapshot_count:     int   = 0
    completeness:       float = 0.0
    errors:             tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id":         self.context_id,
            "execution_id":       self.execution_id,
            "built_at":           self.built_at,
            "builder_time_ms":    round(self.builder_time_ms, 2),
            "validation_passed":  self.validation_passed,
            "validation_time_ms": round(self.validation_time_ms, 2),
            "context_size_bytes": self.context_size_bytes,
            "snapshot_count":     self.snapshot_count,
            "completeness":       round(self.completeness, 4),
        }


@dataclass
class ExecutionContextStatistics:
    """
    Thread-safe aggregate statistics for the Execution Context registry.
    """

    created_at: float = field(default_factory=time.time)

    # Counters
    context_count:          int = 0
    validation_success:     int = 0
    validation_failure:     int = 0
    published_count:        int = 0
    rejected_count:         int = 0
    archived_count:         int = 0

    # Timing (milliseconds)
    _total_builder_ms:      float = field(default=0.0, repr=False)
    _total_validation_ms:   float = field(default=0.0, repr=False)

    # Size (bytes)
    _total_size_bytes:      int   = field(default=0, repr=False)

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ── Mutation ──────────────────────────────────────────────────────────────

    def record_build(self, build_stats: ContextBuildStatistics) -> None:
        with self._lock:
            self.context_count      += 1
            self._total_builder_ms  += build_stats.builder_time_ms
            self._total_size_bytes  += build_stats.context_size_bytes
            self._total_validation_ms += build_stats.validation_time_ms
            if build_stats.validation_passed:
                self.validation_success += 1
            else:
                self.validation_failure += 1

    def record_published(self) -> None:
        with self._lock:
            self.published_count += 1

    def record_rejected(self) -> None:
        with self._lock:
            self.rejected_count += 1

    def record_archived(self) -> None:
        with self._lock:
            self.archived_count += 1

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def validation_success_rate(self) -> float:
        total = self.validation_success + self.validation_failure
        if total == 0:
            return 0.0
        return self.validation_success / total

    @property
    def avg_builder_time_ms(self) -> float:
        if self.context_count == 0:
            return 0.0
        return self._total_builder_ms / self.context_count

    @property
    def avg_context_size_bytes(self) -> float:
        if self.context_count == 0:
            return 0.0
        return self._total_size_bytes / self.context_count

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at":              self.created_at,
            "context_count":           self.context_count,
            "validation_success":      self.validation_success,
            "validation_failure":      self.validation_failure,
            "validation_success_rate": round(self.validation_success_rate, 4),
            "published_count":         self.published_count,
            "rejected_count":          self.rejected_count,
            "archived_count":          self.archived_count,
            "avg_builder_time_ms":     round(self.avg_builder_time_ms, 2),
            "avg_context_size_bytes":  round(self.avg_context_size_bytes, 0),
        }
