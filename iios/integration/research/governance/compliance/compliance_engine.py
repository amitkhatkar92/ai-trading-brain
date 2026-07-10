"""compliance/compliance_engine.py — Compliance orchestrator."""
from __future__ import annotations

from typing import Any, Callable, Optional

from iios.integration.research.governance.governance_constants import ComplianceStatus, PolicyType
from iios.integration.research.governance.compliance.policy_validator import (
    GovernancePolicy,
    PolicyValidator,
    PolicyViolation,
)


class ComplianceEngine:
    """Facade for policy registration and compliance checking."""

    def __init__(self) -> None:
        self._validator  = PolicyValidator()
        self._run_count  = 0

    def register_policy(self, policy: GovernancePolicy) -> None:
        self._validator.register_policy(policy)

    def register_check(self, fn_name: str, fn: Callable[[dict], bool]) -> None:
        self._validator.register_check(fn_name, fn)

    def run_compliance_check(
        self,
        entity: dict[str, Any],
        *,
        policy_id: Optional[str] = None,
    ) -> list[PolicyViolation]:
        self._run_count += 1
        if policy_id:
            return self._validator.validate(entity, policy_id)
        return self._validator.validate_all(entity)

    def compliance_status(self, violations: list[PolicyViolation]) -> ComplianceStatus:
        if not violations:
            return ComplianceStatus.COMPLIANT
        severities = {v.severity for v in violations}
        if "critical" in severities:
            return ComplianceStatus.VIOLATED
        if "high" in severities:
            return ComplianceStatus.VIOLATED
        return ComplianceStatus.WARNING

    def all_policies(self) -> list[GovernancePolicy]:
        return self._validator.all_policies()

    def stats(self) -> dict[str, Any]:
        return {
            "run_count": self._run_count,
            "validator": self._validator.stats(),
        }
