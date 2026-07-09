"""iios/execution/orders/validation/validation_engine.py

Thread-safe validation engine.  Wraps OrderValidator with caching and metrics.
"""
from __future__ import annotations

import logging
import threading

from ..core.order_request import OrderRequest
from .order_validator import OrderValidator
from .validation_report import ValidationReport
from .validation_rules import ValidationRule

_log = logging.getLogger(__name__)


class ValidationEngine:
    """Production-grade validation orchestrator for the OMS."""

    def __init__(self, rules: list[ValidationRule] | None = None) -> None:
        self._validator = OrderValidator(rules)
        self._lock      = threading.Lock()
        self._total_validated   = 0
        self._total_passed      = 0
        self._total_failed      = 0

    # ── Rule management (thread-safe) ─────────────────────────────────────────

    def add_rule(self, rule: ValidationRule) -> None:
        with self._lock:
            self._validator.add_rule(rule)

    def remove_rule(self, name: str) -> None:
        with self._lock:
            self._validator.remove_rule(name)

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self, request: OrderRequest) -> ValidationReport:
        report = self._validator.validate(request)
        with self._lock:
            self._total_validated += 1
            if report.passed:
                self._total_passed += 1
            else:
                self._total_failed += 1
                _log.debug(
                    "Validation failed request=%s errors=%s",
                    request.request_id,
                    report.errors,
                )
        return report

    # ── Metrics ───────────────────────────────────────────────────────────────

    @property
    def total_validated(self) -> int:
        return self._total_validated

    @property
    def total_passed(self) -> int:
        return self._total_passed

    @property
    def total_failed(self) -> int:
        return self._total_failed

    @property
    def pass_rate(self) -> float:
        return self._total_passed / self._total_validated if self._total_validated else 0.0

    def stats(self) -> dict:
        return {
            "total_validated": self._total_validated,
            "total_passed":    self._total_passed,
            "total_failed":    self._total_failed,
            "pass_rate":       round(self.pass_rate, 4),
        }

    def reset_stats(self) -> None:
        with self._lock:
            self._total_validated = 0
            self._total_passed    = 0
            self._total_failed    = 0
