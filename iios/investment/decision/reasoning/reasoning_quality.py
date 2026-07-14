"""iios/investment/decision/reasoning/reasoning_quality.py
ReasoningQuality — 5-dimension quality scorer for reasoning snapshots.
"""
from __future__ import annotations

from typing import Any, Dict, List

from iios.investment.decision.reasoning.reasoning_chain import ReasoningChain
from iios.investment.decision.reasoning.reasoning_constants import (
    ReasoningQualityDimension,
    ReasoningStepType,
)
from iios.investment.decision.reasoning.logic_validator import LogicValidationResult
from iios.investment.decision.reasoning.reasoning_constants import LogicValidationStatus
from iios.investment.decision.reasoning.reasoning_score import ReasoningQualityScore, compute_reasoning_score


_EXPECTED_STEPS = set(ReasoningStepType)
_MAX_CHAIN_DEPTH = 10


class ReasoningQuality:
    """
    5-dimension quality scorer:
      1. Completeness   (0.25) — fraction of expected step types present
      2. Consistency    (0.25) — based on logic validation status
      3. Transparency   (0.20) — fraction of steps with evidence trace_ids
      4. Evidence Coverage (0.20) — fraction of evidence items cited in chain
      5. Chain Depth    (0.10) — normalised number of steps
    """

    def score(
        self,
        chain:              ReasoningChain,
        logic_result:       LogicValidationResult,
        total_evidence_items: int,
    ) -> ReasoningQualityScore:
        step_types = {s.step_type for s in chain.steps}
        completeness = len(step_types) / len(_EXPECTED_STEPS) * 100.0

        consistency_map = {
            LogicValidationStatus.VALID:           100.0,
            LogicValidationStatus.VALID_WITH_GAPS:  70.0,
            LogicValidationStatus.CONTRADICTORY:    20.0,
            LogicValidationStatus.INSUFFICIENT:      0.0,
        }
        consistency = consistency_map.get(logic_result.status, 50.0)

        steps_with_traces = sum(1 for s in chain.steps if s.evidence_trace_ids)
        transparency = steps_with_traces / chain.step_count * 100.0 if chain.step_count else 0.0

        evidence_coverage = (
            min(100.0, chain.total_evidence_refs / total_evidence_items * 100.0)
            if total_evidence_items else 0.0
        )

        depth_score = min(100.0, chain.step_count / _MAX_CHAIN_DEPTH * 100.0)

        return compute_reasoning_score(
            completeness=completeness,
            consistency=consistency,
            transparency=transparency,
            evidence_coverage=evidence_coverage,
            chain_depth=depth_score,
        )
