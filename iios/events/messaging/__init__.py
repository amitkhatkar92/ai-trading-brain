"""
iios/events/messaging/__init__.py
"""
from __future__ import annotations

from .message import (
    MessageStatus, MessageType, MessageEnvelope,
    Message, Command, Query, Response, make_message_id,
)
from .command import CommandHandlerBase, CommandRegistry
from .message_queue import (
    FifoQueue, PriorityQueue, DelayQueue, RetryQueue,
    DeadLetterQueue, BatchQueue, StreamingQueue,
)
from .message_dispatcher import MessageDispatcher, MessageHandler, DispatchStats
from .message_router import MessageRoute, MessageRouter
from .message_registry import MessageTypeDescriptor, MessageRegistry, get_message_registry, reset_message_registry
from .message_factory import MessageFactory
from .command_bus import CommandBus, CommandStats, get_command_bus, reset_command_bus
from .query_bus import QueryBus, QueryStats, get_query_bus, reset_query_bus
from .response_bus import ResponseBus, get_response_bus, reset_response_bus

__all__ = [
    # Message types
    "MessageStatus", "MessageType", "MessageEnvelope",
    "Message", "Command", "Query", "Response", "make_message_id",
    # Handlers
    "CommandHandlerBase", "CommandRegistry",
    # Queues
    "FifoQueue", "PriorityQueue", "DelayQueue", "RetryQueue",
    "DeadLetterQueue", "BatchQueue", "StreamingQueue",
    # Dispatch
    "MessageDispatcher", "MessageHandler", "DispatchStats",
    # Routing
    "MessageRoute", "MessageRouter",
    # Registry
    "MessageTypeDescriptor", "MessageRegistry",
    "get_message_registry", "reset_message_registry",
    # Factory
    "MessageFactory",
    # Buses
    "CommandBus", "CommandStats", "get_command_bus", "reset_command_bus",
    "QueryBus", "QueryStats", "get_query_bus", "reset_query_bus",
    "ResponseBus", "get_response_bus", "reset_response_bus",
]
