"""iios/investment/portfolio/allocation/allocation_report.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.portfolio.portfolio_constants import AllocationStatus


@dataclass
class AllocationReport:
    """
    Output of AllocationEngine.analyze():
    current allocations, deviations from targets, and rebalance flags.
    """

    report_id:              str             = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:           str             = ""
    timestamp:              float           = field(default_factory=time.time)

    # Current weights: asset_class.value → actual fraction
    current_allocations:    dict[str, float] = field(default_factory=dict)
    # Target weights from constraints
    target_allocations:     dict[str, float] = field(default_factory=dict)
    # Deviations: actual − target
    deviations:             dict[str, float] = field(default_factory=dict)
    # Abs deviation > threshold → True
    rebalance_flags:        dict[str, bool]  = field(default_factory=dict)

    rebalancing_needed:     bool            = False
    allocation_score:       float           = 50.0    # 0–100; higher = closer to targets
    status:                 AllocationStatus = AllocationStatus.UNKNOWN
    notes:                  list[str]        = field(default_factory=list)
    metadata:               dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":           self.report_id,
            "portfolio_id":        self.portfolio_id,
            "timestamp":           self.timestamp,
            "current_allocations": self.current_allocations,
            "target_allocations":  self.target_allocations,
            "deviations":          self.deviations,
            "rebalance_flags":     self.rebalance_flags,
            "rebalancing_needed":  self.rebalancing_needed,
            "allocation_score":    self.allocation_score,
            "status":              self.status.value,
            "notes":               self.notes,
            "metadata":            self.metadata,
        }
