"""
integration_gateway_validation.py — iios.integration.gateway
--------------------------------------------------------------
Gateway request, response, and state validation.

Runs 7 checks in VALIDATION_CHECK_ORDER:
  1. GATEWAY_CONSISTENCY   — gateway must be ACTIVE
  2. WORKFLOW_CONSISTENCY  — workflow_id and enterprise_id must be non-empty
  3. COMPONENT_AVAILABILITY — all required components must be registered
  4. LIFECYCLE_INTEGRITY   — lifecycle component available
  5. GOVERNANCE_INTEGRITY  — policies component available
  6. SNAPSHOT_INTEGRITY    — snapshot component available
  7. RESPONSE_COMPLETENESS — response_id and completed_at present

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    GatewayComponentType,
    GatewayOperationType,
    GatewayState,
    GatewayValidationCheck,
    OPERATION_REQUIRED_COMPONENTS,
    VALIDATION_CHECK_ORDER,
)
from .integration_gateway_request import IntegrationGatewayRequest
from .integration_gateway_response import IntegrationGatewayResponse


# ════════════════════════════════════════════════════════════════════════
# Issue and Report
# ════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class GatewayValidationIssue:
    """A single validation issue found during a gateway check."""
    check:    GatewayValidationCheck
    severity: str          # "error" | "warning"
    message:  str


@dataclass(frozen=True)
class GatewayValidationReport:
    """Result of running all gateway validation checks."""

    request_id: str
    issues:     Tuple[GatewayValidationIssue, ...]
    passed:     bool
    checked_at: str

    @property
    def errors(self) -> List[GatewayValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[GatewayValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


# ════════════════════════════════════════════════════════════════════════
# Validator
# ════════════════════════════════════════════════════════════════════════


class IntegrationGatewayValidation:
    """
    Runs all 7 gateway validation checks against a request.

    The validator is stateless; every call to *validate_request*
    produces a fresh GatewayValidationReport.

    The optional *gateway_state* and *available_components* parameters
    allow the gateway to pass its own runtime state so checks 1, 3, 4,
    5, and 6 can be performed accurately.
    """

    # ─── public entry points ─────────────────────────────────────────

    def validate_request(
        self,
        request:              IntegrationGatewayRequest,
        *,
        gateway_state:        Optional[GatewayState]           = None,
        available_components: Optional[List[GatewayComponentType]] = None,
    ) -> GatewayValidationReport:
        """Run all 7 checks and return a report."""
        issues: List[GatewayValidationIssue] = []
        ctx = {
            "gateway_state":        gateway_state,
            "available_components": available_components or [],
        }

        check_methods = {
            GatewayValidationCheck.GATEWAY_CONSISTENCY:   self._check_gateway_consistency,
            GatewayValidationCheck.WORKFLOW_CONSISTENCY:  self._check_workflow_consistency,
            GatewayValidationCheck.COMPONENT_AVAILABILITY: self._check_component_availability,
            GatewayValidationCheck.LIFECYCLE_INTEGRITY:   self._check_lifecycle_integrity,
            GatewayValidationCheck.GOVERNANCE_INTEGRITY:  self._check_governance_integrity,
            GatewayValidationCheck.SNAPSHOT_INTEGRITY:    self._check_snapshot_integrity,
            GatewayValidationCheck.RESPONSE_COMPLETENESS: self._check_response_completeness_request,
        }

        for check in VALIDATION_CHECK_ORDER:
            method = check_methods[check]
            issues.extend(method(request, ctx))

        passed = all(i.severity != "error" for i in issues)
        return GatewayValidationReport(
            request_id = request.request_id,
            issues     = tuple(issues),
            passed     = passed,
            checked_at = datetime.now(timezone.utc).isoformat(),
        )

    def validate_response(
        self,
        response:      IntegrationGatewayResponse,
        request_id:    str = "",
    ) -> GatewayValidationReport:
        """Validate a gateway response for completeness."""
        issues: List[GatewayValidationIssue] = []

        if not response.response_id:
            issues.append(GatewayValidationIssue(
                check    = GatewayValidationCheck.RESPONSE_COMPLETENESS,
                severity = "error",
                message  = "Response ID is missing",
            ))
        if not response.completed_at:
            issues.append(GatewayValidationIssue(
                check    = GatewayValidationCheck.RESPONSE_COMPLETENESS,
                severity = "error",
                message  = "Response completed_at is missing",
            ))
        if not response.status:
            issues.append(GatewayValidationIssue(
                check    = GatewayValidationCheck.RESPONSE_COMPLETENESS,
                severity = "error",
                message  = "Response status is missing",
            ))

        passed = all(i.severity != "error" for i in issues)
        return GatewayValidationReport(
            request_id = request_id or response.request_id,
            issues     = tuple(issues),
            passed     = passed,
            checked_at = datetime.now(timezone.utc).isoformat(),
        )

    # ─── individual checks ────────────────────────────────────────────

    def _check_gateway_consistency(
        self,
        request: IntegrationGatewayRequest,
        ctx:     Dict[str, Any],
    ) -> List[GatewayValidationIssue]:
        issues: List[GatewayValidationIssue] = []
        gateway_state: Optional[GatewayState] = ctx.get("gateway_state")

        # Only block if state was explicitly provided AND is non-ACTIVE
        if gateway_state is not None and gateway_state != GatewayState.ACTIVE:
            issues.append(GatewayValidationIssue(
                check    = GatewayValidationCheck.GATEWAY_CONSISTENCY,
                severity = "error",
                message  = f"Gateway is not ACTIVE (state={gateway_state.value!r})",
            ))
        return issues

    def _check_workflow_consistency(
        self,
        request: IntegrationGatewayRequest,
        ctx:     Dict[str, Any],
    ) -> List[GatewayValidationIssue]:
        issues: List[GatewayValidationIssue] = []

        if not request.workflow_id:
            issues.append(GatewayValidationIssue(
                check    = GatewayValidationCheck.WORKFLOW_CONSISTENCY,
                severity = "error",
                message  = "workflow_id is required but empty",
            ))
        if not request.enterprise_id:
            issues.append(GatewayValidationIssue(
                check    = GatewayValidationCheck.WORKFLOW_CONSISTENCY,
                severity = "error",
                message  = "enterprise_id is required but empty",
            ))
        if not request.request_id:
            issues.append(GatewayValidationIssue(
                check    = GatewayValidationCheck.WORKFLOW_CONSISTENCY,
                severity = "error",
                message  = "request_id is required but empty",
            ))
        # Warn if workflow_id appears suspicious (too short)
        if request.workflow_id and len(request.workflow_id) < 3:
            issues.append(GatewayValidationIssue(
                check    = GatewayValidationCheck.WORKFLOW_CONSISTENCY,
                severity = "warning",
                message  = f"workflow_id appears too short: {request.workflow_id!r}",
            ))
        return issues

    def _check_component_availability(
        self,
        request: IntegrationGatewayRequest,
        ctx:     Dict[str, Any],
    ) -> List[GatewayValidationIssue]:
        issues: List[GatewayValidationIssue] = []
        available: List[GatewayComponentType] = ctx.get("available_components", [])

        if not available:
            # No component info provided — cannot check
            return issues

        required = OPERATION_REQUIRED_COMPONENTS.get(request.operation, [])
        for comp in required:
            if comp not in available:
                issues.append(GatewayValidationIssue(
                    check    = GatewayValidationCheck.COMPONENT_AVAILABILITY,
                    severity = "error",
                    message  = f"Required component {comp.value!r} is not available",
                ))
        return issues

    def _check_lifecycle_integrity(
        self,
        request: IntegrationGatewayRequest,
        ctx:     Dict[str, Any],
    ) -> List[GatewayValidationIssue]:
        issues: List[GatewayValidationIssue] = []
        available: List[GatewayComponentType] = ctx.get("available_components", [])

        if not available:
            return issues

        required = OPERATION_REQUIRED_COMPONENTS.get(request.operation, [])
        if GatewayComponentType.LIFECYCLE in required:
            if GatewayComponentType.LIFECYCLE not in available:
                issues.append(GatewayValidationIssue(
                    check    = GatewayValidationCheck.LIFECYCLE_INTEGRITY,
                    severity = "error",
                    message  = "Lifecycle component is required but not registered",
                ))
        return issues

    def _check_governance_integrity(
        self,
        request: IntegrationGatewayRequest,
        ctx:     Dict[str, Any],
    ) -> List[GatewayValidationIssue]:
        issues: List[GatewayValidationIssue] = []
        available: List[GatewayComponentType] = ctx.get("available_components", [])

        if not available:
            return issues

        required = OPERATION_REQUIRED_COMPONENTS.get(request.operation, [])
        if GatewayComponentType.POLICIES in required:
            if GatewayComponentType.POLICIES not in available:
                issues.append(GatewayValidationIssue(
                    check    = GatewayValidationCheck.GOVERNANCE_INTEGRITY,
                    severity = "error",
                    message  = "Governance (policies) component is required but not registered",
                ))
        return issues

    def _check_snapshot_integrity(
        self,
        request: IntegrationGatewayRequest,
        ctx:     Dict[str, Any],
    ) -> List[GatewayValidationIssue]:
        issues: List[GatewayValidationIssue] = []
        available: List[GatewayComponentType] = ctx.get("available_components", [])

        if not available:
            return issues

        required = OPERATION_REQUIRED_COMPONENTS.get(request.operation, [])
        if GatewayComponentType.SNAPSHOT in required:
            if GatewayComponentType.SNAPSHOT not in available:
                issues.append(GatewayValidationIssue(
                    check    = GatewayValidationCheck.SNAPSHOT_INTEGRITY,
                    severity = "error",
                    message  = "Snapshot component is required but not registered",
                ))
        return issues

    def _check_response_completeness_request(
        self,
        request: IntegrationGatewayRequest,
        ctx:     Dict[str, Any],
    ) -> List[GatewayValidationIssue]:
        """
        For a request, check that submitted_at is present (request completeness).
        """
        issues: List[GatewayValidationIssue] = []
        if not request.submitted_at:
            issues.append(GatewayValidationIssue(
                check    = GatewayValidationCheck.RESPONSE_COMPLETENESS,
                severity = "error",
                message  = "Request submitted_at timestamp is missing",
            ))
        return issues
