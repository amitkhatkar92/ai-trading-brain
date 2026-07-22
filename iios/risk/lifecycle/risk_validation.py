"""
risk_validation.py — iios.risk.lifecycle
==========================================
Structural integrity validation for risk sessions.

C11 Risk Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .constants import (
    ACTIVE_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    RiskState,
    RiskValidationCode,
)
from .risk_session import RiskSession


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskValidationCheckResult:
    """
    Result of a single validation check.

    Attributes
    ----------
    code :    Which structural property was checked.
    passed :  True if the check succeeded.
    message : Human-readable description (empty when passed).
    """
    code:    RiskValidationCode
    passed:  bool
    message: str = ""


@dataclass(frozen=True)
class RiskValidationResult:
    """
    Aggregated validation outcome for a risk session.

    Attributes
    ----------
    is_valid :      True iff all checks passed.
    checks :        Full list of individual check results.
    failed_checks : Only the checks that failed.
    passed_count :  Number of checks that passed.
    failed_count :  Number of checks that failed.
    """
    is_valid:      bool
    checks:        Tuple[RiskValidationCheckResult, ...]
    failed_checks: Tuple[RiskValidationCheckResult, ...]
    passed_count:  int
    failed_count:  int

    @property
    def error_messages(self) -> List[str]:
        """Return the failure messages for all failed checks."""
        return [c.message for c in self.failed_checks if c.message]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class RiskValidator:
    """
    Validates structural integrity of a :class:`RiskSession`.

    Performs five checks corresponding to :class:`RiskValidationCode`:

    1. **IDENTIFIER_CONSISTENCY** — session_id, risk_id, and portfolio_id
       are non-empty.
    2. **LIFECYCLE_CONSISTENCY**  — state is a valid :class:`RiskState`.
    3. **TRANSITION_VALIDITY**    — current state reached via a valid path
       (at least one transition in history, or state == CREATED).
    4. **TIMESTAMP_CONSISTENCY**  — timestamps are non-negative and ordered.
    5. **HISTORY_INTEGRITY**      — state_history is non-empty and last entry
       matches the current state.

    Usage
    -----
    ::

        validator = RiskValidator()
        result = validator.validate(session)
        if not result.is_valid:
            for msg in result.error_messages:
                print(msg)
    """

    def validate(self, session: RiskSession) -> RiskValidationResult:
        checks: List[RiskValidationCheckResult] = [
            self._check_identifier_consistency(session),
            self._check_lifecycle_consistency(session),
            self._check_transition_validity(session),
            self._check_timestamp_consistency(session),
            self._check_history_integrity(session),
        ]
        failed = tuple(c for c in checks if not c.passed)
        return RiskValidationResult(
            is_valid      = len(failed) == 0,
            checks        = tuple(checks),
            failed_checks = failed,
            passed_count  = sum(1 for c in checks if c.passed),
            failed_count  = len(failed),
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_identifier_consistency(
        self, session: RiskSession
    ) -> RiskValidationCheckResult:
        ok = bool(
            session.session_id
            and session.risk_id
            and session.portfolio_id
        )
        return RiskValidationCheckResult(
            code    = RiskValidationCode.IDENTIFIER_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "session_id, risk_id, or portfolio_id is empty",
        )

    def _check_lifecycle_consistency(
        self, session: RiskSession
    ) -> RiskValidationCheckResult:
        ok = isinstance(session.state, RiskState)
        return RiskValidationCheckResult(
            code    = RiskValidationCode.LIFECYCLE_CONSISTENCY,
            passed  = ok,
            message = "" if ok else f"Invalid lifecycle state: {session.state!r}",
        )

    def _check_transition_validity(
        self, session: RiskSession
    ) -> RiskValidationCheckResult:
        # CREATED with no transitions is the only zero-transition-valid state
        if session.state == RiskState.CREATED and not session.transitions:
            return RiskValidationCheckResult(
                code   = RiskValidationCode.TRANSITION_VALIDITY,
                passed = True,
            )
        transitions = session.transitions
        if not transitions:
            return RiskValidationCheckResult(
                code    = RiskValidationCode.TRANSITION_VALIDITY,
                passed  = False,
                message = "Session has no transitions but is not in CREATED state",
            )
        # Verify the most recent transition leads to the current state
        last = transitions[-1]
        ok   = last.to_state == session.state
        return RiskValidationCheckResult(
            code    = RiskValidationCode.TRANSITION_VALIDITY,
            passed  = ok,
            message = "" if ok else (
                f"Last transition target {last.to_state.value!r} "
                f"does not match current state {session.state.value!r}"
            ),
        )

    def _check_timestamp_consistency(
        self, session: RiskSession
    ) -> RiskValidationCheckResult:
        ok = (
            session.created_at >= 0.0
            and session.updated_at >= session.created_at
        )
        return RiskValidationCheckResult(
            code    = RiskValidationCode.TIMESTAMP_CONSISTENCY,
            passed  = ok,
            message = "" if ok else (
                "Timestamp ordering violated: "
                f"created_at={session.created_at}, updated_at={session.updated_at}"
            ),
        )

    def _check_history_integrity(
        self, session: RiskSession
    ) -> RiskValidationCheckResult:
        history = session.state_history
        if not history:
            return RiskValidationCheckResult(
                code    = RiskValidationCode.HISTORY_INTEGRITY,
                passed  = False,
                message = "state_history is empty",
            )
        last_state = history[-1].state
        ok = last_state == session.state
        return RiskValidationCheckResult(
            code    = RiskValidationCode.HISTORY_INTEGRITY,
            passed  = ok,
            message = "" if ok else (
                f"Last history entry {last_state.value!r} "
                f"does not match current state {session.state.value!r}"
            ),
        )
