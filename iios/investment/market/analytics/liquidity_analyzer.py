"""iios/investment/market/analytics/liquidity_analyzer.py
Market liquidity scoring from volume and bid-ask spread data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.market.market_constants import LiquidityLevel


@dataclass
class LiquidityAnalysis:
    level:          LiquidityLevel = LiquidityLevel.MODERATE
    avg_volume:     float          = 0.0
    avg_spread_pct: float          = 0.0
    score:          float          = 50.0   # 0–100
    metadata:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level":          self.level.value,
            "avg_volume":     self.avg_volume,
            "avg_spread_pct": self.avg_spread_pct,
            "score":          self.score,
            "metadata":       self.metadata,
        }


class LiquidityAnalyzer:
    """
    Scores market liquidity from volume (60%) and bid-ask spread (40%).

    Higher volume + tighter spread → higher score.

    Volume thresholds (shares/day):  >5M, >1M, >200K, >50K, >10K, ≤10K
    Spread thresholds (% of price):  <0.1%, <0.3%, <1%, <3%, <10%, ≥10%
    """

    _VOL_BREAKS = [5_000_000, 1_000_000, 200_000, 50_000, 10_000]
    _SPD_BREAKS = [0.001,     0.003,      0.01,    0.03,   0.10]

    def analyze(
        self,
        volumes: dict[str, float] | list[float],
        spreads: dict[str, float] | list[float] | None = None,
    ) -> LiquidityAnalysis:
        vol_vals = (
            list(volumes.values()) if isinstance(volumes, dict) else list(volumes)
        )
        spd_vals = (
            list(spreads.values()) if isinstance(spreads, dict)
            else (list(spreads) if spreads else [])
        )

        if not vol_vals:
            return LiquidityAnalysis()

        avg_vol = sum(vol_vals) / len(vol_vals)
        avg_spd = sum(spd_vals) / len(spd_vals) if spd_vals else 0.0

        # Volume band index (0 = best, 5 = worst)
        vi = 5
        for idx, thr in enumerate(self._VOL_BREAKS):
            if avg_vol >= thr:
                vi = idx
                break

        # Spread band index (0 = best, 5 = worst)
        si = 0
        if avg_spd > 0:
            si = 5
            for idx, thr in enumerate(self._SPD_BREAKS):
                if avg_spd <= thr:
                    si = idx
                    break

        # Convert band indices to sub-scores
        vol_scores = [60.0, 50.0, 37.5, 20.0, 8.0, 0.0]
        spd_scores = [40.0, 32.0, 20.0, 8.0,  2.0, 0.0]

        score     = vol_scores[vi] + spd_scores[si]
        level_idx = (vi + si) // 2

        levels = [
            LiquidityLevel.VERY_HIGH,
            LiquidityLevel.HIGH,
            LiquidityLevel.MODERATE,
            LiquidityLevel.LOW,
            LiquidityLevel.VERY_LOW,
            LiquidityLevel.ILLIQUID,
        ]
        level = levels[min(level_idx, 5)]

        return LiquidityAnalysis(
            level          = level,
            avg_volume     = round(avg_vol, 2),
            avg_spread_pct = round(avg_spd, 6),
            score          = round(score, 2),
            metadata       = {"n_symbols": len(vol_vals)},
        )
