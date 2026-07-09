"""iios/execution/planning/core/execution_strategy.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.planning_constants import ExecutionAlgorithm


@dataclass
class ExecutionStrategy:
    strategy_id:   str                = field(default_factory=lambda: str(uuid.uuid4()))
    name:          str                = ""
    algorithm:     ExecutionAlgorithm = ExecutionAlgorithm.DIRECT
    parameters:    dict[str, Any]     = field(default_factory=dict)
    description:   str                = ""
    is_active:     bool               = True
    created_at:    float              = field(default_factory=time.time)
    metadata:      dict               = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name":        self.name,
            "algorithm":   self.algorithm.value,
            "parameters":  dict(self.parameters),
            "description": self.description,
            "is_active":   self.is_active,
        }
