"""iios/execution/core/execution_plan.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionPlan:
    """
    Validated, costed plan generated from an ExecutionRequest.

    The plan captures *what will happen* — the workflow engine decides *how*.
    """

    # ── Identifiers ────────────────────────────────────────────────────────────
    plan_id:      str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = ""
    request_id:   str = ""

    # ── Steps ──────────────────────────────────────────────────────────────────
    # Ordered list of workflow step names that will be executed.
    steps: list[str] = field(default_factory=lambda: [
        "validate",
        "risk_check",
        "generate_plan",
        "queue",
        "execute",
        "finalize",
    ])

    # ── Cost estimates ─────────────────────────────────────────────────────────
    estimated_quantity:   float = 0.0
    estimated_price:      float = 0.0
    estimated_value:      float = 0.0
    estimated_commission: float = 0.0
    estimated_slippage:   float = 0.0

    # ── Validation ─────────────────────────────────────────────────────────────
    risk_check_passed:  bool        = False
    validation_errors:  list[str]   = field(default_factory=list)

    # ── Misc ───────────────────────────────────────────────────────────────────
    constraints: dict[str, Any] = field(default_factory=dict)
    created_at:  float          = field(default_factory=time.time)
    metadata:    dict[str, Any] = field(default_factory=dict)

    # ── Derived ────────────────────────────────────────────────────────────────

    @property
    def is_valid(self) -> bool:
        return len(self.validation_errors) == 0

    @property
    def estimated_total_cost(self) -> float:
        return self.estimated_value + self.estimated_commission

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id":              self.plan_id,
            "execution_id":         self.execution_id,
            "request_id":           self.request_id,
            "steps":                list(self.steps),
            "estimated_quantity":   self.estimated_quantity,
            "estimated_price":      self.estimated_price,
            "estimated_value":      self.estimated_value,
            "estimated_commission": self.estimated_commission,
            "estimated_slippage":   self.estimated_slippage,
            "risk_check_passed":    self.risk_check_passed,
            "validation_errors":    list(self.validation_errors),
            "constraints":          dict(self.constraints),
            "created_at":           self.created_at,
            "metadata":             dict(self.metadata),
        }
