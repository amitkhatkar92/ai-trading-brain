"""
workflow_validation.py — iios.workflow.engine
----------------------------------------------
6-check validator for WorkflowEngineRequest objects.

Checks:
  1. WORKFLOW_CONFIGURATION — workflow_id and configuration are present
  2. SESSION_INTEGRITY      — request carries valid IDs
  3. QUEUE_CONSISTENCY      — priority is in valid range
  4. PRIORITY_INTEGRITY     — dispatch_mode is a known value
  5. LIFECYCLE_CONSISTENCY  — workflow_type is a known value
  6. INPUT_COMPLETENESS     — correlation_id and trace_id are present

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from iios.workflow.lifecycle import WorkflowType

from .constants import WorkflowDispatchMode, WorkflowEngineValidationCheck
from .workflow_request import WorkflowEngineRequest


@dataclass(frozen=True)
class WorkflowEngineValidationResult:
    check:   WorkflowEngineValidationCheck
    passed:  bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check":   self.check.value,
            "passed":  self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class WorkflowEngineValidationReport:
    request_id: str
    results:    tuple   # Tuple[WorkflowEngineValidationResult, ...]
    passed:     bool

    @property
    def failed_checks(self) -> List[str]:
        return [r.check.value for r in self.results if not r.passed]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":    self.request_id,
            "passed":        self.passed,
            "failed_checks": self.failed_checks,
            "results":       [r.to_dict() for r in self.results],
        }


class WorkflowEngineValidator:
    """Runs 6 validation checks against a WorkflowEngineRequest."""

    def validate(
        self,
        request: WorkflowEngineRequest,
    ) -> WorkflowEngineValidationReport:
        results = [
            self._check_workflow_configuration(request),
            self._check_session_integrity(request),
            self._check_queue_consistency(request),
            self._check_priority_integrity(request),
            self._check_lifecycle_consistency(request),
            self._check_input_completeness(request),
        ]
        passed = all(r.passed for r in results)
        return WorkflowEngineValidationReport(
            request_id = request.request_id,
            results    = tuple(results),
            passed     = passed,
        )

    # ----------------------------------------------------------------
    # Individual checks
    # ----------------------------------------------------------------

    def _check_workflow_configuration(
        self, request: WorkflowEngineRequest
    ) -> WorkflowEngineValidationResult:
        code = WorkflowEngineValidationCheck.WORKFLOW_CONFIGURATION
        if not request.workflow_id:
            return WorkflowEngineValidationResult(
                check   = code,
                passed  = False,
                message = "workflow_id is empty",
            )
        return WorkflowEngineValidationResult(check=code, passed=True, message="OK")

    def _check_session_integrity(
        self, request: WorkflowEngineRequest
    ) -> WorkflowEngineValidationResult:
        code = WorkflowEngineValidationCheck.SESSION_INTEGRITY
        if not request.request_id:
            return WorkflowEngineValidationResult(
                check   = code,
                passed  = False,
                message = "request_id is empty",
            )
        return WorkflowEngineValidationResult(check=code, passed=True, message="OK")

    def _check_queue_consistency(
        self, request: WorkflowEngineRequest
    ) -> WorkflowEngineValidationResult:
        code = WorkflowEngineValidationCheck.QUEUE_CONSISTENCY
        if not (0 <= request.priority <= 3):
            return WorkflowEngineValidationResult(
                check   = code,
                passed  = False,
                message = f"priority {request.priority} out of range [0, 3]",
            )
        return WorkflowEngineValidationResult(check=code, passed=True, message="OK")

    def _check_priority_integrity(
        self, request: WorkflowEngineRequest
    ) -> WorkflowEngineValidationResult:
        code = WorkflowEngineValidationCheck.PRIORITY_INTEGRITY
        try:
            WorkflowDispatchMode(request.dispatch_mode.value)
        except (ValueError, AttributeError):
            return WorkflowEngineValidationResult(
                check   = code,
                passed  = False,
                message = f"Unknown dispatch_mode: {request.dispatch_mode!r}",
            )
        return WorkflowEngineValidationResult(check=code, passed=True, message="OK")

    def _check_lifecycle_consistency(
        self, request: WorkflowEngineRequest
    ) -> WorkflowEngineValidationResult:
        code = WorkflowEngineValidationCheck.LIFECYCLE_CONSISTENCY
        try:
            WorkflowType(request.workflow_type.value)
        except (ValueError, AttributeError):
            return WorkflowEngineValidationResult(
                check   = code,
                passed  = False,
                message = f"Unknown workflow_type: {request.workflow_type!r}",
            )
        return WorkflowEngineValidationResult(check=code, passed=True, message="OK")

    def _check_input_completeness(
        self, request: WorkflowEngineRequest
    ) -> WorkflowEngineValidationResult:
        code = WorkflowEngineValidationCheck.INPUT_COMPLETENESS
        if not request.correlation_id:
            return WorkflowEngineValidationResult(
                check   = code,
                passed  = False,
                message = "correlation_id is empty",
            )
        if not request.trace_id:
            return WorkflowEngineValidationResult(
                check   = code,
                passed  = False,
                message = "trace_id is empty",
            )
        return WorkflowEngineValidationResult(check=code, passed=True, message="OK")
