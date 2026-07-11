"""iios/investment/market/trend/trend_transition.py
Detects and records trend-level transitions between lifecycle stages.
"""
from __future__ import annotations

import time
from typing import Optional

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.trend.models import (
    TrendStage,
    TrendTransitionType,
    TrendTransitionRecord,
)
from iios.investment.market.trend.trend_stage import is_advancing, is_declining


class TrendTransitionDetector:
    """
    Detects and records trend-level transitions between lifecycle stages.
    """

    def detect(
        self,
        prev_stage: TrendStage,
        new_stage: TrendStage,
        prev_direction: TrendDirection,
        new_direction: TrendDirection,
        confidence: float,
        bar_index: int,
        symbol: str,
        timeframe: str,
    ) -> Optional[TrendTransitionRecord]:
        """
        Returns a TrendTransitionRecord if a meaningful transition occurred.
        Returns None if stage unchanged AND direction unchanged.
        """
        stage_changed = prev_stage != new_stage
        direction_changed = prev_direction != new_direction

        if not stage_changed and not direction_changed:
            return None

        # Determine transition type
        if new_stage == TrendStage.COMPLETED and new_direction != prev_direction:
            transition_type = TrendTransitionType.RESTART
        elif direction_changed:
            transition_type = TrendTransitionType.REVERSAL
        elif stage_changed and is_advancing(prev_stage, new_stage):
            transition_type = TrendTransitionType.STAGE_ADVANCE
        elif stage_changed and is_declining(prev_stage, new_stage):
            transition_type = TrendTransitionType.STAGE_DECLINE
        else:
            transition_type = TrendTransitionType.STAGE_ADVANCE

        trigger_parts = []
        if stage_changed:
            trigger_parts.append(f"stage:{prev_stage.value}→{new_stage.value}")
        if direction_changed:
            trigger_parts.append(f"dir:{prev_direction.value}→{new_direction.value}")

        return TrendTransitionRecord(
            transition_type=transition_type,
            from_stage=prev_stage,
            to_stage=new_stage,
            from_direction=prev_direction,
            to_direction=new_direction,
            confidence=confidence,
            timestamp=time.time(),
            bar_index=bar_index,
            trigger="; ".join(trigger_parts),
        )
