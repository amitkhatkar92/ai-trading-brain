"""iios/investment/market/breadth/divergence_engine.py
Orchestrates divergence detection and emits BreadthEvents.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.market.breadth.models import (
    BreadthData,
    BreadthEvent,
    BreadthEventType,
    DivergenceSignal,
    DivergenceType,
    MarketHealthSnapshot,
    ParticipationSnapshot,
)
from iios.investment.market.breadth.divergence_detector import DivergenceDetector
from iios.investment.market.breadth.divergence_history import DivergenceHistory


class DivergenceEngine:
    """Runs divergence detection and generates events for confirmed signals."""

    def __init__(
        self,
        detector: Optional[DivergenceDetector] = None,
        history_size: int = 200,
    ) -> None:
        self._detector = detector or DivergenceDetector()
        self._history  = DivergenceHistory(maxlen=history_size)
        self._prev_confirmed_types: set[DivergenceType] = set()

    def update(
        self,
        breadth: BreadthData,
        participation: ParticipationSnapshot,
        health: MarketHealthSnapshot,
        bar_index: int,
        universe_id: str,
        market_regime: Optional[str] = None,
        trend_stage: Optional[str] = None,
    ) -> tuple[List[DivergenceSignal], List[BreadthEvent]]:
        signals = self._detector.detect(
            breadth, participation, health, market_regime, trend_stage
        )
        self._history.append(signals)

        events: List[BreadthEvent] = []
        confirmed_types = {s.divergence_type for s in signals if s.confirmed}

        # Emit event only when a divergence becomes newly confirmed
        new_confirmed = confirmed_types - self._prev_confirmed_types
        for dt in new_confirmed:
            sig = next(s for s in signals if s.divergence_type == dt)
            is_bull = dt.value.startswith("bull") or "bullish" in dt.value
            ev_type = (
                BreadthEventType.BULLISH_DIVERGENCE if is_bull
                else BreadthEventType.BEARISH_DIVERGENCE
            )
            events.append(BreadthEvent(
                event_type=ev_type,
                universe_id=universe_id,
                bar_index=bar_index,
                severity=sig.strength,
                description=sig.description,
            ))

        self._prev_confirmed_types = confirmed_types
        return signals, events
