"""iios/investment/portfolio/diversification/sector_concentration.py

Aggregated sector, industry, and market-cap style concentration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.diversification.concentration_analysis import (
    ExposureConcentrationResult,
    analyze_exposure_concentration,
)
from iios.investment.portfolio.diversification.diversification_types import (
    ConcentrationLevel,
    PositionData,
)


@dataclass(frozen=True)
class SectorConcentrationReport:
    """Full sector/industry/asset-class concentration summary."""

    sector:      ExposureConcentrationResult = field(default_factory=lambda: ExposureConcentrationResult(dimension="sector"))
    industry:    ExposureConcentrationResult = field(default_factory=lambda: ExposureConcentrationResult(dimension="industry"))
    asset_class: ExposureConcentrationResult = field(default_factory=lambda: ExposureConcentrationResult(dimension="asset_class"))
    country:     ExposureConcentrationResult = field(default_factory=lambda: ExposureConcentrationResult(dimension="country"))
    currency:    ExposureConcentrationResult = field(default_factory=lambda: ExposureConcentrationResult(dimension="currency"))

    @property
    def worst_sector_weight(self) -> float:
        return self.sector.top1_weight

    @property
    def sector_count(self) -> int:
        return self.sector.n_buckets

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector":      self.sector.to_dict(),
            "industry":    self.industry.to_dict(),
            "asset_class": self.asset_class.to_dict(),
            "country":     self.country.to_dict(),
            "currency":    self.currency.to_dict(),
        }


def analyze_sector_concentration(positions: List[PositionData]) -> SectorConcentrationReport:
    return SectorConcentrationReport(
        sector      = analyze_exposure_concentration(positions, "sector"),
        industry    = analyze_exposure_concentration(positions, "industry"),
        asset_class = analyze_exposure_concentration(positions, "asset_class"),
        country     = analyze_exposure_concentration(positions, "country"),
        currency    = analyze_exposure_concentration(positions, "currency"),
    )
