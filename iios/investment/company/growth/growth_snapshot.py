"""iios/investment/company/growth/growth_snapshot.py
Primary output of the Growth Intelligence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.company.growth.growth_profile import (
    RevenueGrowthProfile, EarningsGrowthProfile, MarginGrowthProfile,
    CashflowGrowthProfile, GrowthDriverProfile, GrowthSustainabilityProfile,
    GrowthForecastProfile, GrowthQuality, GrowthIntelligenceScore,
    GrowthTrend,
)


@dataclass
class GrowthSnapshot:
    """
    Primary output of the Growth Intelligence Engine.
    Authoritative source of company growth intelligence across IIOS.
    NOT a buy/sell/hold recommendation.
    """
    ticker:       str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Revenue growth analysis
    revenue:       RevenueGrowthProfile = field(default_factory=RevenueGrowthProfile)

    # Earnings and EPS growth analysis
    earnings:      EarningsGrowthProfile = field(default_factory=EarningsGrowthProfile)

    # Margin expansion / contraction
    margin:        MarginGrowthProfile = field(default_factory=MarginGrowthProfile)

    # Cashflow growth
    cashflow:      CashflowGrowthProfile = field(default_factory=CashflowGrowthProfile)

    # Growth drivers
    drivers:       GrowthDriverProfile = field(default_factory=GrowthDriverProfile)

    # Sustainability assessment
    sustainability: GrowthSustainabilityProfile = field(default_factory=GrowthSustainabilityProfile)

    # Forward-looking forecast
    forecast:      GrowthForecastProfile = field(default_factory=GrowthForecastProfile)

    # Quality and score
    quality:       GrowthQuality = field(default_factory=GrowthQuality)
    growth_score:  GrowthIntelligenceScore = field(default_factory=GrowthIntelligenceScore)

    # Metadata
    confidence:    float = 0.0
    history_depth: int   = 0   # Periods of financial history used

    # ── Convenience properties ─────────────────────────────────────────────────

    @property
    def overall_growth_score(self) -> float:
        return self.growth_score.overall_score

    @property
    def is_growing(self) -> Optional[bool]:
        """True if the best available revenue or EPS CAGR is positive."""
        rev = self.revenue.cagr.best_available
        eps = self.earnings.eps_cagr.best_available
        candidates = [x for x in [rev, eps] if x is not None]
        if not candidates:
            return None
        return any(c > 0 for c in candidates)

    @property
    def is_accelerating(self) -> bool:
        return (
            self.revenue.trend == GrowthTrend.ACCELERATING
            or self.earnings.trend == GrowthTrend.ACCELERATING
        )

    @property
    def growth_label(self) -> str:
        return self.growth_score.label

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":            self.ticker,
            "generated_at":      self.generated_at.isoformat(),
            "confidence":        round(self.confidence, 2),
            "history_depth":     self.history_depth,
            "is_growing":        self.is_growing,
            "growth_label":      self.growth_label,
            "revenue":           self.revenue.to_dict(),
            "earnings":          self.earnings.to_dict(),
            "margin":            self.margin.to_dict(),
            "cashflow":          self.cashflow.to_dict(),
            "drivers":           self.drivers.to_dict(),
            "sustainability":    self.sustainability.to_dict(),
            "forecast":          self.forecast.to_dict(),
            "quality":           self.quality.to_dict(),
            "growth_score":      self.growth_score.to_dict(),
        }
