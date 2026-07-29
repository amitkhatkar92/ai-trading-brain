"""
cost_metrics.py -- iios.ai.learning_evaluation.metrics
========================================================
:class:`CostMetrics` — token cost, API calls, total cost.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CostMetrics:
    """Immutable cost metrics for an evaluation or benchmark run."""

    metrics_id:        str
    input_tokens:      int
    output_tokens:     int
    total_tokens:      int
    api_calls:         int
    token_cost_usd:    float    # estimated USD cost of tokens
    api_call_cost_usd: float    # estimated USD cost of API calls
    total_cost_usd:    float    # token_cost + api_call_cost
    computed_at:       float

    @classmethod
    def compute(
        cls,
        input_tokens:          int   = 0,
        output_tokens:         int   = 0,
        api_calls:             int   = 0,
        token_cost_per_1k_usd: float = 0.002,   # default GPT-3.5 pricing
        api_call_cost_usd:     float = 0.0,
    ) -> "CostMetrics":
        total_tokens   = input_tokens + output_tokens
        token_cost     = (total_tokens / 1000.0) * token_cost_per_1k_usd
        total_cost     = token_cost + api_call_cost_usd
        return cls(
            metrics_id        = str(uuid.uuid4()),
            input_tokens      = input_tokens,
            output_tokens     = output_tokens,
            total_tokens      = total_tokens,
            api_calls         = api_calls,
            token_cost_usd    = round(token_cost, 6),
            api_call_cost_usd = round(api_call_cost_usd, 6),
            total_cost_usd    = round(total_cost, 6),
            computed_at       = time.time(),
        )

    def cost_per_call(self) -> float:
        return (self.total_cost_usd / self.api_calls) if self.api_calls else 0.0

    def tokens_per_call(self) -> float:
        return (self.total_tokens / self.api_calls) if self.api_calls else 0.0
