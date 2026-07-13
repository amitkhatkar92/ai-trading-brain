"""iios/investment/company/valuation/scenario_statistics.py
Statistics across scenario outputs (bull / base / bear).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.valuation.valuation_snapshot import ScenarioResult
from iios.investment.company.valuation.valuation_statistics import (
    safe_mean, safe_median, safe_stdev, coefficient_of_variation,
)


@dataclass
class ScenarioStatistics:
    mean_fair_value:   Optional[float] = None
    median_fair_value: Optional[float] = None
    stdev_fair_value:  Optional[float] = None
    cv_fair_value:     Optional[float] = None   # coefficient of variation
    range_pct:         Optional[float] = None   # (bull - bear) / base
    bull_upside_pct:   Optional[float] = None   # (bull - base) / base
    bear_downside_pct: Optional[float] = None   # (bear - base) / base
    explanation:       List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mean_fair_value":   round(self.mean_fair_value, 2)   if self.mean_fair_value   else None,
            "median_fair_value": round(self.median_fair_value, 2) if self.median_fair_value else None,
            "stdev_fair_value":  round(self.stdev_fair_value, 2)  if self.stdev_fair_value  else None,
            "cv_fair_value":     round(self.cv_fair_value, 4)     if self.cv_fair_value     else None,
            "range_pct":         round(self.range_pct, 1)         if self.range_pct         else None,
            "bull_upside_pct":   round(self.bull_upside_pct, 1)   if self.bull_upside_pct   else None,
            "bear_downside_pct": round(self.bear_downside_pct, 1) if self.bear_downside_pct else None,
            "explanation":       self.explanation,
        }


def compute_scenario_statistics(
    bull: Optional[ScenarioResult],
    base: Optional[ScenarioResult],
    bear: Optional[ScenarioResult],
) -> ScenarioStatistics:
    stats = ScenarioStatistics()

    values = [
        s.fair_value
        for s in [bull, base, bear]
        if s and s.fair_value is not None and s.fair_value > 0
    ]

    if not values:
        stats.explanation.append("No scenario results available for statistics")
        return stats

    stats.mean_fair_value   = safe_mean(values)
    stats.median_fair_value = safe_median(values)
    stats.stdev_fair_value  = safe_stdev(values)
    stats.cv_fair_value     = coefficient_of_variation(values)

    bull_fv = bull.fair_value if bull and bull.fair_value else None
    base_fv = base.fair_value if base and base.fair_value else None
    bear_fv = bear.fair_value if bear and bear.fair_value else None

    if bull_fv and bear_fv and base_fv and base_fv > 0:
        stats.range_pct         = (bull_fv - bear_fv) / base_fv * 100.0
        stats.bull_upside_pct   = (bull_fv - base_fv) / base_fv * 100.0
        stats.bear_downside_pct = (bear_fv - base_fv) / base_fv * 100.0
        stats.explanation.append(
            f"Bull {bull_fv:.2f} | Base {base_fv:.2f} | Bear {bear_fv:.2f} "
            f"(range: {stats.range_pct:.1f}%)"
        )

    return stats
