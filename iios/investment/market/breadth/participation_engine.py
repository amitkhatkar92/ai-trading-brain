"""iios/investment/market/breadth/participation_engine.py
Stateful participation orchestrator with rolling history.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Optional

from iios.investment.market.breadth.models import ParticipationSnapshot, UniverseSnapshot
from iios.investment.market.breadth.participation_profile import ParticipationProfileBuilder


class ParticipationEngine:
    """Builds and caches participation snapshots."""

    def __init__(
        self,
        builder: Optional[ParticipationProfileBuilder] = None,
        history_size: int = 100,
    ) -> None:
        self._builder = builder or ParticipationProfileBuilder()
        self._history: Deque[ParticipationSnapshot] = deque(maxlen=history_size)
        self._current: Optional[ParticipationSnapshot] = None

    def update(self, universe: UniverseSnapshot) -> ParticipationSnapshot:
        snap = self._builder.build(universe)
        self._history.append(snap)
        self._current = snap
        return snap

    @property
    def current(self) -> Optional[ParticipationSnapshot]:
        return self._current

    def recent(self, n: int = 10) -> list:
        return list(self._history)[-n:]
