"""
compliance.py -- iios.ai.governance.compliance
================================================
:class:`ComplianceFramework` — compliance framework identifier.
:class:`ComplianceRule`      — immutable compliance rule definition.
:class:`ComplianceResult`    — result of evaluating one rule.
:class:`ComplianceReport`    — aggregate compliance report.
:class:`ComplianceManager`   — thread-safe compliance evaluation engine.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple

from ..core.governance_metadata import GovernanceSeverity
from ..exceptions.governance_exceptions import (
    AIComplianceRuleNotFoundError,
    AIComplianceViolationError,
)


class ComplianceFramework(str, Enum):
    """Compliance framework or regulation identifier."""
    INTERNAL  = "internal"
    ISO_27001 = "iso_27001"
    SOC2      = "soc2"
    GDPR      = "gdpr"
    HIPAA     = "hipaa"
    CUSTOM    = "custom"


@dataclass(frozen=True)
class ComplianceRule:
    """Immutable compliance rule definition."""

    rule_id:     str
    name:        str
    framework:   ComplianceFramework
    description: str
    severity:    GovernanceSeverity
    is_blocking: bool
    metadata:    FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        name:        str,
        framework:   ComplianceFramework  = ComplianceFramework.INTERNAL,
        description: str                  = "",
        severity:    GovernanceSeverity   = GovernanceSeverity.MEDIUM,
        is_blocking: bool                 = False,
        **metadata: Any,
    ) -> "ComplianceRule":
        return cls(
            rule_id     = str(uuid.uuid4()),
            name        = name,
            framework   = framework,
            description = description,
            severity    = severity,
            is_blocking = is_blocking,
            metadata    = frozenset(metadata.items()),
        )


@dataclass(frozen=True)
class ComplianceResult:
    """Immutable result of evaluating one compliance rule against a subject."""

    result_id:    str
    rule_id:      str
    rule_name:    str
    subject_id:   str
    passed:       bool
    finding:      str
    severity:     GovernanceSeverity
    checked_at:   float

    @classmethod
    def build(
        cls,
        rule:       ComplianceRule,
        subject_id: str,
        passed:     bool,
        finding:    str = "",
    ) -> "ComplianceResult":
        return cls(
            result_id  = str(uuid.uuid4()),
            rule_id    = rule.rule_id,
            rule_name  = rule.name,
            subject_id = subject_id,
            passed     = passed,
            finding    = finding,
            severity   = rule.severity,
            checked_at = time.time(),
        )


@dataclass(frozen=True)
class ComplianceReport:
    """Immutable aggregate compliance report for a subject."""

    report_id:       str
    subject_id:      str
    framework:       str
    total_rules:     int
    passed_rules:    int
    failed_rules:    int
    blocking_failures: FrozenSet[str]
    overall_passed:  bool
    compliance_score: float   # 0.0–1.0
    generated_at:    float
    results:         tuple    # Tuple[ComplianceResult, ...]

    @classmethod
    def build(
        cls,
        subject_id: str,
        results:    List[ComplianceResult],
        framework:  str = "internal",
    ) -> "ComplianceReport":
        total   = len(results)
        passed  = sum(1 for r in results if r.passed)
        failed  = total - passed
        blocking = frozenset(
            r.rule_name for r in results
            if not r.passed and r.severity in (GovernanceSeverity.HIGH, GovernanceSeverity.CRITICAL)
        )
        score   = (passed / total) if total else 1.0
        return cls(
            report_id        = str(uuid.uuid4()),
            subject_id       = subject_id,
            framework        = framework,
            total_rules      = total,
            passed_rules     = passed,
            failed_rules     = failed,
            blocking_failures = blocking,
            overall_passed   = len(blocking) == 0,
            compliance_score = round(score, 4),
            generated_at     = time.time(),
            results          = tuple(results),
        )

    def failure_rate(self) -> float:
        return (self.failed_rules / self.total_rules) if self.total_rules else 0.0


# ── Checker function type ─────────────────────────────────────────────────────
CheckerFn = Callable[[Any, ComplianceRule], bool]
"""Callable that checks ``(subject, rule)`` → bool."""


class ComplianceManager:
    """
    Thread-safe compliance evaluation engine.

    Evaluates a subject against registered compliance rules using
    optional custom checker functions per framework.
    """

    def __init__(self, default_checker: Optional[CheckerFn] = None) -> None:
        self._lock:     threading.Lock                = threading.Lock()
        self._rules:    Dict[str, ComplianceRule]     = {}
        self._checker:  CheckerFn                     = default_checker or self._default_checker

    # ── rule management ───────────────────────────────────────────────────────

    def add_rule(self, rule: ComplianceRule) -> None:
        with self._lock:
            self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> None:
        with self._lock:
            self._rules.pop(rule_id, None)

    def get_rule(self, rule_id: str) -> ComplianceRule:
        with self._lock:
            r = self._rules.get(rule_id)
        if r is None:
            raise AIComplianceRuleNotFoundError(f"Rule {rule_id!r} not found")
        return r

    def list_rules(
        self,
        framework: Optional[ComplianceFramework] = None,
    ) -> List[ComplianceRule]:
        with self._lock:
            rules = list(self._rules.values())
        if framework:
            rules = [r for r in rules if r.framework == framework]
        return rules

    def rule_count(self) -> int:
        with self._lock:
            return len(self._rules)

    # ── evaluation ────────────────────────────────────────────────────────────

    def check(
        self,
        subject_id: str,
        subject:    Any,
        framework:  Optional[ComplianceFramework] = None,
        raise_on_blocking: bool = False,
    ) -> ComplianceReport:
        """
        Evaluate ``subject`` against all (or framework-scoped) compliance rules.

        :param raise_on_blocking: if True, raises :class:`AIComplianceViolationError`
                                  when a blocking rule fails.
        """
        rules = self.list_rules(framework)
        results: List[ComplianceResult] = []
        for rule in rules:
            try:
                passed = self._checker(subject, rule)
            except Exception:
                passed = False
            finding = "" if passed else f"Rule {rule.name!r} not satisfied"
            results.append(ComplianceResult.build(rule, subject_id, passed, finding))

        report = ComplianceReport.build(
            subject_id = subject_id,
            results    = results,
            framework  = framework.value if framework else "all",
        )
        if raise_on_blocking and not report.overall_passed:
            raise AIComplianceViolationError(
                f"Compliance violations for {subject_id!r}: {sorted(report.blocking_failures)}"
            )
        return report

    # ── default checker ───────────────────────────────────────────────────────

    @staticmethod
    def _default_checker(subject: Any, rule: ComplianceRule) -> bool:
        """Default pass-all checker. Replace in production."""
        return True
