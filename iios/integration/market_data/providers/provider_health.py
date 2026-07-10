"""iios/integration/market_data/providers/provider_health.py

Health tracking for a market data provider.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderHealth:
    """
    Snapshot of a provider's health state.
    Returned by BaseMarketDataProvider.health_check().
    """

    provider_id:           str   = ""
    is_connected:          bool  = False
    is_authenticated:      bool  = False
    is_streaming:          bool  = False
    latency_ms:            float = 0.0
    last_message_at:       float = 0.0
    messages_per_sec:      float = 0.0
    active_subscriptions:  int   = 0
    error_count:           int   = 0
    last_error:            str   = ""
    uptime_sec:            float = 0.0
    checked_at:            float = field(default_factory=time.time)

    def is_healthy(self) -> bool:
        return self.is_connected and not self.last_error

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id":          self.provider_id,
            "is_connected":         self.is_connected,
            "is_authenticated":     self.is_authenticated,
            "is_streaming":         self.is_streaming,
            "latency_ms":           round(self.latency_ms, 2),
            "last_message_at":      self.last_message_at,
            "messages_per_sec":     round(self.messages_per_sec, 2),
            "active_subscriptions": self.active_subscriptions,
            "error_count":          self.error_count,
            "last_error":           self.last_error,
            "uptime_sec":           round(self.uptime_sec, 1),
            "checked_at":           self.checked_at,
            "is_healthy":           self.is_healthy(),
        }
