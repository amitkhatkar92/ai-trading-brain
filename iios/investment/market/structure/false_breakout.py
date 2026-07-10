"""iios/investment/market/structure/false_breakout.py
Detect false/failed breakouts.

A breakout fails when price closes beyond a zone, then within N bars
closes back inside the zone.
"""
from __future__ import annotations

import logging
from typing import List

from iios.investment.market.structure.models import (
    Bar,
    BreakoutEvent,
    BreakoutStatus,
    BreakoutType,
    ZoneType,
)

logger = logging.getLogger(__name__)


class FalseBreakoutDetector:
    """Detect when a confirmed breakout reverses and re-enters the zone."""

    def __init__(
        self,
        lookback_bars: int = 3,
        reentry_pct: float = 0.0,
    ) -> None:
        self._lookback = lookback_bars
        self._reentry_pct = reentry_pct

    def check(
        self,
        event: BreakoutEvent,
        bars: List[Bar],
    ) -> bool:
        """True if the breakout has failed (price returned inside zone)."""
        if event.status == BreakoutStatus.FAILED:
            return True
        if event.status not in (BreakoutStatus.CONFIRMED, BreakoutStatus.RETESTING):
            return False

        zone = event.zone
        trigger_idx = event.trigger_index
        check_start = trigger_idx + 1
        check_bars = [b for b in bars if check_start <= b.index <= trigger_idx + self._lookback]

        for bar in check_bars:
            if self._has_reentered(event, bar):
                return True
        return False

    def update_events(
        self,
        events: List[BreakoutEvent],
        bars: List[Bar],
    ) -> List[BreakoutEvent]:
        """Update the status of all pending breakout events."""
        updated: List[BreakoutEvent] = []
        for event in events:
            if event.status == BreakoutStatus.CONFIRMED:
                if self.check(event, bars):
                    # Mark as failed
                    from dataclasses import replace
                    event = replace(event, status=BreakoutStatus.FAILED)
                else:
                    # Check for retest
                    retest_bar = self._find_retest(event, bars)
                    if retest_bar is not None:
                        from dataclasses import replace
                        event = replace(
                            event,
                            status=BreakoutStatus.RETESTING,
                            retest_price=retest_bar.close,
                            retest_index=retest_bar.index,
                        )
            updated.append(event)
        return updated

    # ── Private helpers ───────────────────────────────────────────────────

    def _has_reentered(self, event: BreakoutEvent, bar: Bar) -> bool:
        """True if bar's close is back inside the original zone."""
        zone = event.zone
        lower = zone.lower * (1.0 - self._reentry_pct)
        upper = zone.upper * (1.0 + self._reentry_pct)
        return lower <= bar.close <= upper

    def _find_retest(
        self,
        event: BreakoutEvent,
        bars: List[Bar],
    ) -> Bar | None:
        """Find a bar that retested the zone edge without fully re-entering."""
        zone = event.zone
        tolerance = zone.width * 0.3
        trigger_idx = event.trigger_index

        for bar in bars:
            if bar.index <= trigger_idx:
                continue
            # Bullish breakout: retest = price comes back near zone.upper from above
            if event.breakout_type == BreakoutType.BULLISH:
                if zone.upper - tolerance <= bar.low <= zone.upper + tolerance:
                    return bar
            # Bearish breakout: retest = price comes back near zone.lower from below
            elif event.breakout_type == BreakoutType.BEARISH:
                if zone.lower - tolerance <= bar.high <= zone.lower + tolerance:
                    return bar
        return None
