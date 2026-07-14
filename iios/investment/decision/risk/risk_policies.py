"""iios/investment/decision/risk/risk_policies.py
PolicyValidator — validates a DecisionRisk against risk policies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.risk.decision_risk import DecisionRisk
from iios.investment.decision.risk.risk_constants import (
    CRITICAL_RISK_THRESHOLD,
    HIGH_RISK_THRESHOLD,
    MAX_ALLOWED_RISK_DEFAULT,
    RiskPolicyStatus,
)


@dataclass(frozen=True)
class PolicyViolation:
    rule:          str
    actual_value:  float
    limit:         float
    message:       str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule":         self.rule,
            "actual_value": round(self.actual_value, 4),
            "limit":        round(self.limit, 4),
            "message":      self.message,
        }


@dataclass(frozen=True)
class PolicyValidationResult:
    status:     RiskPolicyStatus
    violations: Tuple[PolicyViolation, ...]
    warnings:   Tuple[PolicyViolation, ...]

    @property
    def allows_execution(self) -> bool:
        return self.status.allows_execution

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status":     self.status.value,
            "violations": [v.to_dict() for v in self.violations],
            "warnings":   [v.to_dict() for v in self.warnings],
        }


class PolicyValidator:
    """Validates a DecisionRisk against configurable risk policies."""

    def __init__(self, max_allowed_risk: float = MAX_ALLOWED_RISK_DEFAULT) -> None:
        self._max_allowed = max_allowed_risk

    def validate(self, decision_risk: DecisionRisk) -> PolicyValidationResult:
        violations: List[PolicyViolation] = []
        warnings:   List[PolicyViolation] = []

        # Hard limit
        if decision_risk.overall_risk >= self._max_allowed:
            violations.append(PolicyViolation(
                rule="max_overall_risk",
                actual_value=decision_risk.overall_risk,
                limit=self._max_allowed,
                message=f"Overall risk {decision_risk.overall_risk:.1f} ≥ limit {self._max_allowed:.1f}",
            ))

        # Critical threshold
        if decision_risk.overall_risk >= CRITICAL_RISK_THRESHOLD:
            violations.append(PolicyViolation(
                rule="critical_risk_threshold",
                actual_value=decision_risk.overall_risk,
                limit=CRITICAL_RISK_THRESHOLD,
                message="Decision is at CRITICAL risk level",
            ))

        # Warning threshold
        if decision_risk.overall_risk >= HIGH_RISK_THRESHOLD and not violations:
            warnings.append(PolicyViolation(
                rule="high_risk_warning",
                actual_value=decision_risk.overall_risk,
                limit=HIGH_RISK_THRESHOLD,
                message=f"Overall risk {decision_risk.overall_risk:.1f} is HIGH",
            ))

        # Controls-breached override
        if decision_risk.controls_breached:
            violations.append(PolicyViolation(
                rule="controls_breached",
                actual_value=1.0,
                limit=0.0,
                message="One or more hard risk controls are breached",
            ))

        if violations:
            status = RiskPolicyStatus.VIOLATION
        elif warnings:
            status = RiskPolicyStatus.WARNING
        else:
            status = RiskPolicyStatus.COMPLIANT

        return PolicyValidationResult(
            status=status,
            violations=tuple(violations),
            warnings=tuple(warnings),
        )
