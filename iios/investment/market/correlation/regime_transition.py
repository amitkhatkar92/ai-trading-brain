"""iios/investment/market/correlation/regime_transition.py
Detects correlation regime transitions and emits CorrelationEvents.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.market.correlation.models import (
    CorrelationEvent,
    CorrelationEventType,
    CorrelationRegimeSnapshot,
    CorrelationRegimeType,
)
from iios.investment.market.correlation.correlation_regime import regime_severity


class CorrelationRegimeTransitionDetector:
    def __init__(self) -> None:
        self._regime:         CorrelationRegimeType     = CorrelationRegimeType.UNKNOWN
        self._duration_bars:  int                       = 0
        self._previous_regime: Optional[CorrelationRegimeType] = None

    @property
    def current_regime(self) -> CorrelationRegimeType:
        return self._regime

    @property
    def duration_bars(self) -> int:
        return self._duration_bars

    @property
    def previous_regime(self) -> Optional[CorrelationRegimeType]:
        return self._previous_regime

    def update(
        self,
        new_snapshot: CorrelationRegimeSnapshot,
        bar_index: int,
    ) -> List[CorrelationEvent]:
        events: List[CorrelationEvent] = []
        new_regime = new_snapshot.regime

        if new_regime != self._regime:
            events.extend(self._build_events(new_regime, bar_index))
            self._previous_regime = self._regime
            self._regime          = new_regime
            self._duration_bars   = 1
        else:
            self._duration_bars += 1

        return events

    # ── Internal ──────────────────────────────────────────────────────────

    def _build_events(
        self,
        new_regime: CorrelationRegimeType,
        bar_index: int,
    ) -> List[CorrelationEvent]:
        prev = self._regime
        severity = abs(regime_severity(new_regime) - regime_severity(prev)) / 7.0
        events: List[CorrelationEvent] = []

        # Regime change event
        events.append(CorrelationEvent(
            event_type=CorrelationEventType.REGIME_CHANGE,
            bar_index=bar_index,
            severity=max(0.1, min(1.0, severity)),
            from_regime=prev,
            to_regime=new_regime,
            description=f"Correlation regime: {prev.value} → {new_regime.value}",
        ))

        # Specific regime events
        if new_regime == CorrelationRegimeType.FLIGHT_TO_SAFETY:
            events.append(CorrelationEvent(
                event_type=CorrelationEventType.FLIGHT_TO_SAFETY,
                bar_index=bar_index,
                severity=0.90,
                from_regime=prev,
                to_regime=new_regime,
                description="Flight to safety detected",
            ))

        elif new_regime == CorrelationRegimeType.CORRELATION_BREAKDOWN:
            events.append(CorrelationEvent(
                event_type=CorrelationEventType.CORRELATION_BREAKDOWN,
                bar_index=bar_index,
                severity=0.75,
                from_regime=prev,
                to_regime=new_regime,
                description="Correlation breakdown — regime shift in correlations",
            ))

        elif new_regime == CorrelationRegimeType.HIGHLY_CORRELATED:
            events.append(CorrelationEvent(
                event_type=CorrelationEventType.CORRELATION_SPIKE,
                bar_index=bar_index,
                severity=0.80,
                from_regime=prev,
                to_regime=new_regime,
                description="Correlation spike — all assets moving together",
            ))

        elif new_regime == CorrelationRegimeType.RISK_ON:
            events.append(CorrelationEvent(
                event_type=CorrelationEventType.RISK_ON_TRANSITION,
                bar_index=bar_index,
                severity=0.60,
                from_regime=prev,
                to_regime=new_regime,
                description="Risk-on transition",
            ))

        elif new_regime == CorrelationRegimeType.RISK_OFF:
            events.append(CorrelationEvent(
                event_type=CorrelationEventType.RISK_OFF_TRANSITION,
                bar_index=bar_index,
                severity=0.70,
                from_regime=prev,
                to_regime=new_regime,
                description="Risk-off transition",
            ))

        elif new_regime == CorrelationRegimeType.DIVERSIFICATION_COLLAPSE if False else False:
            pass  # future event type

        return events
