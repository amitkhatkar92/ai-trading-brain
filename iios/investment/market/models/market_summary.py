"""iios/investment/market/models/market_summary.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.market.market_constants import (
    MarketRegime,
    MarketStatus,
    TrendDirection,
)


@dataclass
class MarketSummary:
    """High-level snapshot of a market suitable for dashboards."""

    summary_id:        str          = field(default_factory=lambda: str(uuid.uuid4()))
    market_id:         str          = ""
    name:              str          = ""
    status:            MarketStatus  = MarketStatus.UNKNOWN
    regime:            MarketRegime  = MarketRegime.UNKNOWN
    regime_confidence: float         = 0.0
    trend:             TrendDirection = TrendDirection.UNDEFINED
    health_score:      float         = 50.0
    quality_score:     float         = 50.0
    opportunities:     list[str]     = field(default_factory=list)
    threats:           list[str]     = field(default_factory=list)
    key_observations:  list[str]     = field(default_factory=list)
    metadata:          dict[str, Any] = field(default_factory=dict)
    created_at:        float         = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_id":        self.summary_id,
            "market_id":         self.market_id,
            "name":              self.name,
            "status":            self.status.value,
            "regime":            self.regime.value,
            "regime_confidence": self.regime_confidence,
            "trend":             self.trend.value,
            "health_score":      self.health_score,
            "quality_score":     self.quality_score,
            "opportunities":     self.opportunities,
            "threats":           self.threats,
            "key_observations":  self.key_observations,
            "metadata":          self.metadata,
            "created_at":        self.created_at,
        }
