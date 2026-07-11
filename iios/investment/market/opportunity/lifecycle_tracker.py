"""iios/investment/market/opportunity/lifecycle_tracker.py
Tracks and advances the lifecycle stage for a single opportunity.
"""
from __future__ import annotations

from iios.investment.market.opportunity.models import (
    Opportunity,
    OpportunityEvent,
    OpportunityEventType,
    OpportunityLifecycleStage,
    OpportunityPriority,
)

# Stage advancement rules: (from_stage, composite_threshold) → to_stage
_ADVANCE: dict = {
    OpportunityLifecycleStage.DISCOVERED:    (50.0, OpportunityLifecycleStage.EMERGING),
    OpportunityLifecycleStage.EMERGING:      (60.0, OpportunityLifecycleStage.GROWING),
    OpportunityLifecycleStage.GROWING:       (70.0, OpportunityLifecycleStage.HIGH_PRIORITY),
    OpportunityLifecycleStage.HIGH_PRIORITY: (75.0, OpportunityLifecycleStage.CONFIRMED),
}

# Stage decay rules: (from_stage, decay_threshold, min_bars) → WEAKENING
_DECAY_THRESHOLD    = 40.0
_EXPIRY_THRESHOLD   = 25.0
_MIN_BARS_WEAKENING = 3

_PRIORITY_MAP = {
    OpportunityLifecycleStage.CONFIRMED:    OpportunityPriority.CRITICAL,
    OpportunityLifecycleStage.HIGH_PRIORITY: OpportunityPriority.HIGH,
    OpportunityLifecycleStage.GROWING:      OpportunityPriority.MEDIUM,
    OpportunityLifecycleStage.EMERGING:     OpportunityPriority.MEDIUM,
    OpportunityLifecycleStage.DISCOVERED:   OpportunityPriority.LOW,
    OpportunityLifecycleStage.WEAKENING:    OpportunityPriority.LOW,
    OpportunityLifecycleStage.EXPIRED:      OpportunityPriority.LOW,
    OpportunityLifecycleStage.ARCHIVED:     OpportunityPriority.LOW,
}


class LifecycleTracker:
    """Manages lifecycle transitions for one :class:`Opportunity`."""

    def __init__(self, opp: Opportunity) -> None:
        self._opp          = opp
        self._weakening_bars: int = 0

    def advance(self, bar_index: int) -> list:
        """Advance or decay lifecycle based on current composite_score.

        Returns list of :class:`OpportunityEvent` (may be empty).
        """
        score  = self._opp.composite_score
        stage  = self._opp.lifecycle_stage
        events = []

        if stage in (OpportunityLifecycleStage.EXPIRED, OpportunityLifecycleStage.ARCHIVED):
            return events

        # ── advancement ──────────────────────────────────────────────────────
        if stage in _ADVANCE:
            threshold, next_stage = _ADVANCE[stage]
            if score >= threshold:
                self._weakening_bars = 0
                events.append(self._transition(stage, next_stage, bar_index))
                return events

        # ── decay ─────────────────────────────────────────────────────────────
        if score <= _EXPIRY_THRESHOLD and stage not in (
            OpportunityLifecycleStage.DISCOVERED,
        ):
            events.append(self._transition(stage, OpportunityLifecycleStage.EXPIRED, bar_index))
            return events

        if score <= _DECAY_THRESHOLD:
            self._weakening_bars += 1
            if (
                stage not in (OpportunityLifecycleStage.WEAKENING, OpportunityLifecycleStage.EXPIRED)
                and self._weakening_bars >= _MIN_BARS_WEAKENING
            ):
                events.append(self._transition(stage, OpportunityLifecycleStage.WEAKENING, bar_index))
                return events
        else:
            self._weakening_bars = 0

        # ── weaken → expire ───────────────────────────────────────────────────
        if stage is OpportunityLifecycleStage.WEAKENING and score <= _EXPIRY_THRESHOLD:
            events.append(self._transition(stage, OpportunityLifecycleStage.EXPIRED, bar_index))

        self._opp.stage_duration_bars += 1
        self._opp.last_updated_bar     = bar_index
        return events

    # ── internal ─────────────────────────────────────────────────────────────

    def _transition(
        self,
        from_stage: OpportunityLifecycleStage,
        to_stage:   OpportunityLifecycleStage,
        bar_index:  int,
    ) -> OpportunityEvent:
        event_type = (
            OpportunityEventType.EXPIRED   if to_stage is OpportunityLifecycleStage.EXPIRED
            else OpportunityEventType.CONFIRMED if to_stage is OpportunityLifecycleStage.CONFIRMED
            else OpportunityEventType.WEAKENING if to_stage is OpportunityLifecycleStage.WEAKENING
            else OpportunityEventType.UPGRADED
        )
        self._opp.lifecycle_stage     = to_stage
        self._opp.stage_duration_bars = 1
        self._opp.last_updated_bar    = bar_index
        self._opp.priority            = _PRIORITY_MAP.get(to_stage, OpportunityPriority.LOW)
        return OpportunityEvent(
            event_type=event_type,
            opportunity_id=self._opp.opportunity_id,
            symbol=self._opp.symbol,
            bar_index=bar_index,
            description=f"{self._opp.symbol}: {from_stage.value} → {to_stage.value}",
            severity=0.8 if to_stage is OpportunityLifecycleStage.CONFIRMED else 0.5,
        )
