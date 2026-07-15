"""iios/investment/portfolio/risk/concentration_risk.py

Concentration risk analysis from a risk perspective: HHI, top-holding
thresholds, sector/industry clustering.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    HHI_HIGH_RISK, HHI_MODERATE_RISK, RiskLevel,
    bucket_weights, hhi, risk_score_to_level, RiskPosition,
)


@dataclass(frozen=True)
class ConcentrationRiskResult:
    """Concentration risk assessment."""

    result_id:              str       = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:           str       = ""

    n_positions:            int       = 0

    # Position-level HHI
    position_hhi:           float     = 0.0
    top1_weight:            float     = 0.0
    top3_weight:            float     = 0.0
    top5_weight:            float     = 0.0
    top1_symbol:            str       = ""

    # Sector-level HHI
    sector_hhi:             float     = 0.0
    top_sector:             str       = ""
    top_sector_weight:      float     = 0.0

    # Industry-level HHI
    industry_hhi:           float     = 0.0
    top_industry:           str       = ""
    top_industry_weight:    float     = 0.0

    # Country concentration
    country_hhi:            float     = 0.0
    top_country:            str       = ""
    top_country_weight:     float     = 0.0

    # Composite concentration risk score
    concentration_score:    float     = 0.0   # 0-1 (higher = more concentrated)

    risk_level:             RiskLevel = RiskLevel.MODERATE
    has_high_concentration: bool      = False
    warnings:               tuple     = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_positions":          self.n_positions,
            "position_hhi":         round(self.position_hhi, 4),
            "top1_weight":          round(self.top1_weight, 4),
            "top1_symbol":          self.top1_symbol,
            "sector_hhi":           round(self.sector_hhi, 4),
            "top_sector":           self.top_sector,
            "top_sector_weight":    round(self.top_sector_weight, 4),
            "industry_hhi":         round(self.industry_hhi, 4),
            "concentration_score":  round(self.concentration_score, 4),
            "risk_level":           self.risk_level.value,
            "has_high_concentration": self.has_high_concentration,
            "warnings":             list(self.warnings),
        }


def _top_n_weight(sorted_weights: List[float], n: int) -> float:
    return sum(sorted_weights[:n]) if len(sorted_weights) >= n else sum(sorted_weights)


def analyze_concentration_risk(
    positions:    List[RiskPosition],
    portfolio_id: str = "",
) -> ConcentrationRiskResult:
    if not positions:
        return ConcentrationRiskResult(portfolio_id=portfolio_id)

    weights = [p.weight for p in positions]
    sorted_w = sorted(weights, reverse=True)

    pos_hhi   = hhi(weights)
    top1_w    = sorted_w[0] if sorted_w else 0.0
    top3_w    = _top_n_weight(sorted_w, 3)
    top5_w    = _top_n_weight(sorted_w, 5)

    # Identify top1 symbol
    top1_sym = max(positions, key=lambda p: p.weight).symbol

    # Sector
    sec_w = bucket_weights(positions, "sector")
    sec_hhi = hhi(list(sec_w.values()))
    top_sec = max(sec_w, key=sec_w.__getitem__, default="")
    top_sec_w = sec_w.get(top_sec, 0.0)

    # Industry
    ind_w = bucket_weights(positions, "industry")
    ind_hhi = hhi(list(ind_w.values()))
    top_ind = max(ind_w, key=ind_w.__getitem__, default="")
    top_ind_w = ind_w.get(top_ind, 0.0)

    # Country
    cnt_w = bucket_weights(positions, "country")
    cnt_hhi = hhi(list(cnt_w.values()))
    top_cnt = max(cnt_w, key=cnt_w.__getitem__, default="")
    top_cnt_w = cnt_w.get(top_cnt, 0.0)

    # Composite score: weighted average of HHI components
    conc_score = (
        pos_hhi  * 0.40 +
        sec_hhi  * 0.30 +
        ind_hhi  * 0.20 +
        cnt_hhi  * 0.10
    )

    risk_level = risk_score_to_level(min(1.0, conc_score / 0.60))
    has_high   = pos_hhi >= HHI_HIGH_RISK or top1_w >= 0.30 or top_sec_w >= 0.50

    warnings = []
    if top1_w >= 0.30:
        warnings.append(f"Top position {top1_sym} at {top1_w:.1%} of portfolio")
    elif top1_w >= 0.20:
        warnings.append(f"Top position {top1_sym} elevated at {top1_w:.1%}")
    if top5_w >= 0.70:
        warnings.append(f"Top-5 positions represent {top5_w:.1%} of portfolio")
    if top_sec_w >= 0.50:
        warnings.append(f"Sector '{top_sec}' at critical {top_sec_w:.1%}")
    elif top_sec_w >= 0.35:
        warnings.append(f"Sector '{top_sec}' elevated at {top_sec_w:.1%}")
    if top_ind_w >= 0.40:
        warnings.append(f"Industry '{top_ind}' at {top_ind_w:.1%}")

    return ConcentrationRiskResult(
        portfolio_id           = portfolio_id,
        n_positions            = len(positions),
        position_hhi           = round(pos_hhi, 6),
        top1_weight            = round(top1_w, 4),
        top3_weight            = round(top3_w, 4),
        top5_weight            = round(top5_w, 4),
        top1_symbol            = top1_sym,
        sector_hhi             = round(sec_hhi, 6),
        top_sector             = top_sec,
        top_sector_weight      = round(top_sec_w, 4),
        industry_hhi           = round(ind_hhi, 6),
        top_industry           = top_ind,
        top_industry_weight    = round(top_ind_w, 4),
        country_hhi            = round(cnt_hhi, 6),
        top_country            = top_cnt,
        top_country_weight     = round(top_cnt_w, 4),
        concentration_score    = round(conc_score, 6),
        risk_level             = risk_level,
        has_high_concentration = has_high,
        warnings               = tuple(warnings),
    )
