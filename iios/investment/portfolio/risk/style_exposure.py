"""iios/investment/portfolio/risk/style_exposure.py

Investment style exposure: growth vs. value, defensive vs. cyclical,
domestic vs. international, large vs. small cap proxies.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    bucket_weights, weighted_average, RiskPosition,
)


# Sector → style mapping
DEFENSIVE_SECTORS  = frozenset({"consumer_staples", "utilities", "healthcare", "pharma"})
CYCLICAL_SECTORS   = frozenset({"auto", "materials", "industrials", "consumer_discretionary"})
GROWTH_SECTORS     = frozenset({"technology", "it_services", "software", "biotech"})
VALUE_SECTORS      = frozenset({"finance", "banking", "energy", "telecom"})


@dataclass(frozen=True)
class StyleExposureResult:
    """Investment style tilts and exposures."""

    result_id:            str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str   = ""

    # Style scores [0, 1]
    growth_score:         float = 0.0
    value_score:          float = 0.0
    quality_score:        float = 0.0
    defensive_score:      float = 0.0
    cyclical_score:       float = 0.0

    # Tilts: positive = tilted toward first style
    growth_vs_value:      float = 0.0   # positive = growth, negative = value
    defensive_vs_cyclical:float = 0.0   # positive = defensive
    domestic_vs_intl:     float = 0.0   # positive = domestic
    large_vs_small:       float = 0.0   # positive = large cap (proxy)

    # Dominant style
    dominant_style:       str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "growth_score":          round(self.growth_score, 4),
            "value_score":           round(self.value_score, 4),
            "quality_score":         round(self.quality_score, 4),
            "defensive_score":       round(self.defensive_score, 4),
            "cyclical_score":        round(self.cyclical_score, 4),
            "growth_vs_value":       round(self.growth_vs_value, 4),
            "defensive_vs_cyclical": round(self.defensive_vs_cyclical, 4),
            "domestic_vs_intl":      round(self.domestic_vs_intl, 4),
            "large_vs_small":        round(self.large_vs_small, 4),
            "dominant_style":        self.dominant_style,
        }


def analyze_style_exposure(
    positions:         List[RiskPosition],
    portfolio_id:      str = "",
    domestic_country:  str = "IN",
) -> StyleExposureResult:
    if not positions:
        return StyleExposureResult(portfolio_id=portfolio_id, dominant_style="unknown")

    # Sector-based style scores
    sector_w = bucket_weights(positions, "sector")
    growth_s   = sum(w for s, w in sector_w.items() if s.lower() in GROWTH_SECTORS)
    value_s    = sum(w for s, w in sector_w.items() if s.lower() in VALUE_SECTORS)
    defensive_s= sum(w for s, w in sector_w.items() if s.lower() in DEFENSIVE_SECTORS)
    cyclical_s = sum(w for s, w in sector_w.items() if s.lower() in CYCLICAL_SECTORS)

    # Quality score from conviction
    quality_s  = weighted_average(positions, "conviction")

    # Domestic vs international
    dom_w   = sum(p.weight for p in positions if p.country == domestic_country)
    intl_w  = 1.0 - dom_w

    # Large vs small cap proxy: more positions + lower risk_score → large cap
    n = len(positions)
    large_cap_proxy = min(1.0, n / 15.0) * (1.0 - weighted_average(positions, "risk_score"))

    tilts = {
        "growth_vs_value":        growth_s - value_s,
        "defensive_vs_cyclical":  defensive_s - cyclical_s,
        "domestic_vs_intl":       dom_w - intl_w,
        "large_vs_small":         large_cap_proxy - 0.5,
    }

    scores = {
        "growth":    growth_s,
        "value":     value_s,
        "quality":   quality_s,
        "defensive": defensive_s,
        "cyclical":  cyclical_s,
    }
    dominant = max(scores, key=scores.__getitem__)

    return StyleExposureResult(
        portfolio_id          = portfolio_id,
        growth_score          = round(growth_s, 4),
        value_score           = round(value_s, 4),
        quality_score         = round(quality_s, 4),
        defensive_score       = round(defensive_s, 4),
        cyclical_score        = round(cyclical_s, 4),
        growth_vs_value       = round(tilts["growth_vs_value"], 4),
        defensive_vs_cyclical = round(tilts["defensive_vs_cyclical"], 4),
        domestic_vs_intl      = round(tilts["domestic_vs_intl"], 4),
        large_vs_small        = round(tilts["large_vs_small"], 4),
        dominant_style        = dominant,
    )
