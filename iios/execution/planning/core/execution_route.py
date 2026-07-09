"""iios/execution/planning/core/execution_route.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.planning_constants import RoutingStrategy


@dataclass
class ExecutionRoute:
    route_id:                  str             = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id:                   str             = ""
    routing_strategy:          RoutingStrategy = RoutingStrategy.SINGLE_VENUE
    primary_venue:             str             = ""
    backup_venues:             list[str]       = field(default_factory=list)
    venue_allocations:         dict[str, float] = field(default_factory=dict)  # venue -> fraction
    estimated_latency_ms:      float           = 0.0
    estimated_fill_probability: float          = 0.95
    venue_reliability:         float           = 0.99   # 0-1
    route_score:               float           = 50.0   # 0-100
    created_at:                float           = field(default_factory=time.time)
    metadata:                  dict            = field(default_factory=dict)

    def all_venues(self) -> list[str]:
        venues = []
        if self.primary_venue:
            venues.append(self.primary_venue)
        venues.extend(v for v in self.backup_venues if v not in venues)
        return venues

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id":                   self.route_id,
            "plan_id":                    self.plan_id,
            "routing_strategy":           self.routing_strategy.value,
            "primary_venue":              self.primary_venue,
            "backup_venues":              list(self.backup_venues),
            "venue_allocations":          dict(self.venue_allocations),
            "estimated_latency_ms":       self.estimated_latency_ms,
            "estimated_fill_probability": self.estimated_fill_probability,
            "venue_reliability":          self.venue_reliability,
            "route_score":                self.route_score,
        }
