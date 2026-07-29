"""
test_collaboration.py — comprehensive test suite for A6 Multi-Agent Collaboration.

Coverage targets
----------------
T-EXC   exceptions              (AI-1100–AI-1151)
T-LC    lifecycle re-exports    (M1)
T-CORE  core types              (metadata, role, participant, context, result)
T-EVT   events + event bus
T-MSG   messaging layer
T-DEB   debate layer
T-CNS   consensus layer
T-ESC   escalation layer
T-POL   policy layer
T-SNAP  snapshot layer
T-SES   collaboration session
T-MGR   collaboration manager
T-GW    collaboration gateway (M6)
T-INT   end-to-end integration

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from typing import FrozenSet

import pytest

# ---------------------------------------------------------------------------
# T-EXC  Exceptions
# ---------------------------------------------------------------------------

class TestExceptions:
    """T-EXC: All 22 exception classes with correct error codes."""

    def test_base_exception_code(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationException,
        )
        ex = AICollaborationException("test")
        assert "AI-1100" in ex.message

    def test_session_not_found(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationSessionNotFoundError,
        )
        ex = AICollaborationSessionNotFoundError("s1")
        assert ex.error_code == "AI-1101"

    def test_session_already_exists(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationSessionAlreadyExistsError,
        )
        ex = AICollaborationSessionAlreadyExistsError("s1")
        assert ex.error_code == "AI-1102"

    def test_session_closed(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationSessionClosedError,
        )
        ex = AICollaborationSessionClosedError("s1")
        assert ex.error_code == "AI-1103"

    def test_participant_not_found(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationParticipantNotFoundError,
        )
        ex = AICollaborationParticipantNotFoundError("a1")
        assert ex.error_code == "AI-1104"

    def test_participant_already_exists(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationParticipantAlreadyExistsError,
        )
        ex = AICollaborationParticipantAlreadyExistsError("a1")
        assert ex.error_code == "AI-1105"

    def test_validation_error(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationValidationError,
        )
        ex = AICollaborationValidationError("bad")
        assert ex.error_code == "AI-1106"

    def test_message_exception(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIMessageException,
        )
        ex = AIMessageException("m")
        assert ex.error_code == "AI-1110"

    def test_message_not_found(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIMessageNotFoundError,
        )
        ex = AIMessageNotFoundError("m")
        assert ex.error_code == "AI-1111"

    def test_message_routing_error(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIMessageRoutingError,
        )
        ex = AIMessageRoutingError("m")
        assert ex.error_code == "AI-1112"

    def test_debate_exception(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIDebateException,
        )
        ex = AIDebateException("d")
        assert ex.error_code == "AI-1120"

    def test_debate_not_found(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIDebateNotFoundError,
        )
        ex = AIDebateNotFoundError("d")
        assert ex.error_code == "AI-1121"

    def test_debate_already_closed(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIDebateAlreadyClosedError,
        )
        ex = AIDebateAlreadyClosedError("d")
        assert ex.error_code == "AI-1122"

    def test_debate_round_error(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIDebateRoundError,
        )
        ex = AIDebateRoundError("d")
        assert ex.error_code == "AI-1123"

    def test_consensus_exception(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIConsensusException,
        )
        ex = AIConsensusException("c")
        assert ex.error_code == "AI-1130"

    def test_consensus_failed(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIConsensusFailedError,
        )
        ex = AIConsensusFailedError("c")
        assert ex.error_code == "AI-1131"

    def test_consensus_timeout(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIConsensusTimeoutError,
        )
        ex = AIConsensusTimeoutError("c")
        assert ex.error_code == "AI-1132"

    def test_escalation_exception(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIEscalationException,
        )
        ex = AIEscalationException("e")
        assert ex.error_code == "AI-1140"

    def test_escalation_not_found(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIEscalationNotFoundError,
        )
        ex = AIEscalationNotFoundError("e")
        assert ex.error_code == "AI-1141"

    def test_escalation_policy_violation(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIEscalationPolicyViolationError,
        )
        ex = AIEscalationPolicyViolationError("e")
        assert ex.error_code == "AI-1142"

    def test_collab_policy_exception(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationPolicyException,
        )
        ex = AICollaborationPolicyException("p")
        assert ex.error_code == "AI-1150"

    def test_collab_policy_violation(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationPolicyViolationError,
        )
        ex = AICollaborationPolicyViolationError("p")
        assert ex.error_code == "AI-1151"


# ---------------------------------------------------------------------------
# T-LC  Lifecycle re-exports
# ---------------------------------------------------------------------------

class TestLifecycleReExports:
    """T-LC: M1 lifecycle re-exports."""

    def test_imports(self):
        from iios.ai.collaboration.lifecycle import (
            AILifecycleAwareMixin,
            AILifecycleState,
            AILifecycleError,
            AIInvalidTransitionError,
            AIModuleAlreadyRunningError,
            AIModuleNotRunningError,
        )
        assert AILifecycleAwareMixin is not None
        assert AILifecycleState is not None


# ---------------------------------------------------------------------------
# T-CORE  Core types
# ---------------------------------------------------------------------------

class TestCollaborationMetadata:
    """T-CORE: CollaborationMetadata factory and fields."""

    def test_create(self):
        from iios.ai.collaboration.core.collaboration_metadata import (
            CollaborationMetadata,
            CollaborationType,
        )
        m = CollaborationMetadata.create(
            topic="Buy NIFTY?",
            collaboration_type=CollaborationType.DEBATE,
            created_by="system",
        )
        assert m.topic == "Buy NIFTY?"
        assert m.collaboration_type == CollaborationType.DEBATE
        assert m.max_participants == 10
        assert m.max_rounds == 3

    def test_session_id_is_uuid(self):
        from iios.ai.collaboration.core.collaboration_metadata import (
            CollaborationMetadata,
            CollaborationType,
        )
        m = CollaborationMetadata.create("t", CollaborationType.ANALYSIS, "sys")
        uuid.UUID(m.session_id)  # must not raise

    def test_status_active_terminal(self):
        from iios.ai.collaboration.core.collaboration_metadata import CollaborationStatus
        assert CollaborationStatus.OPEN.is_active()
        assert CollaborationStatus.CLOSED.is_terminal()
        assert not CollaborationStatus.OPEN.is_terminal()


class TestAgentRoleAssignment:
    """T-CORE: CollaborationRole helpers."""

    def test_can_vote(self):
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        assert CollaborationRole.VOTER.can_vote()
        assert CollaborationRole.LEAD.can_vote()
        assert not CollaborationRole.OBSERVER.can_vote()

    def test_can_debate(self):
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        assert CollaborationRole.ANALYST.can_debate()
        assert not CollaborationRole.OBSERVER.can_debate()

    def test_specialist_default_roles(self):
        from iios.ai.collaboration.core.agent_role_assignment import (
            SPECIALIST_DEFAULT_ROLES,
            CollaborationRole,
        )
        assert SPECIALIST_DEFAULT_ROLES["MarketAnalystAgent"] == CollaborationRole.ANALYST


class TestParticipant:
    """T-CORE: Participant and with_status/with_role mutations."""

    def _make(self):
        from iios.ai.collaboration.core.participant import Participant, ParticipantStatus
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        return Participant(
            participant_id = "p1",
            agent_id       = "a1",
            agent_name     = "Alice",
            agent_type     = "Analyst",
            role           = CollaborationRole.ANALYST,
            status         = ParticipantStatus.ACTIVE,
            joined_at      = time.time(),
            weight         = 1.0,
        )

    def test_with_status(self):
        from iios.ai.collaboration.core.participant import ParticipantStatus
        p  = self._make()
        p2 = p.with_status(ParticipantStatus.REMOVED)
        assert p2.status == ParticipantStatus.REMOVED
        assert p.status == ParticipantStatus.ACTIVE  # original unchanged

    def test_can_vote(self):
        from iios.ai.collaboration.core.participant import Participant, ParticipantStatus
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        p = Participant(
            participant_id = "p2",
            agent_id       = "a2",
            agent_name     = "Bob",
            agent_type     = "Risk",
            role           = CollaborationRole.VOTER,
            status         = ParticipantStatus.ACTIVE,
            joined_at      = time.time(),
            weight         = 1.0,
        )
        assert p.can_vote()


class TestCollaborationContext:
    """T-CORE: CollaborationContext factory."""

    def _metadata(self):
        from iios.ai.collaboration.core.collaboration_metadata import (
            CollaborationMetadata,
            CollaborationType,
        )
        return CollaborationMetadata.create("Test", CollaborationType.DEBATE, "sys")

    def test_create(self):
        from iios.ai.collaboration.core.collaboration_context import CollaborationContext
        from iios.ai.collaboration.core.collaboration_metadata import CollaborationStatus
        ctx = CollaborationContext.create(
            metadata      = self._metadata(),
            status        = CollaborationStatus.OPEN,
            participants  = frozenset(),
            current_round = 1,
            total_rounds  = 3,
        )
        assert ctx.session_id is not None
        assert ctx.participant_count == 0

    def test_active_participant_count(self):
        from iios.ai.collaboration.core.collaboration_context import CollaborationContext
        from iios.ai.collaboration.core.collaboration_metadata import CollaborationStatus
        from iios.ai.collaboration.core.participant import Participant, ParticipantStatus
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        p = Participant(
            participant_id="px", agent_id="ax", agent_name="X", agent_type="T",
            role=CollaborationRole.ANALYST, status=ParticipantStatus.ACTIVE,
            joined_at=time.time(), weight=1.0,
        )
        ctx = CollaborationContext.create(
            metadata      = self._metadata(),
            status        = CollaborationStatus.OPEN,
            participants  = frozenset([p]),
            current_round = 1,
            total_rounds  = 3,
        )
        assert ctx.active_participant_count == 1


class TestCollaborationResult:
    """T-CORE: CollaborationResult factories."""

    def test_consensus_factory(self):
        from iios.ai.collaboration.core.collaboration_result import (
            CollaborationResult,
            CollaborationOutcome,
        )
        r = CollaborationResult.consensus(
            session_id           = "s1",
            decision             = "BUY",
            confidence           = 0.9,
            participating_agents = 2,
            rounds_completed     = 2,
        )
        assert r.outcome == CollaborationOutcome.CONSENSUS_REACHED
        assert r.is_decided()

    def test_failed_factory(self):
        from iios.ai.collaboration.core.collaboration_result import (
            CollaborationResult,
            CollaborationOutcome,
        )
        r = CollaborationResult.failed(
            session_id           = "s1",
            reason               = "no consensus",
            participating_agents = 1,
        )
        assert not r.is_decided()


# ---------------------------------------------------------------------------
# T-EVT  Events + EventBus
# ---------------------------------------------------------------------------

class TestCollaborationEvents:
    """T-EVT: All 13 event types have working create() factories."""

    def test_started_event(self):
        from iios.ai.collaboration.events.collaboration_events import CollaborationStartedEvent
        e = CollaborationStartedEvent.create("s1", "topic", "debate")
        assert e.session_id == "s1"

    def test_closed_event(self):
        from iios.ai.collaboration.events.collaboration_events import CollaborationClosedEvent
        e = CollaborationClosedEvent.create("s1", "consensus_reached", 0.9)
        assert e.outcome == "consensus_reached"

    def test_agent_invited_event(self):
        from iios.ai.collaboration.events.collaboration_events import AgentInvitedEvent
        e = AgentInvitedEvent.create("s1", "a1", "Alice", "Analyst", "analyst")
        assert e.agent_id == "a1"

    def test_debate_events(self):
        from iios.ai.collaboration.events.collaboration_events import (
            DebateStartedEvent,
            DebateRoundClosedEvent,
            DebateCompletedEvent,
        )
        assert DebateStartedEvent.create("s1", "topic").session_id == "s1"
        assert DebateRoundClosedEvent.create("s1", 1, 3).round_number == 1
        assert DebateCompletedEvent.create("s1", 2, 5).rounds_completed == 2

    def test_vote_and_consensus_events(self):
        from iios.ai.collaboration.events.collaboration_events import (
            VoteSubmittedEvent,
            ConsensusReachedEvent,
            ConsensusFailedEvent,
        )
        assert VoteSubmittedEvent.create("s1", "a1", "for", 0.8).confidence == 0.8
        assert ConsensusReachedEvent.create("s1", "for", 0.9, "majority").decision == "for"
        assert ConsensusFailedEvent.create("s1", "tie", "majority").reason == "tie"

    def test_escalation_events(self):
        from iios.ai.collaboration.events.collaboration_events import (
            EscalationTriggeredEvent,
            EscalationResolvedEvent,
        )
        e1 = EscalationTriggeredEvent.create("s1", "consensus_failed", "no consensus", "req-1")
        e2 = EscalationResolvedEvent.create("s1", "req-1", "approve", "admin")
        assert e1.request_id == "req-1"
        assert e2.decided_by == "admin"

    def test_message_sent_event(self):
        from iios.ai.collaboration.events.collaboration_events import MessageSentEvent
        e = MessageSentEvent.create("s1", "m1", "a1", "direct", False)
        assert not e.broadcast


class TestCollaborationEventBus:
    """T-EVT: CollaborationEventBus pub/sub."""

    def test_subscribe_and_publish(self):
        from iios.ai.collaboration.events.collaboration_event_bus import CollaborationEventBus
        from iios.ai.collaboration.events.collaboration_events import (
            CollaborationEventType,
            CollaborationStartedEvent,
        )
        bus    = CollaborationEventBus()
        received = []
        bus.subscribe(CollaborationEventType.COLLABORATION_STARTED, received.append)
        evt = CollaborationStartedEvent.create("s1", "topic", "debate")
        bus.publish(evt)
        assert len(received) == 1
        assert bus.published_count == 1

    def test_unsubscribe(self):
        from iios.ai.collaboration.events.collaboration_event_bus import CollaborationEventBus
        from iios.ai.collaboration.events.collaboration_events import (
            CollaborationEventType,
            CollaborationStartedEvent,
        )
        bus     = CollaborationEventBus()
        handler = []
        bus.subscribe(CollaborationEventType.COLLABORATION_STARTED, handler.append)
        bus.unsubscribe(CollaborationEventType.COLLABORATION_STARTED, handler.append)
        bus.publish(CollaborationStartedEvent.create("s1", "t", "debate"))
        assert len(handler) == 0

    def test_broken_handler_does_not_propagate(self):
        from iios.ai.collaboration.events.collaboration_event_bus import CollaborationEventBus
        from iios.ai.collaboration.events.collaboration_events import (
            CollaborationEventType,
            CollaborationStartedEvent,
        )
        bus = CollaborationEventBus()
        def bad(evt):
            raise RuntimeError("boom")
        bus.subscribe(CollaborationEventType.COLLABORATION_STARTED, bad)
        bus.publish(CollaborationStartedEvent.create("s1", "t", "debate"))  # must not raise

    def test_subscriber_count(self):
        from iios.ai.collaboration.events.collaboration_event_bus import CollaborationEventBus
        from iios.ai.collaboration.events.collaboration_events import CollaborationEventType
        bus = CollaborationEventBus()
        bus.subscribe(CollaborationEventType.DEBATE_STARTED, lambda e: None)
        assert bus.subscriber_count(CollaborationEventType.DEBATE_STARTED) == 1

    def test_clear(self):
        from iios.ai.collaboration.events.collaboration_event_bus import CollaborationEventBus
        from iios.ai.collaboration.events.collaboration_events import CollaborationEventType
        bus = CollaborationEventBus()
        bus.subscribe(CollaborationEventType.DEBATE_STARTED, lambda e: None)
        bus.clear()
        assert bus.subscriber_count(CollaborationEventType.DEBATE_STARTED) == 0


# ---------------------------------------------------------------------------
# T-MSG  Messaging layer
# ---------------------------------------------------------------------------

class TestAgentMessage:
    """T-MSG: AgentMessage creation and properties."""

    def test_create_direct(self):
        from iios.ai.collaboration.messaging.agent_message import (
            AgentMessage, MessageType, MessagePriority,
        )
        m = AgentMessage.create(
            sender_id    = "a1",
            session_id   = "s1",
            message_type = MessageType.DIRECT,
            content      = "hello",
            recipient_id = "a2",
        )
        assert m.sender_id == "a1"
        assert m.recipient_id == "a2"
        assert not m.is_broadcast

    def test_create_broadcast(self):
        from iios.ai.collaboration.messaging.agent_message import AgentMessage, MessageType
        m = AgentMessage.create(
            sender_id    = "a1",
            session_id   = "s1",
            message_type = MessageType.BROADCAST,
            content      = "hi all",
        )
        assert m.is_broadcast

    def test_meta_roundtrip(self):
        from iios.ai.collaboration.messaging.agent_message import AgentMessage, MessageType
        m = AgentMessage.create(
            sender_id="a1", session_id="s1",
            message_type=MessageType.NOTIFICATION, content="x",
            topic="market",
        )
        assert m.get_meta("topic") == "market"
        assert m.get_meta("missing", "default") == "default"


class TestMessageMetadata:
    """T-MSG: MessageMetadata TTL expiry."""

    def test_not_expired_when_no_ttl(self):
        from iios.ai.collaboration.messaging.message_metadata import MessageMetadata
        m = MessageMetadata.create("s1", ttl_s=None)
        assert not m.is_expired()

    def test_expired_when_ttl_exceeded(self):
        from iios.ai.collaboration.messaging.message_metadata import MessageMetadata
        m = MessageMetadata.create("s1", ttl_s=0.001)
        time.sleep(0.01)
        assert m.is_expired()


class TestMessageBus:
    """T-MSG: MessageBus send, history, count, clear."""

    def _msg(self, session_id: str = "s1"):
        from iios.ai.collaboration.messaging.agent_message import AgentMessage, MessageType
        return AgentMessage.create(
            sender_id="a1", session_id=session_id,
            message_type=MessageType.DIRECT, content="hello",
            recipient_id="a2",
        )

    def test_send_and_count(self):
        from iios.ai.collaboration.messaging.message_bus import MessageBus
        bus = MessageBus()
        bus.send(self._msg())
        assert bus.message_count("s1") == 1

    def test_history_filter(self):
        from iios.ai.collaboration.messaging.message_bus import MessageBus
        from iios.ai.collaboration.messaging.agent_message import AgentMessage, MessageType
        bus = MessageBus()
        bus.send(self._msg())
        m2 = AgentMessage.create(
            sender_id="a2", session_id="s1",
            message_type=MessageType.NOTIFICATION, content="y",
        )
        bus.send(m2)
        assert len(bus.get_history("s1", sender_id="a1")) == 1

    def test_clear_session(self):
        from iios.ai.collaboration.messaging.message_bus import MessageBus
        bus = MessageBus()
        bus.send(self._msg())
        bus.clear_session("s1")
        assert bus.message_count("s1") == 0


class TestMessageRouter:
    """T-MSG: MessageRouter dispatch."""

    def test_route_direct(self):
        from iios.ai.collaboration.messaging.message_bus import MessageBus
        from iios.ai.collaboration.messaging.message_envelope import MessageEnvelope
        from iios.ai.collaboration.messaging.message_metadata import MessageMetadata
        from iios.ai.collaboration.messaging.message_router import MessageRouter
        from iios.ai.collaboration.messaging.agent_message import AgentMessage, MessageType

        router   = MessageRouter()
        received = []
        router.register_handler("a2", received.append)

        msg  = AgentMessage.create(sender_id="a1", session_id="s1",
                                   message_type=MessageType.DIRECT,
                                   content="hello", recipient_id="a2")
        meta = MessageMetadata.create("s1")
        env  = MessageEnvelope.wrap(msg, meta).with_delivered()
        router.route(env)
        assert len(received) == 1

    def test_unregister(self):
        from iios.ai.collaboration.messaging.message_router import MessageRouter
        router = MessageRouter()
        h = lambda e: None
        router.register_handler("a1", h)
        router.unregister_handler("a1", h)
        assert router.handler_count("a1") == 0


# ---------------------------------------------------------------------------
# T-DEB  Debate layer
# ---------------------------------------------------------------------------

class TestDebatePosition:
    """T-DEB: DebatePosition factories and helpers."""

    def test_create(self):
        from iios.ai.collaboration.debate.debate_position import DebatePosition, PositionType
        p = DebatePosition.create(
            session_id="s1", agent_id="a1", round_number=1,
            position_type=PositionType.FOR, argument="good", confidence=0.9,
        )
        assert p.position_type == PositionType.FOR
        assert p.confidence == 0.9

    def test_confidence_clamped(self):
        from iios.ai.collaboration.debate.debate_position import DebatePosition, PositionType
        p = DebatePosition.create("s1", "a1", 1, PositionType.FOR, confidence=5.0)
        assert p.confidence == 1.0

    def test_is_decisive(self):
        from iios.ai.collaboration.debate.debate_position import PositionType
        assert PositionType.FOR.is_decisive()
        assert not PositionType.ABSTAIN.is_decisive()


class TestDebateSession:
    """T-DEB: DebateSession full life-cycle."""

    def _ds(self, session_id: str = "s1") -> "DebateSession":
        from iios.ai.collaboration.debate.debate_session import DebateSession
        ds = DebateSession(session_id, "Buy NIFTY?")
        ds.open()
        return ds

    def test_submit_and_close_round(self):
        from iios.ai.collaboration.debate.debate_position import PositionType
        ds  = self._ds()
        pos = ds.submit_position("a1", PositionType.FOR, "momentum")
        r   = ds.close_round()
        assert r.position_count() == 1

    def test_next_round_increments(self):
        ds = self._ds()
        ds.submit_position("a1", __import__("iios.ai.collaboration.debate.debate_position",
                                            fromlist=["PositionType"]).PositionType.FOR)
        ds.next_round()
        assert ds.current_round_number == 2

    def test_close_returns_result(self):
        from iios.ai.collaboration.debate.debate_position import PositionType
        ds = self._ds()
        ds.submit_position("a1", PositionType.FOR, "reason")
        result = ds.close()
        assert result.total_positions == 1
        assert ds.is_closed

    def test_submit_after_close_raises(self):
        from iios.ai.collaboration.debate.debate_position import PositionType
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIDebateAlreadyClosedError,
        )
        ds = self._ds()
        ds.submit_position("a1", PositionType.FOR)
        ds.close()
        with pytest.raises(AIDebateAlreadyClosedError):
            ds.submit_position("a1", PositionType.FOR)

    def test_double_close_idempotent(self):
        from iios.ai.collaboration.debate.debate_position import PositionType
        ds = self._ds()
        ds.submit_position("a1", PositionType.FOR)
        r1 = ds.close()
        r2 = ds.close()
        assert r1.result_id == r2.result_id


class TestDebateResult:
    """T-DEB: DebateResult.from_rounds dominant position detection."""

    def test_dominant_for(self):
        from iios.ai.collaboration.debate.debate_position import DebatePosition, PositionType
        from iios.ai.collaboration.debate.debate_round import DebateRound
        from iios.ai.collaboration.debate.debate_result import DebateResult
        positions = frozenset([
            DebatePosition.create("s1","a1",1,PositionType.FOR),
            DebatePosition.create("s1","a2",1,PositionType.FOR),
            DebatePosition.create("s1","a3",1,PositionType.AGAINST),
        ])
        round_ = DebateRound.close("s1", 1, "topic", positions, time.time())
        result = DebateResult.from_rounds("s1", [round_])
        assert result.dominant_position == PositionType.FOR

    def test_no_dominant_on_tie(self):
        from iios.ai.collaboration.debate.debate_position import DebatePosition, PositionType
        from iios.ai.collaboration.debate.debate_round import DebateRound
        from iios.ai.collaboration.debate.debate_result import DebateResult
        positions = frozenset([
            DebatePosition.create("s1","a1",1,PositionType.FOR),
            DebatePosition.create("s1","a2",1,PositionType.AGAINST),
        ])
        round_ = DebateRound.close("s1", 1, "topic", positions, time.time())
        result = DebateResult.from_rounds("s1", [round_])
        assert result.dominant_position is None


class TestDebateManager:
    """T-DEB: DebateManager CRUD."""

    def test_create_and_get(self):
        from iios.ai.collaboration.debate.debate_manager import DebateManager
        dm = DebateManager()
        ds = dm.create("s1", "topic")
        assert ds.is_open
        assert dm.get("s1") is ds

    def test_get_missing_raises(self):
        from iios.ai.collaboration.debate.debate_manager import DebateManager
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIDebateNotFoundError,
        )
        dm = DebateManager()
        with pytest.raises(AIDebateNotFoundError):
            dm.get("nonexistent")

    def test_remove(self):
        from iios.ai.collaboration.debate.debate_manager import DebateManager
        dm = DebateManager()
        dm.create("s1", "topic")
        dm.remove("s1")
        assert not dm.exists("s1")


# ---------------------------------------------------------------------------
# T-CNS  Consensus layer
# ---------------------------------------------------------------------------

def _make_positions(session_id: str = "s1"):
    from iios.ai.collaboration.debate.debate_position import DebatePosition, PositionType
    return [
        DebatePosition.create(session_id,"a1",0,PositionType.FOR,confidence=0.9),
        DebatePosition.create(session_id,"a2",0,PositionType.FOR,confidence=0.8),
        DebatePosition.create(session_id,"a3",0,PositionType.AGAINST,confidence=0.7),
    ]


class TestMajorityVoteStrategy:
    """T-CNS: MajorityVoteStrategy."""

    def test_majority_wins(self):
        from iios.ai.collaboration.consensus.consensus_strategy import MajorityVoteStrategy
        from iios.ai.collaboration.consensus.consensus_result import ConsensusOutcome
        strat  = MajorityVoteStrategy()
        result = strat.calculate("s1", _make_positions(), {})
        assert result.outcome == ConsensusOutcome.MAJORITY_VOTE
        assert result.winning_position == "for"

    def test_no_decisive_fails(self):
        from iios.ai.collaboration.debate.debate_position import DebatePosition, PositionType
        from iios.ai.collaboration.consensus.consensus_strategy import MajorityVoteStrategy
        from iios.ai.collaboration.consensus.consensus_result import ConsensusOutcome
        pos = [DebatePosition.create("s1","a1",0,PositionType.ABSTAIN)]
        r   = MajorityVoteStrategy().calculate("s1", pos, {})
        assert r.outcome == ConsensusOutcome.INSUFFICIENT_VOTES


class TestWeightedVoteStrategy:
    """T-CNS: WeightedVoteStrategy."""

    def test_weighted_wins(self):
        from iios.ai.collaboration.consensus.consensus_strategy import WeightedVoteStrategy
        result = WeightedVoteStrategy().calculate(
            "s1", _make_positions(), {"a1": 2.0, "a2": 2.0, "a3": 1.0}
        )
        assert result.winning_position == "for"


class TestUnanimousStrategy:
    """T-CNS: UnanimousStrategy."""

    def test_unanimous_success(self):
        from iios.ai.collaboration.debate.debate_position import DebatePosition, PositionType
        from iios.ai.collaboration.consensus.consensus_strategy import UnanimousStrategy
        from iios.ai.collaboration.consensus.consensus_result import ConsensusOutcome
        pos = [
            DebatePosition.create("s1","a1",0,PositionType.FOR),
            DebatePosition.create("s1","a2",0,PositionType.FOR),
        ]
        r = UnanimousStrategy().calculate("s1", pos, {})
        assert r.outcome == ConsensusOutcome.REACHED

    def test_unanimous_failure(self):
        from iios.ai.collaboration.consensus.consensus_strategy import UnanimousStrategy
        from iios.ai.collaboration.consensus.consensus_result import ConsensusOutcome
        r = UnanimousStrategy().calculate("s1", _make_positions(), {})
        assert r.outcome == ConsensusOutcome.FAILED


class TestConfidenceThresholdStrategy:
    """T-CNS: ConfidenceThresholdStrategy."""

    def test_above_threshold(self):
        from iios.ai.collaboration.consensus.consensus_strategy import ConfidenceThresholdStrategy
        from iios.ai.collaboration.consensus.consensus_result import ConsensusOutcome
        r = ConfidenceThresholdStrategy(0.7).calculate("s1", _make_positions(), {})
        assert r.outcome == ConsensusOutcome.MAJORITY_VOTE

    def test_below_threshold(self):
        from iios.ai.collaboration.debate.debate_position import DebatePosition, PositionType
        from iios.ai.collaboration.consensus.consensus_strategy import ConfidenceThresholdStrategy
        from iios.ai.collaboration.consensus.consensus_result import ConsensusOutcome
        pos = [
            DebatePosition.create("s1","a1",0,PositionType.FOR,confidence=0.3),
            DebatePosition.create("s1","a2",0,PositionType.FOR,confidence=0.3),
            DebatePosition.create("s1","a3",0,PositionType.AGAINST,confidence=0.9),
        ]
        r = ConfidenceThresholdStrategy(0.7).calculate("s1", pos, {})
        assert r.outcome == ConsensusOutcome.THRESHOLD_NOT_MET


class TestConsensusManager:
    """T-CNS: ConsensusManager strategy dispatch."""

    def test_unknown_strategy_raises(self):
        from iios.ai.collaboration.consensus.consensus_manager import ConsensusManager
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIConsensusFailedError,
        )
        with pytest.raises(AIConsensusFailedError):
            ConsensusManager().calculate("s1", [], "nonexistent")

    def test_register_custom(self):
        from iios.ai.collaboration.consensus.consensus_manager import ConsensusManager
        from iios.ai.collaboration.consensus.consensus_strategy import MajorityVoteStrategy

        class MyStrategy(MajorityVoteStrategy):
            name = "custom_majority"

        mgr = ConsensusManager()
        mgr.register_strategy(MyStrategy())
        assert "custom_majority" in mgr.list_strategies()


# ---------------------------------------------------------------------------
# T-ESC  Escalation layer
# ---------------------------------------------------------------------------

class TestEscalationRequest:
    """T-ESC: EscalationRequest life-cycle."""

    def test_create(self):
        from iios.ai.collaboration.escalation.escalation_request import EscalationRequest
        from iios.ai.collaboration.escalation.escalation_rule import EscalationTrigger
        req = EscalationRequest.create("s1", EscalationTrigger.MANUAL, "no consensus", "agent-1")
        assert not req.is_terminal()

    def test_update_status(self):
        from iios.ai.collaboration.escalation.escalation_request import (
            EscalationRequest,
            EscalationStatus,
        )
        from iios.ai.collaboration.escalation.escalation_rule import EscalationTrigger
        req = EscalationRequest.create("s1", EscalationTrigger.MANUAL, "r", "a1")
        req.update_status(EscalationStatus.RESOLVED, "approved")
        assert req.is_terminal()


class TestEscalationDecision:
    """T-ESC: EscalationDecision creation."""

    def test_create(self):
        from iios.ai.collaboration.escalation.escalation_decision import (
            EscalationDecision,
            EscalationAction,
        )
        d = EscalationDecision.create(
            request_id = "r1",
            session_id = "s1",
            action     = EscalationAction.APPROVE,
            decided_by = "admin",
            rationale  = "OK",
        )
        assert d.action == EscalationAction.APPROVE
        assert d.get_data("missing") is None


class TestEscalationManager:
    """T-ESC: EscalationManager full life-cycle."""

    def test_create_and_resolve(self):
        from iios.ai.collaboration.escalation.escalation_manager import EscalationManager
        from iios.ai.collaboration.escalation.escalation_rule import EscalationTrigger
        from iios.ai.collaboration.escalation.escalation_decision import EscalationAction
        mgr = EscalationManager()
        req = mgr.create("s1", EscalationTrigger.MANUAL, "reason", "agent")
        dec = mgr.resolve(req.request_id, EscalationAction.APPROVE, "admin")
        assert dec.action == EscalationAction.APPROVE
        assert req.is_terminal()

    def test_resolve_already_terminal_raises(self):
        from iios.ai.collaboration.escalation.escalation_manager import EscalationManager
        from iios.ai.collaboration.escalation.escalation_rule import EscalationTrigger
        from iios.ai.collaboration.escalation.escalation_decision import EscalationAction
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIEscalationPolicyViolationError,
        )
        mgr = EscalationManager()
        req = mgr.create("s1", EscalationTrigger.MANUAL, "r", "a")
        mgr.resolve(req.request_id, EscalationAction.APPROVE, "admin")
        with pytest.raises(AIEscalationPolicyViolationError):
            mgr.resolve(req.request_id, EscalationAction.APPROVE, "admin")

    def test_get_missing_raises(self):
        from iios.ai.collaboration.escalation.escalation_manager import EscalationManager
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AIEscalationNotFoundError,
        )
        with pytest.raises(AIEscalationNotFoundError):
            EscalationManager().get_request("nope")


# ---------------------------------------------------------------------------
# T-POL  Policies
# ---------------------------------------------------------------------------

class TestPolicies:
    """T-POL: Default policy implementations."""

    def _ctx(self, active: int = 2):
        from iios.ai.collaboration.core.collaboration_context import CollaborationContext
        from iios.ai.collaboration.core.collaboration_metadata import (
            CollaborationMetadata,
            CollaborationStatus,
            CollaborationType,
        )
        from iios.ai.collaboration.core.participant import Participant, ParticipantStatus
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        metadata = CollaborationMetadata.create("test", CollaborationType.DEBATE, "sys")
        participants = frozenset(
            Participant(
                participant_id=f"p{i}", agent_id=f"a{i}", agent_name=f"A{i}",
                agent_type="Analyst", role=CollaborationRole.ANALYST,
                status=ParticipantStatus.ACTIVE, joined_at=time.time(), weight=1.0,
            )
            for i in range(active)
        )
        return CollaborationContext.create(
            metadata      = metadata,
            status        = CollaborationStatus.OPEN,
            participants  = participants,
            current_round = 1,
            total_rounds  = 3,
        )

    def test_debate_policy_enough_participants(self):
        from iios.ai.collaboration.policy.debate_policy import DefaultDebatePolicy
        DefaultDebatePolicy().validate_start(self._ctx(2))  # should not raise

    def test_debate_policy_too_few_participants(self):
        from iios.ai.collaboration.policy.debate_policy import DefaultDebatePolicy
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationPolicyViolationError,
        )
        with pytest.raises(AICollaborationPolicyViolationError):
            DefaultDebatePolicy().validate_start(self._ctx(0))

    def test_voting_policy_invalid_confidence(self):
        from iios.ai.collaboration.policy.voting_policy import DefaultVotingPolicy
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationPolicyViolationError,
        )
        with pytest.raises(AICollaborationPolicyViolationError):
            DefaultVotingPolicy().validate_vote(self._ctx(), "a0", 2.0)

    def test_participation_policy_duplicate(self):
        from iios.ai.collaboration.policy.participation_policy import DefaultParticipationPolicy
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationPolicyViolationError,
        )
        with pytest.raises(AICollaborationPolicyViolationError):
            DefaultParticipationPolicy().validate_invite(
                self._ctx(2), "a0", "Analyst", CollaborationRole.ANALYST, 1.0
            )

    def test_escalation_policy_auto_triggers(self):
        from iios.ai.collaboration.policy.escalation_policy import DefaultEscalationPolicy
        from iios.ai.collaboration.escalation.escalation_rule import EscalationTrigger
        pol = DefaultEscalationPolicy()
        assert pol.should_auto_escalate(self._ctx(), EscalationTrigger.CONSENSUS_FAILED)
        assert not pol.should_auto_escalate(self._ctx(), EscalationTrigger.MANUAL)

    def test_timeout_policy_not_expired(self):
        from iios.ai.collaboration.policy.timeout_policy import DefaultTimeoutPolicy
        pol = DefaultTimeoutPolicy()
        assert not pol.is_session_timed_out(self._ctx(), time.time())

    def test_timeout_policy_expired(self):
        from iios.ai.collaboration.policy.timeout_policy import DefaultTimeoutPolicy
        pol = DefaultTimeoutPolicy()
        ancient = time.time() - 7200
        assert pol.is_session_timed_out(self._ctx(), ancient)


# ---------------------------------------------------------------------------
# T-SNAP  Snapshot layer
# ---------------------------------------------------------------------------

class TestSnapshots:
    """T-SNAP: CollaborationSessionSnapshot and CollaborationFrameworkSnapshot."""

    def test_session_snapshot(self):
        from iios.ai.collaboration.snapshot.collaboration_snapshot import (
            CollaborationSessionSnapshot,
        )
        from iios.ai.collaboration.core.collaboration_metadata import (
            CollaborationStatus,
            CollaborationType,
        )
        s = CollaborationSessionSnapshot.capture(
            session_id           = "s1",
            topic                = "topic",
            collaboration_type   = CollaborationType.DEBATE,
            status               = CollaborationStatus.OPEN,
            participant_count    = 3,
            current_round        = 1,
            total_rounds         = 3,
            message_count        = 5,
        )
        assert s.is_active()
        assert not s.is_terminal()

    def test_framework_snapshot(self):
        from iios.ai.collaboration.snapshot.collaboration_snapshot import (
            CollaborationFrameworkSnapshot,
        )
        snap = CollaborationFrameworkSnapshot.capture(
            system_id        = "iios:ai:collaboration",
            version          = "1.0.0",
            is_running       = True,
            sessions         = frozenset(),
            events_published = 42,
        )
        assert snap.is_running
        assert snap.events_published == 42


# ---------------------------------------------------------------------------
# T-SES  CollaborationSession
# ---------------------------------------------------------------------------

def _build_session():
    """Return a ready-to-use CollaborationSession."""
    from iios.ai.collaboration.core.collaboration_metadata import (
        CollaborationMetadata,
        CollaborationType,
    )
    from iios.ai.collaboration.events.collaboration_event_bus import CollaborationEventBus
    from iios.ai.collaboration.debate.debate_manager import DebateManager
    from iios.ai.collaboration.consensus.consensus_manager import ConsensusManager
    from iios.ai.collaboration.escalation.escalation_manager import EscalationManager
    from iios.ai.collaboration.messaging.message_bus import MessageBus
    from iios.ai.collaboration.session.collaboration_session import CollaborationSession

    metadata = CollaborationMetadata.create("Buy NIFTY?", CollaborationType.DEBATE, "sys")
    session  = CollaborationSession(
        metadata           = metadata,
        event_bus          = CollaborationEventBus(),
        debate_manager     = DebateManager(),
        consensus_manager  = ConsensusManager(),
        escalation_manager = EscalationManager(),
        message_bus        = MessageBus(),
    )
    session.open()
    return session


class TestCollaborationSession:
    """T-SES: CollaborationSession integration."""

    def test_invite_agent(self):
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        s = _build_session()
        p = s.invite_agent("a1", "Alice", "Analyst", CollaborationRole.ANALYST)
        assert p.agent_id == "a1"
        assert s.participant_count == 1

    def test_invite_duplicate_raises(self):
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationParticipantAlreadyExistsError,
        )
        s = _build_session()
        s.invite_agent("a1", "Alice", "Analyst", CollaborationRole.ANALYST)
        with pytest.raises(AICollaborationParticipantAlreadyExistsError):
            s.invite_agent("a1", "Alice2", "Analyst", CollaborationRole.ANALYST)

    def test_send_message(self):
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        s = _build_session()
        s.invite_agent("a1", "Alice", "Analyst", CollaborationRole.ANALYST)
        s.invite_agent("a2", "Bob",   "Risk",    CollaborationRole.CHALLENGER)
        msg = s.send_message("a1", "a2", "hello")
        assert msg.content == "hello"
        assert len(s.get_messages()) >= 1

    def test_full_debate_and_vote(self):
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        from iios.ai.collaboration.debate.debate_position import PositionType
        s = _build_session()
        s.invite_agent("a1", "Alice", "Analyst",    CollaborationRole.ANALYST)
        s.invite_agent("a2", "Bob",   "Challenger", CollaborationRole.CHALLENGER)
        s.start_debate()
        s.submit_argument("a1", PositionType.FOR, "bullish momentum")
        s.submit_argument("a2", PositionType.FOR, "confirming signal")
        s.close_debate()
        s.vote("a1", PositionType.FOR, 0.9)
        s.vote("a2", PositionType.FOR, 0.8)
        result = s.calculate_consensus()
        assert result.winning_position == "for"

    def test_escalate(self):
        from iios.ai.collaboration.escalation.escalation_rule import EscalationTrigger
        s = _build_session()
        req = s.escalate(EscalationTrigger.MANUAL, "deadlock")
        assert req.session_id == s.session_id

    def test_close_returns_result(self):
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        from iios.ai.collaboration.debate.debate_position import PositionType
        s = _build_session()
        s.invite_agent("a1", "Alice", "Analyst", CollaborationRole.ANALYST)
        s.start_debate()
        s.submit_argument("a1", PositionType.FOR)
        s.close_debate()
        s.vote("a1", PositionType.FOR)
        s.calculate_consensus()
        final = s.close()
        assert final is not None

    def test_context(self):
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        s = _build_session()
        s.invite_agent("a1", "A", "T", CollaborationRole.ANALYST)
        ctx = s.context()
        assert ctx.participant_count == 1


# ---------------------------------------------------------------------------
# T-MGR  CollaborationManager
# ---------------------------------------------------------------------------

class TestCollaborationManager:
    """T-MGR: CollaborationManager CRUD and snapshots."""

    def _mgr(self):
        from iios.ai.collaboration.events.collaboration_event_bus import CollaborationEventBus
        from iios.ai.collaboration.debate.debate_manager import DebateManager
        from iios.ai.collaboration.consensus.consensus_manager import ConsensusManager
        from iios.ai.collaboration.escalation.escalation_manager import EscalationManager
        from iios.ai.collaboration.messaging.message_bus import MessageBus
        from iios.ai.collaboration.manager.collaboration_manager import CollaborationManager
        return CollaborationManager(
            event_bus          = CollaborationEventBus(),
            debate_manager     = DebateManager(),
            consensus_manager  = ConsensusManager(),
            escalation_manager = EscalationManager(),
            message_bus        = MessageBus(),
        )

    def test_create_and_get(self):
        mgr = self._mgr()
        s   = mgr.create("topic")
        assert mgr.get(s.session_id) is s

    def test_get_missing_raises(self):
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationSessionNotFoundError,
        )
        with pytest.raises(AICollaborationSessionNotFoundError):
            self._mgr().get("nope")

    def test_session_count(self):
        mgr = self._mgr()
        mgr.create("t1")
        mgr.create("t2")
        assert mgr.session_count() == 2

    def test_snapshot_session(self):
        mgr  = self._mgr()
        s    = mgr.create("snap topic")
        snap = mgr.snapshot_session(s.session_id)
        assert snap.session_id == s.session_id

    def test_framework_snapshot(self):
        mgr  = self._mgr()
        mgr.create("t1")
        fsnap = mgr.framework_snapshot("iios:test", "1.0.0", True)
        assert fsnap.total_sessions == 1
        assert fsnap.is_running


# ---------------------------------------------------------------------------
# T-GW  CollaborationGateway
# ---------------------------------------------------------------------------

class TestCollaborationGateway:
    """T-GW: M6 gateway life-cycle and API."""

    def _gw(self):
        from iios.ai.collaboration.gateway.collaboration_gateway import CollaborationGateway
        gw = CollaborationGateway()
        gw.start()
        return gw

    def test_start_stop(self):
        gw = self._gw()
        assert gw.is_ai_running
        gw.stop()
        assert not gw.is_ai_running

    def test_health_keys(self):
        gw = self._gw()
        h  = gw.health()
        assert "is_running" in h
        assert h["is_running"] is True
        gw.stop()

    def test_create_collaboration_returns_session_id(self):
        gw  = self._gw()
        sid = gw.create_collaboration("Buy NIFTY?")
        uuid.UUID(sid)  # must be a valid UUID
        gw.stop()

    def test_invite_agent(self):
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        gw  = self._gw()
        sid = gw.create_collaboration("topic")
        p   = gw.invite_agent(sid, "a1", "Alice", "Analyst", CollaborationRole.ANALYST)
        assert p.agent_id == "a1"
        gw.stop()

    def test_full_cycle_via_gateway(self):
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        from iios.ai.collaboration.debate.debate_position import PositionType
        gw  = self._gw()
        sid = gw.create_collaboration("NIFTY direction")
        gw.invite_agent(sid, "bull", "Bull", "MarketAnalystAgent", CollaborationRole.ANALYST)
        gw.invite_agent(sid, "bear", "Bear", "RiskAnalystAgent",   CollaborationRole.CHALLENGER)
        gw.start_debate(sid)
        gw.submit_argument(sid, "bull", PositionType.FOR, "RSI oversold")
        gw.submit_argument(sid, "bear", PositionType.FOR, "momentum confirms")
        gw.close_debate(sid)
        gw.vote(sid, "bull", PositionType.FOR, 0.85)
        gw.vote(sid, "bear", PositionType.FOR, 0.75)
        cns = gw.calculate_consensus(sid)
        assert cns.winning_position == "for"
        final = gw.close_session(sid)
        assert final is not None
        gw.stop()

    def test_snapshot(self):
        gw   = self._gw()
        gw.create_collaboration("t")
        snap = gw.snapshot()
        assert snap.total_sessions == 1
        gw.stop()

    def test_list_sessions(self):
        gw = self._gw()
        gw.create_collaboration("t1")
        gw.create_collaboration("t2")
        snaps = gw.list_sessions()
        assert len(snaps) == 2
        gw.stop()

    def test_escalate_via_gateway(self):
        from iios.ai.collaboration.escalation.escalation_rule import EscalationTrigger
        gw  = self._gw()
        sid = gw.create_collaboration("risk session")
        req = gw.escalate(sid, EscalationTrigger.MANUAL, "manual override")
        assert req.session_id == sid
        gw.stop()

    def test_send_message_via_gateway(self):
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        from iios.ai.collaboration.messaging.agent_message import MessageType
        gw  = self._gw()
        sid = gw.create_collaboration("msg session")
        gw.invite_agent(sid, "a1", "Alice", "Analyst", CollaborationRole.ANALYST)
        gw.invite_agent(sid, "a2", "Bob",   "Risk",    CollaborationRole.CHALLENGER)
        msg = gw.send_message(sid, "a1", "a2", "hello", MessageType.DIRECT)
        assert msg.content == "hello"
        gw.stop()

    def test_call_before_start_raises(self):
        from iios.ai.collaboration.gateway.collaboration_gateway import CollaborationGateway
        from iios.ai.collaboration.exceptions.collaboration_exceptions import (
            AICollaborationException,
        )
        gw = CollaborationGateway()
        with pytest.raises(AICollaborationException):
            gw.create_collaboration("topic")

    def test_status(self):
        gw = self._gw()
        st = gw.status()
        assert "total_sessions" in st
        gw.stop()


# ---------------------------------------------------------------------------
# T-INT  End-to-end integration
# ---------------------------------------------------------------------------

class TestEndToEndIntegration:
    """T-INT: Full multi-agent debate → consensus → escalation pipeline."""

    def test_consensus_reached_pipeline(self):
        """5 agents debate and reach consensus via weighted vote."""
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        from iios.ai.collaboration.debate.debate_position import PositionType
        from iios.ai.collaboration.gateway.collaboration_gateway import CollaborationGateway

        gw  = CollaborationGateway()
        gw.start()
        sid = gw.create_collaboration("NIFTY direction 15m", created_by="orchestrator")

        agents = [
            ("ma",  "MarketAnalyst",  "MarketAnalystAgent",  CollaborationRole.ANALYST),
            ("ra",  "RiskAnalyst",    "RiskAnalystAgent",    CollaborationRole.CHALLENGER),
            ("mod", "Moderator",      "AuditAgent",          CollaborationRole.MODERATOR),
            ("v1",  "Voter1",         "MarketAnalystAgent",  CollaborationRole.VOTER),
            ("v2",  "Voter2",         "RiskAnalystAgent",    CollaborationRole.VOTER),
        ]
        for aid, name, atype, role in agents:
            gw.invite_agent(sid, aid, name, atype, role)

        gw.start_debate(sid)
        gw.submit_argument(sid, "ma",  PositionType.FOR,     "Momentum breakout")
        gw.submit_argument(sid, "ra",  PositionType.FOR,     "Risk acceptable")
        gw.submit_argument(sid, "mod", PositionType.NEUTRAL, "Monitoring")
        gw.next_round(sid)
        gw.submit_argument(sid, "ma",  PositionType.FOR,     "Breakout confirmed")
        gw.submit_argument(sid, "ra",  PositionType.AGAINST, "Volume spike concern")
        gw.close_debate(sid)

        # All voters + analysts vote FOR
        for aid in ["ma", "v1", "v2"]:
            gw.vote(sid, aid, PositionType.FOR, 0.8)
        gw.vote(sid, "ra", PositionType.AGAINST, 0.6)

        cns = gw.calculate_consensus(sid, "majority")
        assert cns.winning_position == "for"
        assert cns.is_decided()

        final = gw.close_session(sid)
        assert final is not None
        gw.stop()

    def test_escalation_on_consensus_failure(self):
        """Simulate a tie → escalate."""
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        from iios.ai.collaboration.debate.debate_position import PositionType
        from iios.ai.collaboration.escalation.escalation_rule import EscalationTrigger
        from iios.ai.collaboration.gateway.collaboration_gateway import CollaborationGateway

        gw  = CollaborationGateway()
        gw.start()
        sid = gw.create_collaboration("Borderline trade")
        gw.invite_agent(sid, "bull", "Bull", "MarketAnalystAgent", CollaborationRole.VOTER)
        gw.invite_agent(sid, "bear", "Bear", "RiskAnalystAgent",   CollaborationRole.VOTER)

        gw.start_debate(sid)
        gw.submit_argument(sid, "bull", PositionType.FOR,     "Good entry")
        gw.submit_argument(sid, "bear", PositionType.AGAINST, "Too risky")
        gw.close_debate(sid)

        gw.vote(sid, "bull", PositionType.FOR,     1.0)
        gw.vote(sid, "bear", PositionType.AGAINST, 1.0)

        cns = gw.calculate_consensus(sid, "unanimous")
        assert not cns.is_decided()

        req = gw.escalate(sid, EscalationTrigger.CONSENSUS_FAILED, "Tie vote")
        assert req.trigger == EscalationTrigger.CONSENSUS_FAILED
        gw.stop()

    def test_event_bus_captures_full_cycle(self):
        """All expected events are published during a full cycle."""
        from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
        from iios.ai.collaboration.debate.debate_position import PositionType
        from iios.ai.collaboration.events.collaboration_events import CollaborationEventType
        from iios.ai.collaboration.gateway.collaboration_gateway import CollaborationGateway

        gw  = CollaborationGateway()
        gw.start()
        bus    = gw._container.event_bus
        events = []
        for et in CollaborationEventType:
            bus.subscribe(et, events.append)

        sid = gw.create_collaboration("event test")
        gw.invite_agent(sid, "a1", "A", "T", CollaborationRole.ANALYST)
        gw.start_debate(sid)
        gw.submit_argument(sid, "a1", PositionType.FOR)
        gw.close_debate(sid)
        gw.vote(sid, "a1", PositionType.FOR)
        gw.calculate_consensus(sid)
        gw.close_session(sid)

        event_types = {e.event_type for e in events}
        assert CollaborationEventType.COLLABORATION_STARTED   in event_types
        assert CollaborationEventType.AGENT_INVITED            in event_types
        assert CollaborationEventType.DEBATE_STARTED           in event_types
        assert CollaborationEventType.AGENT_RESPONDED          in event_types
        assert CollaborationEventType.VOTE_SUBMITTED           in event_types
        assert CollaborationEventType.COLLABORATION_CLOSED     in event_types
        gw.stop()
