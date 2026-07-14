"""iios/investment/decision/reasoning/reasoning_chain.py
ReasoningChain — ordered, immutable sequence of ReasoningSteps.
Sealed once complete; downstream consumers receive read-only access.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.reasoning.reasoning_constants import ReasoningStepType
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep


@dataclass(frozen=True)
class ReasoningChain:
    """
    The complete ordered sequence of reasoning steps for one decision.
    Immutable — produced once, consumed by downstream engines.
    """
    chain_id:           str
    decision_id:        str
    steps:              Tuple[ReasoningStep, ...]
    final_conclusion:   str            # the synthesized conclusion from all steps
    chain_version:      int
    total_evidence_refs: int           # total unique trace_ids referenced
    avg_step_confidence: float         # 0–100
    created_at:         datetime
    reasoning_module:   str            # pipeline that produced this chain

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def steps_of_type(self, step_type: ReasoningStepType) -> List[ReasoningStep]:
        return [s for s in self.steps if s.step_type == step_type]

    def last_step(self) -> Optional[ReasoningStep]:
        return self.steps[-1] if self.steps else None

    def all_trace_ids(self) -> List[str]:
        seen = set()
        result = []
        for step in self.steps:
            for tid in step.evidence_trace_ids:
                if tid not in seen:
                    seen.add(tid)
                    result.append(tid)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id":            self.chain_id,
            "decision_id":         self.decision_id,
            "step_count":          self.step_count,
            "final_conclusion":    self.final_conclusion,
            "chain_version":       self.chain_version,
            "total_evidence_refs": self.total_evidence_refs,
            "avg_step_confidence": round(self.avg_step_confidence, 2),
            "created_at":          self.created_at.isoformat(),
            "reasoning_module":    self.reasoning_module,
            "steps":               [s.to_dict() for s in self.steps],
        }


def build_chain(
    decision_id:      str,
    steps:            List[ReasoningStep],
    final_conclusion: str,
    chain_version:    int  = 1,
    reasoning_module: str  = "ReasoningPipeline",
) -> ReasoningChain:
    ordered = tuple(sorted(steps, key=lambda s: s.order))
    avg_conf = sum(s.confidence for s in ordered) / len(ordered) if ordered else 0.0
    all_tids = set()
    for s in ordered:
        all_tids.update(s.evidence_trace_ids)
    return ReasoningChain(
        chain_id=str(uuid.uuid4()),
        decision_id=decision_id,
        steps=ordered,
        final_conclusion=final_conclusion,
        chain_version=chain_version,
        total_evidence_refs=len(all_tids),
        avg_step_confidence=round(avg_conf, 2),
        created_at=datetime.now(timezone.utc),
        reasoning_module=reasoning_module,
    )
