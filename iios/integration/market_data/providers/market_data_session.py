"""iios/integration/market_data/providers/market_data_session.py

Tracks one active connection / streaming session for a provider.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.market_data.market_data_constants import MarketDataProviderStatus


@dataclass
class SubscriptionHandle:
    """Opaque handle returned by BaseMarketDataProvider.subscribe()."""

    handle_id:   str                    = field(default_factory=lambda: str(uuid.uuid4()))
    provider_id: str                    = ""
    symbols:     list[str]              = field(default_factory=list)
    data_types:  list[str]              = field(default_factory=list)
    created_at:  float                  = field(default_factory=time.time)
    is_active:   bool                   = True
    metadata:    dict[str, Any]         = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.handle_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SubscriptionHandle):
            return self.handle_id == other.handle_id
        return NotImplemented


@dataclass
class MarketDataSession:
    """
    Represents one active provider connection session.
    Each call to connect() creates or reuses a session.
    """

    session_id:    str                      = field(default_factory=lambda: str(uuid.uuid4()))
    provider_id:   str                      = ""
    status:        MarketDataProviderStatus = MarketDataProviderStatus.DISCONNECTED
    started_at:    float                    = field(default_factory=time.time)
    last_active:   float                    = field(default_factory=time.time)
    message_count: int                      = 0
    error_count:   int                      = 0
    reconnects:    int                      = 0
    subscriptions: dict[str, SubscriptionHandle] = field(default_factory=dict)
    metadata:      dict[str, Any]           = field(default_factory=dict)

    def touch(self) -> None:
        self.last_active = time.time()
        self.message_count += 1

    def record_error(self) -> None:
        self.error_count += 1

    def add_subscription(self, handle: SubscriptionHandle) -> None:
        self.subscriptions[handle.handle_id] = handle

    def remove_subscription(self, handle_id: str) -> bool:
        return self.subscriptions.pop(handle_id, None) is not None

    def uptime_sec(self) -> float:
        return time.time() - self.started_at

    def is_connected(self) -> bool:
        return self.status in (
            MarketDataProviderStatus.CONNECTED,
            MarketDataProviderStatus.AUTHENTICATED,
            MarketDataProviderStatus.STREAMING,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":    self.session_id,
            "provider_id":   self.provider_id,
            "status":        self.status.value,
            "started_at":    self.started_at,
            "last_active":   self.last_active,
            "message_count": self.message_count,
            "error_count":   self.error_count,
            "reconnects":    self.reconnects,
            "subscription_count": len(self.subscriptions),
            "uptime_sec":    round(self.uptime_sec(), 1),
        }
