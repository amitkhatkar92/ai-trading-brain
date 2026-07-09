"""iios/investment/portfolio/analytics/diversification_analyzer.py
HHI-based diversification scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.core.portfolio import Portfolio


@dataclass
class DiversificationAnalysis:
    portfolio_id:         str   = ""
    hhi:                  float = 0.0     # Herfindahl-Hirschman Index (0–1)
    diversification_score: float = 50.0  # 0–100; higher = more diversified
    effective_positions:  float = 0.0    # 1 / HHI (inverse HHI)
    sector_count:         int   = 0
    country_count:        int   = 0
    asset_class_count:    int   = 0
    metadata:             dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id":          self.portfolio_id,
            "hhi":                   self.hhi,
            "diversification_score": self.diversification_score,
            "effective_positions":   self.effective_positions,
            "sector_count":          self.sector_count,
            "country_count":         self.country_count,
            "asset_class_count":     self.asset_class_count,
            "metadata":              self.metadata,
        }


class DiversificationAnalyzer:
    """Computes HHI-based diversification from position weights."""

    def analyze(self, portfolio: Portfolio) -> DiversificationAnalysis:
        positions = list(portfolio.positions.values())
        nav       = portfolio.total_nav

        if not positions or nav <= 0:
            return DiversificationAnalysis(portfolio_id=portfolio.portfolio_id)

        weights = [p.market_value / nav for p in positions]
        hhi     = sum(w * w for w in weights)
        div_score = max(0.0, min(100.0, (1.0 - hhi) * 100.0))
        eff_pos   = 1.0 / hhi if hhi > 0 else float("inf")

        sectors      = {p.sector   or "unknown" for p in positions}
        countries    = {p.country  or "unknown" for p in positions}
        asset_classes = {p.asset_class.value     for p in positions}

        return DiversificationAnalysis(
            portfolio_id         = portfolio.portfolio_id,
            hhi                  = round(hhi, 6),
            diversification_score = round(div_score, 2),
            effective_positions  = round(min(eff_pos, 9999.0), 2),
            sector_count         = len(sectors),
            country_count        = len(countries),
            asset_class_count    = len(asset_classes),
            metadata             = {"n_positions": len(positions)},
        )
