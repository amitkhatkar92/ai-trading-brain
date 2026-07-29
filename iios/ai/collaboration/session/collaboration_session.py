"""
collaboration_session.py -- iios.ai.collaboration.session
===========================================================
:class:`CollaborationSession` — central mutable coordinator for one A6 session.

Life-cycle
----------
  session = CollaborationSession(metadata, event_bus, ...)
  session.open()
  p = session.invite_agent(...)
  session.start_debate()
  session.submit_argument(...)
  session.next_round()
  session.close_debate()
  session.vote(...)
  result = session.calculate_consensus()
  final  = session.close()

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, FrozenSet, List, Optional

from ..consensus.consensus_manager  import ConsensusManager
from ..consensus.consensus_result   import ConsensusResult
from ..core.agent_role_assignment   import CollaborationRole
from ..core.collaboration_context   import CollaborationContext
from ..core.collaboration_metadata  import CollaborationMetadata, CollaborationStatus
from ..core.collaboration_result    import CollaborationOutcome, CollaborationResult
from ..core.participant             import Participant, ParticipantStatus
from ..debate.debate_manager        import DebateManager
from ..debate.debate_position       import DebatePosition, PositionType
from ..debate.debate_result         import DebateResult
from ..escalation.escalation_manager import EscalationManager
from ..escalation.escalation_request  import EscalationRequest
from ..escalation.escalation_rule     import EscalationTrigger
from ..events.collaboration_event_bus import CollaborationEventBus
from ..events.collaboration_events    import (
    AgentInvitedEvent,
    AgentRespondedEvent,
    CollaborationClosedEvent,
    CollaborationStartedEvent,
    ConsensusFailedEvent,
    ConsensusReachedEvent,
    DebateCompletedEvent,
    DebateRoundClosedEvent,
    DebateStartedEvent,
    EscalationTriggeredEvent,
    VoteSubmittedEvent,
)
from ..exceptions.collaboration_exceptions import (
    AICollaborationParticipantAlreadyExistsError,
    AICollaborationParticipantNotFoundError,
    AICollaborationSessionClosedError,
    AICollaborationValidationError,
)
from ..messaging.agent_message  import AgentMessage, MessagePriority, MessageType
from ..messaging.message_bus    import MessageBus
from ..messaging.message_envelope import MessageEnvelope


class CollaborationSession:
    """
    Central mutable coordinator for one collaboration session.

    Thread-safe via an internal :class:`RLock`.
    All state mutations are funnelled through this class.
    """

    def __init__(
        self,
        metadata:             CollaborationMetadata,
        event_bus:            CollaborationEventBus,
        debate_manager:       DebateManager,
        consensus_manager:    ConsensusManager,
        escalation_manager:   EscalationManager,
        message_bus:          MessageBus,
    ) -> None:
        self._metadata           = metadata
        self._event_bus          = event_bus
        self._debate_manager     = debate_manager
        self._consensus_manager  = consensus_manager
        self._escalation_manager = escalation_manager
        self._message_bus        = message_bus

        self._lock:          threading.RLock                    = threading.RLock()
        self._status:        CollaborationStatus                = CollaborationStatus.CREATED
        self._participants:  Dict[str, Participant]             = {}
        self._started_at:    Optional[float]                    = None
        self._consensus:     Optional[ConsensusResult]          = None
        self._debate_result: Optional[DebateResult]             = None
        self._result:        Optional[CollaborationResult]      = None
        self._votes:         List[DebatePosition]               = []

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def open(self) -> None:
        with self._lock:
            self._require_not_closed()
            if self._status != CollaborationStatus.CREATED:
                return
            self._status     = CollaborationStatus.OPEN
            self._started_at = time.time()
        self._event_bus.publish(CollaborationStartedEvent.create(
            session_id         = self.session_id,
            topic              = self._metadata.topic,
            collaboration_type = self._metadata.collaboration_type.value,
        ))

    def close(self) -> CollaborationResult:
        with self._lock:
            if self._status in (CollaborationStatus.CLOSED, CollaborationStatus.FAILED):
                if self._result:
                    return self._result
                raise AICollaborationSessionClosedError(f"Session '{self.session_id}' already closed.")

            outcome    = self._determine_outcome()
            confidence = self._consensus.confidence if self._consensus else 0.0
            decision   = (
                self._consensus.winning_position
                if self._consensus and self._consensus.is_decided()
                else None
            )
            participant_ids = list(self._participants.keys())
            dissenting      = frozenset()
            if self._consensus and self._consensus.winning_position:
                dissenting = frozenset(
                    p.agent_id for p in self._participants.values()
                    if p.agent_id not in (
                        [v.agent_id for v in self._votes
                         if v.position_type.value == self._consensus.winning_position]
                    )
                )

            self._result = CollaborationResult(
                result_id            = self._metadata.session_id + ":result",
                session_id           = self.session_id,
                outcome              = outcome,
                decision             = decision,
                confidence           = confidence,
                participating_agents = len(participant_ids),
                rounds_completed    = (
                    self._debate_manager.get(self.session_id).current_round_number
                    if self._debate_manager.exists(self.session_id) else 0
                ),
                dissenting_agents   = dissenting,
                reasoning           = self._build_reasoning(),
                completed_at        = time.time(),
            )
            self._status = CollaborationStatus.CLOSED

        self._event_bus.publish(CollaborationClosedEvent.create(
            session_id  = self.session_id,
            outcome     = outcome.value,
            confidence  = confidence,
        ))
        return self._result

    # ── Participation ─────────────────────────────────────────────────────────

    def invite_agent(
        self,
        agent_id:   str,
        agent_name: str,
        agent_type: str,
        role:       CollaborationRole,
        weight:     float = 1.0,
    ) -> Participant:
        with self._lock:
            self._require_not_closed()
            if agent_id in self._participants:
                raise AICollaborationParticipantAlreadyExistsError(
                    f"Agent '{agent_id}' already in session '{self.session_id}'."
                )
            p = Participant(
                participant_id = agent_id + ":" + self.session_id,
                agent_id       = agent_id,
                agent_name     = agent_name,
                agent_type     = agent_type,
                role           = role,
                status         = ParticipantStatus.ACTIVE,
                joined_at      = time.time(),
                weight         = weight,
            )
            self._participants[agent_id] = p
        self._event_bus.publish(AgentInvitedEvent.create(
            session_id = self.session_id,
            agent_id   = agent_id,
            agent_name = agent_name,
            agent_type = agent_type,
            role       = role.value,
        ))
        return p

    def remove_participant(self, agent_id: str) -> None:
        with self._lock:
            self._require_not_closed()
            if agent_id not in self._participants:
                raise AICollaborationParticipantNotFoundError(
                    f"Agent '{agent_id}' not in session '{self.session_id}'."
                )
            p = self._participants[agent_id]
            self._participants[agent_id] = p.with_status(ParticipantStatus.REMOVED)

    # ── Messaging ─────────────────────────────────────────────────────────────

    def send_message(
        self,
        sender_id:    str,
        recipient_id: str,
        content:      Any,
        message_type: MessageType    = MessageType.DIRECT,
        priority:     MessagePriority = MessagePriority.NORMAL,
    ) -> AgentMessage:
        msg = AgentMessage.create(
            sender_id    = sender_id,
            session_id   = self.session_id,
            message_type = message_type,
            content      = content,
            recipient_id = recipient_id,
            priority     = priority,
        )
        self._message_bus.send(msg)
        return msg

    def broadcast_message(
        self,
        sender_id:    str,
        content:      Any,
        message_type: MessageType     = MessageType.BROADCAST,
    ) -> AgentMessage:
        msg = AgentMessage.create(
            sender_id    = sender_id,
            session_id   = self.session_id,
            message_type = message_type,
            content      = content,
        )
        self._message_bus.send(msg)
        return msg

    def get_messages(
        self,
        sender_id:    Optional[str]        = None,
        message_type: Optional[MessageType] = None,
    ) -> List[AgentMessage]:
        return self._message_bus.get_history(
            session_id   = self.session_id,
            sender_id    = sender_id,
            message_type = message_type,
        )

    # ── Debate ────────────────────────────────────────────────────────────────

    def start_debate(self) -> None:
        with self._lock:
            self._require_not_closed()
            if not self._debate_manager.exists(self.session_id):
                self._debate_manager.create(self.session_id, self._metadata.topic)
            self._status = CollaborationStatus.DEBATING
        self._event_bus.publish(DebateStartedEvent.create(
            session_id = self.session_id,
            topic      = self._metadata.topic,
        ))

    def submit_argument(
        self,
        agent_id:      str,
        position_type: PositionType,
        argument:      str                  = "",
        evidence:      FrozenSet[str]       = frozenset(),
        confidence:    float                = 1.0,
        responds_to:   Optional[str]        = None,
    ) -> DebatePosition:
        ds  = self._debate_manager.get(self.session_id)
        pos = ds.submit_position(
            agent_id      = agent_id,
            position_type = position_type,
            argument      = argument,
            evidence      = evidence,
            confidence    = confidence,
            responds_to   = responds_to,
        )
        self._event_bus.publish(AgentRespondedEvent.create(
            session_id    = self.session_id,
            agent_id      = agent_id,
            position_type = position_type.value,
            round_number  = ds.current_round_number,
        ))
        return pos

    def next_round(self):
        ds    = self._debate_manager.get(self.session_id)
        round_ = ds.closed_rounds[-1] if ds.closed_rounds else None
        ds.next_round()
        if round_:
            self._event_bus.publish(DebateRoundClosedEvent.create(
                session_id     = self.session_id,
                round_number   = round_.round_number,
                position_count = round_.position_count(),
            ))
        return ds

    def close_debate(self) -> DebateResult:
        ds     = self._debate_manager.get(self.session_id)
        result = ds.close()
        self._debate_result = result
        with self._lock:
            self._status = CollaborationStatus.VOTING
        self._event_bus.publish(DebateCompletedEvent.create(
            session_id       = self.session_id,
            rounds_completed = result.rounds_completed,
            total_positions  = result.total_positions,
        ))
        return result

    # ── Voting ────────────────────────────────────────────────────────────────

    def vote(
        self,
        agent_id:      str,
        position_type: PositionType,
        confidence:    float = 1.0,
    ) -> DebatePosition:
        with self._lock:
            self._require_not_closed()
        # Reuse DebatePosition as the vote record
        pos = DebatePosition.create(
            session_id    = self.session_id,
            agent_id      = agent_id,
            round_number  = 0,
            position_type = position_type,
            argument      = "vote",
            confidence    = confidence,
        )
        with self._lock:
            self._votes.append(pos)
        self._event_bus.publish(VoteSubmittedEvent.create(
            session_id    = self.session_id,
            agent_id      = agent_id,
            position_type = position_type.value,
            confidence    = confidence,
        ))
        return pos

    def calculate_consensus(self, strategy_name: str = "majority") -> ConsensusResult:
        with self._lock:
            self._require_not_closed()
            weights = {p.agent_id: p.weight for p in self._participants.values()}
        votes = list(self._votes)
        result = self._consensus_manager.calculate(
            session_id    = self.session_id,
            positions     = votes,
            strategy_name = strategy_name,
            weights       = weights,
        )
        with self._lock:
            self._consensus = result
        if result.is_decided():
            self._event_bus.publish(ConsensusReachedEvent.create(
                session_id = self.session_id,
                decision   = result.winning_position or "",
                confidence = result.confidence,
                strategy   = strategy_name,
            ))
        else:
            self._event_bus.publish(ConsensusFailedEvent.create(
                session_id = self.session_id,
                reason     = result.outcome.value,
                strategy   = strategy_name,
            ))
        return result

    # ── Escalation ────────────────────────────────────────────────────────────

    def escalate(
        self,
        trigger:      EscalationTrigger,
        reason:       str,
        requested_by: str = "system",
        escalate_to:  Optional[str] = None,
    ) -> EscalationRequest:
        req = self._escalation_manager.create(
            session_id   = self.session_id,
            trigger      = trigger,
            reason       = reason,
            requested_by = requested_by,
            escalate_to  = escalate_to,
        )
        with self._lock:
            self._status = CollaborationStatus.ESCALATED
        self._event_bus.publish(EscalationTriggeredEvent.create(
            session_id  = self.session_id,
            trigger     = trigger.value,
            reason      = reason,
            request_id  = req.request_id,
        ))
        return req

    # ── Snapshot / context ────────────────────────────────────────────────────

    def context(self) -> CollaborationContext:
        with self._lock:
            participants = frozenset(self._participants.values())
            status       = self._status
            round_no     = (
                self._debate_manager.get(self.session_id).current_round_number
                if self._debate_manager.exists(self.session_id) else 0
            )
        return CollaborationContext.create(
            metadata      = self._metadata,
            status        = status,
            participants  = participants,
            current_round = round_no,
            total_rounds  = self._metadata.max_rounds,
        )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._metadata.session_id

    @property
    def status(self) -> CollaborationStatus:
        with self._lock:
            return self._status

    @property
    def metadata(self) -> CollaborationMetadata:
        return self._metadata

    @property
    def participant_count(self) -> int:
        with self._lock:
            return len(self._participants)

    @property
    def result(self) -> Optional[CollaborationResult]:
        return self._result

    @property
    def consensus(self) -> Optional[ConsensusResult]:
        return self._consensus

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _require_not_closed(self) -> None:
        if self._status in (CollaborationStatus.CLOSED, CollaborationStatus.FAILED):
            raise AICollaborationSessionClosedError(
                f"Session '{self.session_id}' is closed."
            )

    def _determine_outcome(self) -> CollaborationOutcome:
        if self._status == CollaborationStatus.ESCALATED:
            return CollaborationOutcome.ESCALATED
        if self._consensus and self._consensus.is_decided():
            return CollaborationOutcome.CONSENSUS_REACHED
        if self._votes:
            return CollaborationOutcome.MAJORITY_VOTE
        return CollaborationOutcome.FAILED

    def _build_reasoning(self) -> str:
        parts = []
        if self._debate_result:
            parts.append(self._debate_result.summary)
        if self._consensus:
            parts.append(f"Consensus strategy: {self._consensus.strategy_used}.")
        return " ".join(parts) if parts else "Session closed."
