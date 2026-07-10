"""iios/investment/market/structure/breakout_engine.py
Main breakout detection and management engine.
"""
from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from iios.investment.market.structure.breakout_classifier import BreakoutClassifier
from iios.investment.market.structure.breakout_statistics import BreakoutStatistics
from iios.investment.market.structure.false_breakout import FalseBreakoutDetector
from iios.investment.market.structure.models import (
    Bar,
    BreakoutEvent,
    BreakoutStatus,
    Zone,
    ZoneType,
)
from iios.investment.market.structure.zone_registry import ZoneRegistry

logger = logging.getLogger(__name__)


class BreakoutEngine:
    """Detect new zone breakouts and manage the lifecycle of breakout events."""

    def __init__(
        self,
        classifier: BreakoutClassifier,
        false_detector: FalseBreakoutDetector,
        stats: BreakoutStatistics,
        zone_registry: ZoneRegistry,
    ) -> None:
        self._classifier = classifier
        self._false_detector = false_detector
        self._stats = stats
        self._registry = zone_registry
        self._active_events: List[BreakoutEvent] = []

    def update(
        self,
        bars: List[Bar],
        current_bar: Bar,
    ) -> Optional[BreakoutEvent]:
        """Check for new breakouts and update existing events. Returns latest event."""
        if not bars:
            return None

        avg_vol = self._compute_avg_volume(bars)

        # Update existing events for false-breakout detection
        self._active_events = self._false_detector.update_events(self._active_events, bars)

        # Check each zone for a new breakout
        new_event: Optional[BreakoutEvent] = None
        for zone in self._registry.get_all():
            event = self._check_zone_break(zone, current_bar, bars)
            if event is not None:
                # Avoid duplicate events for the same zone+bar
                already_active = any(
                    e.zone.zone_id == zone.zone_id
                    and e.trigger_index == current_bar.index
                    for e in self._active_events
                )
                if not already_active:
                    self._active_events.append(event)
                    self._stats.record(event)
                    new_event = event

        # Evict resolved events (keep only last 20)
        self._active_events = self._active_events[-20:]

        return new_event

    def get_active_breakout(self) -> Optional[BreakoutEvent]:
        """Return the most recently confirmed breakout that has not failed."""
        confirmed = [
            e for e in reversed(self._active_events)
            if e.status == BreakoutStatus.CONFIRMED
        ]
        return confirmed[0] if confirmed else None

    def get_recent_breakouts(self, n: int = 5) -> List[BreakoutEvent]:
        return list(reversed(self._active_events))[:n]

    # ── Private helpers ───────────────────────────────────────────────────

    def _check_zone_break(
        self,
        zone: Zone,
        bar: Bar,
        bars: List[Bar],
    ) -> Optional[BreakoutEvent]:
        """Return a BreakoutEvent if bar breaks zone, else None."""
        if zone.broken:
            return None

        avg_vol = self._compute_avg_volume(bars)
        is_resistance = zone.zone_type in (
            ZoneType.RESISTANCE, ZoneType.SUPPLY, ZoneType.BROKEN_SUPPORT
        )
        is_support = zone.zone_type in (
            ZoneType.SUPPORT, ZoneType.DEMAND, ZoneType.BROKEN_RESISTANCE
        )

        broke_up = is_resistance and bar.close > zone.upper
        broke_down = is_support and bar.close < zone.lower

        if not broke_up and not broke_down:
            return None

        close_beyond = (
            bar.close - zone.upper if broke_up else zone.lower - bar.close
        )
        from iios.investment.market.structure.models import SwingSequence
        btype = self._classifier.classify(zone, bar, SwingSequence(), avg_vol)

        event = BreakoutEvent(
            breakout_id=str(uuid.uuid4())[:8],
            breakout_type=btype,
            status=BreakoutStatus.CONFIRMED,
            zone=zone,
            trigger_index=bar.index,
            trigger_price=bar.close,
            trigger_volume=bar.volume,
            avg_volume_20=avg_vol,
            close_beyond=close_beyond,
        )
        return event

    def _compute_avg_volume(self, bars: List[Bar], n: int = 20) -> float:
        recent = bars[-n:] if len(bars) >= n else bars
        if not recent:
            return 0.0
        return sum(b.volume for b in recent) / len(recent)
