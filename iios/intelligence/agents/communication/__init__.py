"""iios/intelligence/agents/communication/__init__.py"""
from .agent_message import AgentMessage, MessageEnvelope
from .agent_mailbox import AgentMailbox
from .agent_channel import AgentChannel, ChannelRegistry, get_channel_registry, reset_channel_registry
from .agent_router  import AgentRouter, get_agent_router, reset_agent_router
from .agent_event   import AgentEvent, AgentEventBus, get_agent_event_bus, reset_agent_event_bus

__all__ = [
    "AgentMessage", "MessageEnvelope",
    "AgentMailbox",
    "AgentChannel", "ChannelRegistry", "get_channel_registry", "reset_channel_registry",
    "AgentRouter",  "get_agent_router",  "reset_agent_router",
    "AgentEvent",   "AgentEventBus",     "get_agent_event_bus", "reset_agent_event_bus",
]
