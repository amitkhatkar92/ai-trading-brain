"""iios/execution/planning/core/execution_constraints.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionConstraints:
    max_slippage_pct:       float      = 0.005    # 0.5%
    max_market_impact_pct:  float      = 0.010    # 1.0%
    max_cost_pct:           float      = 0.010    # 1.0%
    min_fill_probability:   float      = 0.80
    max_execution_time_sec: float      = 3_600.0
    max_order_size:         float | None = None
    min_order_size:         float | None = None
    max_split_legs:         int        = 20
    allowed_venues:         list[str]  = field(default_factory=list)
    excluded_venues:        list[str]  = field(default_factory=list)
    compliance_flags:       list[str]  = field(default_factory=list)
    metadata:               dict       = field(default_factory=dict)

    def venue_is_allowed(self, venue: str) -> bool:
        if self.excluded_venues and venue in self.excluded_venues:
            return False
        if self.allowed_venues:
            return venue in self.allowed_venues
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_slippage_pct":       self.max_slippage_pct,
            "max_market_impact_pct":  self.max_market_impact_pct,
            "max_cost_pct":           self.max_cost_pct,
            "min_fill_probability":   self.min_fill_probability,
            "max_execution_time_sec": self.max_execution_time_sec,
            "max_order_size":         self.max_order_size,
            "min_order_size":         self.min_order_size,
            "max_split_legs":         self.max_split_legs,
            "allowed_venues":         list(self.allowed_venues),
            "excluded_venues":        list(self.excluded_venues),
            "compliance_flags":       list(self.compliance_flags),
        }
