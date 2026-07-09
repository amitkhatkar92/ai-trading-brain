"""iios/execution/planning/core/execution_plan.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.planning_constants import (
    DEFAULT_PRIORITY,
    TERMINAL_PLAN_STATUSES,
    ExecutionAlgorithm,
    ExecutionMode,
    ExecutionPlanStatus,
    RoutingStrategy,
)
from iios.execution.planning.core.execution_constraints import ExecutionConstraints
from iios.execution.planning.core.execution_cost import ExecutionCost
from iios.execution.planning.core.execution_instruction import ExecutionInstruction
from iios.execution.planning.core.execution_route import ExecutionRoute
from iios.execution.planning.core.execution_schedule import ExecutionSchedule


@dataclass
class ExecutionPlan:
    plan_id:            str                         = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:           str                         = ""
    execution_id:       str                         = ""
    portfolio_id:       str                         = ""
    strategy_id:        str                         = ""
    decision_id:        str                         = ""
    symbol:             str                         = ""

    status:             ExecutionPlanStatus         = ExecutionPlanStatus.DRAFT
    routing_strategy:   RoutingStrategy             = RoutingStrategy.SINGLE_VENUE
    execution_mode:     ExecutionMode               = ExecutionMode.IMMEDIATE
    algorithm:          ExecutionAlgorithm          = ExecutionAlgorithm.DIRECT
    priority:           int                         = DEFAULT_PRIORITY   # 1-10

    # ── child objects ─────────────────────────────────────────────────────────
    instructions:       list[ExecutionInstruction]  = field(default_factory=list)
    schedule:           ExecutionSchedule | None    = None
    route:              ExecutionRoute | None        = None
    constraints:        ExecutionConstraints        = field(default_factory=ExecutionConstraints)
    estimated_cost:     ExecutionCost               = field(default_factory=ExecutionCost)

    # ── split / merge ─────────────────────────────────────────────────────────
    parent_plan_id:     str | None                  = None
    child_plan_ids:     list[str]                   = field(default_factory=list)

    # ── audit ─────────────────────────────────────────────────────────────────
    rejection_reason:   str                         = ""
    notes:              str                         = ""
    created_at:         float                       = field(default_factory=time.time)
    updated_at:         float                       = field(default_factory=time.time)
    activated_at:       float | None                = None
    completed_at:       float | None                = None
    metadata:           dict                        = field(default_factory=dict)

    # ─────────────────────────────────────────────────────────────────────────
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_PLAN_STATUSES

    def add_instruction(self, instruction: ExecutionInstruction) -> None:
        instruction.plan_id = self.plan_id
        self.instructions.append(instruction)
        self.updated_at = time.time()

    def transition_to(self, new_status: ExecutionPlanStatus, reason: str = "") -> None:
        from iios.execution.planning.planning_exceptions import PlanTerminalError
        if (
            self.status in TERMINAL_PLAN_STATUSES
            and new_status != ExecutionPlanStatus.ARCHIVED
        ):
            raise PlanTerminalError(
                plan_id=self.plan_id,
                status=self.status.value,
            )
        self.status     = new_status
        self.updated_at = time.time()
        if new_status == ExecutionPlanStatus.ACTIVE and self.activated_at is None:
            self.activated_at = self.updated_at
        if new_status in (
            ExecutionPlanStatus.COMPLETED,
            ExecutionPlanStatus.CANCELLED,
            ExecutionPlanStatus.FAILED,
        ):
            self.completed_at = self.updated_at
        if reason:
            self.rejection_reason = reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id":          self.plan_id,
            "order_id":         self.order_id,
            "execution_id":     self.execution_id,
            "portfolio_id":     self.portfolio_id,
            "strategy_id":      self.strategy_id,
            "decision_id":      self.decision_id,
            "symbol":           self.symbol,
            "status":           self.status.value,
            "routing_strategy": self.routing_strategy.value,
            "execution_mode":   self.execution_mode.value,
            "algorithm":        self.algorithm.value,
            "priority":         self.priority,
            "instructions":     [i.to_dict() for i in self.instructions],
            "schedule":         self.schedule.to_dict() if self.schedule else None,
            "route":            self.route.to_dict() if self.route else None,
            "constraints":      self.constraints.to_dict(),
            "estimated_cost":   self.estimated_cost.to_dict(),
            "parent_plan_id":   self.parent_plan_id,
            "child_plan_ids":   list(self.child_plan_ids),
            "rejection_reason": self.rejection_reason,
            "notes":            self.notes,
            "created_at":       self.created_at,
            "updated_at":       self.updated_at,
            "activated_at":     self.activated_at,
            "completed_at":     self.completed_at,
        }
