"""iios/investment/market/models/market_signal.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


class SignalType:
    TREND         = "trend"
    BREADTH       = "breadth"
    VOLATILITY    = "volatility"
    LIQUIDITY     = "liquidity"
    CORRELATION   = "correlation"
    REGIME_CHANGE = "regime_change"
    SENTIMENT     = "sentiment"
    CUSTOM        = "custom"


class SignalStrength:
    STRONG   = "strong"
    MODERATE = "moderate"
    WEAK     = "weak"


@dataclass
class MarketSignal:
    """A single market intelligence signal."""

    signal_id:   str   = field(default_factory=lambda: str(uuid.uuid4()))
    market_id:   str   = ""
    signal_type: str   = SignalType.CUSTOM
    label:       str   = ""
    description: str   = ""
    strength:    str   = SignalStrength.MODERATE
    confidence:  float = 0.5
    direction:   str   = "neutral"   # up / down / neutral
    value:       float | None = None
    metadata:    dict[str, Any] = field(default_factory=dict)
    timestamp:   float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id":   self.signal_id,
            "market_id":   self.market_id,
            "signal_type": self.signal_type,
            "label":       self.label,
            "description": self.description,
            "strength":    self.strength,
            "confidence":  self.confidence,
            "direction":   self.direction,
            "value":       self.value,
            "metadata":    self.metadata,
            "timestamp":   self.timestamp,
        }
