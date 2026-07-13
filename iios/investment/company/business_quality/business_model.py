"""iios/investment/company/business_quality/business_model.py
Business model classification and profiling from financial signals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BusinessModelType(Enum):
    ASSET_LIGHT   = "asset_light"    # Software, SaaS, professional services
    ASSET_HEAVY   = "asset_heavy"    # Infrastructure, utilities, manufacturing
    PLATFORM      = "platform"       # Two-sided marketplaces, aggregators
    SUBSCRIPTION  = "subscription"   # High-recurring revenue
    MARKETPLACE   = "marketplace"    # Transaction-volume-based
    MANUFACTURING = "manufacturing"  # Physical goods
    SERVICES      = "services"       # Fee-for-service, consulting
    FINANCIAL     = "financial"      # Banking, insurance, NBFC
    COMMODITY     = "commodity"      # Undifferentiated goods, cyclical
    CONGLOMERATE  = "conglomerate"   # Diversified multi-sector
    HYBRID        = "hybrid"         # Mixed models
    UNKNOWN       = "unknown"


class RevenueVisibilityLabel(Enum):
    HIGH    = "high"     # >70% recurring / contracted
    MEDIUM  = "medium"   # 30-70% recurring
    LOW     = "low"      # <30% (project / transactional)
    UNKNOWN = "unknown"


class CapexIntensityLabel(Enum):
    LIGHT    = "light"     # <5% of revenue
    MODERATE = "moderate"  # 5-15% of revenue
    HEAVY    = "heavy"     # >15% of revenue
    UNKNOWN  = "unknown"


@dataclass
class BusinessModelProfile:
    """
    Characterisation of a company's business model inferred from financial signals.
    All fields are optional to support partial data scenarios.
    """

    # Classification
    model_type:       BusinessModelType      = BusinessModelType.UNKNOWN
    model_confidence: float                  = 0.0   # 0-1

    # Revenue structure
    gross_margin_level:  Optional[float]      = None   # current gross margin %
    avg_gross_margin:    Optional[float]      = None
    revenue_visibility:  RevenueVisibilityLabel = RevenueVisibilityLabel.UNKNOWN
    is_recurring_dominant: bool               = False

    # Capital intensity
    capex_intensity:    CapexIntensityLabel   = CapexIntensityLabel.UNKNOWN
    capex_pct_revenue:  Optional[float]       = None
    avg_capex_pct:      Optional[float]       = None
    is_asset_light:     bool                  = False

    # Operating leverage (fixed vs variable cost)
    operating_leverage_score:   float = 50.0   # 0-100; high = fixed-cost dominant
    is_high_operating_leverage: bool  = False

    # Complexity / innovation
    sga_pct:       Optional[float] = None   # Selling & admin intensity
    rd_pct:        Optional[float] = None   # R&D intensity
    is_rd_intensive: bool          = False

    # Asset efficiency
    asset_turnover:     Optional[float] = None
    avg_asset_turnover: Optional[float] = None

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_type":                self.model_type.value,
            "model_confidence":          round(self.model_confidence, 2),
            "gross_margin_level":        self.gross_margin_level,
            "avg_gross_margin":          self.avg_gross_margin,
            "revenue_visibility":        self.revenue_visibility.value,
            "is_recurring_dominant":     self.is_recurring_dominant,
            "capex_intensity":           self.capex_intensity.value,
            "capex_pct_revenue":         self.capex_pct_revenue,
            "is_asset_light":            self.is_asset_light,
            "operating_leverage_score":  round(self.operating_leverage_score, 1),
            "is_high_operating_leverage": self.is_high_operating_leverage,
            "asset_turnover":            self.asset_turnover,
            "rd_pct":                    self.rd_pct,
            "is_rd_intensive":           self.is_rd_intensive,
            "flags":                     self.flags,
        }
