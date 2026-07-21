"""
portfolio_validation.py — iios.portfolio.lifecycle
====================================================
Structural integrity validation for portfolio sessions.

C10 Portfolio Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from .constants import (
    ACTIVE_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    PortfolioState,
    PortfolioValidationCode,
)
from .portfolio_session import PortfolioSession


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioValidationCheckResult:
    """
    Result of a single validation check.

    Attributes
    ----------
    code :    Which structural property was checked.
    passed :  True if the check succeeded.
    message : Human-readable description (empty when passed).
    """
    code:    PortfolioValidationCode
    passed:  bool
    message: str = ""


@dataclass(frozen=True)
class PortfolioValidationResult:
    """
    Aggregated validation outcome for a portfolio session.

    Attributes
    ----------
    is_valid :      True iff all checks passed.
    checks :        Full list of individual check results.
    failed_checks : Only the checks that failed.
    passed_count :  Number of checks that passed.
    failed_count :  Number of checks that failed.
    """
    is_valid:      bool
    checks:        Tuple[PortfolioValidationCheckResult, ...]
    failed_checks: Tuple[PortfolioValidationCheckResult, ...]
    passed_count:  int
    failed_count:  int

    @property
    def error_messages(self) -> List[str]:
        """Return the failure messages for all failed checks."""
        return [c.message for c in self.failed_checks if c.message]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class PortfolioValidator:
    """
    Validates structural integrity of a :class:`PortfolioSession`.

    Performs five checks corresponding to :class:`PortfolioValidationCode`:

    1. **IDENTIFIER_CONSISTENCY** — session_id and portfolio_id are non-empty.
    2. **LIFECYCLE_CONSISTENCY**  — state is a valid :class:`PortfolioState`.
    3. **TRANSITION_VALIDITY**    — current state reached via a valid path
       (at least one transition in history, or state == CREATED).
    4. **TIMESTAMP_CONSISTENCY**  — timestamps are non-negative and ordered.
    5. **HISTORY_INTEGRITY**      — state_history is non-empty and last entry
       matches the current state.

    Usage
    -----
    ::

        validator = PortfolioValidator()
        result = validator.validate(session)
        if not result.is_valid:
            for msg in result.error_messages:
                print(msg)
    """

    def validate(self, session: PortfolioSession) -> PortfolioValidationResult:
        checks: List[PortfolioValidationCheckResult] = [
            self._check_identifier_consistency(session),
            self._check_lifecycle_consistency(session),
            self._check_transition_validity(session),
            self._check_timestamp_consistency(session),
            self._check_history_integrity(session),
        ]
        failed = tuple(c for c in checks if not c.passed)
        return PortfolioValidationResult(
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
        self, session: PortfolioSession
    ) -> PortfolioValidationCheckResult:
        ok = bool(session.session_id and session.portfolio_id)
        return PortfolioValidationCheckResult(
            code    = PortfolioValidationCode.IDENTIFIER_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "session_id or portfolio_id is empty",
        )

    def _check_lifecycle_consistency(
        self, session: PortfolioSession
    ) -> PortfolioValidationCheckResult:
        ok = isinstance(session.state, PortfolioState)
        return PortfolioValidationCheckResult(
            code    = PortfolioValidationCode.LIFECYCLE_CONSISTENCY,
            passed  = ok,
            message = "" if ok else f"Invalid lifecycle state: {session.state!r}",
        )

    def _check_transition_validity(
        self, session: PortfolioSession
    ) -> PortfolioValidationCheckResult:
        # CREATED with no transitions is the only zero-transition-valid state
        if session.state == PortfolioState.CREATED and not session.transitions:
            return PortfolioValidationCheckResult(
                code   = PortfolioValidationCode.TRANSITION_VALIDITY,
                passed = True,
            )
        transitions = session.transitions
        if not transitions:
            return PortfolioValidationCheckResult(
                code    = PortfolioValidationCode.TRANSITION_VALIDITY,
                passed  = False,
                message = "Non-CREATED session has no transitions",
            )
        last = transitions[-1]
        ok   = last.to_state == session.state
        return PortfolioValidationCheckResult(
            code    = PortfolioValidationCode.TRANSITION_VALIDITY,
            passed  = ok,
            message = (
                "" if ok
                else (
                    f"Last transition to_state={last.to_state.value!r} "
                    f"does not match current state={session.state.value!r}"
                )
            ),
        )

    def _check_timestamp_consistency(
        self, session: PortfolioSession
    ) -> PortfolioValidationCheckResult:
        if session.created_at < 0:
            return PortfolioValidationCheckResult(
                code    = PortfolioValidationCode.TIMESTAMP_CONSISTENCY,
                passed  = False,
                message = "created_at is negative",
            )
        if session.updated_at < session.created_at:
            return PortfolioValidationCheckResult(
                code    = PortfolioValidationCode.TIMESTAMP_CONSISTENCY,
                passed  = False,
                message = "updated_at precedes created_at",
            )
        if (session.start_time is not None
                and session.start_time < session.created_at):
            return PortfolioValidationCheckResult(
                code    = PortfolioValidationCode.TIMESTAMP_CONSISTENCY,
                passed  = False,
                message = "start_time precedes created_at",
            )
        if (session.end_time is not None
                and session.start_time is not None
                and session.end_time < session.start_time):
            return PortfolioValidationCheckResult(
                code    = PortfolioValidationCode.TIMESTAMP_CONSISTENCY,
                passed  = False,
                message = "end_time precedes start_time",
            )
        return PortfolioValidationCheckResult(
            code   = PortfolioValidationCode.TIMESTAMP_CONSISTENCY,
            passed = True,
        )

    def _check_history_integrity(
        self, session: PortfolioSession
    ) -> PortfolioValidationCheckResult:
        history = session.state_history
        if not history:
            return PortfolioValidationCheckResult(
                code    = PortfolioValidationCode.HISTORY_INTEGRITY,
                passed  = False,
                message = "state_history is empty",
            )
        last_state = history[-1].state
        ok = last_state == session.state
        return PortfolioValidationCheckResult(
            code    = PortfolioValidationCode.HISTORY_INTEGRITY,
            passed  = ok,
            message = (
                "" if ok
                else (
                    f"Last history state={last_state.value!r} "
                    f"does not match current state={session.state.value!r}"
                )
            ),
        )
