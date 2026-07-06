"""
iios/events/__init__.py
========================
Public API for the IIOS Event & Messaging Framework.
"""

from __future__ import annotations

# --- Core event types ---
from .event_constants import (
    DEFAULT_MAX_RETRIES, DEFAULT_RETRY_DELAY, DEFAULT_RETRY_BACKOFF, MAX_RETRY_JITTER,
    DEFAULT_TIMEOUT, DEFAULT_QUEUE_TIMEOUT, DEFAULT_WORKFLOW_TIMEOUT,
    DEFAULT_QUEUE_SIZE, DEFAULT_BATCH_SIZE, DEFAULT_STREAM_CHUNK,
    MAX_HANDLERS, MAX_WORKFLOW_STEPS,
    DLQ_RETENTION_DAYS, WILDCARD, BROADCAST_TOPIC, SYSTEM_SOURCE,
    CORRELATION_HEADER, CAUSATION_HEADER,
)
from .event_exceptions import (
    EventError, PublishError, SubscribeError, HandlerError, HandlerTimeoutError,
    EventNotFoundError, EventTypeError, DispatchError, RouterError, NoRouteError,
    RegistryError, EventAlreadyRegisteredError,
    MessageError, MessageDeliveryError, MessageExpiredError,
    QueueError, QueueFullError, QueueEmptyError, QueueTimeoutError, DeadLetterError,
    CommandError, CommandNotFoundError, CommandHandlerError,
    QueryError, QueryTimeoutError,
    WorkflowError, WorkflowStepError, WorkflowTimeoutError, WorkflowRollbackError,
    RetryExhaustedError, IdempotencyError,
)
from .event_priority import EventPriority, MessagePriority
from .event_metadata import make_event_id, make_correlation_id, EventMetadata, Event
from .event_context import (
    current_event, push_event, pop_event, event_scope,
    EventSpan, EventContext, get_event_context,
)
from .event_factory import EventFactory
from .event_registry import EventTypeDescriptor, EventRegistry, get_event_registry, reset_event_registry
from .event_dispatcher import SubscriberRecord, DispatchResult, EventDispatcher, EventHandler
from .event_router import RouteRule, EventRouter
from .event_bus import BusStats, EventBus, get_event_bus, reset_event_bus
from .event_manager import EventManager, get_event_manager, reset_event_manager

# --- Messaging ---
from .messaging import (
    MessageStatus, MessageType, MessageEnvelope,
    Message, Command, Query, Response, make_message_id,
    CommandHandlerBase, CommandRegistry,
    FifoQueue, PriorityQueue, DelayQueue, RetryQueue,
    DeadLetterQueue, BatchQueue, StreamingQueue,
    MessageDispatcher, DispatchStats,
    MessageRoute, MessageRouter,
    MessageTypeDescriptor, MessageRegistry, get_message_registry, reset_message_registry,
    MessageFactory,
    CommandBus, CommandStats, get_command_bus, reset_command_bus,
    QueryBus, QueryStats, get_query_bus, reset_query_bus,
    ResponseBus, get_response_bus, reset_response_bus,
)

# --- Workflow ---
from .workflow import (
    WorkflowStatus, StepResult, WorkflowStep, WorkflowState,
    WorkflowPipeline, SagaWorkflow, WorkflowEngine,
    get_workflow_engine, reset_workflow_engine,
)

__all__ = [
    # Constants
    "DEFAULT_MAX_RETRIES", "DEFAULT_RETRY_DELAY", "DEFAULT_RETRY_BACKOFF", "MAX_RETRY_JITTER",
    "DEFAULT_TIMEOUT", "DEFAULT_QUEUE_TIMEOUT", "DEFAULT_WORKFLOW_TIMEOUT",
    "DEFAULT_QUEUE_SIZE", "DEFAULT_BATCH_SIZE", "DEFAULT_STREAM_CHUNK",
    "MAX_HANDLERS", "MAX_WORKFLOW_STEPS",
    "DLQ_RETENTION_DAYS", "WILDCARD", "BROADCAST_TOPIC", "SYSTEM_SOURCE",
    "CORRELATION_HEADER", "CAUSATION_HEADER",
    # Exceptions
    "EventError", "PublishError", "SubscribeError", "HandlerError", "HandlerTimeoutError",
    "EventNotFoundError", "EventTypeError", "DispatchError", "RouterError", "NoRouteError",
    "RegistryError", "EventAlreadyRegisteredError",
    "MessageError", "MessageDeliveryError", "MessageExpiredError",
    "QueueError", "QueueFullError", "QueueEmptyError", "QueueTimeoutError", "DeadLetterError",
    "CommandError", "CommandNotFoundError", "CommandHandlerError",
    "QueryError", "QueryTimeoutError",
    "WorkflowError", "WorkflowStepError", "WorkflowTimeoutError", "WorkflowRollbackError",
    "RetryExhaustedError", "IdempotencyError",
    # Priority
    "EventPriority", "MessagePriority",
    # Metadata / Event
    "make_event_id", "make_correlation_id", "EventMetadata", "Event",
    # Context
    "current_event", "push_event", "pop_event", "event_scope",
    "EventSpan", "EventContext", "get_event_context",
    # Factory
    "EventFactory",
    # Registry
    "EventTypeDescriptor", "EventRegistry", "get_event_registry", "reset_event_registry",
    # Dispatcher / Router / Bus
    "SubscriberRecord", "DispatchResult", "EventDispatcher", "EventHandler",
    "RouteRule", "EventRouter",
    "BusStats", "EventBus", "get_event_bus", "reset_event_bus",
    "EventManager", "get_event_manager", "reset_event_manager",
    # Messaging
    "MessageStatus", "MessageType", "MessageEnvelope",
    "Message", "Command", "Query", "Response", "make_message_id",
    "CommandHandlerBase", "CommandRegistry",
    "FifoQueue", "PriorityQueue", "DelayQueue", "RetryQueue",
    "DeadLetterQueue", "BatchQueue", "StreamingQueue",
    "MessageDispatcher", "DispatchStats",
    "MessageRoute", "MessageRouter",
    "MessageTypeDescriptor", "MessageRegistry",
    "get_message_registry", "reset_message_registry",
    "MessageFactory",
    "CommandBus", "CommandStats", "get_command_bus", "reset_command_bus",
    "QueryBus", "QueryStats", "get_query_bus", "reset_query_bus",
    "ResponseBus", "get_response_bus", "reset_response_bus",
    # Workflow
    "WorkflowStatus", "StepResult", "WorkflowStep", "WorkflowState",
    "WorkflowPipeline", "SagaWorkflow", "WorkflowEngine",
    "get_workflow_engine", "reset_workflow_engine",
]
