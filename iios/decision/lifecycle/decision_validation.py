"""
decision_validation.py — iios.decision.lifecycle
==================================================
Validation engine for decision lifecycle sessions.

Runs the five checks mandated by the specification.

C9 Decision Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .constants import (
    VERSION,
    ACTIVE_STATES,
    TERMINAL_STATES,
    DecisionState,
    DecisionValidationCode,
    VALID_TRANSITIONS,
)
from .decision_session import DecisionSession


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ValidationCheckResult:
    """
    Outcome of a single lifecycle validation check.

    Fields
    ------
    code :    :class:`DecisionValidationCode` identifying the check.
    passed :  ``True`` when the check passed.
    message : Human-readable diagnosis.  Empty on pass.
    """
    code:    DecisionValidationCode
    passed:  bool
    message: str = ""


@dataclass(frozen=True)
class DecisionValidationResult:
    """
    Aggregate result of all five decision lifecycle validation checks.

    Fields
    ------
    is_valid :        ``True`` when all five checks passed.
    checks :          Tuple of individual check results.
    failed_checks :   Tuple of codes for failed checks.
    error_messages :  Tuple of messages from failed checks.
    framework_version : Framework version string.
    """
    is_valid:        bool
    checks:          Tuple[ValidationCheckResult, ...]
    failed_checks:   Tuple[DecisionValidationCode, ...]
    error_messages:  Tuple[str, ...]
    framework_version: str = VERSION

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return len(self.failed_checks)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------
class DecisionValidator:
    """
    Validates decision lifecycle sessions against the five specification
    checks.

    Check catalogue
    ---------------
    1. IDENTIFIER_CONSISTENCY  — session_id and decision_id are non-empty strings.
    2. LIFECYCLE_CONSISTENCY   — current state is a recognized :class:`DecisionState`.
    3. TRANSITION_VALIDITY     — last transition in history was permitted by the
                                 state machine.
    4. TIMESTAMP_CONSISTENCY   — timestamps are monotonically non-decreasing.
    5. HISTORY_INTEGRITY       — state history length is consistent with the number
                                 of transitions recorded.
    """

    def validate(self, session: DecisionSession) -> DecisionValidationResult:
        """
        Run all five checks against *session*.

        Parameters
        ----------
        session : The :class:`DecisionSession` to validate.

        Returns
        -------
        DecisionValidationResult
        """
        checks: List[ValidationCheckResult] = [
            self._check_identifier_consistency(session),
            self._check_lifecycle_consistency(session),
            self._check_transition_validity(session),
            self._check_timestamp_consistency(session),
            self._check_history_integrity(session),
        ]

        checks_tuple = tuple(checks)
        failed       = tuple(c.code    for c in checks if not c.passed)
        errors       = tuple(c.message for c in checks if not c.passed and c.message)

        return DecisionValidationResult(
            is_valid       = len(failed) == 0,
            checks         = checks_tuple,
            failed_checks  = failed,
            error_messages = errors,
        )

    def validate_transition(
        self,
        session:   DecisionSession,
        to_state:  DecisionState,
    ) -> Tuple[bool, str]:
        """
        Quick check: is ``session.state → to_state`` allowed?

        Returns ``(True, "")`` on pass, ``(False, message)`` on failure.
        """
        if session.state in frozenset({DecisionState.ARCHIVED}):
            return (
                False,
                f"Session {session.session_id!r} is in immutable state "
                f"{session.state.value!r}",
            )
        allowed = VALID_TRANSITIONS.get(session.state, frozenset())
        if to_state not in allowed:
            return (
                False,
                f"Transition {session.state.value!r} → {to_state.value!r} "
                f"is not permitted for session {session.session_id!r}",
            )
        return True, ""

    # ------------------------------------------------------------------
    # Private check implementations
    # ------------------------------------------------------------------
    @staticmethod
    def _check_identifier_consistency(
        session: DecisionSession,
    ) -> ValidationCheckResult:
        code = DecisionValidationCode.IDENTIFIER_CONSISTENCY
        if not isinstance(session.session_id, str) or not session.session_id.strip():
            return ValidationCheckResult(
                code    = code,
                passed  = False,
                message = "session_id must be a non-empty string",
            )
        if not isinstance(session.decision_id, str) or not session.decision_id.strip():
            return ValidationCheckResult(
                code    = code,
                passed  = False,
                message = "decision_id must be a non-empty string",
            )
        return ValidationCheckResult(code=code, passed=True)

    @staticmethod
    def _check_lifecycle_consistency(
        session: DecisionSession,
    ) -> ValidationCheckResult:
        code = DecisionValidationCode.LIFECYCLE_CONSISTENCY
        if not isinstance(session.state, DecisionState):
            return ValidationCheckResult(
                code    = code,
                passed  = False,
                message = f"Unknown state: {session.state!r}",
            )
        # If terminal and not ARCHIVED, end_time must be set
        if session.state in (DecisionState.COMPLETED, DecisionState.FAILED):
            if session.end_time is None:
                return ValidationCheckResult(
                    code    = code,
                    passed  = False,
                    message = (
                        f"Session in {session.state.value!r} state but end_time is None"
                    ),
                )
        # If ACTIVE, start_time must be set
        if session.state == DecisionState.ACTIVE:
            if session.start_time is None:
                return ValidationCheckResult(
                    code    = code,
                    passed  = False,
                    message = "Session is ACTIVE but start_time is None",
                )
        return ValidationCheckResult(code=code, passed=True)

    @staticmethod
    def _check_transition_validity(
        session: DecisionSession,
    ) -> ValidationCheckResult:
        code = DecisionValidationCode.TRANSITION_VALIDITY
        history = session.state_history
        if len(history) < 2:
            # Only CREATED — nothing to validate
            return ValidationCheckResult(code=code, passed=True)

        # Walk the history and verify each consecutive pair is valid
        for i in range(1, len(history)):
            from_s = history[i - 1].state
            to_s   = history[i].state
            allowed = VALID_TRANSITIONS.get(from_s, frozenset())
            if to_s not in allowed:
                return ValidationCheckResult(
                    code    = code,
                    passed  = False,
                    message = (
                        f"History contains invalid transition "
                        f"{from_s.value!r} → {to_s.value!r} at step {i}"
                    ),
                )
        return ValidationCheckResult(code=code, passed=True)

    @staticmethod
    def _check_timestamp_consistency(
        session: DecisionSession,
    ) -> ValidationCheckResult:
        code = DecisionValidationCode.TIMESTAMP_CONSISTENCY
        history = session.state_history
        if not history:
            return ValidationCheckResult(code=code, passed=True)

        # Timestamps in state_history must be non-decreasing
        for i in range(1, len(history)):
            if history[i].entered_at < history[i - 1].entered_at - 0.001:
                return ValidationCheckResult(
                    code    = code,
                    passed  = False,
                    message = (
                        f"State history timestamp is not monotonic at index {i}: "
                        f"{history[i].entered_at} < {history[i - 1].entered_at}"
                    ),
                )
        # created_at ≤ updated_at
        if session.updated_at < session.created_at - 0.001:
            return ValidationCheckResult(
                code    = code,
                passed  = False,
                message = "updated_at is before created_at",
            )
        return ValidationCheckResult(code=code, passed=True)

    @staticmethod
    def _check_history_integrity(
        session: DecisionSession,
    ) -> ValidationCheckResult:
        code = DecisionValidationCode.HISTORY_INTEGRITY
        n_states      = len(session.state_history)
        n_transitions = session.transition_count

        # There should be exactly one more state-history record than transitions
        # (the initial CREATED record has no preceding transition)
        if n_states == 0:
            return ValidationCheckResult(
                code    = code,
                passed  = False,
                message = "State history is empty",
            )
        if n_states != n_transitions + 1:
            return ValidationCheckResult(
                code    = code,
                passed  = False,
                message = (
                    f"History integrity failure: {n_states} state records "
                    f"but {n_transitions} transitions "
                    f"(expected {n_transitions + 1} state records)"
                ),
            )
        # Last history record must match current state
        if session.state_history[-1].state != session.state:
            return ValidationCheckResult(
                code    = code,
                passed  = False,
                message = (
                    f"Last history record {session.state_history[-1].state.value!r} "
                    f"does not match current state {session.state.value!r}"
                ),
            )
        return ValidationCheckResult(code=code, passed=True)
