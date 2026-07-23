"""
supervisor_validation.py — iios.supervisor.engine
--------------------------------------------------
Input validation for supervisor engine workflow requests.

Performs structural and semantic checks before a request is processed:
  1. Identifier consistency
  2. Workflow type validity
  3. Priority validity
  4. Inputs schema
  5. Context consistency
  6. Lifecycle readiness

No business logic. All checks are structural gate-keepers only.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .constants import (
    DEFAULT_MAX_CONCURRENT_SESSIONS,
    SupervisorWorkflowType,
    SchedulerPriority,
)
from .supervisor_request import SupervisorRequest
from .exceptions import SupervisorEngineValidationError


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SupervisorEngineValidationCheckResult:
    """Result of a single validation check."""
    check_name: str
    passed:     bool
    message:    str = ""


@dataclass
class SupervisorEngineValidationResult:
    """Aggregate result of all validation checks for a request."""
    checks: List[SupervisorEngineValidationCheckResult] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> List[str]:
        return [c.check_name for c in self.checks if not c.passed]

    @property
    def error_messages(self) -> List[str]:
        return [c.message for c in self.checks if not c.passed]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class SupervisorEngineValidator:
    """
    Validates supervisor requests before they enter the execution pipeline.

    Parameters
    ----------
    max_sessions :    Active session limit.
    active_count_fn : Callable returning current active session count.
    """

    def __init__(
        self,
        max_sessions:    int             = DEFAULT_MAX_CONCURRENT_SESSIONS,
        active_count_fn: Optional[callable] = None,
    ) -> None:
        self._max_sessions    = max_sessions
        self._active_count_fn = active_count_fn

    def validate_request(
        self,
        request: SupervisorRequest,
    ) -> SupervisorEngineValidationResult:
        """Run all six validation checks."""
        result = SupervisorEngineValidationResult()
        result.checks.append(self._check_identifier_consistency(request))
        result.checks.append(self._check_workflow_type(request))
        result.checks.append(self._check_priority(request))
        result.checks.append(self._check_inputs_schema(request))
        result.checks.append(self._check_context_consistency(request))
        result.checks.append(self._check_lifecycle_readiness(request))
        return result

    def validate_or_raise(self, request: SupervisorRequest) -> None:
        """Run validation and raise SupervisorEngineValidationError on failure."""
        result = self.validate_request(request)
        if not result.is_valid:
            raise SupervisorEngineValidationError(
                "; ".join(result.error_messages),
                failed_checks=tuple(result.failed_checks),
            )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_identifier_consistency(
        request: SupervisorRequest,
    ) -> SupervisorEngineValidationCheckResult:
        ok = bool(request.request_id) and bool(request.supervision_id)
        return SupervisorEngineValidationCheckResult(
            check_name = "identifier_consistency",
            passed     = ok,
            message    = "" if ok else "request_id and supervision_id must be non-empty",
        )

    @staticmethod
    def _check_workflow_type(
        request: SupervisorRequest,
    ) -> SupervisorEngineValidationCheckResult:
        ok = isinstance(request.workflow_type, SupervisorWorkflowType)
        return SupervisorEngineValidationCheckResult(
            check_name = "workflow_type",
            passed     = ok,
            message    = "" if ok else f"Invalid workflow_type: {request.workflow_type!r}",
        )

    @staticmethod
    def _check_priority(
        request: SupervisorRequest,
    ) -> SupervisorEngineValidationCheckResult:
        ok = isinstance(request.priority, SchedulerPriority)
        return SupervisorEngineValidationCheckResult(
            check_name = "priority",
            passed     = ok,
            message    = "" if ok else f"Invalid priority: {request.priority!r}",
        )

    @staticmethod
    def _check_inputs_schema(
        request: SupervisorRequest,
    ) -> SupervisorEngineValidationCheckResult:
        # Inputs may be empty at validation time — they are collected later
        ok = isinstance(request.inputs, dict)
        return SupervisorEngineValidationCheckResult(
            check_name = "inputs_schema",
            passed     = ok,
            message    = "" if ok else "inputs must be a dict",
        )

    @staticmethod
    def _check_context_consistency(
        request: SupervisorRequest,
    ) -> SupervisorEngineValidationCheckResult:
        ok = (
            request.context is not None
            and request.context.supervision_id == request.supervision_id
        )
        return SupervisorEngineValidationCheckResult(
            check_name = "context_consistency",
            passed     = ok,
            message    = (
                "" if ok else
                "context.supervision_id must match request.supervision_id"
            ),
        )

    def _check_lifecycle_readiness(
        self,
        request: SupervisorRequest,
    ) -> SupervisorEngineValidationCheckResult:
        if self._active_count_fn is None:
            return SupervisorEngineValidationCheckResult(
                check_name = "lifecycle_readiness",
                passed     = True,
            )
        active = self._active_count_fn()
        ok     = active < self._max_sessions
        return SupervisorEngineValidationCheckResult(
            check_name = "lifecycle_readiness",
            passed     = ok,
            message    = (
                "" if ok else
                f"Session capacity reached ({active}/{self._max_sessions})"
            ),
        )
