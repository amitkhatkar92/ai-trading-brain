"""iios/execution/planning/core/execution_instruction.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionInstruction:
    instruction_id:  str        = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id:         str        = ""
    sequence:        int        = 0
    instruction_type: str       = "execute"   # execute | cancel | modify | wait
    venue:           str        = ""
    symbol:          str        = ""
    quantity:        float      = 0.0
    price_limit:     float | None = None
    time_limit_sec:  float | None = None
    conditions:      list[str]  = field(default_factory=list)
    notes:           str        = ""
    is_conditional:  bool       = False
    created_at:      float      = field(default_factory=time.time)
    metadata:        dict       = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instruction_id":   self.instruction_id,
            "plan_id":          self.plan_id,
            "sequence":         self.sequence,
            "instruction_type": self.instruction_type,
            "venue":            self.venue,
            "symbol":           self.symbol,
            "quantity":         self.quantity,
            "price_limit":      self.price_limit,
            "time_limit_sec":   self.time_limit_sec,
            "conditions":       list(self.conditions),
            "is_conditional":   self.is_conditional,
        }
