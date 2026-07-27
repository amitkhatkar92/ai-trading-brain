"""
iios.ai.foundation.events
==========================
AI Foundation typed event framework.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

from .event_types import AIEventType
from .ai_events import (
    AIEvent,
    SessionStartedEvent, SessionEndedEvent, SessionExpiredEvent,
    ExecutionStartedEvent, ExecutionCompletedEvent, ExecutionFailedEvent,
    ExecutionTimedOutEvent,
    ProviderRegisteredEvent, ProviderDeregisteredEvent, ProviderSelectedEvent,
    ProviderUnavailableEvent, ProviderHealthChangedEvent,
    RetryStartedEvent, RetryCompletedEvent, RetryExhaustedEvent,
)
from .event_bus import AIEventBus

__all__ = [
    "AIEventType", "AIEvent", "AIEventBus",
    "SessionStartedEvent", "SessionEndedEvent", "SessionExpiredEvent",
    "ExecutionStartedEvent", "ExecutionCompletedEvent", "ExecutionFailedEvent",
    "ExecutionTimedOutEvent",
    "ProviderRegisteredEvent", "ProviderDeregisteredEvent", "ProviderSelectedEvent",
    "ProviderUnavailableEvent", "ProviderHealthChangedEvent",
    "RetryStartedEvent", "RetryCompletedEvent", "RetryExhaustedEvent",
]
