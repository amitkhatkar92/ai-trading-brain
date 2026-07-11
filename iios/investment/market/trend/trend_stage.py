"""iios/investment/market/trend/trend_stage.py
Stage ordering, lifecycle scores, and utility functions for TrendStage.
"""
from __future__ import annotations

from typing import Dict, List

from iios.investment.market.trend.models import TrendStage


# ── Stage ordering ─────────────────────────────────────────────────────────

STAGE_ORDER: List[TrendStage] = [
    TrendStage.EMERGING,
    TrendStage.DEVELOPING,
    TrendStage.ESTABLISHED,
    TrendStage.MATURE,
    TrendStage.EXHAUSTING,
    TrendStage.FAILING,
    TrendStage.REVERSING,
    TrendStage.COMPLETED,
]

_STAGE_INDEX: Dict[TrendStage, int] = {s: i for i, s in enumerate(STAGE_ORDER)}


def stage_index(stage: TrendStage) -> int:
    """Returns 0-based position in STAGE_ORDER."""
    return _STAGE_INDEX.get(stage, 0)


def is_advancing(from_stage: TrendStage, to_stage: TrendStage) -> bool:
    """Returns True if to_stage is later in lifecycle than from_stage."""
    return stage_index(to_stage) > stage_index(from_stage)


def is_declining(from_stage: TrendStage, to_stage: TrendStage) -> bool:
    """Returns True if to_stage is earlier in lifecycle (recovery path)."""
    return stage_index(to_stage) < stage_index(from_stage)


# ── Lifecycle scores ───────────────────────────────────────────────────────

STAGE_LIFECYCLE_SCORES: Dict[TrendStage, float] = {
    TrendStage.EMERGING:    60.0,
    TrendStage.DEVELOPING:  75.0,
    TrendStage.ESTABLISHED: 90.0,
    TrendStage.MATURE:      70.0,
    TrendStage.EXHAUSTING:  40.0,
    TrendStage.FAILING:     20.0,
    TrendStage.REVERSING:   10.0,
    TrendStage.COMPLETED:   5.0,
}
