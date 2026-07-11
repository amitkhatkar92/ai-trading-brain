"""iios/investment/market/sector_rotation/sector_lifecycle.py
Orchestrates lifecycle stage tracking for all sectors.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from iios.investment.market.sector_rotation.models import (
    RelativeStrengthScore,
    SectorEvent,
    SectorLifecycleProfile,
    SectorPerformance,
    SectorStage,
)
from iios.investment.market.sector_rotation.sector_stage import classify_stage
from iios.investment.market.sector_rotation.sector_transition import (
    TransitionTracker,
    stage_confidence,
    transition_probability,
)

log = logging.getLogger(__name__)


class SectorLifecycleEngine:
    """Determines and tracks lifecycle stages for every sector."""

    def __init__(self) -> None:
        self._trackers: Dict[str, TransitionTracker] = {}
        self._current:  Dict[str, SectorLifecycleProfile] = {}

    def update(
        self,
        sector_perfs: Dict[str, SectorPerformance],
        rs_scores: Dict[str, RelativeStrengthScore],
        bar_index: int,
    ) -> tuple[Dict[str, SectorLifecycleProfile], List[SectorEvent]]:
        """Return (profiles, new_events)."""
        events: List[SectorEvent] = []

        for sector, perf in sector_perfs.items():
            rs = rs_scores.get(sector)
            if rs is None:
                continue

            new_stage = classify_stage(perf, rs)

            if sector not in self._trackers:
                self._trackers[sector] = TransitionTracker(sector)

            tracker = self._trackers[sector]
            event   = tracker.update(new_stage, bar_index, perf.momentum_score)
            if event is not None:
                events.append(event)

            confidence = stage_confidence(
                new_stage, tracker.duration, perf.momentum_score
            )
            trans_prob = transition_probability(new_stage, perf.momentum_score)

            self._current[sector] = SectorLifecycleProfile(
                sector=sector,
                stage=new_stage,
                stage_duration_bars=tracker.duration,
                previous_stage=tracker.previous_stage,
                stage_confidence=confidence,
                transition_probability=trans_prob,
            )

        return dict(self._current), events

    # ── queries ───────────────────────────────────────────────────────────────

    def current_profiles(self) -> Dict[str, SectorLifecycleProfile]:
        return dict(self._current)

    def sectors_in_stage(self, stage: SectorStage) -> List[str]:
        return [s for s, p in self._current.items() if p.stage is stage]

    def leaders(self) -> List[str]:
        return self.sectors_in_stage(SectorStage.LEADING)

    def laggards(self) -> List[str]:
        return self.sectors_in_stage(SectorStage.LAGGING)

    def emerging(self) -> List[str]:
        return self.sectors_in_stage(SectorStage.EMERGING)

    def recovering(self) -> List[str]:
        return self.sectors_in_stage(SectorStage.RECOVERING)

    def get(self, sector: str) -> Optional[SectorLifecycleProfile]:
        return self._current.get(sector)
