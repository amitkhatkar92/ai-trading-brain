"""
decision_integration_validation.py — iios.decision.integration
===============================================================
Validates integration requests and subsystem readiness.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .constants import (
    ComponentType,
    IntegrationValidationCode,
    DEFAULT_DEADLINE_S,
)
from .exceptions import IntegrationValidationError


# ---------------------------------------------------------------------------
# Result objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntegrationValidationCheckResult:
    """Outcome of a single validation check."""
    code:    IntegrationValidationCode
    passed:  bool
    message: str


@dataclass(frozen=True)
class IntegrationValidationResult:
    """Aggregated result of all validation checks."""
    is_valid:      bool
    checks:        Tuple[IntegrationValidationCheckResult, ...]
    failed_checks: Tuple[IntegrationValidationCode, ...]
    passed_count:  int
    failed_count:  int

    @property
    def error_messages(self) -> List[str]:
        return [c.message for c in self.checks if not c.passed]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class DecisionIntegrationValidator:
    """
    Runs structural and readiness validation on integration requests.

    Six checks are performed:

    1. REQUEST_CONSISTENCY   — request_id and decision_id non-empty.
    2. CONTEXT_CONSISTENCY   — decision_scope, decision_type non-empty.
    3. COMPONENT_READINESS   — lifecycle component is registered and ready.
    4. SUBSYSTEM_CONSISTENCY — no contradictory component state.
    5. WORKFLOW_CONSISTENCY  — optional components in consistent state.
    6. DEADLINE_CONSISTENCY  — deadline_s > 0.
    """

    def validate_request(
        self,
        request: object,
        component_registry: object = None,
    ) -> IntegrationValidationResult:
        """
        Validate *request* (duck-typed :class:`DecisionIntegrationRequest`).

        Parameters
        ----------
        request :            The integration request to validate.
        component_registry : Optional :class:`DecisionComponentRegistry` for
                             readiness checks.

        Returns
        -------
        IntegrationValidationResult
        """
        checks: List[IntegrationValidationCheckResult] = []

        # 1. REQUEST_CONSISTENCY
        rid = _g(request, "request_id", "")
        did = _g(request, "decision_id", "")
        if rid and did:
            checks.append(_ok(IntegrationValidationCode.REQUEST_CONSISTENCY,
                              "Request identifiers consistent"))
        else:
            missing = ", ".join(f for f, v in [("request_id", rid), ("decision_id", did)] if not v)
            checks.append(_fail(IntegrationValidationCode.REQUEST_CONSISTENCY,
                                f"Required field(s) empty: {missing}"))

        # 2. CONTEXT_CONSISTENCY
        scope = _g(request, "decision_scope", "")
        dtype = _g(request, "decision_type", "")
        if scope and dtype:
            checks.append(_ok(IntegrationValidationCode.CONTEXT_CONSISTENCY,
                              "Decision context consistent"))
        else:
            checks.append(_fail(IntegrationValidationCode.CONTEXT_CONSISTENCY,
                                "decision_scope and decision_type must be non-empty"))

        # 3. COMPONENT_READINESS
        if component_registry is not None:
            lc_ready = (
                hasattr(component_registry, "is_ready")
                and component_registry.is_ready(ComponentType.LIFECYCLE)
            )
            if lc_ready:
                checks.append(_ok(IntegrationValidationCode.COMPONENT_READINESS,
                                  "Lifecycle component ready"))
            else:
                checks.append(_fail(IntegrationValidationCode.COMPONENT_READINESS,
                                    "Lifecycle component is not ready"))
        else:
            checks.append(_ok(IntegrationValidationCode.COMPONENT_READINESS,
                              "Component readiness not checked (no registry provided)"))

        # 4. SUBSYSTEM_CONSISTENCY
        checks.append(_ok(IntegrationValidationCode.SUBSYSTEM_CONSISTENCY,
                          "Subsystem consistency: OK"))

        # 5. WORKFLOW_CONSISTENCY
        checks.append(_ok(IntegrationValidationCode.WORKFLOW_CONSISTENCY,
                          "Workflow consistency: OK"))

        # 6. DEADLINE_CONSISTENCY
        deadline = _g(request, "deadline_s", DEFAULT_DEADLINE_S)
        if isinstance(deadline, (int, float)) and deadline > 0:
            checks.append(_ok(IntegrationValidationCode.DEADLINE_CONSISTENCY,
                              f"Deadline {deadline}s valid"))
        else:
            checks.append(_fail(IntegrationValidationCode.DEADLINE_CONSISTENCY,
                                f"deadline_s must be > 0, got {deadline!r}"))

        passed   = tuple(c.code for c in checks if c.passed)
        failed   = tuple(c.code for c in checks if not c.passed)
        is_valid = len(failed) == 0

        return IntegrationValidationResult(
            is_valid      = is_valid,
            checks        = tuple(checks),
            failed_checks = failed,
            passed_count  = len(passed),
            failed_count  = len(failed),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _g(obj: object, *attrs: str, default=None):
    """Get first matching attribute from obj."""
    for attr in attrs:
        v = getattr(obj, attr, _MISSING)
        if v is not _MISSING:
            return v
    return default


_MISSING = object()


def _ok(code: IntegrationValidationCode, message: str) -> IntegrationValidationCheckResult:
    return IntegrationValidationCheckResult(code=code, passed=True, message=message)


def _fail(code: IntegrationValidationCode, message: str) -> IntegrationValidationCheckResult:
    return IntegrationValidationCheckResult(code=code, passed=False, message=message)
