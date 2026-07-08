"""
iios/decisions/models/decision_option.py
=========================================
DecisionOption — a concrete, typed choice that can be selected.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..decision_constants import DecisionType


@dataclass
class DecisionOption:
    """
    A single possible action the Decision Engine can take.

    Attributes
    ----------
    option_id   : Unique identifier.
    name        : Human-readable label.
    option_type : The kind of action (ACCEPT, REJECT, …).
    description : Verbose explanation of this option.
    confidence  : Estimated likelihood this is correct [0, 1].
    risk_score  : Associated risk level [0, 1] (higher = riskier).
    evidence    : Supporting evidence items (free-form dicts).
    constraints : Any constraints that apply to this option.
    metadata    : Caller-supplied extras.
    created_at  : Unix creation timestamp.
    """

    option_id:   str              = field(default_factory=lambda: str(uuid.uuid4()))
    name:        str              = ""
    option_type: DecisionType     = DecisionType.GENERIC
    description: str              = ""
    confidence:  float            = 0.5
    risk_score:  float            = 0.5
    evidence:    list[dict[str, Any]] = field(default_factory=list)
    constraints: dict[str, Any]   = field(default_factory=dict)
    metadata:    dict[str, Any]   = field(default_factory=dict)
    created_at:  float            = field(default_factory=time.time)

    def add_evidence(self, evidence_item: dict[str, Any]) -> None:
        self.evidence.append(evidence_item)

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_id":   self.option_id,
            "name":        self.name,
            "option_type": self.option_type.value,
            "description": self.description,
            "confidence":  round(self.confidence, 4),
            "risk_score":  round(self.risk_score, 4),
            "evidence":    list(self.evidence),
            "constraints": dict(self.constraints),
            "metadata":    dict(self.metadata),
            "created_at":  self.created_at,
        }
