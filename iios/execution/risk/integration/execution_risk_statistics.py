"""iios/execution/risk/integration/execution_risk_statistics.py
==================================================
IntegrationStatistics — runtime metrics for the integration subsystem.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class IntegrationStatistics:
    """
    Mutable runtime statistics accumulated by the integration engine.

    Not thread-safe on its own — the engine acquires its lock before
    calling any record_* method.
    """

    requests_processed:      int   = 0
    successful_evaluations:  int   = 0
    blocked_evaluations:     int   = 0
    warnings_issued:         int   = 0
    overrides_applied:       int   = 0
    emergency_stops:         int   = 0
    validation_failures:     int   = 0
    evaluation_errors:       int   = 0
    total_processing_time_ms: float = 0.0
    uptime_start:            float = field(default_factory=time.time)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def average_processing_time_ms(self) -> float:
        if self.requests_processed == 0:
            return 0.0
        return self.total_processing_time_ms / self.requests_processed

    @property
    def subsystem_availability(self) -> float:
        """Fraction of requests that resulted in a successful (non-error) evaluation."""
        total = self.requests_processed
        if total == 0:
            return 1.0
        errors = self.validation_failures + self.evaluation_errors
        return max(0.0, (total - errors) / total)

    @property
    def block_rate(self) -> float:
        if self.requests_processed == 0:
            return 0.0
        return self.blocked_evaluations / self.requests_processed

    @property
    def uptime_sec(self) -> float:
        return time.time() - self.uptime_start

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def record_request(
        self,
        elapsed_ms:   float,
        action:       str,
        approved:     bool,
    ) -> None:
        self.requests_processed      += 1
        self.total_processing_time_ms += elapsed_ms

        action_upper = action.upper()
        if approved:
            self.successful_evaluations += 1
        else:
            self.blocked_evaluations += 1

        if action_upper in ("ALLOW_WITH_WARNING",):
            self.warnings_issued += 1
        if action_upper == "EMERGENCY_STOP":
            self.emergency_stops += 1

    def record_override(self) -> None:
        self.overrides_applied += 1

    def record_validation_failure(self) -> None:
        self.requests_processed += 1
        self.validation_failures += 1

    def record_evaluation_error(self) -> None:
        self.requests_processed  += 1
        self.evaluation_errors   += 1

    def reset(self) -> None:
        self.requests_processed       = 0
        self.successful_evaluations   = 0
        self.blocked_evaluations      = 0
        self.warnings_issued          = 0
        self.overrides_applied        = 0
        self.emergency_stops          = 0
        self.validation_failures      = 0
        self.evaluation_errors        = 0
        self.total_processing_time_ms = 0.0
        self.uptime_start             = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_processed":       self.requests_processed,
            "successful_evaluations":   self.successful_evaluations,
            "blocked_evaluations":      self.blocked_evaluations,
            "warnings_issued":          self.warnings_issued,
            "overrides_applied":        self.overrides_applied,
            "emergency_stops":          self.emergency_stops,
            "validation_failures":      self.validation_failures,
            "evaluation_errors":        self.evaluation_errors,
            "total_processing_time_ms": self.total_processing_time_ms,
            "average_processing_time_ms": self.average_processing_time_ms,
            "subsystem_availability":   self.subsystem_availability,
            "block_rate":               self.block_rate,
            "uptime_sec":               self.uptime_sec,
        }

    def copy(self) -> "IntegrationStatistics":
        s = IntegrationStatistics()
        s.requests_processed       = self.requests_processed
        s.successful_evaluations   = self.successful_evaluations
        s.blocked_evaluations      = self.blocked_evaluations
        s.warnings_issued          = self.warnings_issued
        s.overrides_applied        = self.overrides_applied
        s.emergency_stops          = self.emergency_stops
        s.validation_failures      = self.validation_failures
        s.evaluation_errors        = self.evaluation_errors
        s.total_processing_time_ms = self.total_processing_time_ms
        s.uptime_start             = self.uptime_start
        return s
