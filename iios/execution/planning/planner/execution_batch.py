"""iios/execution/planning/planner/execution_batch.py
Batch grouping of related execution plans.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionBatch:
    """Groups multiple plans that should be tracked together."""

    batch_id:    str           = field(default_factory=lambda: str(uuid.uuid4()))
    name:        str           = ""
    plan_ids:    list[str]     = field(default_factory=list)
    portfolio_id: str          = ""
    strategy_id: str           = ""
    created_at:  float         = field(default_factory=time.time)
    metadata:    dict[str, Any] = field(default_factory=dict)

    def add_plan(self, plan_id: str) -> None:
        if plan_id not in self.plan_ids:
            self.plan_ids.append(plan_id)

    def remove_plan(self, plan_id: str) -> None:
        self.plan_ids = [p for p in self.plan_ids if p != plan_id]

    @property
    def size(self) -> int:
        return len(self.plan_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id":    self.batch_id,
            "name":        self.name,
            "plan_ids":    self.plan_ids,
            "portfolio_id": self.portfolio_id,
            "strategy_id": self.strategy_id,
            "size":        self.size,
            "created_at":  self.created_at,
            "metadata":    self.metadata,
        }
