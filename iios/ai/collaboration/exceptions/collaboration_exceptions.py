"""
collaboration_exceptions.py -- iios.ai.collaboration.exceptions
================================================================
A6 exception hierarchy.  All exceptions extend :class:`AIException` from A1.

Error code range: AI-1100 – AI-1199

Hierarchy
---------
AIException (A1, AI-000)
└── AICollaborationException          AI-1100  base collaboration exception
    ├── AICollaborationSessionNotFoundError   AI-1101
    ├── AICollaborationSessionAlreadyExistsError  AI-1102
    ├── AICollaborationSessionClosedError     AI-1103
    ├── AICollaborationParticipantNotFoundError  AI-1104
    ├── AICollaborationParticipantAlreadyExistsError  AI-1105
    ├── AICollaborationValidationError        AI-1106
    ├── AIMessageException                    AI-1110  base message exception
    │   ├── AIMessageNotFoundError            AI-1111
    │   └── AIMessageRoutingError             AI-1112
    ├── AIDebateException                     AI-1120  base debate exception
    │   ├── AIDebateNotFoundError             AI-1121
    │   ├── AIDebateAlreadyClosedError        AI-1122
    │   └── AIDebateRoundError               AI-1123
    ├── AIConsensusException                  AI-1130  base consensus exception
    │   ├── AIConsensusFailedError            AI-1131
    │   └── AIConsensusTimeoutError          AI-1132
    ├── AIEscalationException                 AI-1140  base escalation exception
    │   ├── AIEscalationNotFoundError         AI-1141
    │   └── AIEscalationPolicyViolationError  AI-1142
    └── AICollaborationPolicyException        AI-1150  base policy exception
        └── AICollaborationPolicyViolationError  AI-1151

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

from iios.ai.foundation.exceptions import AIException


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class AICollaborationException(AIException):
    """Base exception for the A6 Collaboration Framework (AI-1100)."""

    def __init__(self, message: str = "Collaboration error", code: str = "AI-1100") -> None:
        super().__init__(message, code=code)


# ---------------------------------------------------------------------------
# Session errors  AI-1101–AI-1106
# ---------------------------------------------------------------------------

class AICollaborationSessionNotFoundError(AICollaborationException):
    """Collaboration session not found (AI-1101)."""

    def __init__(self, session_id: str = "") -> None:
        super().__init__(
            f"Collaboration session not found: {session_id!r}" if session_id else "Collaboration session not found",
            code="AI-1101",
        )


class AICollaborationSessionAlreadyExistsError(AICollaborationException):
    """Collaboration session with that ID already exists (AI-1102)."""

    def __init__(self, session_id: str = "") -> None:
        super().__init__(
            f"Collaboration session already exists: {session_id!r}" if session_id else "Session already exists",
            code="AI-1102",
        )


class AICollaborationSessionClosedError(AICollaborationException):
    """Operation not permitted on a closed collaboration session (AI-1103)."""

    def __init__(self, session_id: str = "") -> None:
        super().__init__(
            f"Collaboration session is closed: {session_id!r}" if session_id else "Session is closed",
            code="AI-1103",
        )


class AICollaborationParticipantNotFoundError(AICollaborationException):
    """Agent is not a participant in this session (AI-1104)."""

    def __init__(self, agent_id: str = "") -> None:
        super().__init__(
            f"Participant not found: {agent_id!r}" if agent_id else "Participant not found",
            code="AI-1104",
        )


class AICollaborationParticipantAlreadyExistsError(AICollaborationException):
    """Agent is already a participant in this session (AI-1105)."""

    def __init__(self, agent_id: str = "") -> None:
        super().__init__(
            f"Participant already invited: {agent_id!r}" if agent_id else "Participant already invited",
            code="AI-1105",
        )


class AICollaborationValidationError(AICollaborationException):
    """Collaboration request failed validation (AI-1106)."""

    def __init__(self, message: str = "Collaboration validation failed") -> None:
        super().__init__(message, code="AI-1106")


# ---------------------------------------------------------------------------
# Message errors  AI-1110–AI-1112
# ---------------------------------------------------------------------------

class AIMessageException(AICollaborationException):
    """Base exception for messaging operations (AI-1110)."""

    def __init__(self, message: str = "Message error", code: str = "AI-1110") -> None:
        super().__init__(message, code=code)


class AIMessageNotFoundError(AIMessageException):
    """Message not found (AI-1111)."""

    def __init__(self, message_id: str = "") -> None:
        super().__init__(
            f"Message not found: {message_id!r}" if message_id else "Message not found",
            code="AI-1111",
        )


class AIMessageRoutingError(AIMessageException):
    """Message could not be routed to recipient (AI-1112)."""

    def __init__(self, message: str = "Message routing failed") -> None:
        super().__init__(message, code="AI-1112")


# ---------------------------------------------------------------------------
# Debate errors  AI-1120–AI-1123
# ---------------------------------------------------------------------------

class AIDebateException(AICollaborationException):
    """Base exception for debate operations (AI-1120)."""

    def __init__(self, message: str = "Debate error", code: str = "AI-1120") -> None:
        super().__init__(message, code=code)


class AIDebateNotFoundError(AIDebateException):
    """Debate session not found (AI-1121)."""

    def __init__(self, session_id: str = "") -> None:
        super().__init__(
            f"Debate session not found: {session_id!r}" if session_id else "Debate session not found",
            code="AI-1121",
        )


class AIDebateAlreadyClosedError(AIDebateException):
    """Debate session is already closed (AI-1122)."""

    def __init__(self, session_id: str = "") -> None:
        super().__init__(
            f"Debate already closed: {session_id!r}" if session_id else "Debate already closed",
            code="AI-1122",
        )


class AIDebateRoundError(AIDebateException):
    """Invalid debate round operation (AI-1123)."""

    def __init__(self, message: str = "Debate round error") -> None:
        super().__init__(message, code="AI-1123")


# ---------------------------------------------------------------------------
# Consensus errors  AI-1130–AI-1132
# ---------------------------------------------------------------------------

class AIConsensusException(AICollaborationException):
    """Base exception for consensus operations (AI-1130)."""

    def __init__(self, message: str = "Consensus error", code: str = "AI-1130") -> None:
        super().__init__(message, code=code)


class AIConsensusFailedError(AIConsensusException):
    """Consensus could not be reached (AI-1131)."""

    def __init__(self, message: str = "Consensus failed") -> None:
        super().__init__(message, code="AI-1131")


class AIConsensusTimeoutError(AIConsensusException):
    """Consensus calculation timed out (AI-1132)."""

    def __init__(self, message: str = "Consensus timed out") -> None:
        super().__init__(message, code="AI-1132")


# ---------------------------------------------------------------------------
# Escalation errors  AI-1140–AI-1142
# ---------------------------------------------------------------------------

class AIEscalationException(AICollaborationException):
    """Base exception for escalation operations (AI-1140)."""

    def __init__(self, message: str = "Escalation error", code: str = "AI-1140") -> None:
        super().__init__(message, code=code)


class AIEscalationNotFoundError(AIEscalationException):
    """Escalation request not found (AI-1141)."""

    def __init__(self, request_id: str = "") -> None:
        super().__init__(
            f"Escalation request not found: {request_id!r}" if request_id else "Escalation not found",
            code="AI-1141",
        )


class AIEscalationPolicyViolationError(AIEscalationException):
    """Escalation policy was violated (AI-1142)."""

    def __init__(self, message: str = "Escalation policy violation") -> None:
        super().__init__(message, code="AI-1142")


# ---------------------------------------------------------------------------
# Policy errors  AI-1150–AI-1151
# ---------------------------------------------------------------------------

class AICollaborationPolicyException(AICollaborationException):
    """Base exception for collaboration policy operations (AI-1150)."""

    def __init__(self, message: str = "Policy error", code: str = "AI-1150") -> None:
        super().__init__(message, code=code)


class AICollaborationPolicyViolationError(AICollaborationPolicyException):
    """A collaboration policy was violated (AI-1151)."""

    def __init__(self, message: str = "Collaboration policy violation") -> None:
        super().__init__(message, code="AI-1151")
