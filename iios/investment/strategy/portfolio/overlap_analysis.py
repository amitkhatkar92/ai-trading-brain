"""iios/investment/strategy/portfolio/overlap_analysis.py
OverlapAnalysis — sector, timeframe, regime, and tag overlap between strategies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy


@dataclass(frozen=True)
class OverlapReport:
    total_strategies:   int
    unique_tags:        int
    unique_sectors:     int
    unique_regimes:     int
    unique_timeframes:  int
    shared_tags:        List[str]     # tags held by >50% of strategies
    dominant_sector:    str           # most common sector
    dominant_regime:    str           # most common regime
    tag_concentration:  float         # fraction of tags that are shared across majority
    sector_spread:      float         # unique_sectors / total_strategies (higher = more spread)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_strategies":  self.total_strategies,
            "unique_tags":       self.unique_tags,
            "unique_sectors":    self.unique_sectors,
            "unique_regimes":    self.unique_regimes,
            "unique_timeframes": self.unique_timeframes,
            "shared_tags":       self.shared_tags,
            "dominant_sector":   self.dominant_sector,
            "dominant_regime":   self.dominant_regime,
            "tag_concentration": round(self.tag_concentration, 4),
            "sector_spread":     round(self.sector_spread, 4),
        }


class OverlapAnalysis:
    """
    Analyses how much attribute overlap exists across portfolio strategies.
    Higher overlap → lower diversification benefit.
    """

    def analyse(self, strategies: List[PortfolioStrategy]) -> OverlapReport:
        n = len(strategies)
        if n == 0:
            return OverlapReport(0, 0, 0, 0, 0, [], "", "", 0.0, 0.0)

        # Collect all attributes
        from collections import Counter

        tag_counter: Counter = Counter()
        sector_counter: Counter = Counter()
        regime_counter: Counter = Counter()
        timeframe_counter: Counter = Counter()

        for s in strategies:
            for t in s.tags:
                tag_counter[t] += 1
            for sec in s.sectors:
                sector_counter[sec] += 1
            for reg in s.supported_regimes:
                regime_counter[reg] += 1
            for tf in s.supported_timeframes:
                timeframe_counter[tf] += 1

        majority = n * 0.50

        shared_tags = [tag for tag, count in tag_counter.items() if count > majority]
        tag_conc = len(shared_tags) / max(len(tag_counter), 1)

        dominant_sector  = sector_counter.most_common(1)[0][0] if sector_counter else ""
        dominant_regime  = regime_counter.most_common(1)[0][0] if regime_counter else ""
        sector_spread    = len(sector_counter) / n if n > 0 else 0.0

        return OverlapReport(
            total_strategies=n,
            unique_tags=len(tag_counter),
            unique_sectors=len(sector_counter),
            unique_regimes=len(regime_counter),
            unique_timeframes=len(timeframe_counter),
            shared_tags=sorted(shared_tags),
            dominant_sector=dominant_sector,
            dominant_regime=dominant_regime,
            tag_concentration=tag_conc,
            sector_spread=sector_spread,
        )
