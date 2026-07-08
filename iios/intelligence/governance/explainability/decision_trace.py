"""
iios/intelligence/governance/explainability/decision_trace.py
=============================================================
DecisionTraceRecord — captures the governance approval/rejection decision.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..quality_constants import ApprovalStatus, QualityLevel


@dataclass
class DecisionFactor:
    """A single factor that influenced the governance decision."""

    name:        str
    value:       Any
    weight:      float         = 1.0
    contribution: float        = 0.0   # positive = towards approval

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":         self.name,
            "value":        str(self.value),
            "weight":       round(self.weight, 4),
            "contribution": round(self.contribution, 4),
        }


@dataclass
class DecisionTraceRecord:
    """
    Full audit trail of how a governance approval decision was reached.
    """

    trace_id:     str                   = field(default_factory=lambda: str(uuid.uuid4()))
    record_id:    str                   = ""
    product_id:   str                   = ""
    decision:     ApprovalStatus        = ApprovalStatus.PENDING
    quality_score: float                = 0.0
    quality_level: QualityLevel         = QualityLevel.POOR
    factors:      list[DecisionFactor]  = field(default_factory=list)
    rationale:    str                   = ""
    rules_applied: list[str]            = field(default_factory=list)
    overridden:   bool                  = False
    override_reason: str                = ""
    created_at:   float                 = field(default_factory=time.time)

    def add_factor(
        self,
        name:         str,
        value:        Any,
        weight:       float = 1.0,
        contribution: float = 0.0,
    ) -> None:
        self.factors.append(DecisionFactor(
            name=name, value=value, weight=weight, contribution=contribution
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id":       self.trace_id,
            "record_id":      self.record_id,
            "product_id":     self.product_id,
            "decision":       self.decision.value,
            "quality_score":  round(self.quality_score, 4),
            "quality_level":  self.quality_level.value,
            "factors":        [f.to_dict() for f in self.factors],
            "rationale":      self.rationale,
            "rules_applied":  list(self.rules_applied),
            "overridden":     self.overridden,
            "override_reason": self.override_reason,
            "created_at":     self.created_at,
        }
