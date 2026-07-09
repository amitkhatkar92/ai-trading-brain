"""iios/investment/company/models/company_health.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _label(score: float, invert: bool = False) -> str:
    """Converts a 0–100 score to a human-readable label."""
    effective = (100.0 - score) if invert else score
    if effective >= 75:
        return "GOOD"
    elif effective >= 50:
        return "FAIR"
    else:
        return "POOR"


@dataclass
class CompanyHealth:
    """
    Aggregated health across multiple analytical dimensions.

    Scores are 0–100; higher = healthier.
    ``valuation_score`` represents cheapness (higher = more undervalued).
    """

    overall_score:     float          = 50.0
    financial_score:   float          = 50.0
    governance_score:  float          = 50.0
    growth_score:      float          = 50.0
    quality_score:     float          = 50.0
    valuation_score:   float          = 50.0
    labels:            dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._rebuild_labels()

    def _rebuild_labels(self) -> None:
        self.labels = {
            "overall":    _label(self.overall_score),
            "financial":  _label(self.financial_score),
            "governance": _label(self.governance_score),
            "growth":     _label(self.growth_score),
            "quality":    _label(self.quality_score),
            "valuation":  _label(self.valuation_score),
        }

    @property
    def is_healthy(self) -> bool:
        return self.overall_score >= 60.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score":    self.overall_score,
            "financial_score":  self.financial_score,
            "governance_score": self.governance_score,
            "growth_score":     self.growth_score,
            "quality_score":    self.quality_score,
            "valuation_score":  self.valuation_score,
            "labels":           self.labels,
            "is_healthy":       self.is_healthy,
        }
