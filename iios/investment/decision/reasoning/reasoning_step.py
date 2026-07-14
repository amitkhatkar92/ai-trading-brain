"""iios/investment/decision/reasoning/reasoning_step.py
ReasoningStep — atomic, traceable unit of reasoning.
Every step references the evidence trace_ids that produced it.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from iios.investment.decision.reasoning.reasoning_constants import ReasoningStepType


@dataclass(frozen=True)
class ReasoningStep:
    """
    One atomic step in the reasoning process.
    Immutable — reasoning is never mutated after creation.
    Always traceable to originating evidence via trace_ids.
    """
    step_id:                str
    step_type:              ReasoningStepType
    description:            str
    intermediate_conclusion: str           # the conclusion drawn in this step
    evidence_trace_ids:     Tuple[str, ...] # trace_ids from EvidenceItem
    confidence:             float           # 0–100 confidence in this step
    order:                  int             # position in the chain
    module_name:            str             # which reasoning module produced this
    reasoning_version:      str             # reasoning engine version
    created_at:             datetime
    metadata:               Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id":               self.step_id,
            "step_type":             self.step_type.value,
            "description":           self.description,
            "intermediate_conclusion": self.intermediate_conclusion,
            "evidence_trace_ids":    list(self.evidence_trace_ids),
            "confidence":            round(self.confidence, 2),
            "order":                 self.order,
            "module_name":           self.module_name,
            "reasoning_version":     self.reasoning_version,
            "created_at":            self.created_at.isoformat(),
            "metadata":              self.metadata,
        }


def make_step(
    step_type:              ReasoningStepType,
    description:            str,
    intermediate_conclusion: str,
    evidence_trace_ids:     Tuple[str, ...] = (),
    confidence:             float           = 70.0,
    order:                  int             = 0,
    module_name:            str             = "unknown",
    reasoning_version:      str             = "1.0",
    metadata:               Optional[Dict[str, Any]] = None,
) -> ReasoningStep:
    return ReasoningStep(
        step_id=str(uuid.uuid4()),
        step_type=step_type,
        description=description,
        intermediate_conclusion=intermediate_conclusion,
        evidence_trace_ids=evidence_trace_ids,
        confidence=max(0.0, min(100.0, confidence)),
        order=order,
        module_name=module_name,
        reasoning_version=reasoning_version,
        created_at=datetime.now(timezone.utc),
        metadata=metadata or {},
    )
