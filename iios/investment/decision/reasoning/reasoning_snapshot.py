"""iios/investment/decision/reasoning/reasoning_snapshot.py
ReasoningSnapshot — immutable, versioned, published reasoning output.
Consumed by all downstream Decision Intelligence engines.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.reasoning.argument_engine import ArgumentReport
from iios.investment.decision.reasoning.context_analyzer import ContextProfile
from iios.investment.decision.reasoning.hypothesis_engine import Hypothesis
from iios.investment.decision.reasoning.logic_validator import LogicValidationResult
from iios.investment.decision.reasoning.reasoning_chain import ReasoningChain
from iios.investment.decision.reasoning.reasoning_constants import (
    HypothesisType,
    LogicValidationStatus,
    ReasoningStatus,
)
from iios.investment.decision.reasoning.reasoning_score import ReasoningQualityScore


@dataclass(frozen=True)
class ReasoningSnapshot:
    """
    Canonical, immutable, versioned reasoning output.
    Downstream engines consume ONLY this object.
    No investment scores, no recommendations.
    """
    snapshot_id:          str
    decision_id:          str
    subject_id:           str
    subject_type:         str
    version:              int
    evidence_snapshot_id: str           # which EvidenceSnapshot was used
    reasoning_chain:      ReasoningChain
    hypotheses:           Tuple[Hypothesis, ...]
    argument_reports:     Tuple[ArgumentReport, ...]
    context_profile:      ContextProfile
    logic_result:         LogicValidationResult
    quality_score:        ReasoningQualityScore
    primary_hypothesis:   Optional[Hypothesis]
    status:               ReasoningStatus
    reasoning_duration_ms: float
    created_at:           datetime

    @property
    def is_complete(self) -> bool:
        return self.status == ReasoningStatus.COMPLETE

    @property
    def is_usable(self) -> bool:
        return self.logic_result.status.is_usable

    def hypothesis_by_type(self, hypothesis_type: HypothesisType) -> Optional[Hypothesis]:
        for h in self.hypotheses:
            if h.hypothesis_type == hypothesis_type:
                return h
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":          self.snapshot_id,
            "decision_id":          self.decision_id,
            "subject_id":           self.subject_id,
            "subject_type":         self.subject_type,
            "version":              self.version,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "status":               self.status.value,
            "is_complete":          self.is_complete,
            "is_usable":            self.is_usable,
            "hypothesis_count":     len(self.hypotheses),
            "primary_hypothesis":   self.primary_hypothesis.hypothesis_type.value
                                    if self.primary_hypothesis else None,
            "quality_score":        self.quality_score.to_dict(),
            "logic_result":         self.logic_result.to_dict(),
            "context_profile":      self.context_profile.to_dict(),
            "final_conclusion":     self.reasoning_chain.final_conclusion,
            "step_count":           self.reasoning_chain.step_count,
            "reasoning_duration_ms": round(self.reasoning_duration_ms, 1),
            "created_at":           self.created_at.isoformat(),
        }


def build_reasoning_snapshot(
    decision_id:          str,
    subject_id:           str,
    subject_type:         str,
    evidence_snapshot_id: str,
    chain:                ReasoningChain,
    hypotheses:           Tuple[Hypothesis, ...],
    argument_reports:     Tuple[ArgumentReport, ...],
    context_profile:      ContextProfile,
    logic_result:         LogicValidationResult,
    quality_score:        ReasoningQualityScore,
    primary_hypothesis:   Optional[Hypothesis],
    version:              int,
    reasoning_start:      datetime,
) -> ReasoningSnapshot:
    duration_ms = (datetime.now(timezone.utc) - reasoning_start).total_seconds() * 1000.0
    status = (
        ReasoningStatus.COMPLETE
        if logic_result.status.is_usable
        else ReasoningStatus.FAILED
    )
    return ReasoningSnapshot(
        snapshot_id=str(uuid.uuid4()),
        decision_id=decision_id,
        subject_id=subject_id,
        subject_type=subject_type,
        version=version,
        evidence_snapshot_id=evidence_snapshot_id,
        reasoning_chain=chain,
        hypotheses=hypotheses,
        argument_reports=argument_reports,
        context_profile=context_profile,
        logic_result=logic_result,
        quality_score=quality_score,
        primary_hypothesis=primary_hypothesis,
        status=status,
        reasoning_duration_ms=round(duration_ms, 1),
        created_at=datetime.now(timezone.utc),
    )
