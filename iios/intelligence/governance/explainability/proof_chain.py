"""
iios/intelligence/governance/explainability/proof_chain.py
===========================================================
GovernanceProofChain — verifiable logical chain backing a quality decision.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GovernanceProofStep:
    """One step in a governance proof chain."""

    step_id:    str            = field(default_factory=lambda: str(uuid.uuid4()))
    order:      int            = 0
    premise:    str            = ""
    conclusion: str            = ""
    rule:       str            = ""
    confidence: float          = 1.0
    valid:      bool           = True
    metadata:   dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id":    self.step_id,
            "order":      self.order,
            "premise":    self.premise,
            "conclusion": self.conclusion,
            "rule":       self.rule,
            "confidence": round(self.confidence, 4),
            "valid":      self.valid,
        }


@dataclass
class GovernanceProofChain:
    """
    Ordered sequence of logical steps that justify a governance decision.
    """

    chain_id:    str                          = field(default_factory=lambda: str(uuid.uuid4()))
    record_id:   str                          = ""
    product_id:  str                          = ""
    steps:       list[GovernanceProofStep]    = field(default_factory=list)
    conclusion:  str                          = ""
    is_valid:    bool                         = True
    created_at:  float                        = field(default_factory=time.time)

    def add_step(
        self,
        premise:    str,
        conclusion: str,
        rule:       str   = "",
        confidence: float = 1.0,
        valid:      bool  = True,
    ) -> GovernanceProofStep:
        step = GovernanceProofStep(
            order      = len(self.steps),
            premise    = premise,
            conclusion = conclusion,
            rule       = rule,
            confidence = confidence,
            valid      = valid,
        )
        self.steps.append(step)
        # Chain is invalid if any step is invalid
        if not valid:
            self.is_valid = False
        return step

    def cumulative_confidence(self) -> float:
        """Product of all step confidences."""
        if not self.steps:
            return 0.0
        conf = 1.0
        for s in self.steps:
            conf *= s.confidence
        return conf

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id":               self.chain_id,
            "record_id":              self.record_id,
            "product_id":             self.product_id,
            "steps":                  [s.to_dict() for s in self.steps],
            "conclusion":             self.conclusion,
            "is_valid":               self.is_valid,
            "cumulative_confidence":  round(self.cumulative_confidence(), 4),
            "created_at":             self.created_at,
        }
