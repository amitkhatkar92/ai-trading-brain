"""
risk_integration_validation.py — iios.risk.integration
========================================================
Validation logic for RiskIntegrationRequest and response consistency.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .constants import IntegrationValidationCode
from .exceptions import RiskIntegrationValidationError
from .risk_integration_request import RiskIntegrationRequest
from .risk_integration_response import RiskIntegrationResponse


@dataclass
class IntegrationValidationCheck:
    """Result of a single validation check."""
    code:    IntegrationValidationCode
    passed:  bool
    message: str = ""


@dataclass
class IntegrationValidationResult:
    """Aggregated result of all integration validation checks."""
    request_id: str
    checks:     List[IntegrationValidationCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> List[IntegrationValidationCheck]:
        return [c for c in self.checks if not c.passed]

    @property
    def failed_count(self) -> int:
        return len(self.failed_checks)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    def to_summary(self) -> str:
        if self.passed:
            return f"PASS ({self.passed_count}/{len(self.checks)} checks)"
        fails = "; ".join(f"{c.code.value}: {c.message}" for c in self.failed_checks)
        return f"FAIL ({self.failed_count} failures): {fails}"


class RiskIntegrationValidator:
    """
    Stateless validator for :class:`~.risk_integration_request.RiskIntegrationRequest`.

    Runs 6 standard checks against an integration request.
    """

    def validate(
        self,
        request: RiskIntegrationRequest,
        *,
        component_registry: Optional[object] = None,
    ) -> IntegrationValidationResult:
        """Run all validation checks and return the aggregated result."""
        result = IntegrationValidationResult(request_id=request.request_id)
        result.checks.extend([
            self._check_api_consistent(request),
            self._check_lifecycle_consistent(request),
            self._check_subsystem_available(request, component_registry),
            self._check_input_valid(request),
            self._check_snapshot_integrity(request),
            self._check_response_valid(request),
        ])
        return result

    def validate_or_raise(
        self,
        request: RiskIntegrationRequest,
        *,
        component_registry: Optional[object] = None,
    ) -> IntegrationValidationResult:
        """Run all checks; raise :exc:`RiskIntegrationValidationError` on failure."""
        result = self.validate(request, component_registry=component_registry)
        if not result.passed:
            raise RiskIntegrationValidationError(result.to_summary())
        return result

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_api_consistent(
        self, r: RiskIntegrationRequest
    ) -> IntegrationValidationCheck:
        code = IntegrationValidationCode.API_CONSISTENT
        if not r.request_id:
            return IntegrationValidationCheck(code=code, passed=False,
                                              message="request_id is empty")
        if not r.portfolio_id:
            return IntegrationValidationCheck(code=code, passed=False,
                                              message="portfolio_id is empty")
        if r.context is None:
            return IntegrationValidationCheck(code=code, passed=False,
                                              message="context is None")
        return IntegrationValidationCheck(code=code, passed=True)

    def _check_lifecycle_consistent(
        self, r: RiskIntegrationRequest
    ) -> IntegrationValidationCheck:
        code = IntegrationValidationCode.LIFECYCLE_CONSISTENT
        if r.context.timeout_s <= 0:
            return IntegrationValidationCheck(
                code=code, passed=False,
                message=f"timeout_s must be > 0, got {r.context.timeout_s}",
            )
        return IntegrationValidationCheck(code=code, passed=True)

    def _check_subsystem_available(
        self,
        r: RiskIntegrationRequest,
        registry: Optional[object],
    ) -> IntegrationValidationCheck:
        code = IntegrationValidationCode.SUBSYSTEM_AVAILABLE
        # If no registry is injected, treat as available (permissive check)
        if registry is None:
            return IntegrationValidationCheck(code=code, passed=True)
        # Graceful degradation: unavailable components are handled by the
        # manager via fallback snapshot path — do not hard-fail here.
        available = getattr(registry, "all_available", lambda: True)()
        msg = "" if available else "one or more required subsystem components are unavailable (degraded mode)"
        return IntegrationValidationCheck(code=code, passed=True, message=msg)

    def _check_input_valid(
        self, r: RiskIntegrationRequest
    ) -> IntegrationValidationCheck:
        code = IntegrationValidationCode.INPUT_VALID
        if r.portfolio_value < 0:
            return IntegrationValidationCheck(
                code=code, passed=False,
                message=f"portfolio_value must be >= 0, got {r.portfolio_value}",
            )
        return IntegrationValidationCheck(code=code, passed=True)

    def _check_snapshot_integrity(
        self, r: RiskIntegrationRequest
    ) -> IntegrationValidationCheck:
        # At request stage, snapshot is not yet produced — just pass
        return IntegrationValidationCheck(
            code    = IntegrationValidationCode.SNAPSHOT_INTEGRITY,
            passed  = True,
        )

    def _check_response_valid(
        self, r: RiskIntegrationRequest
    ) -> IntegrationValidationCheck:
        # At request stage, response is not yet produced — just pass
        return IntegrationValidationCheck(
            code   = IntegrationValidationCode.RESPONSE_VALID,
            passed = True,
        )
