"""iios/investment/strategy/portfolio/strategy_correlation.py
Feature-based strategy correlation using Jaccard similarity of attributes.
No return-series data is required.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.portfolio_statistics import jaccard


# ── per-pair similarity record ────────────────────────────────────────────────

@dataclass(frozen=True)
class StrategyCorrelation:
    """
    Pairwise similarity between two strategies.
    similarity ∈ [0, 1]; 0 = orthogonal, 1 = identical profile.
    """
    strategy_id_a: str
    strategy_id_b: str
    similarity:    float          # overall feature similarity
    tag_overlap:   float          # Jaccard(tags_a, tags_b)
    sector_overlap: float         # Jaccard(sectors_a, sectors_b)
    regime_overlap: float         # Jaccard(regimes_a, regimes_b)
    timeframe_overlap: float      # Jaccard(timeframes_a, timeframes_b)

    @property
    def is_highly_correlated(self) -> bool:
        return self.similarity >= 0.70

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id_a": self.strategy_id_a,
            "strategy_id_b": self.strategy_id_b,
            "similarity":    round(self.similarity, 4),
            "tag_overlap":   round(self.tag_overlap, 4),
            "sector_overlap": round(self.sector_overlap, 4),
            "regime_overlap": round(self.regime_overlap, 4),
            "timeframe_overlap": round(self.timeframe_overlap, 4),
            "is_highly_correlated": self.is_highly_correlated,
        }


# ── correlation matrix ────────────────────────────────────────────────────────

class CorrelationMatrix:
    """
    Pairwise strategy correlation matrix computed from feature similarity.

    Weights:
        tags       40%
        sectors    25%
        regimes    20%
        timeframes 15%
    """

    _TAG_W  = 0.40
    _SEC_W  = 0.25
    _REG_W  = 0.20
    _TFW    = 0.15

    def __init__(self, strategies: List[PortfolioStrategy]) -> None:
        self._strategies: Dict[str, PortfolioStrategy] = {
            s.strategy_id: s for s in strategies
        }
        self._pairs: Dict[Tuple[str, str], StrategyCorrelation] = {}
        self._build()

    def _build(self) -> None:
        ids = list(self._strategies.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                corr = self._compute(self._strategies[ids[i]], self._strategies[ids[j]])
                self._pairs[(ids[i], ids[j])] = corr
                self._pairs[(ids[j], ids[i])] = corr

    def _compute(self, a: PortfolioStrategy, b: PortfolioStrategy) -> StrategyCorrelation:
        tag_j  = jaccard(a.tags,               b.tags)
        sec_j  = jaccard(a.sectors,            b.sectors)
        reg_j  = jaccard(a.supported_regimes,  b.supported_regimes)
        tf_j   = jaccard(a.supported_timeframes, b.supported_timeframes)
        sim    = (
            self._TAG_W * tag_j
            + self._SEC_W * sec_j
            + self._REG_W * reg_j
            + self._TFW  * tf_j
        )
        return StrategyCorrelation(
            strategy_id_a=a.strategy_id,
            strategy_id_b=b.strategy_id,
            similarity=round(sim, 6),
            tag_overlap=round(tag_j, 6),
            sector_overlap=round(sec_j, 6),
            regime_overlap=round(reg_j, 6),
            timeframe_overlap=round(tf_j, 6),
        )

    def get(self, id_a: str, id_b: str) -> Optional[StrategyCorrelation]:
        return self._pairs.get((id_a, id_b))

    def average_correlation(self) -> float:
        if not self._pairs:
            return 0.0
        vals = list({(min(k), max(k)): v for k, v in self._pairs.items()}.values())
        return sum(c.similarity for c in vals) / len(vals)

    def all_pairs(self) -> List[StrategyCorrelation]:
        seen = set()
        result = []
        for (a, b), corr in self._pairs.items():
            key = (min(a, b), max(a, b))
            if key not in seen:
                seen.add(key)
                result.append(corr)
        return result

    def matrix_as_dict(self) -> Dict[str, Dict[str, float]]:
        ids = list(self._strategies.keys())
        mat: Dict[str, Dict[str, float]] = {}
        for id_a in ids:
            mat[id_a] = {}
            for id_b in ids:
                if id_a == id_b:
                    mat[id_a][id_b] = 1.0
                else:
                    corr = self.get(id_a, id_b)
                    mat[id_a][id_b] = corr.similarity if corr else 0.0
        return mat
