"""
workflow_validation.py — iios.workflow.lifecycle
-------------------------------------------------
Validation logic for workflow sessions and lifecycle transitions.

5 validation checks:
  1. IDENTIFIER_CONSISTENCY — required IDs non-empty
  2. LIFECYCLE_CONSISTENCY  — state is a valid WorkflowLifecycleState member
  3. TRANSITION_VALIDITY    — current state exists in VALID_TRANSITIONS table
  4. TIMESTAMP_CONSISTENCY  — created_at <= updated_at
  5. HISTORY_INTEGRITY      — session transition list is consistent

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .constants import (
    VALID_TRANSITIONS,
    WorkflowLifecycleState,
    WorkflowValidationCode,
)
from .workflow_session import WorkflowSession


@dataclass(frozen=True)
class WorkflowValidationResult:
    code:    WorkflowValidationCode
    passed:  bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code":    self.code.value,
            "passed":  self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class WorkflowValidationReport:
    session_id: str
    results:    tuple   # Tuple[WorkflowValidationResult, ...]
    passed:     bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "passed":     self.passed,
            "results":    [r.to_dict() for r in self.results],
        }

    @property
    def failed_checks(self) -> List[str]:
        return [r.code.value for r in self.results if not r.passed]


class WorkflowValidator:
    """Runs 5 validation checks against a WorkflowSession."""

    def validate(self, session: WorkflowSession) -> WorkflowValidationReport:
        results = [
            self._check_identifier_consistency(session),
            self._check_lifecycle_consistency(session),
            self._check_transition_validity(session),
            self._check_timestamp_consistency(session),
            self._check_history_integrity(session),
        ]
        passed = all(r.passed for r in results)
        return WorkflowValidationReport(
            session_id = session.session_id,
            results    = tuple(results),
            passed     = passed,
        )

    # ----------------------------------------------------------------
    # Individual checks
    # ----------------------------------------------------------------

    def _check_identifier_consistency(
        self, session: WorkflowSession
    ) -> WorkflowValidationResult:
        code    = WorkflowValidationCode.IDENTIFIER_CONSISTENCY
        missing = [
            f for f in ("session_id", "workflow_id")
            if not getattr(session, f, "")
        ]
        if missing:
            return WorkflowValidationResult(
                code    = code,
                passed  = False,
                message = f"Missing required identifiers: {missing!r}",
            )
        return WorkflowValidationResult(code=code, passed=True, message="OK")

    def _check_lifecycle_consistency(
        self, session: WorkflowSession
    ) -> WorkflowValidationResult:
        code  = WorkflowValidationCode.LIFECYCLE_CONSISTENCY
        state = session.state
        if not isinstance(state, WorkflowLifecycleState):
            return WorkflowValidationResult(
                code    = code,
                passed  = False,
                message = f"State {state!r} is not a valid WorkflowLifecycleState",
            )
        return WorkflowValidationResult(code=code, passed=True, message="OK")

    def _check_transition_validity(
        self, session: WorkflowSession
    ) -> WorkflowValidationResult:
        code  = WorkflowValidationCode.TRANSITION_VALIDITY
        state = session.state
        if state not in VALID_TRANSITIONS:
            return WorkflowValidationResult(
                code    = code,
                passed  = False,
                message = f"State {state.value!r} not in transition table",
            )
        return WorkflowValidationResult(code=code, passed=True, message="OK")

    def _check_timestamp_consistency(
        self, session: WorkflowSession
    ) -> WorkflowValidationResult:
        code = WorkflowValidationCode.TIMESTAMP_CONSISTENCY
        try:
            ok = session.created_at <= session.updated_at
            if not ok:
                return WorkflowValidationResult(
                    code    = code,
                    passed  = False,
                    message = (
                        f"created_at {session.created_at!r} is after "
                        f"updated_at {session.updated_at!r}"
                    ),
                )
        except Exception as exc:
            return WorkflowValidationResult(
                code    = code,
                passed  = False,
                message = f"Timestamp comparison error: {exc!r}",
            )
        return WorkflowValidationResult(code=code, passed=True, message="OK")

    def _check_history_integrity(
        self, session: WorkflowSession
    ) -> WorkflowValidationResult:
        code = WorkflowValidationCode.HISTORY_INTEGRITY
        try:
            state_count      = len(session.state_records())
            transition_count = session.transition_count()
            # Each transition produces one state record; initial state adds one more
            expected_states = transition_count + 1
            if state_count != expected_states:
                return WorkflowValidationResult(
                    code    = code,
                    passed  = False,
                    message = (
                        f"State record count {state_count} does not match "
                        f"expected {expected_states} "
                        f"(transitions={transition_count})"
                    ),
                )
        except Exception as exc:
            return WorkflowValidationResult(
                code    = code,
                passed  = False,
                message = f"History integrity error: {exc!r}",
            )
        return WorkflowValidationResult(code=code, passed=True, message="OK")
