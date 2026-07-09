"""iios/execution/orders/validation/order_validator.py

Applies a configurable list of ValidationRule objects to an OrderRequest.
"""
from __future__ import annotations

import time

from ..core.order_request import OrderRequest
from .validation_report import RuleResult, ValidationReport
from .validation_rules import DEFAULT_RULES, ValidationRule


class OrderValidator:
    """Single-shot validator for an OrderRequest."""

    def __init__(self, rules: list[ValidationRule] | None = None) -> None:
        self._rules: list[ValidationRule] = rules if rules is not None else list(DEFAULT_RULES)

    # ── Rule management ───────────────────────────────────────────────────────

    def add_rule(self, rule: ValidationRule) -> None:
        self._rules.append(rule)

    def remove_rule(self, name: str) -> None:
        self._rules = [r for r in self._rules if r.name != name]

    @property
    def rules(self) -> list[ValidationRule]:
        return list(self._rules)

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self, request: OrderRequest) -> ValidationReport:
        t0     = time.perf_counter()
        report = ValidationReport(request_id=request.request_id)

        for rule in self._rules:
            passed, errors, warnings = rule.validate(request)
            report.add_result(RuleResult(
                rule_name = rule.name,
                passed    = passed,
                errors    = errors,
                warnings  = warnings,
            ))

        report.finalise()
        report.duration_ms = (time.perf_counter() - t0) * 1000.0
        return report
