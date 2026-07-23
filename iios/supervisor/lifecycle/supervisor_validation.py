"""
supervisor_validation.py — iios.supervisor.lifecycle
-----------------------------------------------------
Structural integrity validation for supervisor sessions.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .constants import (
    ACTIVE_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    SupervisorState,
    SupervisorValidationCode,
)
from .supervisor_session import SupervisorSession


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SupervisorValidationCheckResult:
    """
    Result of a single validation check.

    Attributes
    ----------
    code :    Which structural property was checked.
    passed :  True if the check succeeded.
    message : Human-readable description (empty when passed).
    """
    code:    SupervisorValidationCode
    passed:  bool
    message: str = ""


@dataclass(frozen=True)
class SupervisorValidationResult:
    """
    Aggregated validation outcome for a supervisor session.

    Attributes
    ----------
    is_valid :      True iff all checks passed.
    checks :        Full list of individual check results.
    failed_checks : Only the checks that failed.
    passed_count :  Number of checks that passed.
    failed_count :  Number of checks that failed.
    """
    is_valid:      bool
    checks:        Tuple[SupervisorValidationCheckResult, ...]
    failed_checks: Tuple[SupervisorValidationCheckResult, ...]
    passed_count:  int
    failed_count:  int

    @property
    def error_messages(self) -> List[str]:
        """Return the failure messages for all failed checks."""
        return [c.message for c in self.failed_checks if c.message]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class SupervisorValidator:
    """
    Validates structural integrity of a :class:`SupervisorSession`.

    Performs five checks corresponding to :class:`SupervisorValidationCode`:

    1. **IDENTIFIER_CONSISTENCY** — session_id and supervisor_id are non-empty.
    2. **LIFECYCLE_CONSISTENCY**  — state is a valid :class:`SupervisorState`.
    3. **TRANSITION_VALIDITY**    — current state reached via a valid path
       (at least one transition in history, or state == CREATED).
    4. **TIMESTAMP_CONSISTENCY**  — timestamps are non-negative and ordered.
    5. **HISTORY_INTEGRITY**      — state_history is non-empty and last entry
       matches the current state.
    """

    def validate(self, session: SupervisorSession) -> SupervisorValidationResult:
        checks: List[SupervisorValidationCheckResult] = [
            self._check_identifier_consistency(session),
            self._check_lifecycle_consistency(session),
            self._check_transition_validity(session),
            self._check_timestamp_consistency(session),
            self._check_history_integrity(session),
        ]
        failed = tuple(c for c in checks if not c.passed)
        return SupervisorValidationResult(
            is_valid      = len(failed) == 0,
            checks        = tuple(checks),
            failed_checks = failed,
            passed_count  = len(checks) - len(failed),
            failed_count  = len(failed),
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_identifier_consistency(
        self, session: SupervisorSession
    ) -> SupervisorValidationCheckResult:
        ok = bool(session.session_id) and bool(session.supervisor_id)
        return SupervisorValidationCheckResult(
            code    = SupervisorValidationCode.IDENTIFIER_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "session_id and supervisor_id must be non-empty",
        )

    def _check_lifecycle_consistency(
        self, session: SupervisorSession
    ) -> SupervisorValidationCheckResult:
        ok = isinstance(session.state, SupervisorState)
        return SupervisorValidationCheckResult(
            code    = SupervisorValidationCode.LIFECYCLE_CONSISTENCY,
            passed  = ok,
            message = "" if ok else f"Invalid lifecycle state: {session.state!r}",
        )

    def _check_transition_validity(
        self, session: SupervisorSession
    ) -> SupervisorValidationCheckResult:
        # CREATED state with no transitions is always valid
        if session.state == SupervisorState.CREATED and not session.transitions:
            return SupervisorValidationCheckResult(
                code   = SupervisorValidationCode.TRANSITION_VALIDITY,
                passed = True,
            )
        # For any other state there must be at least one transition
        ok = len(session.transitions) >= 1
        return SupervisorValidationCheckResult(
            code    = SupervisorValidationCode.TRANSITION_VALIDITY,
            passed  = ok,
            message = "" if ok else "Non-CREATED state must have at least one transition",
        )

    def _check_timestamp_consistency(
        self, session: SupervisorSession
    ) -> SupervisorValidationCheckResult:
        ok = (
            session.created_at >= 0
            and session.updated_at >= session.created_at
        )
        return SupervisorValidationCheckResult(
            code    = SupervisorValidationCode.TIMESTAMP_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "Timestamps are invalid or not ordered correctly",
        )

    def _check_history_integrity(
        self, session: SupervisorSession
    ) -> SupervisorValidationCheckResult:
        history = session.state_history
        ok = bool(history) and history[-1].state == session.state
        return SupervisorValidationCheckResult(
            code    = SupervisorValidationCode.HISTORY_INTEGRITY,
            passed  = ok,
            message = (
                "" if ok else
                "state_history is empty or last entry does not match current state"
            ),
        )
