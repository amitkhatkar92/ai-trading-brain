"""iios/decision_policies/compliance/compliance_policy.py — Compliance policy base + result model."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from ..policy_constants import ComplianceCategory
from ..policy_context import EvaluationContext


@dataclass
class ComplianceResult:
    policy_id:       str
    policy_name:     str
    category:        ComplianceCategory = ComplianceCategory.INTERNAL
    passed:          bool               = True
    mandatory:       bool               = True
    reason:          str                = ""
    violations:      list[str]          = field(default_factory=list)
    recommendations: list[str]          = field(default_factory=list)
    duration_ms:     float              = 0.0
    metadata:        dict               = field(default_factory=dict)
    evaluated_at:    float              = field(default_factory=time.time)

    @property
    def violated(self) -> bool:
        return not self.passed

    @property
    def blocks_decision(self) -> bool:
        return self.violated and self.mandatory

    def to_dict(self) -> dict:
        return {
            "policy_id":   self.policy_id,
            "policy_name": self.policy_name,
            "category":    self.category.value,
            "passed":      self.passed,
            "mandatory":   self.mandatory,
            "reason":      self.reason,
            "violations":  self.violations,
            "duration_ms": self.duration_ms,
        }


class CompliancePolicy(ABC):
    @property
    @abstractmethod
    def policy_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def category(self) -> ComplianceCategory:
        return ComplianceCategory.INTERNAL

    @property
    def mandatory(self) -> bool:
        return True

    def is_applicable(self, context: EvaluationContext) -> bool:
        return True

    @abstractmethod
    def check(self, context: EvaluationContext) -> ComplianceResult: ...

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "name":      self.name,
            "category":  self.category.value,
            "mandatory": self.mandatory,
        }


class StaticCompliancePolicy(CompliancePolicy):
    """Compliance policy backed by a callable checker."""

    def __init__(
        self,
        policy_id:  str,
        name:       str,
        checker:    Callable[[EvaluationContext], tuple[bool, str]],
        *,
        category:   ComplianceCategory = ComplianceCategory.INTERNAL,
        mandatory:  bool = True,
        condition:  Callable[[EvaluationContext], bool] | None = None,
    ) -> None:
        self._policy_id = policy_id
        self._name      = name
        self._checker   = checker
        self._category  = category
        self._mandatory = mandatory
        self._condition = condition

    @property
    def policy_id(self) -> str:
        return self._policy_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> ComplianceCategory:
        return self._category

    @property
    def mandatory(self) -> bool:
        return self._mandatory

    def is_applicable(self, context: EvaluationContext) -> bool:
        if self._condition is not None:
            return bool(self._condition(context))
        return True

    def check(self, context: EvaluationContext) -> ComplianceResult:
        t0 = time.perf_counter()
        if not self.is_applicable(context):
            return ComplianceResult(
                policy_id   = self._policy_id,
                policy_name = self._name,
                category    = self._category,
                passed      = True,
                mandatory   = self._mandatory,
                reason      = "not applicable (skipped)",
                duration_ms = (time.perf_counter() - t0) * 1_000,
            )
        try:
            passed, reason = self._checker(context)
        except Exception as exc:  # noqa: BLE001
            return ComplianceResult(
                policy_id   = self._policy_id,
                policy_name = self._name,
                category    = self._category,
                passed      = False,
                mandatory   = self._mandatory,
                reason      = f"check error: {exc}",
                violations  = [str(exc)],
                duration_ms = (time.perf_counter() - t0) * 1_000,
            )
        viol = [] if passed else [reason]
        return ComplianceResult(
            policy_id   = self._policy_id,
            policy_name = self._name,
            category    = self._category,
            passed      = passed,
            mandatory   = self._mandatory,
            reason      = reason,
            violations  = viol,
            duration_ms = (time.perf_counter() - t0) * 1_000,
        )
