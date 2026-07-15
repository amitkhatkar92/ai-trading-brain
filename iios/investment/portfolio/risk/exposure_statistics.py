"""iios/investment/portfolio/risk/exposure_statistics.py

Aggregate exposure statistics across all dimensions.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    bucket_weights, hhi, RiskPosition,
)


@dataclass(frozen=True)
class ExposureStatistics:
    """Summary statistics of portfolio exposure across all dimensions."""

    result_id:             str            = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:          str            = ""

    # Dimension HHIs (higher = more concentrated)
    sector_hhi:            float          = 0.0
    industry_hhi:          float          = 0.0
    country_hhi:           float          = 0.0
    currency_hhi:          float          = 0.0
    asset_class_hhi:       float          = 0.0

    # Dimension counts
    n_sectors:             int            = 0
    n_industries:          int            = 0
    n_countries:           int            = 0
    n_currencies:          int            = 0
    n_asset_classes:       int            = 0

    # Top exposure per dimension
    top_sector:            str            = ""
    top_sector_weight:     float          = 0.0
    top_industry:          str            = ""
    top_industry_weight:   float          = 0.0
    top_country:           str            = ""
    top_country_weight:    float          = 0.0

    # Composite concentration index
    overall_concentration: float          = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector_hhi":            round(self.sector_hhi, 4),
            "industry_hhi":          round(self.industry_hhi, 4),
            "country_hhi":           round(self.country_hhi, 4),
            "asset_class_hhi":       round(self.asset_class_hhi, 4),
            "n_sectors":             self.n_sectors,
            "n_industries":          self.n_industries,
            "n_countries":           self.n_countries,
            "n_asset_classes":       self.n_asset_classes,
            "top_sector":            self.top_sector,
            "top_sector_weight":     round(self.top_sector_weight, 4),
            "overall_concentration": round(self.overall_concentration, 4),
        }


def compute_exposure_statistics(
    positions:    List[RiskPosition],
    portfolio_id: str = "",
) -> ExposureStatistics:
    if not positions:
        return ExposureStatistics(portfolio_id=portfolio_id)

    def _top(d: Dict[str, float]) -> tuple:
        k = max(d, key=d.__getitem__, default="")
        return k, d.get(k, 0.0)

    sec_w  = bucket_weights(positions, "sector")
    ind_w  = bucket_weights(positions, "industry")
    cnt_w  = bucket_weights(positions, "country")
    ccy_w  = bucket_weights(positions, "currency")
    ac_w   = bucket_weights(positions, "asset_class")

    top_sec,  top_sec_w  = _top(sec_w)
    top_ind,  top_ind_w  = _top(ind_w)
    top_cnt,  top_cnt_w  = _top(cnt_w)

    s_hhi  = hhi(list(sec_w.values()))
    i_hhi  = hhi(list(ind_w.values()))
    c_hhi  = hhi(list(cnt_w.values()))
    cy_hhi = hhi(list(ccy_w.values()))
    ac_hhi = hhi(list(ac_w.values()))

    overall = (s_hhi * 0.30 + i_hhi * 0.25 + ac_hhi * 0.25
               + c_hhi * 0.10 + cy_hhi * 0.10)

    return ExposureStatistics(
        portfolio_id         = portfolio_id,
        sector_hhi           = round(s_hhi, 4),
        industry_hhi         = round(i_hhi, 4),
        country_hhi          = round(c_hhi, 4),
        currency_hhi         = round(cy_hhi, 4),
        asset_class_hhi      = round(ac_hhi, 4),
        n_sectors            = len(sec_w),
        n_industries         = len(ind_w),
        n_countries          = len(cnt_w),
        n_currencies         = len(ccy_w),
        n_asset_classes      = len(ac_w),
        top_sector           = top_sec,
        top_sector_weight    = round(top_sec_w, 4),
        top_industry         = top_ind,
        top_industry_weight  = round(top_ind_w, 4),
        top_country          = top_cnt,
        top_country_weight   = round(top_cnt_w, 4),
        overall_concentration= round(overall, 4),
    )
