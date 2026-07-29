"""
prompt_events.py -- iios.ai.prompt_context.events
====================================================
Immutable event dataclasses for the A3 Prompt & Context Platform.

Mirrors the proven pattern from ``iios.ai.foundation.events.ai_events``
but is fully self-contained (A3 does not modify A1).

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .event_types import PromptEventType

VERSION    = "1.0.0"
SCHEMA_VER = "1.0"


@dataclass(frozen=True)
class PromptEvent:
    """Base class for all A3 Prompt & Context Platform events."""
    event_id:   str
    event_type: PromptEventType
    source_id:  str
    timestamp:  float
    trace_id:   str
    version:    str = VERSION
    schema:     str = SCHEMA_VER

    @classmethod
    def _base_kwargs(
        cls,
        event_type: PromptEventType,
        source_id:  str,
        trace_id:   str = "",
    ) -> Dict[str, Any]:
        return dict(
            event_id   = str(uuid.uuid4()),
            event_type = event_type,
            source_id  = source_id,
            timestamp  = time.time(),
            trace_id   = trace_id or str(uuid.uuid4()),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "source_id":  self.source_id,
            "timestamp":  self.timestamp,
            "trace_id":   self.trace_id,
        }


@dataclass(frozen=True)
class PromptRegisteredEvent(PromptEvent):
    prompt_id: str = ""
    name:      str = ""
    category:  str = ""

    @classmethod
    def create(cls, source_id: str, prompt_id: str, name: str, category: str,
               trace_id: str = "") -> "PromptRegisteredEvent":
        return cls(
            **cls._base_kwargs(PromptEventType.PROMPT_REGISTERED, source_id, trace_id),
            prompt_id=prompt_id, name=name, category=category,
        )


@dataclass(frozen=True)
class PromptRemovedEvent(PromptEvent):
    prompt_id: str = ""

    @classmethod
    def create(cls, source_id: str, prompt_id: str, trace_id: str = "") -> "PromptRemovedEvent":
        return cls(
            **cls._base_kwargs(PromptEventType.PROMPT_REMOVED, source_id, trace_id),
            prompt_id=prompt_id,
        )


@dataclass(frozen=True)
class PromptEnabledEvent(PromptEvent):
    prompt_id: str = ""

    @classmethod
    def create(cls, source_id: str, prompt_id: str, trace_id: str = "") -> "PromptEnabledEvent":
        return cls(
            **cls._base_kwargs(PromptEventType.PROMPT_ENABLED, source_id, trace_id),
            prompt_id=prompt_id,
        )


@dataclass(frozen=True)
class PromptDisabledEvent(PromptEvent):
    prompt_id: str = ""

    @classmethod
    def create(cls, source_id: str, prompt_id: str, trace_id: str = "") -> "PromptDisabledEvent":
        return cls(
            **cls._base_kwargs(PromptEventType.PROMPT_DISABLED, source_id, trace_id),
            prompt_id=prompt_id,
        )


@dataclass(frozen=True)
class PromptUpdatedEvent(PromptEvent):
    prompt_id:      str = ""
    version_id:     str = ""
    version_number: int = 0

    @classmethod
    def create(cls, source_id: str, prompt_id: str, version_id: str,
               version_number: int, trace_id: str = "") -> "PromptUpdatedEvent":
        return cls(
            **cls._base_kwargs(PromptEventType.PROMPT_UPDATED, source_id, trace_id),
            prompt_id=prompt_id, version_id=version_id, version_number=version_number,
        )


@dataclass(frozen=True)
class PromptRenderedEvent(PromptEvent):
    prompt_id:        str = ""
    version_id:       str = ""
    estimated_tokens: int = 0

    @classmethod
    def create(cls, source_id: str, prompt_id: str, version_id: str,
               estimated_tokens: int, trace_id: str = "") -> "PromptRenderedEvent":
        return cls(
            **cls._base_kwargs(PromptEventType.PROMPT_RENDERED, source_id, trace_id),
            prompt_id=prompt_id, version_id=version_id, estimated_tokens=estimated_tokens,
        )


@dataclass(frozen=True)
class ContextBuiltEvent(PromptEvent):
    context_id:       str  = ""
    segment_count:    int  = 0
    estimated_tokens: int  = 0
    within_budget:    bool = True

    @classmethod
    def create(cls, source_id: str, context_id: str, segment_count: int,
               estimated_tokens: int, within_budget: bool,
               trace_id: str = "") -> "ContextBuiltEvent":
        return cls(
            **cls._base_kwargs(PromptEventType.CONTEXT_BUILT, source_id, trace_id),
            context_id=context_id, segment_count=segment_count,
            estimated_tokens=estimated_tokens, within_budget=within_budget,
        )


@dataclass(frozen=True)
class ValidationSucceededEvent(PromptEvent):
    target:    str = ""   # "prompt" | "context" | "variables"
    target_id: str = ""

    @classmethod
    def create(cls, source_id: str, target: str, target_id: str,
               trace_id: str = "") -> "ValidationSucceededEvent":
        return cls(
            **cls._base_kwargs(PromptEventType.VALIDATION_SUCCEEDED, source_id, trace_id),
            target=target, target_id=target_id,
        )


@dataclass(frozen=True)
class ValidationFailedEvent(PromptEvent):
    target:    str            = ""
    target_id: str            = ""
    errors:    Tuple[str, ...] = ()

    @classmethod
    def create(cls, source_id: str, target: str, target_id: str,
               errors: Tuple[str, ...], trace_id: str = "") -> "ValidationFailedEvent":
        return cls(
            **cls._base_kwargs(PromptEventType.VALIDATION_FAILED, source_id, trace_id),
            target=target, target_id=target_id, errors=tuple(errors),
        )


@dataclass(frozen=True)
class TemplateActivatedEvent(PromptEvent):
    prompt_id:      str = ""
    version_id:     str = ""
    version_number: int = 0

    @classmethod
    def create(cls, source_id: str, prompt_id: str, version_id: str,
               version_number: int, trace_id: str = "") -> "TemplateActivatedEvent":
        return cls(
            **cls._base_kwargs(PromptEventType.TEMPLATE_ACTIVATED, source_id, trace_id),
            prompt_id=prompt_id, version_id=version_id, version_number=version_number,
        )
