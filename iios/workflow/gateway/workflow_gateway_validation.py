"""
workflow_gateway_validation.py — iios.workflow.gateway
-------------------------------------------------------
WorkflowGatewayValidation — validates gateway requests and responses.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .exceptions import WorkflowGatewayValidationError
from .workflow_gateway_request import WorkflowGatewayRequest
from .workflow_gateway_response import WorkflowGatewayResponse


@dataclass(frozen=True)
class GatewayValidationResult:
    """Immutable result of gateway validation."""
    target_id: str
    valid:     bool
    issues:    tuple   # Tuple[str, ...]

    @property
    def issue_list(self) -> List[str]:
        return list(self.issues)

    def to_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "valid":     self.valid,
            "issues":    list(self.issues),
        }


class WorkflowGatewayValidation:
    """
    Stateless gateway request/response validator.

    Thread-safe (no mutable state).
    """

    # ── Request validation ────────────────────────────────────────────────────

    def validate_request(self, request: WorkflowGatewayRequest) -> GatewayValidationResult:
        issues: List[str] = []

        if not request.workflow_id:
            issues.append("workflow_id must not be empty")
        if not request.workflow_name:
            issues.append("workflow_name must not be empty")
        if not request.enterprise_id:
            issues.append("enterprise_id must not be empty")
        if not request.correlation_id:
            issues.append("correlation_id must not be empty")
        if not request.created_at:
            issues.append("created_at timestamp is missing")
        if request.priority < 0 or request.priority > 10:
            issues.append(f"priority must be 0–10, got {request.priority}")

        return GatewayValidationResult(
            target_id = request.request_id,
            valid     = len(issues) == 0,
            issues    = tuple(issues),
        )

    def validate_request_or_raise(self, request: WorkflowGatewayRequest) -> None:
        result = self.validate_request(request)
        if not result.valid:
            raise WorkflowGatewayValidationError(
                f"Invalid gateway request: {result.issues}",
                issues=result.issue_list,
            )

    # ── Response validation ───────────────────────────────────────────────────

    def validate_response(self, response: WorkflowGatewayResponse) -> GatewayValidationResult:
        issues: List[str] = []

        if not response.response_id:
            issues.append("response_id must not be empty")
        if not response.request_id:
            issues.append("request_id must not be empty")
        if not response.workflow_id:
            issues.append("workflow_id must not be empty")
        if not response.created_at:
            issues.append("created_at timestamp is missing")

        return GatewayValidationResult(
            target_id = response.response_id,
            valid     = len(issues) == 0,
            issues    = tuple(issues),
        )

    def validate_response_or_raise(self, response: WorkflowGatewayResponse) -> None:
        result = self.validate_response(response)
        if not result.valid:
            raise WorkflowGatewayValidationError(
                f"Invalid gateway response: {result.issues}",
                issues=result.issue_list,
            )
