"""iios/investment/market/liquidity/liquidity_transition.py
Tracks regime-level liquidity changes via LiquidityTransition.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional

from iios.investment.market.liquidity.models import LiquidityProfile

logger = logging.getLogger(__name__)


class LiquidityTransitionType(str, Enum):
    """Tracks regime-level liquidity changes. Separate from LiquidityEventType."""
    IMPROVING  = "improving"
    STABLE     = "stable"
    DEGRADING  = "degrading"
    SHOCK      = "shock"
    RECOVERING = "recovering"


@dataclass
class LiquidityTransition:
    transition_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    transition_type: LiquidityTransitionType = LiquidityTransitionType.STABLE
    from_quality: float = 50.0
    to_quality: float = 50.0
    magnitude: float = 0.0     # abs change in quality
    timestamp: float = field(default_factory=time.time)
    bar_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "transition_type": self.transition_type.value,
            "from_quality": self.from_quality,
            "to_quality": self.to_quality,
            "magnitude": self.magnitude,
            "timestamp": self.timestamp,
            "bar_index": self.bar_index,
        }


class LiquidityTransitionDetector:
    """
    Detects transitions in liquidity quality from sequential LiquidityProfile updates.
    Stateful — maintains previous quality.
    """

    def __init__(self, change_threshold: float = 10.0) -> None:
        self._change_threshold = change_threshold
        self._prev_quality: Optional[float] = None
        self._last_shock: bool = False

    def detect(
        self,
        profile: LiquidityProfile,
        bar_index: int,
    ) -> Optional[LiquidityTransition]:
        """
        Returns a transition if quality changed by >= change_threshold points.
        """
        new_quality = profile.quality

        if self._prev_quality is None:
            self._prev_quality = new_quality
            return None

        delta = new_quality - self._prev_quality
        abs_delta = abs(delta)

        if abs_delta < self._change_threshold:
            self._prev_quality = new_quality
            return None

        # Determine transition type
        if delta <= -25.0:
            ttype = LiquidityTransitionType.SHOCK
            self._last_shock = True
        elif delta >= 20.0 and self._last_shock:
            ttype = LiquidityTransitionType.RECOVERING
            self._last_shock = False
        elif delta >= 10.0:
            ttype = LiquidityTransitionType.IMPROVING
        elif delta <= -10.0:
            ttype = LiquidityTransitionType.DEGRADING
        else:
            self._prev_quality = new_quality
            return None

        transition = LiquidityTransition(
            transition_type=ttype,
            from_quality=self._prev_quality,
            to_quality=new_quality,
            magnitude=abs_delta,
            bar_index=bar_index,
        )
        self._prev_quality = new_quality
        return transition
