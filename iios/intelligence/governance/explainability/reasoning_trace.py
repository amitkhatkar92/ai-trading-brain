"""
iios/intelligence/governance/explainability/reasoning_trace.py
==============================================================
ReasoningTraceRecord — governance-level trace of the reasoning steps
that produced an intelligence product.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReasoningStep:
    """One step in a governance reasoning trace."""

    step_id:    str            = field(default_factory=lambda: str(uuid.uuid4()))
    order:      int            = 0
    label:      str            = ""
    input_:     dict[str, Any] = field(default_factory=dict)
    output:     dict[str, Any] = field(default_factory=dict)
    confidence: float          = 1.0
    duration_ms: float         = 0.0
    metadata:   dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id":     self.step_id,
            "order":       self.order,
            "label":       self.label,
            "input":       self.input_,
            "output":      self.output,
            "confidence":  round(self.confidence, 4),
            "duration_ms": round(self.duration_ms, 2),
            "metadata":    self.metadata,
        }


@dataclass
class ReasoningTraceRecord:
    """
    Complete governance trace of reasoning that led to a quality decision.
    """

    trace_id:      str                   = field(default_factory=lambda: str(uuid.uuid4()))
    record_id:     str                   = ""  # parent QualityRecord
    product_id:    str                   = ""
    steps:         list[ReasoningStep]   = field(default_factory=list)
    summary:       str                   = ""
    total_steps:   int                   = 0
    avg_confidence: float                = 0.0
    created_at:    float                 = field(default_factory=time.time)

    def add_step(
        self,
        label:      str,
        input_:     dict[str, Any] | None = None,
        output:     dict[str, Any] | None = None,
        confidence: float                  = 1.0,
    ) -> ReasoningStep:
        step = ReasoningStep(
            order      = len(self.steps),
            label      = label,
            input_     = input_ or {},
            output     = output or {},
            confidence = confidence,
        )
        self.steps.append(step)
        self.total_steps     = len(self.steps)
        self.avg_confidence  = (
            sum(s.confidence for s in self.steps) / self.total_steps
        )
        return step

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id":       self.trace_id,
            "record_id":      self.record_id,
            "product_id":     self.product_id,
            "steps":          [s.to_dict() for s in self.steps],
            "total_steps":    self.total_steps,
            "avg_confidence": round(self.avg_confidence, 4),
            "summary":        self.summary,
            "created_at":     self.created_at,
        }
