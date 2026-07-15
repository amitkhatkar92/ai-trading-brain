"""iios/investment/portfolio/performance/security_attribution.py

Security-level (stock selection) performance attribution.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.performance.performance_types import PerformancePosition


@dataclass(frozen=True)
class SecurityAttributionRecord:
    """Attribution for a single security."""

    symbol:         str
    weight:         float = 0.0
    period_return:  float = 0.0
    contribution:   float = 0.0   # weight × return
    active_contribution: float = 0.0   # weight × (return - benchmark_return)
    benchmark_return: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":           self.symbol,
            "weight":           round(self.weight, 4),
            "period_return":    round(self.period_return, 4),
            "contribution":     round(self.contribution, 4),
            "active_contribution": round(self.active_contribution, 4),
        }


@dataclass(frozen=True)
class SecurityAttribution:
    """Security-level attribution: contribution and selection."""

    result_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str   = ""

    total_contribution: float = 0.0
    total_active:       float = 0.0

    records:            tuple = field(default_factory=tuple)  # ordered by contribution desc
    top_contributor:    str   = ""
    top_contribution:   float = 0.0
    bottom_contributor: str   = ""
    bottom_contribution:float = 0.0

    n_outperformers:    int   = 0   # securities that beat their benchmark
    n_underperformers:  int   = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_contribution": round(self.total_contribution, 4),
            "total_active":       round(self.total_active, 4),
            "top_contributor":    self.top_contributor,
            "top_contribution":   round(self.top_contribution, 4),
            "n_outperformers":    self.n_outperformers,
            "records":            [r.to_dict() for r in self.records[:10]],
        }


def compute_security_attribution(
    positions:    List[PerformancePosition],
    portfolio_id: str = "",
) -> SecurityAttribution:
    if not positions:
        return SecurityAttribution(portfolio_id=portfolio_id)

    records: List[SecurityAttributionRecord] = []
    for p in positions:
        records.append(SecurityAttributionRecord(
            symbol            = p.symbol,
            weight            = round(p.weight, 4),
            period_return     = round(p.period_return, 4),
            contribution      = round(p.contribution, 6),
            active_contribution = round(p.active_contribution, 6),
            benchmark_return  = round(p.benchmark_period_return, 4),
        ))

    records_sorted = sorted(records, key=lambda r: r.contribution, reverse=True)
    total_contr = sum(r.contribution for r in records)
    total_active = sum(r.active_contribution for r in records)

    n_out = sum(1 for r in records if r.active_contribution > 0)
    n_und = len(records) - n_out

    top = records_sorted[0]
    bot = records_sorted[-1]

    return SecurityAttribution(
        portfolio_id       = portfolio_id,
        total_contribution = round(total_contr, 6),
        total_active       = round(total_active, 6),
        records            = tuple(records_sorted),
        top_contributor    = top.symbol,
        top_contribution   = round(top.contribution, 4),
        bottom_contributor = bot.symbol,
        bottom_contribution= round(bot.contribution, 4),
        n_outperformers    = n_out,
        n_underperformers  = n_und,
    )
