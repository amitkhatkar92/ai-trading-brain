"""iios/investment/company/opportunity/investment_thesis.py
InvestmentThesis dataclass and its sub-components.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from iios.investment.company.opportunity.opportunity_profile import (
    ConfidenceLevel, OpportunityCategory, OpportunityLifecycle,
)


@dataclass
class ThesisEvidence:
    """A single piece of supporting or contradicting evidence."""
    factor:      str            # e.g. "ROIC", "Revenue CAGR", "Debt/Equity"
    value:       str            # human-readable value string
    signal:      str            # "positive" | "negative" | "neutral"
    importance:  str = "medium" # "high" | "medium" | "low"
    source:      str = "analysis"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor":     self.factor,
            "value":      self.value,
            "signal":     self.signal,
            "importance": self.importance,
            "source":     self.source,
        }


@dataclass
class InvestmentThesis:
    """
    Explainable investment thesis for a company opportunity.

    NOT a buy/sell/hold recommendation.
    Describes WHY a company appears interesting based on intelligence signals.
    """
    ticker:   str
    category: OpportunityCategory
    lifecycle: OpportunityLifecycle

    headline:  str = ""    # One-line opportunity summary
    narrative: str = ""    # 2-3 paragraph narrative description

    strengths:    List[str] = field(default_factory=list)  # top positive signals
    weaknesses:   List[str] = field(default_factory=list)  # notable negatives
    key_risks:    List[str] = field(default_factory=list)  # risk factors
    key_catalysts: List[str] = field(default_factory=list) # potential triggers
    monitoring_points: List[str] = field(default_factory=list)  # what to track

    supporting_evidence: List[ThesisEvidence] = field(default_factory=list)
    risk_evidence:       List[ThesisEvidence] = field(default_factory=list)

    confidence_explanation: str = ""
    confidence_level: ConfidenceLevel = ConfidenceLevel.MODERATE

    generated_at: Optional[datetime] = None

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def positive_evidence(self) -> List[ThesisEvidence]:
        return [e for e in self.supporting_evidence if e.signal == "positive"]

    @property
    def negative_evidence(self) -> List[ThesisEvidence]:
        return [e for e in self.supporting_evidence if e.signal == "negative"] + self.risk_evidence

    @property
    def has_strong_thesis(self) -> bool:
        return (
            len(self.strengths) >= 3
            and len(self.key_risks) <= len(self.strengths)
            and self.confidence_level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
        )

    @property
    def risk_reward_balance(self) -> str:
        """Qualitative risk/reward balance — NOT a recommendation."""
        n_str = len(self.strengths)
        n_risk = len(self.key_risks)
        if n_str >= 4 and n_risk <= 2:
            return "favorable"
        if n_str >= 2 and n_risk <= n_str:
            return "balanced"
        if n_risk > n_str:
            return "elevated_risk"
        return "neutral"

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":           self.ticker,
            "category":         self.category.value,
            "lifecycle":        self.lifecycle.value,
            "headline":         self.headline,
            "narrative":        self.narrative,
            "strengths":        self.strengths,
            "weaknesses":       self.weaknesses,
            "key_risks":        self.key_risks,
            "key_catalysts":    self.key_catalysts,
            "monitoring_points": self.monitoring_points,
            "supporting_evidence": [e.to_dict() for e in self.supporting_evidence],
            "risk_evidence":    [e.to_dict() for e in self.risk_evidence],
            "confidence_explanation": self.confidence_explanation,
            "confidence_level": self.confidence_level.value,
            "risk_reward_balance": self.risk_reward_balance,
            "has_strong_thesis": self.has_strong_thesis,
            "generated_at":     self.generated_at.isoformat() if self.generated_at else None,
        }
