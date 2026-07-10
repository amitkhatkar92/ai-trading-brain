"""iios/integration/market_data/providers/provider_capabilities.py

Capability declaration for a market data provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.integration.market_data.market_data_constants import (
    CandleInterval,
    Exchange,
    InstrumentType,
    MarketDataType,
)


@dataclass
class ProviderCapabilities:
    """
    Describes what a market data provider supports.
    Registered once per provider and used by the registry to route
    data requests to the right provider.
    """

    # ── Supported exchanges & instruments ─────────────────────────────────────
    exchanges:         list[Exchange]        = field(default_factory=list)
    instrument_types:  list[InstrumentType]  = field(default_factory=list)

    # ── Data types ─────────────────────────────────────────────────────────────
    data_types:        list[MarketDataType]  = field(default_factory=list)

    # ── Streaming ──────────────────────────────────────────────────────────────
    supports_streaming:         bool         = False
    supports_order_book:        bool         = False
    supports_trade_feed:        bool         = False
    max_symbols_per_stream:     int          = 100
    max_concurrent_streams:     int          = 10

    # ── Historical ─────────────────────────────────────────────────────────────
    supports_historical:        bool         = False
    historical_depth_days:      int          = 0       # 0 = no limit
    supported_intervals:        list[CandleInterval] = field(default_factory=list)

    # ── Snapshots ──────────────────────────────────────────────────────────────
    supports_snapshots:         bool         = False
    max_snapshot_batch_size:    int          = 100

    # ── Authentication ─────────────────────────────────────────────────────────
    requires_authentication:    bool         = False

    # ── Rate limiting ──────────────────────────────────────────────────────────
    requests_per_minute:        int          = 0       # 0 = unlimited
    bytes_per_second:           int          = 0       # 0 = unlimited

    # ── Extra ──────────────────────────────────────────────────────────────────
    extra:             dict[str, Any]        = field(default_factory=dict)

    def supports(self, data_type: MarketDataType) -> bool:
        return data_type in self.data_types

    def supports_exchange(self, exchange: Exchange) -> bool:
        return exchange in self.exchanges or Exchange.GLOBAL in self.exchanges

    def supports_instrument(self, instrument_type: InstrumentType) -> bool:
        return (
            instrument_type in self.instrument_types
            or InstrumentType.UNKNOWN in self.instrument_types
        )

    def supports_interval(self, interval: CandleInterval) -> bool:
        return interval in self.supported_intervals
