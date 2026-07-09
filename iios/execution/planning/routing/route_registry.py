"""iios/execution/planning/routing/route_registry.py
Registry of named execution venues and their capabilities.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VenueInfo:
    """Metadata about a registered execution venue."""

    venue_id:       str            = ""
    name:           str            = ""
    asset_classes:  list[str]      = field(default_factory=list)
    order_types:    list[str]      = field(default_factory=list)
    min_order_size: float          = 0.0
    max_order_size: float          = 1e12
    latency_ms:     float          = 0.0     # expected round-trip latency
    fee_rate:       float          = 0.0003  # taker fee fraction
    is_active:      bool           = True
    metadata:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue_id":       self.venue_id,
            "name":           self.name,
            "asset_classes":  self.asset_classes,
            "order_types":    self.order_types,
            "min_order_size": self.min_order_size,
            "max_order_size": self.max_order_size,
            "latency_ms":     self.latency_ms,
            "fee_rate":       self.fee_rate,
            "is_active":      self.is_active,
            "metadata":       self.metadata,
        }


class RouteRegistry:
    """Thread-safe registry of execution venues."""

    def __init__(self) -> None:
        self._lock:   threading.RLock         = threading.RLock()
        self._venues: dict[str, VenueInfo]    = {}

    def register_venue(self, info: VenueInfo, *, overwrite: bool = False) -> None:
        with self._lock:
            if info.venue_id in self._venues and not overwrite:
                raise KeyError(f"Venue already registered: {info.venue_id!r}")
            self._venues[info.venue_id] = info

    def get_venue(self, venue_id: str) -> VenueInfo:
        with self._lock:
            if venue_id not in self._venues:
                raise KeyError(f"Venue not found: {venue_id!r}")
            return self._venues[venue_id]

    def has_venue(self, venue_id: str) -> bool:
        with self._lock:
            return venue_id in self._venues

    def active_venues(self) -> list[VenueInfo]:
        with self._lock:
            return [v for v in self._venues.values() if v.is_active]

    def all_venues(self) -> list[str]:
        with self._lock:
            return list(self._venues.keys())

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_venues":  len(self._venues),
                "active_venues": sum(1 for v in self._venues.values() if v.is_active),
            }
