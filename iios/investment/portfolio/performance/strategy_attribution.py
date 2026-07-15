"""iios/investment/portfolio/performance/strategy_attribution.py

Strategy-level performance attribution.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.performance.performance_types import PerformancePosition


@dataclass(frozen=True)
class StrategyAttributionRecord:
    """Attribution for a single strategy bucket."""

    strategy_id:         str
    n_positions:         int   = 0
    total_weight:        float = 0.0
    strategy_return:     float = 0.0   # weighted avg period return
    strategy_contribution:float = 0.0  # total_weight × strategy_return
    avg_conviction:      float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":          self.strategy_id,
            "n_positions":          self.n_positions,
            "total_weight":         round(self.total_weight, 4),
            "strategy_return":      round(self.strategy_return, 4),
            "strategy_contribution":round(self.strategy_contribution, 4),
        }


@dataclass(frozen=True)
class StrategyAttribution:
    """Strategy attribution result."""

    result_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str   = ""
    total_contribution: float = 0.0
    n_strategies:       int   = 0
    records:            tuple = field(default_factory=tuple)
    best_strategy:      str   = ""
    best_contribution:  float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_contribution": round(self.total_contribution, 4),
            "n_strategies":       self.n_strategies,
            "best_strategy":      self.best_strategy,
            "records":            [r.to_dict() for r in self.records],
        }


def compute_strategy_attribution(
    positions:    List[PerformancePosition],
    portfolio_id: str = "",
) -> StrategyAttribution:
    if not positions:
        return StrategyAttribution(portfolio_id=portfolio_id)

    # Group by strategy_id
    buckets: Dict[str, List[PerformancePosition]] = {}
    for p in positions:
        sid = p.strategy_id or "unassigned"
        buckets.setdefault(sid, []).append(p)

    records: List[StrategyAttributionRecord] = []
    for sid, ps in buckets.items():
        total_w = sum(p.weight for p in ps)
        if total_w <= 0:
            strat_r = 0.0
        else:
            strat_r = sum(p.weight * p.period_return for p in ps) / total_w
        contribution = total_w * strat_r
        avg_conv = sum(p.conviction for p in ps) / len(ps)
        records.append(StrategyAttributionRecord(
            strategy_id          = sid,
            n_positions          = len(ps),
            total_weight         = round(total_w, 4),
            strategy_return      = round(strat_r, 4),
            strategy_contribution= round(contribution, 6),
            avg_conviction       = round(avg_conv, 4),
        ))

    records_sorted = sorted(records, key=lambda r: r.strategy_contribution, reverse=True)
    total_contr    = sum(r.strategy_contribution for r in records)
    best = records_sorted[0] if records_sorted else None

    return StrategyAttribution(
        portfolio_id       = portfolio_id,
        total_contribution = round(total_contr, 6),
        n_strategies       = len(records),
        records            = tuple(records_sorted),
        best_strategy      = best.strategy_id if best else "",
        best_contribution  = round(best.strategy_contribution, 4) if best else 0.0,
    )
