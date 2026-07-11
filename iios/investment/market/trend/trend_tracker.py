"""iios/investment/market/trend/trend_tracker.py
Stateful tracker that processes consecutive MarketStructureSnapshot objects.
"""
from __future__ import annotations

import logging
from collections import deque
from typing import List, Optional, TYPE_CHECKING

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.structure.models import SwingType
from iios.investment.market.trend.models import (
    ImpulseQuality,
    CorrectionQuality,
    TrendLegMetrics,
)

if TYPE_CHECKING:
    from iios.investment.market.structure.models import MarketStructureSnapshot

logger = logging.getLogger(__name__)

_MAX_LEGS = 10


class TrendTracker:
    """
    Stateful tracker that processes consecutive MarketStructureSnapshot objects
    and maintains enough history to compute trend leg metrics.
    """

    def __init__(self, window: int = 30) -> None:
        self._window = window
        self._history: deque["MarketStructureSnapshot"] = deque(maxlen=window)

    def update(self, structure: "MarketStructureSnapshot") -> None:
        """Add new structure snapshot to rolling history."""
        self._history.append(structure)

    def compute_leg_metrics(self) -> List[TrendLegMetrics]:
        """
        Compute leg metrics from the swing sequence in the latest structure snapshot.
        Returns last 10 legs max (most recent last).
        """
        if not self._history:
            return []

        latest = self._history[-1]
        swing_seq = latest.swing_sequence
        direction = latest.trend.direction

        # Merge highs + lows, sort by index (ascending)
        all_swings = list(swing_seq.highs) + list(swing_seq.lows)
        if len(all_swings) < 2:
            return []

        all_swings.sort(key=lambda s: s.index)

        # Deduplicate by index (keep first occurrence)
        seen: set = set()
        unique_swings = []
        for s in all_swings:
            if s.index not in seen:
                seen.add(s.index)
                unique_swings.append(s)

        if len(unique_swings) < 2:
            return []

        # Compute raw leg displacements
        raw_legs = []
        for i in range(len(unique_swings) - 1):
            a = unique_swings[i]
            b = unique_swings[i + 1]
            displacement = abs(b.price - a.price)
            bars = max(1, b.index - a.index)
            velocity = displacement / bars

            # Determine if this leg is an impulse
            if direction == TrendDirection.UP:
                # LOW→HIGH = impulse, HIGH→LOW = correction
                is_impulse = (a.swing_type == SwingType.LOW and b.swing_type == SwingType.HIGH)
            elif direction == TrendDirection.DOWN:
                # HIGH→LOW = impulse, LOW→HIGH = correction
                is_impulse = (a.swing_type == SwingType.HIGH and b.swing_type == SwingType.LOW)
            else:
                # For sideways/undefined, alternate; longer leg is impulse
                is_impulse = True  # treat all as impulse for neutral direction

            raw_legs.append({
                "a": a,
                "b": b,
                "displacement": displacement,
                "bars": bars,
                "velocity": velocity,
                "is_impulse": is_impulse,
                "direction": direction,
            })

        # Compute historical average velocity for quality classification
        velocities = [l["velocity"] for l in raw_legs if l["velocity"] > 0]
        avg_velocity = sum(velocities) / len(velocities) if velocities else 1.0

        # Build TrendLegMetrics with retracement and quality
        leg_metrics: List[TrendLegMetrics] = []
        for i, raw in enumerate(raw_legs):
            # Retracement: next leg displacement / this leg displacement
            if i + 1 < len(raw_legs):
                retracement_pct = raw_legs[i + 1]["displacement"] / max(1e-9, raw["displacement"])
            else:
                retracement_pct = 0.0

            impulse_q = _classify_impulse(
                raw["velocity"], avg_velocity,
                raw["displacement"],
                raw_legs[i - 1]["displacement"] if i > 0 else None,
            )
            correction_q = _classify_correction(retracement_pct)

            leg_metrics.append(TrendLegMetrics(
                leg_number=i + 1,
                is_impulse=raw["is_impulse"],
                direction=raw["direction"],
                displacement=raw["displacement"],
                bars=raw["bars"],
                velocity=raw["velocity"],
                retracement_pct=retracement_pct,
                impulse_quality=impulse_q,
                correction_quality=correction_q,
            ))

        # Return last _MAX_LEGS, most recent last
        return leg_metrics[-_MAX_LEGS:]

    def latest_structure(self) -> Optional["MarketStructureSnapshot"]:
        if not self._history:
            return None
        return self._history[-1]

    def prev_structure(self) -> Optional["MarketStructureSnapshot"]:
        if len(self._history) < 2:
            return None
        return self._history[-2]

    def history(self) -> List["MarketStructureSnapshot"]:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()


def _classify_impulse(
    velocity: float,
    avg_velocity: float,
    displacement: float,
    prev_displacement: Optional[float],
) -> ImpulseQuality:
    if avg_velocity > 0 and velocity >= 1.5 * avg_velocity:
        return ImpulseQuality.STRONG
    if prev_displacement is not None and prev_displacement > 0:
        if displacement > prev_displacement * 1.10:
            return ImpulseQuality.STRONG
        if displacement < prev_displacement * 0.50:
            return ImpulseQuality.WEAK
    if avg_velocity > 0 and velocity < 0.5 * avg_velocity:
        return ImpulseQuality.WEAK
    return ImpulseQuality.MODERATE


def _classify_correction(retracement_pct: float) -> CorrectionQuality:
    if retracement_pct >= 1.0:
        return CorrectionQuality.FAILED
    if retracement_pct > 0.618:
        return CorrectionQuality.DEEP
    if retracement_pct >= 0.382:
        return CorrectionQuality.NORMAL
    return CorrectionQuality.SHALLOW
