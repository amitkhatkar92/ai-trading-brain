"""
integration_validation.py — iios.integration.lifecycle
-------------------------------------------------------
Validation logic for integration sessions and lifecycle transitions.

5 validation checks:
  1. IDENTIFIER_CONSISTENCY  — required IDs non-empty
  2. LIFECYCLE_CONSISTENCY   — state is a valid enum member
  3. TRANSITION_VALIDITY     — proposed transition is in VALID_TRANSITIONS
  4. TIMESTAMP_CONSISTENCY   — created_at <= updated_at
  5. HISTORY_INTEGRITY       — transition count matches history

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .constants import (
    VALID_TRANSITIONS,
    IntegrationLifecycleState,
    IntegrationValidationCode,
)
from .integration_session import IntegrationSession


@dataclass(frozen=True)
class IntegrationValidationResult:
    code:    IntegrationValidationCode
    passed:  bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code":    self.code.value,
            "passed":  self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class IntegrationValidationReport:
    session_id: str
    results:    tuple   # Tuple[IntegrationValidationResult]
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


class IntegrationValidator:
    """Runs 5 validation checks against an IntegrationSession."""

    def validate(self, session: IntegrationSession) -> IntegrationValidationReport:
        results = [
            self._check_identifier_consistency(session),
            self._check_lifecycle_consistency(session),
            self._check_transition_validity(session),
            self._check_timestamp_consistency(session),
            self._check_history_integrity(session),
        ]
        passed = all(r.passed for r in results)
        return IntegrationValidationReport(
            session_id = session.session_id,
            results    = tuple(results),
            passed     = passed,
        )

    # ----------------------------------------------------------------
    # Individual checks
    # ----------------------------------------------------------------

    def _check_identifier_consistency(
        self, session: IntegrationSession
    ) -> IntegrationValidationResult:
        code    = IntegrationValidationCode.IDENTIFIER_CONSISTENCY
        missing = [
            f for f in ("session_id", "workflow_id")
            if not getattr(session, f, "")
        ]
        if missing:
            return IntegrationValidationResult(
                code    = code,
                passed  = False,
                message = f"Missing required identifiers: {missing!r}",
            )
        return IntegrationValidationResult(code=code, passed=True, message="OK")

    def _check_lifecycle_consistency(
        self, session: IntegrationSession
    ) -> IntegrationValidationResult:
        code  = IntegrationValidationCode.LIFECYCLE_CONSISTENCY
        state = session.state
        if not isinstance(state, IntegrationLifecycleState):
            return IntegrationValidationResult(
                code    = code,
                passed  = False,
                message = f"State {state!r} is not a valid IntegrationLifecycleState",
            )
        return IntegrationValidationResult(code=code, passed=True, message="OK")

    def _check_transition_validity(
        self, session: IntegrationSession
    ) -> IntegrationValidationResult:
        code  = IntegrationValidationCode.TRANSITION_VALIDITY
        state = session.state
        if state not in VALID_TRANSITIONS:
            return IntegrationValidationResult(
                code    = code,
                passed  = False,
                message = f"State {state.value!r} not in transition table",
            )
        return IntegrationValidationResult(code=code, passed=True, message="OK")

    def _check_timestamp_consistency(
        self, session: IntegrationSession
    ) -> IntegrationValidationResult:
        code = IntegrationValidationCode.TIMESTAMP_CONSISTENCY
        if session.created_at and session.updated_at:
            if session.updated_at < session.created_at:
                return IntegrationValidationResult(
                    code    = code,
                    passed  = False,
                    message = (
                        f"updated_at ({session.updated_at!r}) is before "
                        f"created_at ({session.created_at!r})"
                    ),
                )
        return IntegrationValidationResult(code=code, passed=True, message="OK")

    def _check_history_integrity(
        self, session: IntegrationSession
    ) -> IntegrationValidationResult:
        code           = IntegrationValidationCode.HISTORY_INTEGRITY
        transition_cnt = session.transition_count()
        state_cnt      = len(session.state_records())
        # state_records should be transition_count + 1 (initial CREATED record)
        expected_state_cnt = transition_cnt + 1
        if state_cnt != expected_state_cnt:
            return IntegrationValidationResult(
                code    = code,
                passed  = False,
                message = (
                    f"History mismatch: {transition_cnt} transitions "
                    f"but {state_cnt} state records (expected {expected_state_cnt})"
                ),
            )
        return IntegrationValidationResult(code=code, passed=True, message="OK")

    # ----------------------------------------------------------------
    # Transition pre-check
    # ----------------------------------------------------------------

    def validate_transition(
        self,
        session:  IntegrationSession,
        to_state: IntegrationLifecycleState,
    ) -> bool:
        """Return True if the proposed transition is valid."""
        return session.can_transition_to(to_state)
