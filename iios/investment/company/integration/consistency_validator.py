"""iios/investment/company/integration/consistency_validator.py
Runs consistency rules and produces a ValidationReport.
"""
from __future__ import annotations

from typing import Any, List, Optional

from iios.investment.company.integration.consistency_rules import ALL_RULES
from iios.investment.company.integration.validation_report import ValidationCheck, ValidationReport


class ConsistencyValidator:
    """
    Stateless validator — runs all registered consistency rules against
    an AggregatedIntelligence object and assembles a ValidationReport.

    Additional rules can be registered at runtime without modifying this class.
    """

    def __init__(self) -> None:
        self._rules = list(ALL_RULES)

    def register_rule(self, rule) -> None:
        """Register a custom rule callable."""
        if rule not in self._rules:
            self._rules.append(rule)

    def validate(self, ticker: str, intel: Any) -> ValidationReport:
        """
        Run all rules against *intel* (AggregatedIntelligence) and return
        a ValidationReport.

        Rules that raise an exception are silently skipped to avoid
        crashing the integration pipeline.
        """
        report = ValidationReport(ticker=ticker)
        for rule in self._rules:
            try:
                check: Optional[ValidationCheck] = rule(intel)
                if check is not None:
                    report.checks.append(check)
            except Exception:
                # Rule failure must never propagate
                pass
        return report

    def rule_count(self) -> int:
        return len(self._rules)
