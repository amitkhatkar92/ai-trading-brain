"""
iios/intelligence/reasoning/explanation/reasoning_trace.py
==========================================================
ReasoningTrace — ordered record of every step in a reasoning session.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import TraceStepType, MAX_TRACE_STEPS


@dataclass
class TraceStep:
    """One observable step during reasoning."""
    step_id:     str             = field(default_factory=lambda: str(uuid.uuid4()))
    session_id:  str             = ""
    step_type:   TraceStepType   = TraceStepType.INFERENCE
    description: str             = ""
    inputs:      dict[str, Any]  = field(default_factory=dict)
    outputs:     dict[str, Any]  = field(default_factory=dict)
    evidence_ids: list[str]      = field(default_factory=list)
    duration_ms: float           = 0.0
    timestamp:   float           = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id":     self.step_id,
            "session_id":  self.session_id,
            "step_type":   self.step_type.value,
            "description": self.description,
            "inputs":      self.inputs,
            "outputs":     self.outputs,
            "evidence_ids": self.evidence_ids,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp":   self.timestamp,
        }


class ReasoningTrace:
    """
    Ordered list of TraceSteps for one reasoning session.
    Bounded at MAX_TRACE_STEPS; older steps are dropped when the buffer is full.
    """

    def __init__(self, session_id: str) -> None:
        self.trace_id:  str              = str(uuid.uuid4())
        self.session_id: str             = session_id
        self._steps:    list[TraceStep]  = []
        self._created_at: float          = time.time()

    # -- Building ──────────────────────────────────────────────────────────────

    def add_step(
        self,
        step_type:   TraceStepType,
        description: str              = "",
        inputs:      dict[str, Any]   | None = None,
        outputs:     dict[str, Any]   | None = None,
        evidence_ids: list[str]       | None = None,
        duration_ms: float            = 0.0,
    ) -> TraceStep:
        step = TraceStep(
            session_id   = self.session_id,
            step_type    = step_type,
            description  = description,
            inputs       = inputs or {},
            outputs      = outputs or {},
            evidence_ids = evidence_ids or [],
            duration_ms  = duration_ms,
        )
        if len(self._steps) >= MAX_TRACE_STEPS:
            self._steps.pop(0)  # Evict oldest
        self._steps.append(step)
        return step

    # -- Query ─────────────────────────────────────────────────────────────────

    def get_steps(
        self, step_type: TraceStepType | None = None
    ) -> list[TraceStep]:
        if step_type is None:
            return list(self._steps)
        return [s for s in self._steps if s.step_type == step_type]

    @property
    def step_count(self) -> int:
        return len(self._steps)

    @property
    def total_duration_ms(self) -> float:
        return sum(s.duration_ms for s in self._steps)

    # -- Text rendering ────────────────────────────────────────────────────────

    def to_text(self) -> str:
        lines = [f"Reasoning Trace  [session={self.session_id}]"]
        for i, s in enumerate(self._steps, 1):
            lines.append(
                f"  {i:3d}. [{s.step_type.value:10s}] {s.description}"
                + (f" ({s.duration_ms:.1f}ms)" if s.duration_ms else "")
            )
        return "\n".join(lines)

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id":       self.trace_id,
            "session_id":     self.session_id,
            "step_count":     self.step_count,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "steps":          [s.to_dict() for s in self._steps],
            "created_at":     self._created_at,
        }
