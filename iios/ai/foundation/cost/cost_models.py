"""
cost_models.py -- iios.ai.foundation.cost
==========================================
Immutable cost tracking framework models.

This framework provides the infrastructure for cost tracking only.
No provider pricing is calculated here -- actual rates are injected
by A2 Model Management when it knows the provider.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA_VER = "1.0"


@dataclass(frozen=True)
class TokenUsage:
    """
    Immutable token consumption record for one AI execution.

    Fields
    ------
    prompt_tokens :    Tokens consumed by the prompt.
    completion_tokens: Tokens generated in the completion.
    total_tokens :     ``prompt_tokens + completion_tokens``.
    cached_tokens :    Prompt tokens served from provider cache (if any).
    reasoning_tokens : Internal reasoning tokens (o1-style models).
    """
    prompt_tokens:     int
    completion_tokens: int
    total_tokens:      int
    cached_tokens:     int   = 0
    reasoning_tokens:  int   = 0
    schema:            str   = SCHEMA_VER

    @classmethod
    def create(
        cls,
        prompt_tokens:     int,
        completion_tokens: int,
        cached_tokens:     int = 0,
        reasoning_tokens:  int = 0,
    ) -> "TokenUsage":
        return cls(
            prompt_tokens     = prompt_tokens,
            completion_tokens = completion_tokens,
            total_tokens      = prompt_tokens + completion_tokens,
            cached_tokens     = cached_tokens,
            reasoning_tokens  = reasoning_tokens,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens":     self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens":      self.total_tokens,
            "cached_tokens":     self.cached_tokens,
            "reasoning_tokens":  self.reasoning_tokens,
        }


@dataclass(frozen=True)
class ExecutionCost:
    """
    Immutable cost record for one AI execution.

    Cost values are zero until a pricing provider populates them.
    Framework uses USD as the reference currency; other currencies
    are conversion-layer concerns.

    Fields
    ------
    execution_id :   Unique execution identifier.
    provider_id :    Provider that processed the request.
    model_id :       Model used.
    token_usage :    Token consumption breakdown.
    input_cost_usd : Cost attributed to input/prompt tokens.
    output_cost_usd: Cost attributed to output/completion tokens.
    total_cost_usd : ``input_cost_usd + output_cost_usd``.
    currency :       Always ``"USD"`` at framework level.
    timestamp :      Wall-clock time of cost record creation.
    """
    execution_id:    str
    provider_id:     str
    model_id:        str
    token_usage:     TokenUsage
    input_cost_usd:  float = 0.0
    output_cost_usd: float = 0.0
    total_cost_usd:  float = 0.0
    currency:        str   = "USD"
    timestamp:       float = field(default_factory=time.time)
    schema:          str   = SCHEMA_VER

    @classmethod
    def create(
        cls,
        provider_id:     str,
        model_id:        str,
        token_usage:     TokenUsage,
        input_cost_usd:  float = 0.0,
        output_cost_usd: float = 0.0,
    ) -> "ExecutionCost":
        return cls(
            execution_id    = str(uuid.uuid4()),
            provider_id     = provider_id,
            model_id        = model_id,
            token_usage     = token_usage,
            input_cost_usd  = input_cost_usd,
            output_cost_usd = output_cost_usd,
            total_cost_usd  = input_cost_usd + output_cost_usd,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id":    self.execution_id,
            "provider_id":     self.provider_id,
            "model_id":        self.model_id,
            "token_usage":     self.token_usage.to_dict(),
            "input_cost_usd":  round(self.input_cost_usd,  6),
            "output_cost_usd": round(self.output_cost_usd, 6),
            "total_cost_usd":  round(self.total_cost_usd,  6),
            "currency":        self.currency,
            "timestamp":       self.timestamp,
        }


@dataclass(frozen=True)
class CostSummary:
    """
    Immutable aggregated cost summary for a session or time window.

    Fields
    ------
    period_id :       Identifier for this summary (session_id or window label).
    execution_count : Number of executions included.
    total_tokens :    Sum of all token usage.
    total_cost_usd :  Sum of all costs.
    avg_cost_usd :    Average cost per execution.
    period_start :    Start of the summary period (wall clock).
    period_end :      End of the summary period.
    by_provider :     Per-provider cost breakdown dict (provider_id -> total_cost_usd).
    """
    period_id:       str
    execution_count: int
    total_tokens:    int
    total_cost_usd:  float
    avg_cost_usd:    float
    period_start:    float
    period_end:      float
    by_provider:     Dict[str, float] = field(default_factory=dict)
    schema:          str              = SCHEMA_VER

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_id":       self.period_id,
            "execution_count": self.execution_count,
            "total_tokens":    self.total_tokens,
            "total_cost_usd":  round(self.total_cost_usd, 4),
            "avg_cost_usd":    round(self.avg_cost_usd,   6),
            "period_start":    self.period_start,
            "period_end":      self.period_end,
            "by_provider":     {k: round(v, 4) for k, v in self.by_provider.items()},
        }
