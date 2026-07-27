"""
ai_events.py -- iios.ai.foundation.events
==========================================
Immutable event dataclasses for the AI Foundation event framework.

All events are frozen dataclasses -- safe for cross-thread publishing,
audit logs, and snapshot storage.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .event_types import AIEventType

VERSION      = "1.0.0"
SCHEMA_VER   = "1.0"


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIEvent:
    """Base class for all AI Foundation events."""
    event_id:    str
    event_type:  AIEventType
    source_id:   str
    timestamp:   float
    trace_id:    str
    correlation: str
    version:     str  = VERSION
    schema:      str  = SCHEMA_VER

    @classmethod
    def _base_kwargs(
        cls,
        event_type:  AIEventType,
        source_id:   str,
        trace_id:    str  = "",
        correlation: str  = "",
    ) -> Dict[str, Any]:
        return dict(
            event_id    = str(uuid.uuid4()),
            event_type  = event_type,
            source_id   = source_id,
            timestamp   = time.time(),
            trace_id    = trace_id or str(uuid.uuid4()),
            correlation = correlation,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "source_id":  self.source_id,
            "timestamp":  self.timestamp,
            "trace_id":   self.trace_id,
        }


# ---------------------------------------------------------------------------
# Session events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SessionStartedEvent(AIEvent):
    session_id: str = ""
    module_id:  str = ""
    capability: str = ""

    @classmethod
    def create(cls, source_id: str, session_id: str, module_id: str,
               capability: str = "", trace_id: str = "") -> "SessionStartedEvent":
        return cls(**cls._base_kwargs(AIEventType.SESSION_STARTED, source_id, trace_id),
                   session_id=session_id, module_id=module_id, capability=capability)


@dataclass(frozen=True)
class SessionEndedEvent(AIEvent):
    session_id:  str   = ""
    duration_s:  float = 0.0
    reason:      str   = "completed"

    @classmethod
    def create(cls, source_id: str, session_id: str, duration_s: float,
               reason: str = "completed", trace_id: str = "") -> "SessionEndedEvent":
        return cls(**cls._base_kwargs(AIEventType.SESSION_ENDED, source_id, trace_id),
                   session_id=session_id, duration_s=duration_s, reason=reason)


@dataclass(frozen=True)
class SessionExpiredEvent(AIEvent):
    session_id: str   = ""
    ttl_s:      float = 0.0

    @classmethod
    def create(cls, source_id: str, session_id: str, ttl_s: float,
               trace_id: str = "") -> "SessionExpiredEvent":
        return cls(**cls._base_kwargs(AIEventType.SESSION_EXPIRED, source_id, trace_id),
                   session_id=session_id, ttl_s=ttl_s)


# ---------------------------------------------------------------------------
# Execution events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionStartedEvent(AIEvent):
    request_id:  str = ""
    session_id:  str = ""
    capability:  str = ""
    provider_id: str = ""

    @classmethod
    def create(cls, source_id: str, request_id: str, session_id: str,
               capability: str = "", provider_id: str = "",
               trace_id: str = "") -> "ExecutionStartedEvent":
        return cls(**cls._base_kwargs(AIEventType.EXECUTION_STARTED, source_id, trace_id),
                   request_id=request_id, session_id=session_id,
                   capability=capability, provider_id=provider_id)


@dataclass(frozen=True)
class ExecutionCompletedEvent(AIEvent):
    request_id:    str   = ""
    session_id:    str   = ""
    provider_id:   str   = ""
    latency_ms:    float = 0.0
    prompt_tokens: int   = 0
    output_tokens: int   = 0

    @classmethod
    def create(cls, source_id: str, request_id: str, session_id: str,
               provider_id: str, latency_ms: float,
               prompt_tokens: int = 0, output_tokens: int = 0,
               trace_id: str = "") -> "ExecutionCompletedEvent":
        return cls(**cls._base_kwargs(AIEventType.EXECUTION_COMPLETED, source_id, trace_id),
                   request_id=request_id, session_id=session_id, provider_id=provider_id,
                   latency_ms=latency_ms, prompt_tokens=prompt_tokens, output_tokens=output_tokens)


@dataclass(frozen=True)
class ExecutionFailedEvent(AIEvent):
    request_id:  str = ""
    session_id:  str = ""
    provider_id: str = ""
    error_code:  str = ""
    error_msg:   str = ""

    @classmethod
    def create(cls, source_id: str, request_id: str, session_id: str,
               provider_id: str, error_code: str, error_msg: str,
               trace_id: str = "") -> "ExecutionFailedEvent":
        return cls(**cls._base_kwargs(AIEventType.EXECUTION_FAILED, source_id, trace_id),
                   request_id=request_id, session_id=session_id, provider_id=provider_id,
                   error_code=error_code, error_msg=error_msg)


@dataclass(frozen=True)
class ExecutionTimedOutEvent(AIEvent):
    request_id:  str   = ""
    session_id:  str   = ""
    timeout_s:   float = 0.0

    @classmethod
    def create(cls, source_id: str, request_id: str, session_id: str,
               timeout_s: float, trace_id: str = "") -> "ExecutionTimedOutEvent":
        return cls(**cls._base_kwargs(AIEventType.EXECUTION_TIMED_OUT, source_id, trace_id),
                   request_id=request_id, session_id=session_id, timeout_s=timeout_s)


# ---------------------------------------------------------------------------
# Provider events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProviderRegisteredEvent(AIEvent):
    provider_id:   str  = ""
    model_id:      str  = ""
    capabilities:  tuple = field(default_factory=tuple)

    @classmethod
    def create(cls, source_id: str, provider_id: str, model_id: str,
               capabilities: tuple = (), trace_id: str = "") -> "ProviderRegisteredEvent":
        return cls(**cls._base_kwargs(AIEventType.PROVIDER_REGISTERED, source_id, trace_id),
                   provider_id=provider_id, model_id=model_id, capabilities=capabilities)


@dataclass(frozen=True)
class ProviderDeregisteredEvent(AIEvent):
    provider_id: str = ""

    @classmethod
    def create(cls, source_id: str, provider_id: str,
               trace_id: str = "") -> "ProviderDeregisteredEvent":
        return cls(**cls._base_kwargs(AIEventType.PROVIDER_DEREGISTERED, source_id, trace_id),
                   provider_id=provider_id)


@dataclass(frozen=True)
class ProviderSelectedEvent(AIEvent):
    provider_id:  str = ""
    request_id:   str = ""
    capability:   str = ""
    strategy:     str = ""

    @classmethod
    def create(cls, source_id: str, provider_id: str, request_id: str,
               capability: str, strategy: str = "",
               trace_id: str = "") -> "ProviderSelectedEvent":
        return cls(**cls._base_kwargs(AIEventType.PROVIDER_SELECTED, source_id, trace_id),
                   provider_id=provider_id, request_id=request_id,
                   capability=capability, strategy=strategy)


@dataclass(frozen=True)
class ProviderUnavailableEvent(AIEvent):
    provider_id: str = ""
    reason:      str = ""

    @classmethod
    def create(cls, source_id: str, provider_id: str, reason: str = "",
               trace_id: str = "") -> "ProviderUnavailableEvent":
        return cls(**cls._base_kwargs(AIEventType.PROVIDER_UNAVAILABLE, source_id, trace_id),
                   provider_id=provider_id, reason=reason)


@dataclass(frozen=True)
class ProviderHealthChangedEvent(AIEvent):
    provider_id:  str = ""
    old_status:   str = ""
    new_status:   str = ""

    @classmethod
    def create(cls, source_id: str, provider_id: str, old_status: str,
               new_status: str, trace_id: str = "") -> "ProviderHealthChangedEvent":
        return cls(**cls._base_kwargs(AIEventType.PROVIDER_HEALTH_CHANGED, source_id, trace_id),
                   provider_id=provider_id, old_status=old_status, new_status=new_status)


# ---------------------------------------------------------------------------
# Retry events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetryStartedEvent(AIEvent):
    request_id:  str = ""
    attempt:     int = 1
    max_attempts: int = 3
    delay_s:     float = 0.0

    @classmethod
    def create(cls, source_id: str, request_id: str, attempt: int,
               max_attempts: int, delay_s: float,
               trace_id: str = "") -> "RetryStartedEvent":
        return cls(**cls._base_kwargs(AIEventType.RETRY_STARTED, source_id, trace_id),
                   request_id=request_id, attempt=attempt,
                   max_attempts=max_attempts, delay_s=delay_s)


@dataclass(frozen=True)
class RetryCompletedEvent(AIEvent):
    request_id:    str  = ""
    total_attempts: int = 1
    succeeded:     bool = True

    @classmethod
    def create(cls, source_id: str, request_id: str, total_attempts: int,
               succeeded: bool, trace_id: str = "") -> "RetryCompletedEvent":
        return cls(**cls._base_kwargs(AIEventType.RETRY_COMPLETED, source_id, trace_id),
                   request_id=request_id, total_attempts=total_attempts, succeeded=succeeded)


@dataclass(frozen=True)
class RetryExhaustedEvent(AIEvent):
    request_id:   str = ""
    max_attempts: int = 3
    last_error:   str = ""

    @classmethod
    def create(cls, source_id: str, request_id: str, max_attempts: int,
               last_error: str = "", trace_id: str = "") -> "RetryExhaustedEvent":
        return cls(**cls._base_kwargs(AIEventType.RETRY_EXHAUSTED, source_id, trace_id),
                   request_id=request_id, max_attempts=max_attempts, last_error=last_error)
