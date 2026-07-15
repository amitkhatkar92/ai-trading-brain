"""iios/investment/portfolio/performance/sector_attribution.py

Sector-level performance attribution using BHB model.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.performance.performance_types import (
    PerformancePosition, bucket_returns, bucket_weights,
)


@dataclass(frozen=True)
class SectorAttributionRecord:
    """BHB attribution for a single sector."""

    sector:               str
    portfolio_weight:     float = 0.0
    benchmark_weight:     float = 0.0
    portfolio_return:     float = 0.0   # sector-avg return in portfolio
    benchmark_return:     float = 0.0   # benchmark sector return

    allocation_effect:    float = 0.0   # (w_p - w_b) × (R_b_sector - R_b_total)
    selection_effect:     float = 0.0   # w_p × (R_p_sector - R_b_sector)
    interaction_effect:   float = 0.0   # (w_p - w_b) × (R_p_sector - R_b_sector)
    total_effect:         float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector":            self.sector,
            "portfolio_weight":  round(self.portfolio_weight, 4),
            "benchmark_weight":  round(self.benchmark_weight, 4),
            "allocation_effect": round(self.allocation_effect, 4),
            "selection_effect":  round(self.selection_effect, 4),
            "total_effect":      round(self.total_effect, 4),
        }


@dataclass(frozen=True)
class SectorAttribution:
    """BHB sector attribution result."""

    result_id:            str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str   = ""

    total_allocation:     float = 0.0
    total_selection:      float = 0.0
    total_interaction:    float = 0.0
    total_active:         float = 0.0

    records:              tuple = field(default_factory=tuple)  # tuple[SectorAttributionRecord]
    top_sector:           str   = ""
    top_sector_effect:    float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_allocation":  round(self.total_allocation, 4),
            "total_selection":   round(self.total_selection, 4),
            "total_interaction": round(self.total_interaction, 4),
            "total_active":      round(self.total_active, 4),
            "top_sector":        self.top_sector,
            "records":           [r.to_dict() for r in self.records],
        }


def compute_sector_attribution(
    positions:           List[PerformancePosition],
    benchmark_return:    float = 0.0,
    portfolio_id:        str   = "",
    benchmark_sector_weights: Optional[Dict[str, float]] = None,
    benchmark_sector_returns: Optional[Dict[str, float]] = None,
) -> SectorAttribution:
    """
    BHB (Brinson-Hood-Beebower) sector attribution.

    When benchmark sector weights/returns are not provided, equal-weight
    across sectors is assumed with the overall benchmark return per sector.
    """
    if not positions:
        return SectorAttribution(portfolio_id=portfolio_id)

    port_sec_w  = bucket_weights(positions, "sector")
    port_sec_r  = bucket_returns(positions, "sector")
    total_bmk_r = benchmark_return

    sectors = sorted(port_sec_w.keys())
    n_sec   = len(sectors)
    uniform_bmk_w = 1.0 / n_sec if n_sec > 0 else 0.0

    records: List[SectorAttributionRecord] = []
    ta = ts = ti = 0.0

    for sec in sectors:
        pw = port_sec_w.get(sec, 0.0)
        bw = (benchmark_sector_weights or {}).get(sec, uniform_bmk_w)
        pr = port_sec_r.get(sec, 0.0)
        br = (benchmark_sector_returns or {}).get(sec, total_bmk_r)

        alloc = (pw - bw) * (br - total_bmk_r)
        sel   = pw * (pr - br)
        inter = (pw - bw) * (pr - br)
        tot   = alloc + sel + inter

        ta += alloc
        ts += sel
        ti += inter

        records.append(SectorAttributionRecord(
            sector              = sec,
            portfolio_weight    = round(pw, 4),
            benchmark_weight    = round(bw, 4),
            portfolio_return    = round(pr, 4),
            benchmark_return    = round(br, 4),
            allocation_effect   = round(alloc, 6),
            selection_effect    = round(sel, 6),
            interaction_effect  = round(inter, 6),
            total_effect        = round(tot, 6),
        ))

    records_sorted = sorted(records, key=lambda r: abs(r.total_effect), reverse=True)
    top = records_sorted[0] if records_sorted else None

    return SectorAttribution(
        portfolio_id      = portfolio_id,
        total_allocation  = round(ta, 6),
        total_selection   = round(ts, 6),
        total_interaction = round(ti, 6),
        total_active      = round(ta + ts + ti, 6),
        records           = tuple(records),
        top_sector        = top.sector if top else "",
        top_sector_effect = round(top.total_effect, 4) if top else 0.0,
    )
