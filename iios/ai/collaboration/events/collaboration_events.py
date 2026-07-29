"""
collaboration_events.py -- iios.ai.collaboration.events
=========================================================
Immutable event types for the A6 Collaboration Framework.

All events are frozen dataclasses with a ``create()`` factory.

Event types
-----------
CollaborationStarted       — session transitioned to OPEN
AgentInvited               — agent joined as participant
AgentResponded             — agent submitted a position
DebateStarted              — debate phase opened
DebateRoundClosed          — a debate round was completed
DebateCompleted            — debate phase closed
VoteSubmitted              — agent cast a final vote
ConsensusReached           — consensus strategy succeeded
ConsensusFailed            — consensus strategy failed
EscalationTriggered        — escalation was requested
EscalationResolved         — escalation was decided
MessageSent                — message dispatched on message bus
CollaborationClosed        — session closed (terminal)

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CollaborationEventType(str, Enum):
    """All collaboration event identifiers.  Values are persisted — do not rename."""

    COLLABORATION_STARTED  = "collaboration_started"
    AGENT_INVITED          = "agent_invited"
    AGENT_RESPONDED        = "agent_responded"
    DEBATE_STARTED         = "debate_started"
    DEBATE_ROUND_CLOSED    = "debate_round_closed"
    DEBATE_COMPLETED       = "debate_completed"
    VOTE_SUBMITTED         = "vote_submitted"
    CONSENSUS_REACHED      = "consensus_reached"
    CONSENSUS_FAILED       = "consensus_failed"
    ESCALATION_TRIGGERED   = "escalation_triggered"
    ESCALATION_RESOLVED    = "escalation_resolved"
    MESSAGE_SENT           = "message_sent"
    COLLABORATION_CLOSED   = "collaboration_closed"


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CollaborationEvent:
    """Base class for all A6 collaboration events."""

    event_id:   str
    event_type: CollaborationEventType
    session_id: str
    occurred_at: float


# ---------------------------------------------------------------------------
# Session lifecycle events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CollaborationStartedEvent(CollaborationEvent):
    topic: str
    collaboration_type: str

    @classmethod
    def create(cls, session_id: str, topic: str, collaboration_type: str) -> "CollaborationStartedEvent":
        return cls(
            event_id           = str(uuid.uuid4()),
            event_type         = CollaborationEventType.COLLABORATION_STARTED,
            session_id         = session_id,
            occurred_at        = time.time(),
            topic              = topic,
            collaboration_type = collaboration_type,
        )


@dataclass(frozen=True)
class CollaborationClosedEvent(CollaborationEvent):
    outcome: str
    confidence: float

    @classmethod
    def create(cls, session_id: str, outcome: str, confidence: float) -> "CollaborationClosedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = CollaborationEventType.COLLABORATION_CLOSED,
            session_id  = session_id,
            occurred_at = time.time(),
            outcome     = outcome,
            confidence  = confidence,
        )


# ---------------------------------------------------------------------------
# Participant events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentInvitedEvent(CollaborationEvent):
    agent_id:   str
    agent_name: str
    agent_type: str
    role:       str

    @classmethod
    def create(
        cls,
        session_id: str,
        agent_id:   str,
        agent_name: str,
        agent_type: str,
        role:       str,
    ) -> "AgentInvitedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = CollaborationEventType.AGENT_INVITED,
            session_id  = session_id,
            occurred_at = time.time(),
            agent_id    = agent_id,
            agent_name  = agent_name,
            agent_type  = agent_type,
            role        = role,
        )


@dataclass(frozen=True)
class AgentRespondedEvent(CollaborationEvent):
    agent_id:      str
    position_type: str
    round_number:  int

    @classmethod
    def create(
        cls,
        session_id:    str,
        agent_id:      str,
        position_type: str,
        round_number:  int,
    ) -> "AgentRespondedEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = CollaborationEventType.AGENT_RESPONDED,
            session_id    = session_id,
            occurred_at   = time.time(),
            agent_id      = agent_id,
            position_type = position_type,
            round_number  = round_number,
        )


# ---------------------------------------------------------------------------
# Debate events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DebateStartedEvent(CollaborationEvent):
    topic: str

    @classmethod
    def create(cls, session_id: str, topic: str) -> "DebateStartedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = CollaborationEventType.DEBATE_STARTED,
            session_id  = session_id,
            occurred_at = time.time(),
            topic       = topic,
        )


@dataclass(frozen=True)
class DebateRoundClosedEvent(CollaborationEvent):
    round_number:     int
    position_count:   int

    @classmethod
    def create(
        cls,
        session_id:     str,
        round_number:   int,
        position_count: int,
    ) -> "DebateRoundClosedEvent":
        return cls(
            event_id        = str(uuid.uuid4()),
            event_type      = CollaborationEventType.DEBATE_ROUND_CLOSED,
            session_id      = session_id,
            occurred_at     = time.time(),
            round_number    = round_number,
            position_count  = position_count,
        )


@dataclass(frozen=True)
class DebateCompletedEvent(CollaborationEvent):
    rounds_completed: int
    total_positions:  int

    @classmethod
    def create(
        cls,
        session_id:      str,
        rounds_completed: int,
        total_positions:  int,
    ) -> "DebateCompletedEvent":
        return cls(
            event_id         = str(uuid.uuid4()),
            event_type       = CollaborationEventType.DEBATE_COMPLETED,
            session_id       = session_id,
            occurred_at      = time.time(),
            rounds_completed = rounds_completed,
            total_positions  = total_positions,
        )


# ---------------------------------------------------------------------------
# Voting and consensus events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VoteSubmittedEvent(CollaborationEvent):
    agent_id:      str
    position_type: str
    confidence:    float

    @classmethod
    def create(
        cls,
        session_id:    str,
        agent_id:      str,
        position_type: str,
        confidence:    float,
    ) -> "VoteSubmittedEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = CollaborationEventType.VOTE_SUBMITTED,
            session_id    = session_id,
            occurred_at   = time.time(),
            agent_id      = agent_id,
            position_type = position_type,
            confidence    = confidence,
        )


@dataclass(frozen=True)
class ConsensusReachedEvent(CollaborationEvent):
    decision:   str
    confidence: float
    strategy:   str

    @classmethod
    def create(
        cls,
        session_id: str,
        decision:   str,
        confidence: float,
        strategy:   str,
    ) -> "ConsensusReachedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = CollaborationEventType.CONSENSUS_REACHED,
            session_id  = session_id,
            occurred_at = time.time(),
            decision    = decision,
            confidence  = confidence,
            strategy    = strategy,
        )


@dataclass(frozen=True)
class ConsensusFailedEvent(CollaborationEvent):
    reason:   str
    strategy: str

    @classmethod
    def create(cls, session_id: str, reason: str, strategy: str) -> "ConsensusFailedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = CollaborationEventType.CONSENSUS_FAILED,
            session_id  = session_id,
            occurred_at = time.time(),
            reason      = reason,
            strategy    = strategy,
        )


# ---------------------------------------------------------------------------
# Escalation events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EscalationTriggeredEvent(CollaborationEvent):
    trigger:    str
    reason:     str
    request_id: str

    @classmethod
    def create(
        cls,
        session_id:  str,
        trigger:     str,
        reason:      str,
        request_id:  str,
    ) -> "EscalationTriggeredEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = CollaborationEventType.ESCALATION_TRIGGERED,
            session_id  = session_id,
            occurred_at = time.time(),
            trigger     = trigger,
            reason      = reason,
            request_id  = request_id,
        )


@dataclass(frozen=True)
class EscalationResolvedEvent(CollaborationEvent):
    request_id: str
    action:     str
    decided_by: str

    @classmethod
    def create(
        cls,
        session_id:  str,
        request_id:  str,
        action:      str,
        decided_by:  str,
    ) -> "EscalationResolvedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = CollaborationEventType.ESCALATION_RESOLVED,
            session_id  = session_id,
            occurred_at = time.time(),
            request_id  = request_id,
            action      = action,
            decided_by  = decided_by,
        )


# ---------------------------------------------------------------------------
# Message event
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MessageSentEvent(CollaborationEvent):
    message_id:   str
    sender_id:    str
    message_type: str
    broadcast:    bool

    @classmethod
    def create(
        cls,
        session_id:   str,
        message_id:   str,
        sender_id:    str,
        message_type: str,
        broadcast:    bool = False,
    ) -> "MessageSentEvent":
        return cls(
            event_id     = str(uuid.uuid4()),
            event_type   = CollaborationEventType.MESSAGE_SENT,
            session_id   = session_id,
            occurred_at  = time.time(),
            message_id   = message_id,
            sender_id    = sender_id,
            message_type = message_type,
            broadcast    = broadcast,
        )
