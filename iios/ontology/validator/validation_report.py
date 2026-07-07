"""
iios/ontology/validator/validation_report.py
=============================================
ValidationReport aggregates all ValidationResult objects from one
validation run and provides summary statistics, severity roll-up,
and history management.
"""

from __future__ import annotations

import collections
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .validation_constants import (
    MAX_HISTORY_PER_TARGET,
    ValidationPhase,
    ValidationScope,
    ValidationSeverity,
    max_severity,
    severity_ge,
)
from .validation_result import ValidationResult

__all__ = [
    "ValidationReport",
    "ValidationHistory",
]


@dataclass
class ValidationReport:
    """
    Aggregated outcome of validating one ontology target.

    Attributes:
        target_id    – Stable identifier of the validated object (URI / name).
        target_type  – Human label for the target kind ("OntologyTypeDef", etc.).
        phase        – Lifecycle phase during which validation ran.
        results      – Ordered list of individual constraint results.
        started_at   – Unix epoch seconds.
        finished_at  – Unix epoch seconds (0 until finalised).
        duration_ms  – Wall-clock duration of the validation run.
        metadata     – Arbitrary extra key/value data from the caller.
    """

    target_id:   str                    = ""
    target_type: str                    = ""
    phase:       ValidationPhase        = ValidationPhase.ON_DEMAND
    results:     list[ValidationResult] = field(default_factory=list)
    started_at:  float                  = field(default_factory=time.time)
    finished_at: float                  = 0.0
    duration_ms: float                  = 0.0
    metadata:    dict[str, Any]         = field(default_factory=dict)

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def add(self, result: ValidationResult) -> None:
        """Append one ValidationResult."""
        self.results.append(result)

    def add_all(self, results: list[ValidationResult]) -> None:
        """Append a list of ValidationResult objects."""
        self.results.extend(results)

    def merge(self, other: "ValidationReport") -> None:
        """Merge another report's results into this one."""
        self.results.extend(other.results)

    def finalise(self) -> None:
        """Record finish time and compute duration_ms."""
        self.finished_at = time.time()
        self.duration_ms = (self.finished_at - self.started_at) * 1_000.0

    # ── Derived statistics ────────────────────────────────────────────────────

    @property
    def passed(self) -> bool:
        """True if no ERROR or CRITICAL results are present."""
        return not any(r.is_error for r in self.results)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.severity == ValidationSeverity.ERROR)

    @property
    def critical_count(self) -> int:
        return sum(1 for r in self.results if r.severity == ValidationSeverity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.results if r.severity == ValidationSeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for r in self.results if r.severity == ValidationSeverity.INFO)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.severity == ValidationSeverity.PASS)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0 or self.critical_count > 0

    @property
    def has_criticals(self) -> bool:
        return self.critical_count > 0

    @property
    def severity(self) -> ValidationSeverity:
        """Highest severity found in all results."""
        return max_severity([r.severity for r in self.results]) if self.results else ValidationSeverity.PASS

    @property
    def errors(self) -> list[ValidationResult]:
        return [r for r in self.results if r.severity == ValidationSeverity.ERROR]

    @property
    def criticals(self) -> list[ValidationResult]:
        return [r for r in self.results if r.severity == ValidationSeverity.CRITICAL]

    @property
    def warnings(self) -> list[ValidationResult]:
        return [r for r in self.results if r.severity == ValidationSeverity.WARNING]

    def by_scope(self, scope: ValidationScope) -> list[ValidationResult]:
        return [r for r in self.results if r.scope == scope]

    def by_constraint(self, constraint_id: str) -> list[ValidationResult]:
        return [r for r in self.results if r.constraint_id == constraint_id]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Concise summary dict (no per-result detail)."""
        return {
            "target_id":      self.target_id,
            "target_type":    self.target_type,
            "phase":          self.phase.value,
            "passed":         self.passed,
            "severity":       self.severity.value,
            "total":          self.total,
            "errors":         self.error_count,
            "criticals":      self.critical_count,
            "warnings":       self.warning_count,
            "duration_ms":    round(self.duration_ms, 2),
        }

    def to_dict(self) -> dict[str, Any]:
        """Full serialisation including all results."""
        return {
            **self.summary(),
            "started_at":  self.started_at,
            "finished_at": self.finished_at,
            "metadata":    self.metadata,
            "results": [r.to_dict() for r in self.results],
        }

    # ── Filtering ──────────────────────────────────────────────────────────────

    def errors_and_criticals(self) -> list[ValidationResult]:
        return [r for r in self.results if r.is_error]

    def at_or_above(self, severity: ValidationSeverity) -> list[ValidationResult]:
        return [r for r in self.results if severity_ge(r.severity, severity)]


# ── Validation history ────────────────────────────────────────────────────────

class ValidationHistory:
    """
    Thread-safe circular buffer of ValidationReport objects per target.

    Keeps the last ``max_per_target`` reports for any target_id.
    """

    def __init__(self, max_per_target: int = MAX_HISTORY_PER_TARGET) -> None:
        self._max    = max_per_target
        self._store: dict[str, collections.deque[ValidationReport]] = {}
        self._lock   = threading.RLock()

    def record(self, report: ValidationReport) -> None:
        with self._lock:
            key = report.target_id
            if key not in self._store:
                self._store[key] = collections.deque(maxlen=self._max)
            self._store[key].append(report)

    def get(self, target_id: str, limit: Optional[int] = None) -> list[ValidationReport]:
        with self._lock:
            if target_id not in self._store:
                return []
            items = list(self._store[target_id])
            if limit is not None:
                items = items[-limit:]
            return items

    def last(self, target_id: str) -> Optional[ValidationReport]:
        reports = self.get(target_id, limit=1)
        return reports[0] if reports else None

    def all_targets(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def clear(self, target_id: Optional[str] = None) -> None:
        with self._lock:
            if target_id is not None:
                self._store.pop(target_id, None)
            else:
                self._store.clear()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "tracked_targets": len(self._store),
                "total_reports":   sum(len(v) for v in self._store.values()),
                "max_per_target":  self._max,
            }
