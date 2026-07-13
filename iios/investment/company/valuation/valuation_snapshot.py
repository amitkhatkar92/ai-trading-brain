"""iios/investment/company/valuation/valuation_snapshot.py
Primary output of the Valuation Intelligence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.company.valuation.valuation_model import (
    ValuationResult, ValuationBand, ValuationStatus,
)
from iios.investment.company.valuation.fair_value_estimate import (
    FairValueEstimate, MarginOfSafetyProfile, ValuationRange,
)


@dataclass
class ValuationIntelligenceScore:
    """
    Overall valuation intelligence quality score (0-100).
    Measures the quality and confidence of the valuation estimate —
    NOT the attractiveness of the investment.
    """
    overall_score:       float = 0.0

    # Dimension scores
    model_coverage_score: float = 0.0   # How many models produced valid results
    data_quality_score:   float = 0.0   # Quality of input financial data
    assumption_score:     float = 0.0   # How calibrated the assumptions are
    convergence_score:    float = 0.0   # Agreement between models

    label:               str   = "insufficient"   # "high" | "medium" | "low" | "insufficient"
    explanation:         List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score":        round(self.overall_score, 1),
            "label":                self.label,
            "model_coverage_score": round(self.model_coverage_score, 1),
            "data_quality_score":   round(self.data_quality_score, 1),
            "assumption_score":     round(self.assumption_score, 1),
            "convergence_score":    round(self.convergence_score, 1),
            "explanation":          self.explanation,
        }


@dataclass
class ScenarioResult:
    """Result of a single valuation scenario (bull / base / bear)."""
    scenario:        str    # "bull" | "base" | "bear" | "stress"
    fair_value:      Optional[float] = None   # per share
    mos_pct:         Optional[float] = None   # margin of safety vs market price
    assumptions:     Dict[str, Any]  = field(default_factory=dict)
    explanation:     List[str]       = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario":   self.scenario,
            "fair_value": round(self.fair_value, 2) if self.fair_value else None,
            "mos_pct":    round(self.mos_pct, 1) if self.mos_pct is not None else None,
            "assumptions": self.assumptions,
            "explanation": self.explanation,
        }


@dataclass
class ValuationSnapshot:
    """
    Primary output of the Valuation Intelligence Engine.

    This is the single source of truth for valuation analysis across IIOS.
    All downstream engines must consume this object.
    NOT a buy/sell/hold recommendation.
    """
    ticker:       str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Market data (provided by caller)
    market_price:       Optional[float] = None   # per share
    shares_outstanding: Optional[float] = None   # total shares
    market_cap:         Optional[float] = None   # market_price * shares_outstanding

    # Individual model results
    dcf_result:       Optional[ValuationResult] = None
    ddm_result:       Optional[ValuationResult] = None
    rim_result:       Optional[ValuationResult] = None
    asset_result:     Optional[ValuationResult] = None
    relative_result:  Optional[ValuationResult] = None

    # Blended fair value
    fair_value:       Optional[FairValueEstimate] = None

    # Margin of safety (None if no market price)
    mos:              Optional[MarginOfSafetyProfile] = None

    # Scenarios
    bull_case:        Optional[ScenarioResult] = None
    base_case:        Optional[ScenarioResult] = None
    bear_case:        Optional[ScenarioResult] = None

    # Intelligence quality
    valuation_score:  ValuationIntelligenceScore = field(
        default_factory=ValuationIntelligenceScore
    )

    # Plugin results
    plugin_results:   Dict[str, ValuationResult] = field(default_factory=dict)

    # Assumptions used
    assumptions_summary: Dict[str, Any] = field(default_factory=dict)

    @property
    def intrinsic_value(self) -> Optional[float]:
        return self.fair_value.intrinsic_value if self.fair_value else None

    @property
    def margin_of_safety_pct(self) -> Optional[float]:
        return self.mos.margin_of_safety_pct if self.mos else None

    @property
    def valuation_band(self) -> ValuationBand:
        return self.mos.band if self.mos else ValuationBand.UNKNOWN

    @property
    def is_undervalued(self) -> Optional[bool]:
        return self.mos.is_undervalued if self.mos else None

    @property
    def is_overvalued(self) -> Optional[bool]:
        return self.mos.is_overvalued if self.mos else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":              self.ticker,
            "generated_at":        self.generated_at.isoformat(),
            "market_price":        self.market_price,
            "shares_outstanding":  self.shares_outstanding,
            "market_cap":          self.market_cap,
            "intrinsic_value":     self.intrinsic_value,
            "valuation_band":      self.valuation_band.value,
            "fair_value":          self.fair_value.to_dict() if self.fair_value else None,
            "mos":                 self.mos.to_dict() if self.mos else None,
            "dcf_result":          self.dcf_result.to_dict() if self.dcf_result else None,
            "ddm_result":          self.ddm_result.to_dict() if self.ddm_result else None,
            "rim_result":          self.rim_result.to_dict() if self.rim_result else None,
            "asset_result":        self.asset_result.to_dict() if self.asset_result else None,
            "relative_result":     self.relative_result.to_dict() if self.relative_result else None,
            "bull_case":           self.bull_case.to_dict() if self.bull_case else None,
            "base_case":           self.base_case.to_dict() if self.base_case else None,
            "bear_case":           self.bear_case.to_dict() if self.bear_case else None,
            "valuation_score":     self.valuation_score.to_dict(),
            "assumptions":         self.assumptions_summary,
        }
