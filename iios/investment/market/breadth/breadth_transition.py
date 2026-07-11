"""iios/investment/market/breadth/breadth_transition.py
Detects regime transitions and emits BreadthEvent.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.market.breadth.models import (
    BreadthEvent,
    BreadthEventType,
    BreadthRegimeSnapshot,
    BreadthRegimeType,
)
from iios.investment.market.breadth.breadth_regime import regime_severity


class BreadthTransitionDetector:
    def __init__(self) -> None:
        self._regime: BreadthRegimeType     = BreadthRegimeType.UNKNOWN
        self._duration_bars: int            = 0
        self._previous_regime: Optional[BreadthRegimeType] = None

    @property
    def current_regime(self) -> BreadthRegimeType:
        return self._regime

    @property
    def duration_bars(self) -> int:
        return self._duration_bars

    @property
    def previous_regime(self) -> Optional[BreadthRegimeType]:
        return self._previous_regime

    def update(
        self,
        new_snapshot: BreadthRegimeSnapshot,
        bar_index: int,
        universe_id: str,
    ) -> List[BreadthEvent]:
        events: List[BreadthEvent] = []
        new_regime = new_snapshot.regime

        if new_regime != self._regime:
            events.extend(
                self._build_transition_events(new_regime, bar_index, universe_id)
            )
            self._previous_regime = self._regime
            self._regime          = new_regime
            self._duration_bars   = 1
        else:
            self._duration_bars += 1

        return events

    # ── Internal ──────────────────────────────────────────────────────────

    def _build_transition_events(
        self,
        new_regime: BreadthRegimeType,
        bar_index: int,
        universe_id: str,
    ) -> List[BreadthEvent]:
        events: List[BreadthEvent] = []
        prev = self._regime

        severity = abs(regime_severity(new_regime) - regime_severity(prev)) / 8.0

        # Always emit a regime-change event
        events.append(BreadthEvent(
            event_type=BreadthEventType.REGIME_CHANGE,
            universe_id=universe_id,
            bar_index=bar_index,
            severity=max(0.1, min(1.0, severity)),
            from_regime=prev,
            to_regime=new_regime,
            description=f"Breadth regime changed from {prev.value} to {new_regime.value}",
        ))

        # Supplemental health event
        new_s  = regime_severity(new_regime)
        prev_s = regime_severity(prev)

        if new_s > prev_s:
            events.append(BreadthEvent(
                event_type=BreadthEventType.HEALTH_IMPROVEMENT,
                universe_id=universe_id,
                bar_index=bar_index,
                severity=severity,
                from_regime=prev,
                to_regime=new_regime,
                description="Market breadth health improved",
            ))
        elif new_s < prev_s:
            events.append(BreadthEvent(
                event_type=BreadthEventType.HEALTH_DETERIORATION,
                universe_id=universe_id,
                bar_index=bar_index,
                severity=severity,
                from_regime=prev,
                to_regime=new_regime,
                description="Market breadth health deteriorated",
            ))

        # Specific regime events
        if new_regime in (BreadthRegimeType.BROAD_RALLY, BreadthRegimeType.STRONG_PARTICIPATION):
            events.append(BreadthEvent(
                event_type=BreadthEventType.BROAD_RALLY,
                universe_id=universe_id,
                bar_index=bar_index,
                severity=0.8,
                description="Broad rally detected",
            ))
        elif new_regime == BreadthRegimeType.NARROW_RALLY:
            events.append(BreadthEvent(
                event_type=BreadthEventType.NARROW_RALLY,
                universe_id=universe_id,
                bar_index=bar_index,
                severity=0.5,
                description="Narrow rally — limited sector participation",
            ))
        elif new_regime in (BreadthRegimeType.BROAD_SELLOFF, BreadthRegimeType.VERY_WEAK_PARTICIPATION):
            events.append(BreadthEvent(
                event_type=BreadthEventType.BROAD_SELLOFF,
                universe_id=universe_id,
                bar_index=bar_index,
                severity=0.9,
                description="Broad selloff detected",
            ))
        elif new_regime in (BreadthRegimeType.NARROW_SELLOFF, BreadthRegimeType.WEAK_PARTICIPATION):
            events.append(BreadthEvent(
                event_type=BreadthEventType.NARROW_SELLOFF,
                universe_id=universe_id,
                bar_index=bar_index,
                severity=0.5,
                description="Narrow selloff — limited sector participation",
            ))

        return events
