"""
collaboration_gateway.py -- iios.ai.collaboration.gateway
===========================================================
:class:`CollaborationGateway` — M6 single public entry-point for A6.

Inherits :class:`AILifecycleAwareMixin` (A1) so the gateway participates in
the standard IIOS start/stop/health life-cycle.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Optional

from ..container.collaboration_container import CollaborationContainer
from ..core.agent_role_assignment         import CollaborationRole
from ..core.collaboration_metadata       import CollaborationType
from ..core.collaboration_result         import CollaborationResult
from ..core.participant                  import Participant
from ..debate.debate_position            import DebatePosition, PositionType
from ..debate.debate_result              import DebateResult
from ..escalation.escalation_request     import EscalationRequest
from ..escalation.escalation_rule        import EscalationTrigger
from ..exceptions.collaboration_exceptions import (
    AICollaborationSessionNotFoundError,
)
from ..lifecycle                         import AILifecycleAwareMixin
from ..messaging.agent_message           import AgentMessage, MessageType
from ..consensus.consensus_result        import ConsensusResult
from ..snapshot.collaboration_snapshot   import (
    CollaborationFrameworkSnapshot,
    CollaborationSessionSnapshot,
)

SYSTEM_ID = "iios:ai:collaboration:gateway"
VERSION   = "1.0.0"


class CollaborationGateway(AILifecycleAwareMixin):
    """
    Single public entry-point for the A6 Multi-Agent Collaboration Framework.

    Usage::

        gw = CollaborationGateway()
        gw.start()
        sid = gw.create_collaboration("Should we BUY NIFTY?")
        gw.invite_agent(sid, "analyst-1", "Analyst", "MarketAnalystAgent", CollaborationRole.ANALYST)
        gw.start_debate(sid)
        gw.submit_argument(sid, "analyst-1", PositionType.FOR, "Strong momentum.")
        gw.close_debate(sid)
        gw.vote(sid, "analyst-1", PositionType.FOR)
        result = gw.calculate_consensus(sid)
        final  = gw.close_session(sid)
        gw.stop()
    """

    SYSTEM_ID: str = SYSTEM_ID
    VERSION:   str = VERSION

    def __init__(self) -> None:
        self._container: Optional[CollaborationContainer] = None

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    def _on_start(self) -> None:
        """Initialise the DI container when the gateway starts."""
        self._container = CollaborationContainer()

    def _on_stop(self) -> None:
        """Release the DI container when the gateway stops."""
        self._container = None

    def health(self) -> Dict[str, Any]:
        mgr = self._container.collaboration_manager if self._container else None
        return {
            "system_id":        SYSTEM_ID,
            "version":          VERSION,
            "status":           self.lifecycle_state.value,
            "is_running":       self.is_ai_running,
            "active_sessions":  mgr.session_count() if mgr else 0,
            "events_published": (
                self._container.event_bus.published_count
                if self._container else 0
            ),
        }

    def snapshot(self) -> CollaborationFrameworkSnapshot:
        self._require_running()
        return self._container.collaboration_manager.framework_snapshot(
            system_id  = SYSTEM_ID,
            version    = VERSION,
            is_running = self.is_ai_running,
        )

    def status(self) -> Dict[str, Any]:
        snap = self.snapshot()
        return {
            "system_id":      snap.system_id,
            "version":        snap.version,
            "total_sessions": snap.total_sessions,
            "active":         snap.active_sessions,
            "closed":         snap.closed_sessions,
            "captured_at":    snap.captured_at,
        }

    # ── Session management ────────────────────────────────────────────────────

    def create_collaboration(
        self,
        topic:              str,
        collaboration_type: CollaborationType = CollaborationType.DEBATE,
        created_by:         str               = "system",
        **kwargs,
    ) -> str:
        """Create a new session. Returns the *session_id*."""
        self._require_running()
        session = self._container.collaboration_manager.create(
            topic              = topic,
            collaboration_type = collaboration_type,
            created_by         = created_by,
            **kwargs,
        )
        return session.session_id

    def close_session(self, session_id: str) -> CollaborationResult:
        self._require_running()
        session = self._container.collaboration_manager.get(session_id)
        return session.close()

    # ── Participants ──────────────────────────────────────────────────────────

    def invite_agent(
        self,
        session_id: str,
        agent_id:   str,
        agent_name: str,
        agent_type: str,
        role:       CollaborationRole,
        weight:     float = 1.0,
    ) -> Participant:
        self._require_running()
        session = self._container.collaboration_manager.get(session_id)
        return session.invite_agent(
            agent_id   = agent_id,
            agent_name = agent_name,
            agent_type = agent_type,
            role       = role,
            weight     = weight,
        )

    # ── Debate ────────────────────────────────────────────────────────────────

    def start_debate(self, session_id: str) -> None:
        self._require_running()
        self._container.collaboration_manager.get(session_id).start_debate()

    def submit_argument(
        self,
        session_id:    str,
        agent_id:      str,
        position_type: PositionType,
        argument:      str                = "",
        evidence:      FrozenSet[str]     = frozenset(),
        confidence:    float              = 1.0,
        responds_to:   Optional[str]      = None,
    ) -> DebatePosition:
        self._require_running()
        return self._container.collaboration_manager.get(session_id).submit_argument(
            agent_id      = agent_id,
            position_type = position_type,
            argument      = argument,
            evidence      = evidence,
            confidence    = confidence,
            responds_to   = responds_to,
        )

    def next_round(self, session_id: str) -> None:
        self._require_running()
        self._container.collaboration_manager.get(session_id).next_round()

    def close_debate(self, session_id: str) -> DebateResult:
        self._require_running()
        return self._container.collaboration_manager.get(session_id).close_debate()

    # ── Voting and consensus ──────────────────────────────────────────────────

    def vote(
        self,
        session_id:    str,
        agent_id:      str,
        position_type: PositionType,
        confidence:    float = 1.0,
    ) -> DebatePosition:
        self._require_running()
        return self._container.collaboration_manager.get(session_id).vote(
            agent_id      = agent_id,
            position_type = position_type,
            confidence    = confidence,
        )

    def calculate_consensus(
        self,
        session_id:    str,
        strategy:      str = "majority",
    ) -> ConsensusResult:
        self._require_running()
        return self._container.collaboration_manager.get(session_id).calculate_consensus(
            strategy_name = strategy,
        )

    # ── Messaging ─────────────────────────────────────────────────────────────

    def send_message(
        self,
        session_id:   str,
        sender_id:    str,
        recipient_id: str,
        content:      Any,
        message_type: MessageType = MessageType.DIRECT,
    ) -> AgentMessage:
        self._require_running()
        return self._container.collaboration_manager.get(session_id).send_message(
            sender_id    = sender_id,
            recipient_id = recipient_id,
            content      = content,
            message_type = message_type,
        )

    def broadcast_message(
        self,
        session_id: str,
        sender_id:  str,
        content:    Any,
    ) -> AgentMessage:
        self._require_running()
        return self._container.collaboration_manager.get(session_id).broadcast_message(
            sender_id = sender_id,
            content   = content,
        )

    # ── Escalation ────────────────────────────────────────────────────────────

    def escalate(
        self,
        session_id:   str,
        trigger:      EscalationTrigger,
        reason:       str,
        requested_by: str = "system",
    ) -> EscalationRequest:
        self._require_running()
        return self._container.collaboration_manager.get(session_id).escalate(
            trigger      = trigger,
            reason       = reason,
            requested_by = requested_by,
        )

    # ── Snapshot helpers ──────────────────────────────────────────────────────

    def get_session_snapshot(self, session_id: str) -> CollaborationSessionSnapshot:
        self._require_running()
        return self._container.collaboration_manager.snapshot_session(session_id)

    def list_sessions(self) -> List[CollaborationSessionSnapshot]:
        self._require_running()
        snaps = []
        for s in self._container.collaboration_manager.list_sessions():
            snaps.append(self._container.collaboration_manager._session_snapshot(s))
        return snaps

    # ── Internal ──────────────────────────────────────────────────────────────

    def _require_running(self) -> None:
        if not self.is_ai_running or self._container is None:
            from ..exceptions.collaboration_exceptions import AICollaborationException
            raise AICollaborationException(
                "CollaborationGateway is not running. Call start() first."
            )
