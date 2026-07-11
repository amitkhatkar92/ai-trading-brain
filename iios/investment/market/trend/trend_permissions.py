"""iios/investment/market/trend/trend_permissions.py
Strategy permissions and suitability scores per trend stage.
"""
from __future__ import annotations

from typing import ClassVar, Dict, List

from iios.investment.market.trend.models import TrendStage


class TrendStrategyType:
    """Strategy approach constants relevant to trend-based trading."""
    MOMENTUM       = "momentum"
    BREAKOUT       = "breakout"
    RETEST         = "retest"
    MEAN_REVERSION = "mean_reversion"
    SWING          = "swing"
    POSITION       = "position"
    ALL: ClassVar[List[str]] = [
        "momentum", "breakout", "retest", "mean_reversion", "swing", "position",
    ]


STAGE_PERMISSIONS: Dict[TrendStage, Dict[str, float]] = {
    TrendStage.EMERGING: {
        TrendStrategyType.MOMENTUM:       0.40,
        TrendStrategyType.BREAKOUT:       0.50,
        TrendStrategyType.RETEST:         0.20,
        TrendStrategyType.MEAN_REVERSION: 0.30,
        TrendStrategyType.SWING:          0.40,
        TrendStrategyType.POSITION:       0.20,
    },
    TrendStage.DEVELOPING: {
        TrendStrategyType.MOMENTUM:       0.60,
        TrendStrategyType.BREAKOUT:       0.65,
        TrendStrategyType.RETEST:         0.40,
        TrendStrategyType.MEAN_REVERSION: 0.25,
        TrendStrategyType.SWING:          0.60,
        TrendStrategyType.POSITION:       0.30,
    },
    TrendStage.ESTABLISHED: {
        TrendStrategyType.MOMENTUM:       0.85,
        TrendStrategyType.BREAKOUT:       0.75,
        TrendStrategyType.RETEST:         0.80,
        TrendStrategyType.MEAN_REVERSION: 0.15,
        TrendStrategyType.SWING:          0.80,
        TrendStrategyType.POSITION:       0.75,
    },
    TrendStage.MATURE: {
        TrendStrategyType.MOMENTUM:       0.60,
        TrendStrategyType.BREAKOUT:       0.40,
        TrendStrategyType.RETEST:         0.75,
        TrendStrategyType.MEAN_REVERSION: 0.35,
        TrendStrategyType.SWING:          0.70,
        TrendStrategyType.POSITION:       0.55,
    },
    TrendStage.EXHAUSTING: {
        TrendStrategyType.MOMENTUM:       0.25,
        TrendStrategyType.BREAKOUT:       0.15,
        TrendStrategyType.RETEST:         0.45,
        TrendStrategyType.MEAN_REVERSION: 0.65,
        TrendStrategyType.SWING:          0.40,
        TrendStrategyType.POSITION:       0.15,
    },
    TrendStage.FAILING: {
        TrendStrategyType.MOMENTUM:       0.10,
        TrendStrategyType.BREAKOUT:       0.10,
        TrendStrategyType.RETEST:         0.20,
        TrendStrategyType.MEAN_REVERSION: 0.75,
        TrendStrategyType.SWING:          0.20,
        TrendStrategyType.POSITION:       0.05,
    },
    TrendStage.REVERSING: {
        TrendStrategyType.MOMENTUM:       0.05,
        TrendStrategyType.BREAKOUT:       0.05,
        TrendStrategyType.RETEST:         0.10,
        TrendStrategyType.MEAN_REVERSION: 0.80,
        TrendStrategyType.SWING:          0.10,
        TrendStrategyType.POSITION:       0.02,
    },
    TrendStage.COMPLETED: {
        TrendStrategyType.MOMENTUM:       0.05,
        TrendStrategyType.BREAKOUT:       0.10,
        TrendStrategyType.RETEST:         0.05,
        TrendStrategyType.MEAN_REVERSION: 0.30,
        TrendStrategyType.SWING:          0.10,
        TrendStrategyType.POSITION:       0.02,
    },
}


def best_approach(stage: TrendStage) -> str:
    """Return the highest-scoring strategy type for a stage."""
    perms = STAGE_PERMISSIONS.get(stage, {})
    if not perms:
        return "avoid"
    return max(perms, key=lambda k: perms[k])
