"""iios/integration/market_data/core/market_statistics.py

Session-level and rolling market statistics for an instrument.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.market_data.market_data_constants import (
    DataQuality,
    Exchange,
    InstrumentType,
)


@dataclass
class MarketStatistics:
    """
    Computed/aggregated statistics over a period.
    May be supplied directly by a provider or computed by the normalization
    layer from raw data.
    """

    symbol:          str            = ""
    exchange:        Exchange       = Exchange.UNKNOWN
    instrument_type: InstrumentType = InstrumentType.EQUITY
    period_start:    float          = 0.0
    period_end:      float          = 0.0

    # Volume
    total_volume:    float          = 0.0
    avg_volume:      float          = 0.0
    median_volume:   float          = 0.0
    peak_volume:     float          = 0.0

    # Price
    vwap:            float          = 0.0
    twap:            float          = 0.0
    avg_price:       float          = 0.0
    price_std_dev:   float          = 0.0

    # Spread
    avg_spread:      float          = 0.0
    min_spread:      float          = 0.0
    max_spread:      float          = 0.0

    # Activity
    tick_count:      int            = 0
    trade_count:     int            = 0
    trades_per_min:  float          = 0.0
    volatility:      float          = 0.0     # annualised HV (%)
    avg_trade_size:  float          = 0.0

    # Extremes
    high:            float          = 0.0
    low:             float          = 0.0
    open:            float          = 0.0
    close:           float          = 0.0

    computed_at:     float          = field(default_factory=time.time)
    provider_id:     str            = ""
    quality:         DataQuality    = DataQuality.UNKNOWN
    stat_id:         str            = field(default_factory=lambda: str(uuid.uuid4()))
    metadata:        dict[str, Any] = field(default_factory=dict)

    def period_seconds(self) -> float:
        if self.period_end > self.period_start:
            return self.period_end - self.period_start
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stat_id":        self.stat_id,
            "symbol":         self.symbol,
            "exchange":       self.exchange.value,
            "period_start":   self.period_start,
            "period_end":     self.period_end,
            "total_volume":   self.total_volume,
            "avg_volume":     self.avg_volume,
            "vwap":           self.vwap,
            "twap":           self.twap,
            "avg_spread":     self.avg_spread,
            "tick_count":     self.tick_count,
            "trade_count":    self.trade_count,
            "trades_per_min": round(self.trades_per_min, 4),
            "volatility":     round(self.volatility, 4),
            "high":           self.high,
            "low":            self.low,
            "open":           self.open,
            "close":          self.close,
            "computed_at":    self.computed_at,
            "provider_id":    self.provider_id,
        }
