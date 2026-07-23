"""
market_validation.py — iios.market.lifecycle
==============================================
Structural integrity validation for market sessions.

C12 Market Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .constants import (
    ACTIVE_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    MarketState,
    MarketValidationCode,
)
from .market_session import MarketSession


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MarketValidationCheckResult:
    """
    Result of a single validation check.

    Attributes
    ----------
    code :    Which structural property was checked.
    passed :  True if the check succeeded.
    message : Human-readable description (empty when passed).
    """
    code:    MarketValidationCode
    passed:  bool
    message: str = ""


@dataclass(frozen=True)
class MarketValidationResult:
    """
    Aggregated validation outcome for a market session.

    Attributes
    ----------
    is_valid :      True iff all checks passed.
    checks :        Full list of individual check results.
    failed_checks : Only the checks that failed.
    passed_count :  Number of checks that passed.
    failed_count :  Number of checks that failed.
    """
    is_valid:      bool
    checks:        Tuple[MarketValidationCheckResult, ...]
    failed_checks: Tuple[MarketValidationCheckResult, ...]
    passed_count:  int
    failed_count:  int

    @property
    def error_messages(self) -> List[str]:
        """Return the failure messages for all failed checks."""
        return [c.message for c in self.failed_checks if c.message]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class MarketValidator:
    """
    Validates structural integrity of a :class:`MarketSession`.

    Performs five checks corresponding to :class:`MarketValidationCode`:

    1. **IDENTIFIER_CONSISTENCY** — session_id and market_analysis_id are
       non-empty.
    2. **LIFECYCLE_CONSISTENCY**  — state is a valid :class:`MarketState`.
    3. **TRANSITION_VALIDITY**    — current state reached via a valid path
       (at least one transition in history, or state == CREATED).
    4. **TIMESTAMP_CONSISTENCY**  — timestamps are non-negative and ordered.
    5. **HISTORY_INTEGRITY**      — state_history is non-empty and last entry
       matches the current state.
    """

    def validate(self, session: MarketSession) -> MarketValidationResult:
        checks: List[MarketValidationCheckResult] = [
            self._check_identifier_consistency(session),
            self._check_lifecycle_consistency(session),
            self._check_transition_validity(session),
            self._check_timestamp_consistency(session),
            self._check_history_integrity(session),
        ]
        failed = tuple(c for c in checks if not c.passed)
        return MarketValidationResult(
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
        self, session: MarketSession
    ) -> MarketValidationCheckResult:
        code = MarketValidationCode.IDENTIFIER_CONSISTENCY
        if not session.session_id:
            return MarketValidationCheckResult(
                code=code, passed=False,
                message="session_id is empty",
            )
        if not session.market_analysis_id:
            return MarketValidationCheckResult(
                code=code, passed=False,
                message="market_analysis_id is empty",
            )
        return MarketValidationCheckResult(code=code, passed=True)

    def _check_lifecycle_consistency(
        self, session: MarketSession
    ) -> MarketValidationCheckResult:
        code = MarketValidationCode.LIFECYCLE_CONSISTENCY
        if not isinstance(session.state, MarketState):
            return MarketValidationCheckResult(
                code=code, passed=False,
                message=f"Unexpected state type: {type(session.state)}",
            )
        return MarketValidationCheckResult(code=code, passed=True)

    def _check_transition_validity(
        self, session: MarketSession
    ) -> MarketValidationCheckResult:
        code = MarketValidationCode.TRANSITION_VALIDITY
        # CREATED state with no transitions is always valid
        if session.state == MarketState.CREATED and not session.transitions:
            return MarketValidationCheckResult(code=code, passed=True)
        # Otherwise at least one transition must exist
        if not session.transitions:
            return MarketValidationCheckResult(
                code=code, passed=False,
                message="Non-CREATED session has no transition history",
            )
        last = session.transitions[-1]
        if last.to_state != session.state:
            return MarketValidationCheckResult(
                code=code, passed=False,
                message=(
                    f"Last transition to_state {last.to_state.value!r} does not "
                    f"match current state {session.state.value!r}"
                ),
            )
        return MarketValidationCheckResult(code=code, passed=True)

    def _check_timestamp_consistency(
        self, session: MarketSession
    ) -> MarketValidationCheckResult:
        code = MarketValidationCode.TIMESTAMP_CONSISTENCY
        if session.created_at < 0:
            return MarketValidationCheckResult(
                code=code, passed=False,
                message="created_at is negative",
            )
        if session.updated_at < session.created_at:
            return MarketValidationCheckResult(
                code=code, passed=False,
                message="updated_at is before created_at",
            )
        if session.start_time is not None and session.start_time < session.created_at:
            return MarketValidationCheckResult(
                code=code, passed=False,
                message="start_time is before created_at",
            )
        if (
            session.start_time is not None
            and session.end_time is not None
            and session.end_time < session.start_time
        ):
            return MarketValidationCheckResult(
                code=code, passed=False,
                message="end_time is before start_time",
            )
        return MarketValidationCheckResult(code=code, passed=True)

    def _check_history_integrity(
        self, session: MarketSession
    ) -> MarketValidationCheckResult:
        code = MarketValidationCode.HISTORY_INTEGRITY
        history = session.state_history
        if not history:
            return MarketValidationCheckResult(
                code=code, passed=False,
                message="state_history is empty",
            )
        last_record = history[-1]
        if last_record.state != session.state:
            return MarketValidationCheckResult(
                code=code, passed=False,
                message=(
                    f"Last state_history entry {last_record.state.value!r} does not "
                    f"match current state {session.state.value!r}"
                ),
            )
        return MarketValidationCheckResult(code=code, passed=True)
