"""iios/investment/market/liquidity/liquidity_event.py
Detects LiquidityEvent objects from current VolumeBar + analysis results.
"""
from __future__ import annotations

import logging
from typing import List

from iios.investment.market.liquidity.models import (
    VolumeBar, VolumeProfile, ParticipationSnapshot, EffortResultAnalysis,
    LiquidityEvent, LiquidityEventType, VolumeTrend,
)

logger = logging.getLogger(__name__)


class LiquidityEventDetector:
    """
    Detects LiquidityEvent objects from current VolumeBar + analysis results.
    Stateless — pure computation.
    """

    VOLUME_SPIKE_THRESHOLD   = 2.5
    VOLUME_VACUUM_THRESHOLD  = 0.30
    HIGH_PARTICIPATION_SCORE = 80.0
    LOW_PARTICIPATION_SCORE  = 25.0

    _SEVERITY_MAP = {
        LiquidityEventType.SHOCK:               1.0,
        LiquidityEventType.BUYING_CLIMAX:       0.9,
        LiquidityEventType.SELLING_CLIMAX:      0.9,
        LiquidityEventType.ABSORPTION_DETECTED: 0.7,
        LiquidityEventType.VOLUME_SPIKE:        0.6,
        LiquidityEventType.VOLUME_VACUUM:       0.6,
        LiquidityEventType.HIGH_PARTICIPATION:  0.5,
        LiquidityEventType.LOW_PARTICIPATION:   0.5,
        LiquidityEventType.EXPANSION:           0.4,
        LiquidityEventType.DRY_UP:              0.4,
    }

    def detect(
        self,
        vbar: VolumeBar,
        volume_profile: VolumeProfile,
        participation: ParticipationSnapshot,
        er_analysis: EffortResultAnalysis,
        symbol: str,
        timeframe: str,
    ) -> List[LiquidityEvent]:
        events: List[LiquidityEvent] = []

        def _make(etype: LiquidityEventType, desc: str = "") -> LiquidityEvent:
            return LiquidityEvent(
                event_type=etype,
                symbol=symbol,
                timeframe=timeframe,
                timestamp=vbar.timestamp,
                bar_index=vbar.index,
                severity=self._SEVERITY_MAP.get(etype, 0.5),
                description=desc,
            )

        # SHOCK: extreme volume + large price move
        if vbar.relative_volume > 3.5 and abs(vbar.price_change_pct) > 2.0:
            events.append(_make(LiquidityEventType.SHOCK, "Extreme volume shock"))

        # BUYING_CLIMAX
        if er_analysis.is_climax and er_analysis.initiative_buying:
            events.append(_make(LiquidityEventType.BUYING_CLIMAX, "Buying climax detected"))

        # SELLING_CLIMAX
        if er_analysis.is_climax and er_analysis.initiative_selling:
            events.append(_make(LiquidityEventType.SELLING_CLIMAX, "Selling climax detected"))

        # ABSORPTION_DETECTED
        if er_analysis.is_absorption and er_analysis.absorption_strength > 0.5:
            events.append(_make(LiquidityEventType.ABSORPTION_DETECTED, "Absorption detected"))

        # VOLUME_SPIKE
        if vbar.relative_volume > self.VOLUME_SPIKE_THRESHOLD:
            events.append(_make(LiquidityEventType.VOLUME_SPIKE, "Volume spike"))

        # VOLUME_VACUUM
        if vbar.relative_volume < self.VOLUME_VACUUM_THRESHOLD:
            events.append(_make(LiquidityEventType.VOLUME_VACUUM, "Volume vacuum"))

        # HIGH_PARTICIPATION
        if participation.participation_score > self.HIGH_PARTICIPATION_SCORE:
            events.append(_make(LiquidityEventType.HIGH_PARTICIPATION, "High participation"))

        # LOW_PARTICIPATION
        if participation.participation_score < self.LOW_PARTICIPATION_SCORE:
            events.append(_make(LiquidityEventType.LOW_PARTICIPATION, "Low participation"))

        # EXPANSION
        if (
            volume_profile.volume_trend == VolumeTrend.EXPANDING
            and vbar.relative_volume > 1.5
        ):
            events.append(_make(LiquidityEventType.EXPANSION, "Volume expansion"))

        # DRY_UP
        if volume_profile.volume_trend == VolumeTrend.DRYING_UP:
            events.append(_make(LiquidityEventType.DRY_UP, "Volume drying up"))

        return events
