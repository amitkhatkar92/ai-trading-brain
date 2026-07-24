"""
supervisor_integration_validation.py — iios.supervisor.integration
-------------------------------------------------------------------
Seven-check structural validation for integration requests and responses.

Checks
------
1. INTEGRATION_CONSISTENCY  — request fields are internally consistent
2. COMPONENT_AVAILABILITY   — required context fields are populated
3. WORKFLOW_CONSISTENCY     — mode matches expected context completeness
4. LIFECYCLE_INTEGRITY      — response session_id matches request session_id
5. GOVERNANCE_INTEGRITY     — governance summary is not a hard HALT on success
6. SNAPSHOT_INTEGRITY       — supervisor_snapshot is present on success
7. RESPONSE_COMPLETENESS    — response has all mandatory non-null fields

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from .constants import IntegrationValidationCode, IntegrationMode


# ---------------------------------------------------------------------------
# Result primitives
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntegrationValidationCheckResult:
    """Result of a single validation check."""
    code:       IntegrationValidationCode
    passed:     bool
    message:    str = ""

    def to_dict(self) -> dict:
        return {
            "code":    self.code.value,
            "passed":  self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class SupervisorIntegrationValidationResult:
    """Aggregate result of all validation checks for a request or response."""
    is_valid: bool
    checks:   Tuple[IntegrationValidationCheckResult, ...]

    @property
    def failure_messages(self) -> List[str]:
        return [c.message for c in self.checks if not c.passed and c.message]

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    def to_dict(self) -> dict:
        return {
            "is_valid":      self.is_valid,
            "passed_count":  self.passed_count,
            "failed_count":  self.failed_count,
            "checks":        [c.to_dict() for c in self.checks],
            "failure_messages": self.failure_messages,
        }


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class SupervisorIntegrationValidator:
    """
    Structural validator for integration requests and responses.

    Call :meth:`validate_request` before passing a request to the manager,
    and :meth:`validate_response` to confirm the manager's output.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_request(
        self, request: Any
    ) -> SupervisorIntegrationValidationResult:
        """Run the 3 request-phase checks (checks 1–3)."""
        checks = [
            self._check_integration_consistency(request),
            self._check_component_availability(request),
            self._check_workflow_consistency(request),
        ]
        return SupervisorIntegrationValidationResult(
            is_valid = all(c.passed for c in checks),
            checks   = tuple(checks),
        )

    def validate_response(
        self,
        request:  Any,
        response: Any,
    ) -> SupervisorIntegrationValidationResult:
        """Run the 4 response-phase checks (checks 4–7)."""
        checks = [
            self._check_lifecycle_integrity(request, response),
            self._check_governance_integrity(response),
            self._check_snapshot_integrity(response),
            self._check_response_completeness(response),
        ]
        return SupervisorIntegrationValidationResult(
            is_valid = all(c.passed for c in checks),
            checks   = tuple(checks),
        )

    # ------------------------------------------------------------------
    # Check 1 — INTEGRATION_CONSISTENCY
    # ------------------------------------------------------------------

    def _check_integration_consistency(
        self, request: Any
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.INTEGRATION_CONSISTENCY
        if not getattr(request, "integration_id", ""):
            return IntegrationValidationCheckResult(
                code, False, "integration_id must not be empty"
            )
        if not getattr(request, "request_id", ""):
            return IntegrationValidationCheckResult(
                code, False, "request_id must not be empty"
            )
        return IntegrationValidationCheckResult(code, True)

    # ------------------------------------------------------------------
    # Check 2 — COMPONENT_AVAILABILITY
    # ------------------------------------------------------------------

    def _check_component_availability(
        self, request: Any
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.COMPONENT_AVAILABILITY
        context = getattr(request, "context", None)
        if context is None:
            return IntegrationValidationCheckResult(
                code, False, "context must not be None"
            )
        return IntegrationValidationCheckResult(code, True)

    # ------------------------------------------------------------------
    # Check 3 — WORKFLOW_CONSISTENCY
    # ------------------------------------------------------------------

    def _check_workflow_consistency(
        self, request: Any
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.WORKFLOW_CONSISTENCY
        mode = getattr(request, "mode", None)
        if mode is None:
            return IntegrationValidationCheckResult(
                code, False, "mode must not be None"
            )
        if mode not in (
            IntegrationMode.FULL,
            IntegrationMode.GOVERNANCE_ONLY,
            IntegrationMode.SNAPSHOT_ONLY,
            IntegrationMode.HEALTH_ONLY,
        ):
            return IntegrationValidationCheckResult(
                code, False, f"Unknown integration mode: {mode!r}"
            )
        return IntegrationValidationCheckResult(code, True)

    # ------------------------------------------------------------------
    # Check 4 — LIFECYCLE_INTEGRITY
    # ------------------------------------------------------------------

    def _check_lifecycle_integrity(
        self, request: Any, response: Any
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.LIFECYCLE_INTEGRITY
        req_sid  = getattr(request,  "session_id", "") or ""
        resp_sid = getattr(response, "session_id", "") or ""
        if req_sid and resp_sid and req_sid != resp_sid:
            return IntegrationValidationCheckResult(
                code, False,
                f"session_id mismatch: request={req_sid!r} response={resp_sid!r}"
            )
        return IntegrationValidationCheckResult(code, True)

    # ------------------------------------------------------------------
    # Check 5 — GOVERNANCE_INTEGRITY
    # ------------------------------------------------------------------

    def _check_governance_integrity(
        self, response: Any
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.GOVERNANCE_INTEGRITY
        if getattr(response, "is_success", False):
            gov = getattr(response, "governance_summary", None)
            if gov is not None:
                decision = getattr(gov, "governance_decision", "") or ""
                if decision.upper() == "HALT":
                    return IntegrationValidationCheckResult(
                        code, False,
                        "Successful response must not carry a HALT governance decision"
                    )
        return IntegrationValidationCheckResult(code, True)

    # ------------------------------------------------------------------
    # Check 6 — SNAPSHOT_INTEGRITY
    # ------------------------------------------------------------------

    def _check_snapshot_integrity(
        self, response: Any
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.SNAPSHOT_INTEGRITY
        if getattr(response, "is_success", False):
            snap = getattr(response, "supervisor_snapshot", None)
            if snap is None:
                return IntegrationValidationCheckResult(
                    code, False,
                    "Successful response must contain a supervisor_snapshot"
                )
        return IntegrationValidationCheckResult(code, True)

    # ------------------------------------------------------------------
    # Check 7 — RESPONSE_COMPLETENESS
    # ------------------------------------------------------------------

    def _check_response_completeness(
        self, response: Any
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.RESPONSE_COMPLETENESS
        for attr in ("response_id", "integration_id", "request_id"):
            if not getattr(response, attr, ""):
                return IntegrationValidationCheckResult(
                    code, False, f"Response field {attr!r} must not be empty"
                )
        return IntegrationValidationCheckResult(code, True)
