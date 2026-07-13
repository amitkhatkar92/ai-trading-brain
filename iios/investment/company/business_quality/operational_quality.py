"""iios/investment/company/business_quality/operational_quality.py
Operational quality and capital efficiency profiles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CapitalEfficiencyProfile:
    """How efficiently the business deploys capital to generate returns."""

    # Returns on capital
    current_roic:   Optional[float] = None
    avg_roic:       Optional[float] = None
    current_roe:    Optional[float] = None
    avg_roe:        Optional[float] = None
    current_roa:    Optional[float] = None
    avg_roa:        Optional[float] = None

    # Asset utilisation
    asset_turnover:         Optional[float] = None
    avg_asset_turnover:     Optional[float] = None
    inventory_turnover:     Optional[float] = None
    receivables_days:       Optional[float] = None
    payables_days:          Optional[float] = None
    cash_conversion_cycle:  Optional[float] = None   # DSO + DIO - DPO

    # FCF conversion
    fcf_margin:             Optional[float] = None
    avg_fcf_margin:         Optional[float] = None
    ocf_to_ni:              Optional[float] = None
    capex_pct:              Optional[float] = None

    # Scores
    capital_efficiency_score: float = 0.0    # 0-100
    asset_utilisation_score:  float = 0.0

    is_capital_efficient: bool = False

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_roic":            self.current_roic,
            "avg_roic":                self.avg_roic,
            "asset_turnover":          self.asset_turnover,
            "inventory_turnover":      self.inventory_turnover,
            "receivables_days":        self.receivables_days,
            "cash_conversion_cycle":   self.cash_conversion_cycle,
            "fcf_margin":              self.fcf_margin,
            "capital_efficiency_score": round(self.capital_efficiency_score, 1),
            "asset_utilisation_score": round(self.asset_utilisation_score, 1),
            "is_capital_efficient":    self.is_capital_efficient,
            "flags":                   self.flags,
        }


@dataclass
class ExecutionQualityProfile:
    """Consistency and reliability of operational execution."""

    # Revenue execution
    revenue_growth_consistency: Optional[float] = None   # 1 - CV of revenue growth
    margin_consistency:         Optional[float] = None   # 1 - CV of margins

    # Expense management
    sga_trend:   Optional[str] = None   # "improving" | "stable" | "deteriorating"
    cost_discipline_score: float = 50.0  # 0-100

    # Working capital management
    working_capital_trend: Optional[str] = None
    wc_efficiency_score:   float = 50.0

    # Overall execution score
    execution_score: float = 0.0   # 0-100
    consistency_score: float = 0.0

    periods_analyzed: int = 0
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "revenue_growth_consistency": self.revenue_growth_consistency,
            "margin_consistency":         self.margin_consistency,
            "cost_discipline_score":      round(self.cost_discipline_score, 1),
            "execution_score":            round(self.execution_score, 1),
            "consistency_score":          round(self.consistency_score, 1),
            "periods_analyzed":           self.periods_analyzed,
            "flags":                      self.flags,
        }


@dataclass
class OperationalQualityProfile:
    """Composite operational quality: capital efficiency + execution."""

    capital_efficiency: CapitalEfficiencyProfile = field(
        default_factory=CapitalEfficiencyProfile
    )
    execution_quality: ExecutionQualityProfile = field(
        default_factory=ExecutionQualityProfile
    )

    # Composite
    operational_quality_score: float = 0.0  # 0-100
    is_operationally_excellent: bool = False

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capital_efficiency":         self.capital_efficiency.to_dict(),
            "execution_quality":          self.execution_quality.to_dict(),
            "operational_quality_score":  round(self.operational_quality_score, 1),
            "is_operationally_excellent": self.is_operationally_excellent,
            "flags":                      self.flags,
        }
