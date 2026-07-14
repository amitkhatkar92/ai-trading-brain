"""iios/investment/strategy/integration/coverage_monitor.py
Monitors how completely all strategies are covered by intelligence sources.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.integration.integration_constants import (
    IntelligenceSource,
)
from iios.investment.strategy.integration.strategy_intelligence_aggregator import (
    StrategyIntelligenceAggregator,
)

# Minimum completeness (0–1) to count a strategy as "complete"
_COMPLETE_THRESHOLD = 0.75


@dataclass(frozen=True)
class CoverageReport:
    total_strategies:     int
    complete_strategies:  int
    partial_strategies:   int
    avg_completeness:     float
    by_source_coverage:   Dict[str, float]  # source.value → fraction of strategies covered
    computed_at:          datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_strategies":    self.total_strategies,
            "complete_strategies": self.complete_strategies,
            "partial_strategies":  self.partial_strategies,
            "avg_completeness":    round(self.avg_completeness, 4),
            "by_source_coverage":  {k: round(v, 4) for k, v in self.by_source_coverage.items()},
            "computed_at":         self.computed_at.isoformat(),
        }


class CoverageMonitor:
    """
    Computes coverage statistics across all known strategies.
    Uses a StrategyIntelligenceAggregator (read-only).
    """

    def compute(
        self,
        aggregator: StrategyIntelligenceAggregator,
    ) -> CoverageReport:
        strategies = aggregator.known_strategies()
        total      = len(strategies)

        if total == 0:
            return CoverageReport(
                total_strategies=0,
                complete_strategies=0,
                partial_strategies=0,
                avg_completeness=0.0,
                by_source_coverage={s.value: 0.0 for s in IntelligenceSource},
                computed_at=datetime.now(timezone.utc),
            )

        completeness_sum = 0.0
        complete_count   = 0
        source_counts: Dict[str, int] = {s.value: 0 for s in IntelligenceSource}

        for sid in strategies:
            c = aggregator.completeness(sid)
            completeness_sum += c
            if c >= 0.75:
                complete_count += 1

            latest = aggregator.all_latest(sid)
            for src in latest:
                source_counts[src.value] = source_counts.get(src.value, 0) + 1

        avg_comp    = completeness_sum / total
        partial_ct  = total - complete_count
        by_source   = {k: round(v / total, 4) for k, v in source_counts.items()}

        return CoverageReport(
            total_strategies=total,
            complete_strategies=complete_count,
            partial_strategies=partial_ct,
            avg_completeness=round(avg_comp, 4),
            by_source_coverage=by_source,
            computed_at=datetime.now(timezone.utc),
        )
