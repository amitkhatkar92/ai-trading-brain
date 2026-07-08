"""
iios/intelligence/reasoning/reasoning_exceptions.py
====================================================
Exception hierarchy for the Reasoning & Debate Engine.
Error-code prefix: RSN-
"""
from __future__ import annotations


class ReasoningError(Exception):
    """Base exception for all reasoning errors.  Code: RSN-000"""
    code = "RSN-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}")


# ── Session errors (RSN-01x) ──────────────────────────────────────────────────

class ReasoningSessionError(ReasoningError):
    """Base for session lifecycle errors.  Code: RSN-010"""
    code = "RSN-010"


class SessionNotFoundError(ReasoningSessionError):
    """Session ID not in registry.  Code: RSN-011"""
    code = "RSN-011"

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session not found: {session_id!r}")


class SessionAlreadyExistsError(ReasoningSessionError):
    """Duplicate session registration.  Code: RSN-012"""
    code = "RSN-012"

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session already exists: {session_id!r}")


class SessionTimeoutError(ReasoningSessionError):
    """Session exceeded its time budget.  Code: RSN-013"""
    code = "RSN-013"

    def __init__(self, session_id: str, timeout_s: float) -> None:
        super().__init__(
            f"Session {session_id!r} timed out after {timeout_s:.1f}s"
        )


class SessionStateError(ReasoningSessionError):
    """Operation not permitted in the current session state.  Code: RSN-014"""
    code = "RSN-014"

    def __init__(self, session_id: str, current: str, expected: str) -> None:
        super().__init__(
            f"Session {session_id!r} is {current!r}; expected {expected!r}"
        )


# ── Evidence errors (RSN-02x) ─────────────────────────────────────────────────

class EvidenceError(ReasoningError):
    """Base for evidence handling errors.  Code: RSN-020"""
    code = "RSN-020"


class EvidenceNotFoundError(EvidenceError):
    """Evidence ID not in registry.  Code: RSN-021"""
    code = "RSN-021"

    def __init__(self, evidence_id: str) -> None:
        super().__init__(f"Evidence not found: {evidence_id!r}")


class EvidenceValidationError(EvidenceError):
    """Evidence failed validation checks.  Code: RSN-022"""
    code = "RSN-022"

    def __init__(self, evidence_id: str, reason: str) -> None:
        super().__init__(
            f"Evidence {evidence_id!r} failed validation: {reason}"
        )


class EvidenceConflictError(EvidenceError):
    """Conflicting evidence items detected.  Code: RSN-023"""
    code = "RSN-023"

    def __init__(self, ids: list[str]) -> None:
        super().__init__(f"Conflicting evidence items: {ids}")


class InsufficientEvidenceError(EvidenceError):
    """Not enough evidence to proceed.  Code: RSN-024"""
    code = "RSN-024"

    def __init__(self, required: int, available: int) -> None:
        super().__init__(
            f"Insufficient evidence: need {required}, have {available}"
        )


# ── Debate errors (RSN-03x) ────────────────────────────────────────────────────

class DebateError(ReasoningError):
    """Base for debate execution errors.  Code: RSN-030"""
    code = "RSN-030"


class DebateNotFoundError(DebateError):
    """Debate session ID not found.  Code: RSN-031"""
    code = "RSN-031"

    def __init__(self, debate_id: str) -> None:
        super().__init__(f"Debate not found: {debate_id!r}")


class DebateDeadlockError(DebateError):
    """Debate could not reach consensus.  Code: RSN-032"""
    code = "RSN-032"

    def __init__(self, debate_id: str, rounds: int) -> None:
        super().__init__(
            f"Debate {debate_id!r} deadlocked after {rounds} round(s)"
        )


class DebateTimeoutError(DebateError):
    """Debate exceeded its time budget.  Code: RSN-033"""
    code = "RSN-033"

    def __init__(self, debate_id: str, timeout_s: float) -> None:
        super().__init__(
            f"Debate {debate_id!r} timed out after {timeout_s:.1f}s"
        )


class InsufficientParticipantsError(DebateError):
    """Not enough participants for a meaningful debate.  Code: RSN-034"""
    code = "RSN-034"

    def __init__(self, required: int, available: int) -> None:
        super().__init__(
            f"Insufficient debate participants: need {required}, have {available}"
        )


# ── Confidence errors (RSN-04x) ────────────────────────────────────────────────

class ConfidenceError(ReasoningError):
    """Base for confidence calculation errors.  Code: RSN-040"""
    code = "RSN-040"


class InsufficientDataForConfidenceError(ConfidenceError):
    """Not enough data to compute a confidence score.  Code: RSN-041"""
    code = "RSN-041"

    def __init__(self, reason: str) -> None:
        super().__init__(f"Insufficient data for confidence: {reason}")


class ConfidenceCalculationError(ConfidenceError):
    """Numeric error during confidence calculation.  Code: RSN-042"""
    code = "RSN-042"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Confidence calculation failed: {detail}")


# ── Explanation errors (RSN-05x) ───────────────────────────────────────────────

class ExplanationError(ReasoningError):
    """Base for explanation generation errors.  Code: RSN-050"""
    code = "RSN-050"


class ExplanationNotFoundError(ExplanationError):
    """No explanation available for the given ID.  Code: RSN-051"""
    code = "RSN-051"

    def __init__(self, explanation_id: str) -> None:
        super().__init__(f"Explanation not found: {explanation_id!r}")


class TraceNotFoundError(ExplanationError):
    """No trace exists for the given session.  Code: RSN-052"""
    code = "RSN-052"

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Reasoning trace not found for session: {session_id!r}")


# ── Engine errors (RSN-06x) ────────────────────────────────────────────────────

class ReasoningEngineError(ReasoningError):
    """Base for top-level engine errors.  Code: RSN-060"""
    code = "RSN-060"


class EngineNotInitializedError(ReasoningEngineError):
    """Engine used before initialize() was called.  Code: RSN-061"""
    code = "RSN-061"

    def __init__(self) -> None:
        super().__init__(
            "Reasoning engine not initialized; call initialize() first"
        )


class EngineAlreadyRunningError(ReasoningEngineError):
    """Engine.start() called while already running.  Code: RSN-062"""
    code = "RSN-062"

    def __init__(self) -> None:
        super().__init__("Reasoning engine is already running")
