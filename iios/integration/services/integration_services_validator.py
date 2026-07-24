"""
integration_services_validator.py — iios.integration.services
---------------------------------------------------------------
IntegrationServicesValidator — runs 6 structural checks against a
ConnectorRequest before it enters the execution pipeline.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from .connector_request import ConnectorRequest
from .constants import ServiceValidationCheck


@dataclass(frozen=True)
class ServiceValidationIssue:
    """A single validation issue."""
    check:    ServiceValidationCheck
    severity: str   # "error" | "warning"
    message:  str


@dataclass(frozen=True)
class ServiceValidationReport:
    """Complete validation report for one ConnectorRequest."""
    request_id: str
    passed:     bool
    issues:     tuple              # tuple[ServiceValidationIssue, ...]
    checked_at: str

    @property
    def errors(self) -> List[ServiceValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[ServiceValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


class IntegrationServicesValidator:
    """
    Validates ConnectorRequests against 6 structural checks.

    Raises no exceptions — all problems are returned in the report.
    """

    def validate(self, request: ConnectorRequest) -> ServiceValidationReport:
        issues: List[ServiceValidationIssue] = []

        self._check_connector_compatibility(request, issues)
        self._check_protocol_compatibility(request, issues)
        self._check_auth_validity(request, issues)
        self._check_response_integrity(request, issues)
        self._check_connection_health(request, issues)
        self._check_transport_availability(request, issues)

        passed = not any(i.severity == "error" for i in issues)
        return ServiceValidationReport(
            request_id = request.request_id,
            passed     = passed,
            issues     = tuple(issues),
            checked_at = datetime.now(timezone.utc).isoformat(),
        )

    # ── Checks ────────────────────────────────────────────────────────────

    def _check_connector_compatibility(
        self, req: ConnectorRequest, issues: List[ServiceValidationIssue]
    ) -> None:
        if not req.service_type:
            issues.append(ServiceValidationIssue(
                check    = ServiceValidationCheck.CONNECTOR_COMPATIBILITY,
                severity = "error",
                message  = "service_type is missing",
            ))

    def _check_protocol_compatibility(
        self, req: ConnectorRequest, issues: List[ServiceValidationIssue]
    ) -> None:
        if not req.transport_type:
            issues.append(ServiceValidationIssue(
                check    = ServiceValidationCheck.PROTOCOL_COMPATIBILITY,
                severity = "warning",
                message  = "transport_type not specified — defaulting to HTTP",
            ))

    def _check_auth_validity(
        self, req: ConnectorRequest, issues: List[ServiceValidationIssue]
    ) -> None:
        from .constants import AuthScheme
        if req.auth_scheme != AuthScheme.NONE and not req.auth_config:
            issues.append(ServiceValidationIssue(
                check    = ServiceValidationCheck.AUTH_VALIDITY,
                severity = "warning",
                message  = f"auth_scheme={req.auth_scheme.value!r} but auth_config is empty",
            ))

    def _check_response_integrity(
        self, req: ConnectorRequest, issues: List[ServiceValidationIssue]
    ) -> None:
        if req.timeout_ms <= 0:
            issues.append(ServiceValidationIssue(
                check    = ServiceValidationCheck.RESPONSE_INTEGRITY,
                severity = "error",
                message  = f"timeout_ms must be > 0, got {req.timeout_ms}",
            ))

    def _check_connection_health(
        self, req: ConnectorRequest, issues: List[ServiceValidationIssue]
    ) -> None:
        if not req.endpoint:
            issues.append(ServiceValidationIssue(
                check    = ServiceValidationCheck.CONNECTION_HEALTH,
                severity = "error",
                message  = "endpoint is empty",
            ))

    def _check_transport_availability(
        self, req: ConnectorRequest, issues: List[ServiceValidationIssue]
    ) -> None:
        if req.retry_max_attempts < 0:
            issues.append(ServiceValidationIssue(
                check    = ServiceValidationCheck.TRANSPORT_AVAILABILITY,
                severity = "warning",
                message  = f"retry_max_attempts={req.retry_max_attempts} is negative — defaulting to 0",
            ))
