"""iios/investment/portfolio/risk/portfolio_exposure.py

Comprehensive portfolio exposure report combining asset, factor, style, and
statistical exposure analyses.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from iios.investment.portfolio.risk.asset_exposure import (
    AssetExposureResult, analyze_asset_exposure,
)
from iios.investment.portfolio.risk.exposure_statistics import (
    ExposureStatistics, compute_exposure_statistics,
)
from iios.investment.portfolio.risk.factor_exposure import (
    FactorExposureResult, analyze_factor_exposure,
)
from iios.investment.portfolio.risk.risk_types import (
    bucket_weights, RiskPosition,
)
from iios.investment.portfolio.risk.style_exposure import (
    StyleExposureResult, analyze_style_exposure,
)


@dataclass(frozen=True)
class PortfolioExposureReport:
    """All-in-one portfolio exposure report across every dimension."""

    report_id:    str                 = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str                 = ""
    plan_id:      str                 = ""
    n_positions:  int                 = 0

    asset:        AssetExposureResult = field(default_factory=AssetExposureResult)
    factor:       FactorExposureResult = field(default_factory=FactorExposureResult)
    style:        StyleExposureResult = field(default_factory=StyleExposureResult)
    statistics:   ExposureStatistics  = field(default_factory=ExposureStatistics)

    # Sector and country breakdowns (convenience denormalised copies)
    sector_weights:  Dict[str, float] = field(default_factory=dict)
    country_weights: Dict[str, float] = field(default_factory=dict)

    # Theme exposure: tech-heavy, financial-heavy, etc.
    dominant_theme:  str              = ""
    theme_concentration: float        = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":          self.report_id,
            "portfolio_id":       self.portfolio_id,
            "n_positions":        self.n_positions,
            "asset":              self.asset.to_dict(),
            "factor":             self.factor.to_dict(),
            "style":              self.style.to_dict(),
            "statistics":         self.statistics.to_dict(),
            "sector_weights":     {k: round(v, 4) for k, v in self.sector_weights.items()},
            "country_weights":    {k: round(v, 4) for k, v in self.country_weights.items()},
            "dominant_theme":     self.dominant_theme,
            "theme_concentration": round(self.theme_concentration, 4),
        }


class PortfolioExposureAnalyzer:
    """Orchestrates all exposure sub-analyses into a single PortfolioExposureReport."""

    def __init__(self, domestic_currency: str = "INR", domestic_country: str = "IN") -> None:
        self._domestic_currency = domestic_currency
        self._domestic_country  = domestic_country

    def analyze(
        self,
        positions:    List[RiskPosition],
        portfolio_id: str = "",
        plan_id:      str = "",
    ) -> PortfolioExposureReport:
        if not positions:
            return PortfolioExposureReport(
                portfolio_id=portfolio_id,
                plan_id=plan_id,
            )

        asset_exp  = analyze_asset_exposure(positions, portfolio_id)
        factor_exp = analyze_factor_exposure(positions, portfolio_id)
        style_exp  = analyze_style_exposure(
            positions, portfolio_id, self._domestic_country
        )
        stats      = compute_exposure_statistics(positions, portfolio_id)

        sec_w = bucket_weights(positions, "sector")
        cnt_w = bucket_weights(positions, "country")

        # Dominant theme = top sector + asset class combination
        dominant_theme = (
            f"{asset_exp.dominant_class}/{stats.top_sector}"
            if stats.top_sector else asset_exp.dominant_class
        )

        return PortfolioExposureReport(
            portfolio_id      = portfolio_id,
            plan_id           = plan_id,
            n_positions       = len(positions),
            asset             = asset_exp,
            factor            = factor_exp,
            style             = style_exp,
            statistics        = stats,
            sector_weights    = {k: round(v, 4) for k, v in sec_w.items()},
            country_weights   = {k: round(v, 4) for k, v in cnt_w.items()},
            dominant_theme    = dominant_theme,
            theme_concentration = round(stats.sector_hhi, 4),
        )
