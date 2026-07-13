"""iios/investment/strategy/portfolio/strategy_allocation.py
StrategyAllocation — a single strategy's slot within a portfolio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class AllocationStatus(str, Enum):
    ACTIVE  = "active"
    PAUSED  = "paused"
    REMOVED = "removed"
    PENDING = "pending"


class AllocationMethod(str, Enum):
    EQUAL_WEIGHT        = "equal_weight"
    RISK_PARITY         = "risk_parity"
    PERFORMANCE_WEIGHT  = "performance_weight"
    CONFIDENCE_WEIGHT   = "confidence_weight"
    VOLATILITY_WEIGHT   = "volatility_weight"
    EVALUATION_WEIGHT   = "evaluation_weight"
    COMPOSITE_WEIGHT    = "composite_weight"
    CUSTOM              = "custom"


@dataclass
class StrategyAllocation:
    """
    Mutable slot representing one strategy's position in a portfolio.
    weight + target_weight are in [0, 1]; portfolio weights sum to 1.0.
    """
    strategy_id:       str
    strategy_name:     str
    weight:            float            # current effective weight
    target_weight:     float            # optimiser target
    status:            AllocationStatus = AllocationStatus.ACTIVE
    allocation_method: AllocationMethod = AllocationMethod.EQUAL_WEIGHT
    evaluation_score:  float = 0.0     # cached from EvaluationEngine
    added_at:          datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at:        datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata:          Dict[str, Any] = field(default_factory=dict)

    @property
    def weight_drift(self) -> float:
        """Absolute drift from target."""
        return abs(self.weight - self.target_weight)

    @property
    def is_active(self) -> bool:
        return self.status == AllocationStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":       self.strategy_id,
            "strategy_name":     self.strategy_name,
            "weight":            self.weight,
            "target_weight":     self.target_weight,
            "status":            self.status.value,
            "allocation_method": self.allocation_method.value,
            "evaluation_score":  self.evaluation_score,
            "weight_drift":      self.weight_drift,
            "added_at":          self.added_at.isoformat(),
        }
