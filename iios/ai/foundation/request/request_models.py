"""
request_models.py -- iios.ai.foundation.request
================================================
Immutable request/response DTOs for the AI execution pipeline.

These are the framework-level objects that flow through the pipeline.
They are distinct from the lower-level ``AIProviderRequest/Response``
in ``iios.ai.foundation.adapters`` which are provider-specific.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Request metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RequestMetadata:
    """
    Immutable metadata attached to every AI framework request.

    Fields
    ------
    request_id :   Unique request identifier.
    session_id :   Originating AI session.
    trace_id :     Distributed trace identifier.
    module_id :    Requesting AI module.
    capability :   Required AI capability.
    priority :     Scheduling priority string.
    timeout_s :    Hard deadline for this request.
    user_id :      Optional caller identifier.
    created_at :   Wall-clock creation time.
    tags :         Caller-supplied string key-value tags.
    """
    request_id:  str
    session_id:  str
    trace_id:    str
    module_id:   str
    capability:  str
    priority:    str              = "normal"
    timeout_s:   float            = 30.0
    user_id:     str              = ""
    created_at:  float            = field(default_factory=time.time)
    tags:        Dict[str, str]   = field(default_factory=dict)
    schema:      str              = SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        session_id:  str,
        module_id:   str,
        *,
        capability:  str   = "completion",
        priority:    str   = "normal",
        timeout_s:   float = 30.0,
        user_id:     str   = "",
        trace_id:    str   = "",
        **tags: str,
    ) -> "RequestMetadata":
        return cls(
            request_id = str(uuid.uuid4()),
            session_id = session_id,
            trace_id   = trace_id or str(uuid.uuid4()),
            module_id  = module_id,
            capability = capability,
            priority   = priority,
            timeout_s  = timeout_s,
            user_id    = user_id,
            tags       = dict(tags),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "trace_id":   self.trace_id,
            "module_id":  self.module_id,
            "capability": self.capability,
            "priority":   self.priority,
            "timeout_s":  self.timeout_s,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# AI Request
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIRequest:
    """
    Immutable framework-level AI request.

    This is the object submitted to :class:`ExecutionPipeline`.

    Fields
    ------
    metadata :        Request descriptor.
    messages :        Ordered list of {role, content} dicts (from AIContext).
    max_tokens :      Maximum output tokens requested.
    temperature :     Sampling temperature.
    provider_hint :   Optional preferred provider ID (overrides automatic routing).
    """
    metadata:       RequestMetadata
    messages:       tuple[Dict[str, str], ...]
    max_tokens:     int
    temperature:    float               = 0.0
    provider_hint:  str                 = ""
    extra:          Dict[str, Any]      = field(default_factory=dict)
    schema:         str                 = SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        metadata:      RequestMetadata,
        messages:      List[Dict[str, str]],
        *,
        max_tokens:    int   = 1_024,
        temperature:   float = 0.0,
        provider_hint: str   = "",
        **extra: Any,
    ) -> "AIRequest":
        return cls(
            metadata      = metadata,
            messages      = tuple(messages),
            max_tokens    = max_tokens,
            temperature   = temperature,
            provider_hint = provider_hint,
            extra         = dict(extra),
        )

    @property
    def request_id(self) -> str:
        return self.metadata.request_id

    @property
    def session_id(self) -> str:
        return self.metadata.session_id

    @property
    def capability(self) -> str:
        return self.metadata.capability

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":   self.request_id,
            "session_id":   self.session_id,
            "capability":   self.capability,
            "message_count": len(self.messages),
            "max_tokens":   self.max_tokens,
            "temperature":  self.temperature,
            "provider_hint": self.provider_hint,
        }


# ---------------------------------------------------------------------------
# AI Response
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIResponse:
    """
    Immutable framework-level AI response.

    Produced by :class:`ExecutionPipeline` and returned to the caller.

    Fields
    ------
    request_id :    Echoed from the originating request.
    response_id :   Unique response identifier.
    session_id :    Originating session.
    content :       Generated text content.
    provider_id :   Provider that handled the request.
    model_id :      Specific model used.
    finish_reason : Provider finish reason.
    prompt_tokens : Input tokens consumed.
    output_tokens : Output tokens generated.
    total_tokens :  Sum.
    latency_ms :    End-to-end pipeline latency.
    succeeded :     ``True`` iff the request completed successfully.
    error :         Error message if not succeeded.
    timestamp :     Wall-clock completion time.
    """
    request_id:    str
    response_id:   str
    session_id:    str
    content:       str
    provider_id:   str
    model_id:      str
    finish_reason: str
    prompt_tokens: int
    output_tokens: int
    total_tokens:  int
    latency_ms:    float
    succeeded:     bool
    error:         str              = ""
    timestamp:     float            = field(default_factory=time.time)
    metadata:      Dict[str, Any]   = field(default_factory=dict)
    schema:        str              = SCHEMA_VERSION

    @classmethod
    def success(
        cls,
        request_id:    str,
        session_id:    str,
        content:       str,
        provider_id:   str,
        model_id:      str,
        finish_reason: str,
        prompt_tokens: int,
        output_tokens: int,
        latency_ms:    float,
    ) -> "AIResponse":
        return cls(
            request_id    = request_id,
            response_id   = str(uuid.uuid4()),
            session_id    = session_id,
            content       = content,
            provider_id   = provider_id,
            model_id      = model_id,
            finish_reason = finish_reason,
            prompt_tokens = prompt_tokens,
            output_tokens = output_tokens,
            total_tokens  = prompt_tokens + output_tokens,
            latency_ms    = latency_ms,
            succeeded     = True,
        )

    @classmethod
    def failure(
        cls,
        request_id:  str,
        session_id:  str,
        error:       str,
        latency_ms:  float,
        provider_id: str = "",
        model_id:    str = "",
    ) -> "AIResponse":
        return cls(
            request_id    = request_id,
            response_id   = str(uuid.uuid4()),
            session_id    = session_id,
            content       = "",
            provider_id   = provider_id,
            model_id      = model_id,
            finish_reason = "error",
            prompt_tokens = 0,
            output_tokens = 0,
            total_tokens  = 0,
            latency_ms    = latency_ms,
            succeeded     = False,
            error         = error,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":    self.request_id,
            "response_id":   self.response_id,
            "session_id":    self.session_id,
            "succeeded":     self.succeeded,
            "provider_id":   self.provider_id,
            "model_id":      self.model_id,
            "finish_reason": self.finish_reason,
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens":  self.total_tokens,
            "latency_ms":    round(self.latency_ms, 2),
            "error":         self.error,
            "timestamp":     self.timestamp,
        }


# ---------------------------------------------------------------------------
# Execution request / result (higher-level wrappers)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIExecutionRequest:
    """
    Full execution package submitted to the AI Foundation pipeline.

    Bundles the request with its pre-assembled context metadata for
    pipeline stages.
    """
    request:         AIRequest
    context_id:      str              = ""
    policy_overrides: Dict[str, Any]  = field(default_factory=dict)
    schema:          str              = SCHEMA_VERSION

    @property
    def request_id(self) -> str:
        return self.request.request_id

    @property
    def session_id(self) -> str:
        return self.request.session_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":  self.request_id,
            "session_id":  self.session_id,
            "context_id":  self.context_id,
        }


@dataclass(frozen=True)
class AIExecutionResult:
    """
    Full execution result produced by the pipeline.

    Bundles the response with pipeline-level statistics.
    """
    response:          AIResponse
    pipeline_id:       str
    stages_completed:  int
    stages_total:      int
    policy_decisions:  tuple[str, ...]     = field(default_factory=tuple)
    provider_selected: str                 = ""
    total_latency_ms:  float               = 0.0
    schema:            str                 = SCHEMA_VERSION

    @property
    def request_id(self) -> str:
        return self.response.request_id

    @property
    def succeeded(self) -> bool:
        return self.response.succeeded

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":       self.request_id,
            "pipeline_id":      self.pipeline_id,
            "succeeded":        self.succeeded,
            "stages_completed": self.stages_completed,
            "stages_total":     self.stages_total,
            "provider_selected": self.provider_selected,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "response":         self.response.to_dict(),
        }
