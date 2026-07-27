"""
ai_metadata.py — iios.ai.foundation.adapters
============================================
Immutable metadata and execution-result objects for the AI Platform.

Every AI execution produces an :class:`AIExecutionResult` — a structured
record used by A7 Routing, A8 Governance, and A13 Learning.

A1 AI Foundation — Phase 3, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import AIExecutionStatus, AICapability, SCHEMA_VERSION, VERSION


@dataclass(frozen=True)
class AIMetadata:
    """
    Immutable context metadata attached to every AI operation.

    Passed top-down through the execution pipeline so governance and
    observability layers have full context.

    Fields
    ------
    trace_id :     Distributed trace identifier (links across modules).
    span_id :      Span identifier within the trace.
    session_id :   Originating AI Foundation session.
    module_id :    Requesting AI module identifier.
    capability :   Required AI capability.
    priority :     Request priority string (from :class:`AIRequestPriority`).
    user_id :      Optional user or strategy identifier.
    tags :         Arbitrary string key-value tags.
    """
    trace_id:   str
    span_id:    str
    session_id: str
    module_id:  str
    capability: AICapability
    priority:   str              = "normal"
    user_id:    str              = ""
    tags:       Dict[str, str]   = field(default_factory=dict)
    version:    str              = VERSION
    schema:     str              = SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        module_id:  str,
        session_id: str,
        capability: AICapability,
        priority:   str = "normal",
        user_id:    str = "",
        trace_id:   str = "",
        **tags: str,
    ) -> "AIMetadata":
        """Convenience factory — auto-generates trace/span IDs if not supplied."""
        return cls(
            trace_id   = trace_id or str(uuid.uuid4()),
            span_id    = str(uuid.uuid4()),
            session_id = session_id,
            module_id  = module_id,
            capability = capability,
            priority   = priority,
            user_id    = user_id,
            tags       = dict(tags),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id":   self.trace_id,
            "span_id":    self.span_id,
            "session_id": self.session_id,
            "module_id":  self.module_id,
            "capability": self.capability.value,
            "priority":   self.priority,
            "user_id":    self.user_id,
            "tags":       self.tags,
        }


@dataclass(frozen=True)
class AIExecutionResult:
    """
    Immutable record of one completed (or failed) AI execution.

    Produced by every AI module after an operation completes.  Consumed by:
    * A7 Routing — for latency-based model selection feedback.
    * A8 Governance — for audit and cost tracking.
    * A13 Learning  — for strategy-level performance tracking.

    Fields
    ------
    result_id :     Unique result identifier.
    trace_id :      Originating trace identifier.
    module_id :     Executing AI module.
    provider_id :   Provider that handled the request.
    model_id :      Specific model used.
    status :        Execution status.
    latency_ms :    End-to-end wall-clock latency.
    prompt_tokens : Tokens consumed by the prompt.
    output_tokens : Tokens generated.
    total_tokens :  ``prompt_tokens + output_tokens``.
    cost_usd :      Estimated cost in USD (0.0 if unknown).
    error :         Error message if status is not SUCCESS.
    timestamp :     Wall-clock time of result creation.
    """
    result_id:     str
    trace_id:      str
    module_id:     str
    provider_id:   str
    model_id:      str
    status:        AIExecutionStatus
    latency_ms:    float
    prompt_tokens: int
    output_tokens: int
    total_tokens:  int
    cost_usd:      float = 0.0
    error:         str   = ""
    timestamp:     float = field(default_factory=time.time)
    schema:        str   = SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        trace_id:      str,
        module_id:     str,
        provider_id:   str,
        model_id:      str,
        status:        AIExecutionStatus,
        latency_ms:    float,
        prompt_tokens: int,
        output_tokens: int,
        cost_usd:      float = 0.0,
        error:         str   = "",
    ) -> "AIExecutionResult":
        return cls(
            result_id     = str(uuid.uuid4()),
            trace_id      = trace_id,
            module_id     = module_id,
            provider_id   = provider_id,
            model_id      = model_id,
            status        = status,
            latency_ms    = latency_ms,
            prompt_tokens = prompt_tokens,
            output_tokens = output_tokens,
            total_tokens  = prompt_tokens + output_tokens,
            cost_usd      = cost_usd,
            error         = error,
        )

    @property
    def succeeded(self) -> bool:
        return self.status == AIExecutionStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":     self.result_id,
            "trace_id":      self.trace_id,
            "module_id":     self.module_id,
            "provider_id":   self.provider_id,
            "model_id":      self.model_id,
            "status":        self.status.value,
            "latency_ms":    round(self.latency_ms, 2),
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens":  self.total_tokens,
            "cost_usd":      round(self.cost_usd, 6),
            "error":         self.error,
            "timestamp":     self.timestamp,
        }


@dataclass(frozen=True)
class AIProviderStatistics:
    """
    Aggregated execution statistics for one AI provider.

    Produced by A2 Model Management; consumed by A7 Routing and A8 Governance.
    """
    provider_id:      str
    model_id:         str
    total_requests:   int
    successful:       int
    failed:           int
    total_tokens:     int
    avg_latency_ms:   float
    p95_latency_ms:   float
    total_cost_usd:   float
    error_rate:       float
    period_start:     float
    period_end:       float
    schema:           str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id":    self.provider_id,
            "model_id":       self.model_id,
            "total_requests": self.total_requests,
            "successful":     self.successful,
            "failed":         self.failed,
            "total_tokens":   self.total_tokens,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "error_rate":     round(self.error_rate, 4),
            "period_start":   self.period_start,
            "period_end":     self.period_end,
        }
