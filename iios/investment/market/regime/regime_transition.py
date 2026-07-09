"""iios/investment/market/regime/regime_transition.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.market.market_constants import MarketRegime


@dataclass
class RegimeTransition:
    """Records a market regime change event."""

    transition_id: str         = field(default_factory=lambda: str(uuid.uuid4()))
    market_id:     str         = ""
    from_regime:   MarketRegime = MarketRegime.UNKNOWN
    to_regime:     MarketRegime = MarketRegime.UNKNOWN
    confidence:    float        = 0.0
    trigger:       str          = ""
    duration_bars: int          = 0   # bars the previous regime lasted
    metadata:      dict[str, Any] = field(default_factory=dict)
    timestamp:     float        = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "market_id":     self.market_id,
            "from_regime":   self.from_regime.value,
            "to_regime":     self.to_regime.value,
            "confidence":    self.confidence,
            "trigger":       self.trigger,
            "duration_bars": self.duration_bars,
            "metadata":      self.metadata,
            "timestamp":     self.timestamp,
        }
