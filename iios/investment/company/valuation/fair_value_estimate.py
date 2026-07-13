"""iios/investment/company/valuation/fair_value_estimate.py
FairValueEstimate — blended per-share fair value with confidence interval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.valuation.valuation_model import (
    ValuationModelType, ValuationBand,
)


@dataclass
class ValuationRange:
    """Bear-to-bull fair value range per share."""
    low:    float   # pessimistic fair value (per share)
    mid:    float   # base fair value (per share)
    high:   float   # optimistic fair value (per share)

    def spread_pct(self) -> float:
        """Width of range as fraction of mid."""
        return (self.high - self.low) / self.mid if self.mid else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "low":       round(self.low, 2),
            "mid":       round(self.mid, 2),
            "high":      round(self.high, 2),
            "spread_pct": round(self.spread_pct() * 100, 1),
        }


@dataclass
class FairValueEstimate:
    """
    Blended per-share fair value from multiple valuation models.
    This is an ESTIMATE — not a price target or investment recommendation.
    """

    # Blended point estimate
    intrinsic_value:  float   # per share
    value_range:      ValuationRange = field(default_factory=lambda: ValuationRange(0, 0, 0))

    # Blend metadata
    method:           str          = "blended"   # "blended" | "dcf" | "relative" etc.
    model_weights_used: Dict[str, float] = field(default_factory=dict)
    contributing_models: List[str]  = field(default_factory=list)

    # Confidence in the estimate
    confidence:       float = 0.0    # 0-1

    # Currency
    currency:         str = "INR"

    explanation:      List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intrinsic_value":   round(self.intrinsic_value, 2),
            "value_range":       self.value_range.to_dict(),
            "method":            self.method,
            "model_weights_used": self.model_weights_used,
            "contributing_models": self.contributing_models,
            "confidence":        round(self.confidence, 3),
            "currency":          self.currency,
            "explanation":       self.explanation,
        }


@dataclass
class MarginOfSafetyProfile:
    """
    Premium / discount of market price relative to fair value estimate.
    Positive MoS = market price below fair value (potential upside).
    Negative MoS = market price above fair value (premium).
    """

    fair_value:     float
    market_price:   float

    margin_of_safety_pct: float   # (FV - MP) / FV * 100
    premium_discount_pct: float   # (MP - FV) / FV * 100 (inverse of MoS)

    upside_to_fair_value: float   # % gain if price reaches FV
    downside_to_fair_value: float  # % loss if price drops to FV (negative)

    band:           ValuationBand = ValuationBand.UNKNOWN
    is_undervalued: bool = False
    is_overvalued:  bool = False

    explanation:    List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fair_value":             round(self.fair_value, 2),
            "market_price":           round(self.market_price, 2),
            "margin_of_safety_pct":   round(self.margin_of_safety_pct, 1),
            "premium_discount_pct":   round(self.premium_discount_pct, 1),
            "upside_to_fair_value":   round(self.upside_to_fair_value, 1),
            "downside_to_fair_value": round(self.downside_to_fair_value, 1),
            "band":                   self.band.value,
            "is_undervalued":         self.is_undervalued,
            "is_overvalued":          self.is_overvalued,
            "explanation":            self.explanation,
        }


def classify_margin_of_safety(mos_pct: float) -> ValuationBand:
    """Classify valuation band from margin of safety percentage."""
    if mos_pct >= 40.0:
        return ValuationBand.DEEPLY_UNDERVALUED
    if mos_pct >= 15.0:
        return ValuationBand.UNDERVALUED
    if mos_pct >= -15.0:
        return ValuationBand.FAIR_VALUE
    if mos_pct >= -40.0:
        return ValuationBand.OVERVALUED
    return ValuationBand.SIGNIFICANTLY_OVERVALUED
