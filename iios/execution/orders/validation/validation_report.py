"""iios/execution/orders/validation/validation_report.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..order_constants import ValidationStatus


@dataclass
class RuleResult:
    rule_name: str
    passed:    bool
    errors:    list[str] = field(default_factory=list)
    warnings:  list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "passed":    self.passed,
            "errors":    list(self.errors),
            "warnings":  list(self.warnings),
        }


@dataclass
class ValidationReport:
    """Aggregated result of running all validation rules against one request."""

    report_id:  str              = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str              = ""
    status:     ValidationStatus = ValidationStatus.PENDING
    results:    list[RuleResult] = field(default_factory=list)
    duration_ms: float           = 0.0
    timestamp:  float            = field(default_factory=time.time)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASSED

    @property
    def errors(self) -> list[str]:
        out: list[str] = []
        for r in self.results:
            out.extend(r.errors)
        return out

    @property
    def warnings(self) -> list[str]:
        out: list[str] = []
        for r in self.results:
            out.extend(r.warnings)
        return out

    @property
    def error_count(self) -> int:
        return sum(len(r.errors) for r in self.results)

    @property
    def warning_count(self) -> int:
        return sum(len(r.warnings) for r in self.results)

    # ── Builders ──────────────────────────────────────────────────────────────

    def add_result(self, result: RuleResult) -> None:
        self.results.append(result)

    def finalise(self) -> None:
        """Compute overall status from individual rule results."""
        if any(not r.passed for r in self.results):
            self.status = ValidationStatus.FAILED
        elif any(r.warnings for r in self.results):
            self.status = ValidationStatus.WARNINGS
        else:
            self.status = ValidationStatus.PASSED

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":   self.report_id,
            "request_id":  self.request_id,
            "status":      self.status.value,
            "passed":      self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors":      self.errors,
            "warnings":    self.warnings,
            "results":     [r.to_dict() for r in self.results],
            "duration_ms": self.duration_ms,
            "timestamp":   self.timestamp,
        }
