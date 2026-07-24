"""
knowledge_validation.py — iios.knowledge.lifecycle
----------------------------------------------------
Structural validation checks for knowledge lifecycle sessions.

Five validation checks
-----------------------
1. IDENTIFIER_CONSISTENCY  — session_id and artifact_id are non-empty strings
2. LIFECYCLE_CONSISTENCY   — state is a valid KnowledgeLifecycleState member
3. TRANSITION_VALIDITY     — each transition's from/to pair is a valid pair in the state machine
4. TIMESTAMP_CONSISTENCY   — created_at ≤ updated_at; end_time ≥ start_time (if set)
5. HISTORY_INTEGRITY       — state_history is non-empty; first record is CREATED

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

from .constants import VALID_TRANSITIONS, KnowledgeLifecycleState
from .exceptions import KnowledgeValidationError
from .knowledge_session import KnowledgeSession


class KnowledgeValidationCode(str, Enum):
    IDENTIFIER_CONSISTENCY  = "IDENTIFIER_CONSISTENCY"
    LIFECYCLE_CONSISTENCY   = "LIFECYCLE_CONSISTENCY"
    TRANSITION_VALIDITY     = "TRANSITION_VALIDITY"
    TIMESTAMP_CONSISTENCY   = "TIMESTAMP_CONSISTENCY"
    HISTORY_INTEGRITY       = "HISTORY_INTEGRITY"


@dataclass(frozen=True)
class KnowledgeValidationResult:
    """Result of a single validation check."""
    code:    KnowledgeValidationCode
    passed:  bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code":    self.code.value,
            "passed":  self.passed,
            "message": self.message,
        }


class KnowledgeValidator:
    """
    Validates the structural integrity of :class:`KnowledgeSession` objects.
    """

    def validate(
        self, session: KnowledgeSession, *, raise_on_failure: bool = False
    ) -> List[KnowledgeValidationResult]:
        """
        Run all five checks against *session*.

        Parameters
        ----------
        session :          Session to validate.
        raise_on_failure : When ``True``, raise :class:`KnowledgeValidationError`
                           if any check fails.

        Returns
        -------
        List[KnowledgeValidationResult]
            One result per check, in definition order.
        """
        results = [
            self._check_identifier_consistency(session),
            self._check_lifecycle_consistency(session),
            self._check_transition_validity(session),
            self._check_timestamp_consistency(session),
            self._check_history_integrity(session),
        ]

        if raise_on_failure:
            failures = [r for r in results if not r.passed]
            if failures:
                msgs = "; ".join(f.message for f in failures)
                raise KnowledgeValidationError(f"Validation failed: {msgs}")

        return results

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_identifier_consistency(
        session: KnowledgeSession,
    ) -> KnowledgeValidationResult:
        code = KnowledgeValidationCode.IDENTIFIER_CONSISTENCY
        if not isinstance(session.session_id, str) or not session.session_id.strip():
            return KnowledgeValidationResult(
                code=code, passed=False, message="session_id is empty or not a string"
            )
        if not isinstance(session.artifact_id, str) or not session.artifact_id.strip():
            return KnowledgeValidationResult(
                code=code, passed=False, message="artifact_id is empty or not a string"
            )
        return KnowledgeValidationResult(code=code, passed=True, message="OK")

    @staticmethod
    def _check_lifecycle_consistency(
        session: KnowledgeSession,
    ) -> KnowledgeValidationResult:
        code = KnowledgeValidationCode.LIFECYCLE_CONSISTENCY
        try:
            KnowledgeLifecycleState(session.state.value)
        except (ValueError, AttributeError):
            return KnowledgeValidationResult(
                code=code, passed=False, message=f"Invalid state value: {session.state!r}"
            )
        return KnowledgeValidationResult(code=code, passed=True, message="OK")

    @staticmethod
    def _check_transition_validity(
        session: KnowledgeSession,
    ) -> KnowledgeValidationResult:
        code = KnowledgeValidationCode.TRANSITION_VALIDITY
        for t in session.transitions:
            allowed = VALID_TRANSITIONS.get(t.from_state, frozenset())
            if t.to_state not in allowed:
                return KnowledgeValidationResult(
                    code=code,
                    passed=False,
                    message=(
                        f"Invalid transition {t.from_state.value!r} → "
                        f"{t.to_state.value!r} in session {session.session_id!r}"
                    ),
                )
        return KnowledgeValidationResult(code=code, passed=True, message="OK")

    @staticmethod
    def _check_timestamp_consistency(
        session: KnowledgeSession,
    ) -> KnowledgeValidationResult:
        code = KnowledgeValidationCode.TIMESTAMP_CONSISTENCY
        if session.updated_at < session.created_at:
            return KnowledgeValidationResult(
                code=code,
                passed=False,
                message="updated_at is before created_at",
            )
        if session.start_time is not None and session.start_time < session.created_at:
            return KnowledgeValidationResult(
                code=code,
                passed=False,
                message="start_time is before created_at",
            )
        if (
            session.start_time is not None
            and session.end_time is not None
            and session.end_time < session.start_time
        ):
            return KnowledgeValidationResult(
                code=code,
                passed=False,
                message="end_time is before start_time",
            )
        return KnowledgeValidationResult(code=code, passed=True, message="OK")

    @staticmethod
    def _check_history_integrity(
        session: KnowledgeSession,
    ) -> KnowledgeValidationResult:
        code = KnowledgeValidationCode.HISTORY_INTEGRITY
        history = session.state_history
        if not history:
            return KnowledgeValidationResult(
                code=code, passed=False, message="State history is empty"
            )
        first = history[0]
        if first.state != KnowledgeLifecycleState.CREATED:
            return KnowledgeValidationResult(
                code=code,
                passed=False,
                message=f"First history entry is {first.state.value!r}, expected 'created'",
            )
        return KnowledgeValidationResult(code=code, passed=True, message="OK")
