"""
collaboration_container.py -- iios.ai.collaboration.container
===============================================================
:class:`CollaborationContainer` — dependency-injection root for A6.

Instantiates all shared singletons (event bus, debate manager, etc.) and
exposes them through :class:`CollaborationManager`.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

from ..consensus.consensus_manager    import ConsensusManager
from ..debate.debate_manager          import DebateManager
from ..escalation.escalation_manager  import EscalationManager
from ..events.collaboration_event_bus import CollaborationEventBus
from ..manager.collaboration_manager  import CollaborationManager
from ..messaging.message_bus          import MessageBus
from ..messaging.message_router       import MessageRouter


class CollaborationContainer:
    """
    Dependency-injection root for the A6 Multi-Agent Collaboration Framework.

    Create exactly *one* instance per process (held by
    :class:`CollaborationGateway`).
    """

    def __init__(self) -> None:
        # Shared infrastructure
        self.event_bus:          CollaborationEventBus = CollaborationEventBus()
        self.message_bus:        MessageBus            = MessageBus()
        self.message_router:     MessageRouter         = MessageRouter()

        # Domain managers
        self.debate_manager:     DebateManager         = DebateManager()
        self.consensus_manager:  ConsensusManager      = ConsensusManager()
        self.escalation_manager: EscalationManager     = EscalationManager()

        # Top-level session manager
        self.collaboration_manager: CollaborationManager = CollaborationManager(
            event_bus          = self.event_bus,
            debate_manager     = self.debate_manager,
            consensus_manager  = self.consensus_manager,
            escalation_manager = self.escalation_manager,
            message_bus        = self.message_bus,
        )
