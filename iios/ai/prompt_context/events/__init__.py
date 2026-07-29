"""
iios.ai.prompt_context.events
================================
Immutable domain events + typed event bus for the A3 Prompt & Context
Platform (part of M4 Core Framework).
"""
from __future__ import annotations

from .event_bus     import PromptEventBus
from .event_types   import PromptEventType
from .prompt_events import (
    ContextBuiltEvent,
    PromptDisabledEvent,
    PromptEnabledEvent,
    PromptEvent,
    PromptRegisteredEvent,
    PromptRemovedEvent,
    PromptRenderedEvent,
    PromptUpdatedEvent,
    TemplateActivatedEvent,
    ValidationFailedEvent,
    ValidationSucceededEvent,
)

__all__ = [
    "PromptEventBus",
    "PromptEventType",
    "PromptEvent",
    "PromptRegisteredEvent",
    "PromptRemovedEvent",
    "PromptEnabledEvent",
    "PromptDisabledEvent",
    "PromptUpdatedEvent",
    "PromptRenderedEvent",
    "ContextBuiltEvent",
    "ValidationSucceededEvent",
    "ValidationFailedEvent",
    "TemplateActivatedEvent",
]
