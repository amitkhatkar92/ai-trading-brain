"""iios/investment/portfolio/core/position_group.py
Aggregated view of positions along a single dimension (sector / country / asset_class).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PositionGroup:
    """Aggregated positions for a single grouping dimension."""

    group_id:          str            = field(default_factory=lambda: str(uuid.uuid4()))
    group_name:        str            = ""     # e.g. "TECHNOLOGY", "INDIA"
    dimension:         str            = ""     # "sector" | "country" | "asset_class"
    position_ids:      list[str]      = field(default_factory=list)
    position_count:    int            = 0
    total_market_value: float         = 0.0
    total_weight:      float          = 0.0    # sum of position weights (fraction of portfolio NAV)
    unrealized_pnl:    float          = 0.0
    metadata:          dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id":           self.group_id,
            "group_name":         self.group_name,
            "dimension":          self.dimension,
            "position_ids":       self.position_ids,
            "position_count":     self.position_count,
            "total_market_value": self.total_market_value,
            "total_weight":       self.total_weight,
            "unrealized_pnl":     self.unrealized_pnl,
            "metadata":           self.metadata,
        }
