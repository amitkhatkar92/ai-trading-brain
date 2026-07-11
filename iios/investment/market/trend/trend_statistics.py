"""iios/investment/market/trend/trend_statistics.py
Historical trend statistics accumulated over engine lifetime.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from iios.investment.market.trend.models import TrendStage, TrendEventType


@dataclass
class TrendStageStats:
    stage: TrendStage
    count: int
    avg_duration_bars: float
    min_duration: int
    max_duration: int
    avg_confidence: float


class TrendStatistics:
    """Historical trend statistics accumulated over engine lifetime."""

    def __init__(self) -> None:
        self._stage_durations: Dict[TrendStage, List[int]] = defaultdict(list)
        self._stage_confidences: Dict[TrendStage, List[float]] = defaultdict(list)
        self._event_counts: Dict[str, int] = defaultdict(int)
        self._total_stages: int = 0

    def record_stage_end(
        self, stage: TrendStage, duration_bars: int, confidence: float
    ) -> None:
        self._stage_durations[stage].append(duration_bars)
        self._stage_confidences[stage].append(confidence)
        self._total_stages += 1

    def record_event(self, event_type: TrendEventType) -> None:
        self._event_counts[event_type.value] += 1

    def stats_for(self, stage: TrendStage) -> TrendStageStats:
        durations = self._stage_durations.get(stage, [])
        confidences = self._stage_confidences.get(stage, [])
        if not durations:
            return TrendStageStats(
                stage=stage, count=0,
                avg_duration_bars=0.0, min_duration=0, max_duration=0,
                avg_confidence=0.0,
            )
        return TrendStageStats(
            stage=stage,
            count=len(durations),
            avg_duration_bars=sum(durations) / len(durations),
            min_duration=min(durations),
            max_duration=max(durations),
            avg_confidence=sum(confidences) / len(confidences) if confidences else 0.0,
        )

    def all_stats(self) -> Dict[TrendStage, TrendStageStats]:
        return {stage: self.stats_for(stage) for stage in TrendStage}

    def event_counts(self) -> Dict[str, int]:
        return dict(self._event_counts)

    def total_stages_observed(self) -> int:
        return self._total_stages

    def most_common_stage(self) -> Optional[TrendStage]:
        if not self._stage_durations:
            return None
        return max(self._stage_durations, key=lambda s: len(self._stage_durations[s]))

    def avg_duration(self, stage: TrendStage) -> float:
        durations = self._stage_durations.get(stage, [])
        if not durations:
            return 0.0
        return sum(durations) / len(durations)
