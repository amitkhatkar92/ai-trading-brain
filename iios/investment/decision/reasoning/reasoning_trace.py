"""iios/investment/decision/reasoning/reasoning_trace.py
ReasoningTrace — rich audit log of the full reasoning process.
Provides step-by-step provenance and query APIs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.reasoning.reasoning_chain import ReasoningChain
from iios.investment.decision.reasoning.reasoning_constants import ReasoningStepType
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep


@dataclass(frozen=True)
class TraceEntry:
    """One traced reasoning event with full provenance."""
    step_id:       str
    step_type:     str
    description:   str
    conclusion:    str
    trace_ids:     Tuple[str, ...]
    confidence:    float
    order:         int
    module:        str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id":    self.step_id,
            "step_type":  self.step_type,
            "description": self.description,
            "conclusion":  self.conclusion,
            "trace_ids":   list(self.trace_ids),
            "confidence":  round(self.confidence, 2),
            "order":       self.order,
            "module":      self.module,
        }


class ReasoningTrace:
    """
    Immutable audit representation of a reasoning chain.
    Built from a ReasoningChain; provides rich query APIs.
    """

    def __init__(self, chain: ReasoningChain) -> None:
        self._chain   = chain
        self._entries: List[TraceEntry] = [
            TraceEntry(
                step_id=s.step_id,
                step_type=s.step_type.value,
                description=s.description,
                conclusion=s.intermediate_conclusion,
                trace_ids=s.evidence_trace_ids,
                confidence=s.confidence,
                order=s.order,
                module=s.module_name,
            )
            for s in chain.steps
        ]

    @property
    def chain_id(self) -> str:
        return self._chain.chain_id

    @property
    def decision_id(self) -> str:
        return self._chain.decision_id

    @property
    def final_conclusion(self) -> str:
        return self._chain.final_conclusion

    def entries(self) -> List[TraceEntry]:
        return list(self._entries)

    def entries_for_step_type(self, step_type: ReasoningStepType) -> List[TraceEntry]:
        return [e for e in self._entries if e.step_type == step_type.value]

    def entries_citing_trace(self, trace_id: str) -> List[TraceEntry]:
        return [e for e in self._entries if trace_id in e.trace_ids]

    def avg_confidence(self) -> float:
        if not self._entries:
            return 0.0
        return round(sum(e.confidence for e in self._entries) / len(self._entries), 2)

    def depth(self) -> int:
        return len(self._entries)

    def all_trace_ids(self) -> List[str]:
        seen = set()
        result = []
        for e in self._entries:
            for tid in e.trace_ids:
                if tid not in seen:
                    seen.add(tid)
                    result.append(tid)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id":        self.chain_id,
            "decision_id":     self.decision_id,
            "final_conclusion": self.final_conclusion,
            "depth":           self.depth(),
            "avg_confidence":  self.avg_confidence(),
            "total_trace_ids": len(self.all_trace_ids()),
            "entries":         [e.to_dict() for e in self._entries],
        }
