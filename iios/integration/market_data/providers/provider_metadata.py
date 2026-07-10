"""iios/integration/market_data/providers/provider_metadata.py

Static metadata for a market data provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.integration.market_data.market_data_constants import MarketDataProviderStatus


@dataclass
class ProviderMetadata:
    """
    Descriptive information about a market data provider.
    Populated once at registration time.
    """

    provider_id:   str                      = ""
    display_name:  str                      = ""
    description:   str                      = ""
    version:       str                      = "1.0.0"
    vendor:        str                      = ""
    vendor_url:    str                      = ""
    is_free:       bool                     = False
    is_demo:       bool                     = False    # paper / sandbox mode
    status:        MarketDataProviderStatus = MarketDataProviderStatus.DISCONNECTED
    tags:          list[str]                = field(default_factory=list)
    extra:         dict[str, Any]           = field(default_factory=dict)

    # Connection stats (mutable at runtime)
    connect_count:     int   = 0
    disconnect_count:  int   = 0
    total_uptime_sec:  float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id":   self.provider_id,
            "display_name":  self.display_name,
            "description":   self.description,
            "version":       self.version,
            "vendor":        self.vendor,
            "is_free":       self.is_free,
            "is_demo":       self.is_demo,
            "status":        self.status.value,
            "tags":          self.tags,
        }
