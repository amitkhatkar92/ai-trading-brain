"""iios/investment/decision/explainability/reasoning_mapper.py
ReasoningMapper — maps ReasoningSnapshot steps to traceability nodes.
"""
from __future__ import annotations

from typing import FrozenSet, List, Tuple

from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.explainability.decision_trace import ReasoningTraceNode


class ReasoningMapper:
    """
    Maps a ReasoningSnapshot's chain steps to ReasoningTraceNodes.
    Also returns the set of evidence keys referenced across all steps.
    """

    def map(
        self, snapshot: ReasoningSnapshot,
    ) -> Tuple[List[ReasoningTraceNode], FrozenSet[str]]:
        """
        Returns (nodes, referenced_evidence_keys).
        """
        chain   = snapshot.reasoning_chain
        steps   = chain.steps if hasattr(chain, "steps") else []
        nodes: List[ReasoningTraceNode] = []
        all_evidence_refs: List[str]    = []

        if not steps:
            # No step-level detail available — produce a single synthetic node
            synthetic = ReasoningTraceNode(
                step_index=0,
                conclusion=chain.final_conclusion,
                confidence=chain.avg_step_confidence,
                evidence_refs=(),
                logic_valid=snapshot.logic_result.consistency_score >= 50.0,
            )
            nodes.append(synthetic)
            return nodes, frozenset()

        for i, step in enumerate(steps):
            # Attempt to extract evidence references from step
            refs: List[str] = []
            if hasattr(step, "evidence_refs"):
                refs = [str(r) for r in step.evidence_refs]
            elif hasattr(step, "evidence_keys"):
                refs = list(step.evidence_keys)

            all_evidence_refs.extend(refs)

            step_conf = getattr(step, "confidence", chain.avg_step_confidence)
            step_conc = getattr(step, "conclusion", getattr(step, "content", str(step)))
            logic_ok  = getattr(step, "is_valid", True)

            nodes.append(ReasoningTraceNode(
                step_index=i,
                conclusion=str(step_conc),
                confidence=float(step_conf),
                evidence_refs=tuple(refs),
                logic_valid=bool(logic_ok),
            ))

        return nodes, frozenset(all_evidence_refs)
