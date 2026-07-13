"""iios/investment/company/business_quality/business_resilience.py
Business resilience, cyclicality, and stress tolerance profiles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CyclicalityLabel(Enum):
    DEFENSIVE     = "defensive"      # Revenue almost non-cyclical
    LOW_CYCLICAL  = "low_cyclical"   # Mild demand sensitivity
    MODERATE      = "moderate"       # Normal economic sensitivity
    HIGH_CYCLICAL = "high_cyclical"  # Strong business cycle sensitivity
    UNKNOWN       = "unknown"


class PricingPowerLabel(Enum):
    STRONG   = "strong"    # Can raise prices above inflation
    MODERATE = "moderate"  # Limited price increases
    WEAK     = "weak"      # Price taker / commodity-like
    UNKNOWN  = "unknown"


@dataclass
class CyclicalityProfile:
    """How sensitive the business is to economic cycles."""

    label:              CyclicalityLabel = CyclicalityLabel.UNKNOWN
    cyclicality_score:  float            = 50.0   # 0 = most defensive, 100 = highly cyclical
    revenue_volatility: Optional[float]  = None   # CV of revenue growth
    margin_volatility:  Optional[float]  = None   # stdev of gross margin
    loss_rate:          float            = 0.0    # fraction of periods with losses
    min_revenue_growth: Optional[float]  = None
    min_gross_margin:   Optional[float]  = None

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label":              self.label.value,
            "cyclicality_score":  round(self.cyclicality_score, 1),
            "revenue_volatility": self.revenue_volatility,
            "margin_volatility":  self.margin_volatility,
            "loss_rate":          round(self.loss_rate, 3),
            "min_revenue_growth": self.min_revenue_growth,
            "min_gross_margin":   self.min_gross_margin,
            "flags":              self.flags,
        }


@dataclass
class BusinessRiskProfile:
    """Financial and operational risk signals."""

    # Leverage risk
    debt_to_equity:       Optional[float] = None
    net_debt_to_ebitda:   Optional[float] = None
    interest_coverage:    Optional[float] = None
    is_over_leveraged:    bool            = False

    # Liquidity risk
    current_ratio:        Optional[float] = None
    quick_ratio:          Optional[float] = None
    is_liquidity_stressed: bool           = False

    # Earnings risk
    earnings_quality_score: float = 50.0  # from EarningsSnapshot
    has_high_accruals:      bool  = False

    # Risk score (high = more risky)
    financial_risk_score: float = 50.0   # 0-100; high = high risk
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "debt_to_equity":       self.debt_to_equity,
            "net_debt_to_ebitda":   self.net_debt_to_ebitda,
            "interest_coverage":    self.interest_coverage,
            "is_over_leveraged":    self.is_over_leveraged,
            "current_ratio":        self.current_ratio,
            "financial_risk_score": round(self.financial_risk_score, 1),
            "is_liquidity_stressed": self.is_liquidity_stressed,
            "flags":                self.flags,
        }


@dataclass
class StressResilienceProfile:
    """
    Ability to withstand economic stress: margins in downturns,
    FCF generation, balance sheet strength.
    """

    # Balance sheet buffers
    avg_fcf_margin:      Optional[float] = None
    min_fcf_margin:      Optional[float] = None
    is_fcf_positive_all: bool = False  # FCF positive in all observed periods

    # Margin floor
    min_gross_margin:    Optional[float] = None
    min_ebit_margin:     Optional[float] = None

    # Debt serviceability
    avg_interest_coverage: Optional[float] = None

    # Resilience score (high = more resilient)
    stress_resilience_score: float = 50.0   # 0-100
    is_stress_resilient:     bool  = False

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_fcf_margin":          self.avg_fcf_margin,
            "min_fcf_margin":          self.min_fcf_margin,
            "is_fcf_positive_all":     self.is_fcf_positive_all,
            "min_gross_margin":        self.min_gross_margin,
            "avg_interest_coverage":   self.avg_interest_coverage,
            "stress_resilience_score": round(self.stress_resilience_score, 1),
            "is_stress_resilient":     self.is_stress_resilient,
            "flags":                   self.flags,
        }


@dataclass
class ResilienceProfile:
    """Composite resilience: cyclicality + risk + stress tolerance."""

    cyclicality:      CyclicalityProfile    = field(default_factory=CyclicalityProfile)
    business_risk:    BusinessRiskProfile   = field(default_factory=BusinessRiskProfile)
    stress_resilience: StressResilienceProfile = field(default_factory=StressResilienceProfile)

    # Pricing power
    pricing_power:        PricingPowerLabel = PricingPowerLabel.UNKNOWN
    pricing_power_score:  float             = 50.0

    # Composite resilience score
    resilience_score: float = 0.0    # 0-100; high = more resilient
    is_resilient:     bool  = False

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cyclicality":          self.cyclicality.to_dict(),
            "business_risk":        self.business_risk.to_dict(),
            "stress_resilience":    self.stress_resilience.to_dict(),
            "pricing_power":        self.pricing_power.value,
            "pricing_power_score":  round(self.pricing_power_score, 1),
            "resilience_score":     round(self.resilience_score, 1),
            "is_resilient":         self.is_resilient,
            "flags":                self.flags,
        }
