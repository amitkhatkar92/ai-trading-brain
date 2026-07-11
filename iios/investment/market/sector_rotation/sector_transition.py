"""iios/investment/market/sector_rotation/sector_transition.py
Detects stage transitions and derives transition probability.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Tuple

from iios.investment.market.sector_rotation.models import SectorEvent, SectorEventType, SectorStage

# Probability of transitioning to each stage given momentum direction
_TRANSITION_MATRIX: Dict[SectorStage, Dict[str, float]] = {
    SectorStage.EMERGING:        {"improving": 0.70, "stable": 0.25, "declining": 0.05},
    SectorStage.LEADING:         {"improving": 0.15, "stable": 0.65, "declining": 0.20},
    SectorStage.OUTPERFORMING:   {"improving": 0.10, "stable": 0.60, "declining": 0.30},
    SectorStage.MATURE:          {"improving": 0.20, "stable": 0.50, "declining": 0.30},
    SectorStage.WEAKENING:       {"improving": 0.25, "stable": 0.20, "declining": 0.55},
    SectorStage.LAGGING:         {"improving": 0.30, "stable": 0.40, "declining": 0.30},
    SectorStage.UNDERPERFORMING: {"improving": 0.35, "stable": 0.30, "declining": 0.35},
    SectorStage.RECOVERING:      {"improving": 0.55, "stable": 0.30, "declining": 0.15},
    SectorStage.UNKNOWN:         {"improving": 0.33, "stable": 0.34, "declining": 0.33},
}


def transition_probability(stage: SectorStage, momentum_score: float) -> float:
    """Probability that the sector will *change* stage next bar."""
    matrix = _TRANSITION_MATRIX.get(stage, _TRANSITION_MATRIX[SectorStage.UNKNOWN])
    if momentum_score >= 60:
        direction = "improving"
    elif momentum_score <= 40:
        direction = "declining"
    else:
        direction = "stable"
    # probability of NOT staying = probability of transitioning
    # "stable" key encodes probability of staying in same stage
    stay = matrix.get("stable", 0.5)
    return 1.0 - stay


def stage_confidence(
    stage: SectorStage,
    stage_duration_bars: int,
    momentum_score: float,
) -> float:
    """0-1 confidence that the current stage classification is correct."""
    # More bars in a stage → more confident (plateaus at 20 bars)
    duration_factor = min(1.0, stage_duration_bars / 20.0)
    # Momentum alignment
    _stage_momentum_alignment = {
        SectorStage.LEADING:         lambda m: (m - 50.0) / 50.0,
        SectorStage.EMERGING:        lambda m: (m - 50.0) / 50.0,
        SectorStage.OUTPERFORMING:   lambda m: (m - 50.0) / 50.0,
        SectorStage.MATURE:          lambda m: 1.0 - abs(m - 55.0) / 45.0,
        SectorStage.WEAKENING:       lambda m: (50.0 - m) / 50.0,
        SectorStage.LAGGING:         lambda m: (50.0 - m) / 50.0,
        SectorStage.UNDERPERFORMING: lambda m: (50.0 - m) / 50.0,
        SectorStage.RECOVERING:      lambda m: (m - 50.0) / 50.0,
        SectorStage.UNKNOWN:         lambda m: 0.5,
    }
    fn = _stage_momentum_alignment.get(stage, lambda m: 0.5)
    alignment = max(0.0, min(1.0, fn(momentum_score)))
    return duration_factor * 0.6 + alignment * 0.4


class TransitionTracker:
    """Tracks stage transitions for a single sector."""

    def __init__(self, sector: str) -> None:
        self._sector   = sector
        self._stage:   Optional[SectorStage]  = None
        self._duration: int = 0
        self._prev:    Optional[SectorStage]  = None

    def update(
        self, new_stage: SectorStage, bar_index: int, momentum_score: float
    ) -> Optional[SectorEvent]:
        """Return a SectorEvent if a stage transition occurred."""
        event: Optional[SectorEvent] = None

        if self._stage is None:
            self._stage    = new_stage
            self._duration = 1
            return None

        if new_stage != self._stage:
            event = SectorEvent(
                event_type=SectorEventType.STAGE_TRANSITION,
                sector=self._sector,
                bar_index=bar_index,
                severity=0.5,
                description=(
                    f"{self._sector}: {self._stage.value} → {new_stage.value}"
                ),
                from_stage=self._stage,
                to_stage=new_stage,
            )
            # Severity: LEADING→LAGGING is more severe than MATURE→WEAKENING
            _severe_pairs = {
                (SectorStage.LEADING, SectorStage.WEAKENING),
                (SectorStage.LEADING, SectorStage.LAGGING),
                (SectorStage.OUTPERFORMING, SectorStage.UNDERPERFORMING),
            }
            if (self._stage, new_stage) in _severe_pairs:
                event.severity = 0.9
                event.event_type = SectorEventType.FALLING_LEADER
            elif new_stage in (SectorStage.LEADING, SectorStage.EMERGING):
                event.event_type = SectorEventType.EMERGING_LEADER
                event.severity   = 0.6
            elif new_stage in (SectorStage.RECOVERING,):
                event.event_type = SectorEventType.RECOVERY_START
                event.severity   = 0.4

            self._prev     = self._stage
            self._stage    = new_stage
            self._duration = 1
        else:
            self._duration += 1

        return event

    @property
    def current_stage(self) -> Optional[SectorStage]:
        return self._stage

    @property
    def duration(self) -> int:
        return self._duration

    @property
    def previous_stage(self) -> Optional[SectorStage]:
        return self._prev
