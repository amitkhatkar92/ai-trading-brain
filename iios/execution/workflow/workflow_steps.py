"""iios/execution/workflow/workflow_steps.py"""
from __future__ import annotations

import time

from iios.execution.core.execution_plan   import ExecutionPlan
from iios.execution.core.execution_result import ExecutionResult
from iios.execution.execution_constants   import ExecutionStatus, WorkflowStepStatus
from iios.execution.workflow.execution_workflow import StepResult, WorkflowContext, WorkflowStep
from iios.execution.workflow.workflow_validator import WorkflowValidator


class ValidateStep(WorkflowStep):
    """
    Step 1 — validate the execution request.

    Transitions session: CREATED → PLANNED (if valid) or stays + error.
    """

    step_name = "validate"

    def __init__(self, validator: WorkflowValidator | None = None) -> None:
        self._validator = validator or WorkflowValidator()

    def execute(self, ctx: WorkflowContext) -> StepResult:
        t0 = time.time()
        is_valid, errors = self._validator.validate(ctx.request)
        duration = (time.time() - t0) * 1_000.0

        if not is_valid:
            for e in errors:
                ctx.add_error(e)
            return StepResult(
                step_name=self.step_name,
                status=WorkflowStepStatus.FAILED,
                error="; ".join(errors),
                duration_ms=duration,
            )

        # Valid — transition state.
        if ctx.session.can_transition(ExecutionStatus.PLANNED):
            ctx.session.transition(ExecutionStatus.PLANNED, reason="validation passed")

        return StepResult(
            step_name=self.step_name,
            status=WorkflowStepStatus.COMPLETED,
            duration_ms=duration,
        )


class RiskCheckStep(WorkflowStep):
    """
    Step 2 — lightweight risk guard.

    In PAPER / SIMULATION mode this always passes.
    When broker adapters are added, live risk checks will be injected here.
    Transitions session: PLANNED → VALIDATED.
    """

    step_name = "risk_check"

    def execute(self, ctx: WorkflowContext) -> StepResult:
        t0 = time.time()

        # For paper / simulation: unconditional pass.
        if ctx.session.plan:
            ctx.session.plan.risk_check_passed = True

        if ctx.session.can_transition(ExecutionStatus.VALIDATED):
            ctx.session.transition(ExecutionStatus.VALIDATED, reason="risk check passed")

        return StepResult(
            step_name=self.step_name,
            status=WorkflowStepStatus.COMPLETED,
            duration_ms=(time.time() - t0) * 1_000.0,
            metadata={"risk_check": "passed", "mode": ctx.request.execution_mode.value},
        )


class GeneratePlanStep(WorkflowStep):
    """
    Step 3 — generate the ExecutionPlan.

    Estimates cost, commission (zero for paper), and slippage.
    Transitions session: VALIDATED → APPROVED.
    """

    step_name = "generate_plan"

    # Paper-mode commission model: zero.
    _COMMISSION_RATE: float = 0.0
    # Paper-mode slippage model: zero (perfect fill at target price).
    _SLIPPAGE_RATE:   float = 0.0

    def execute(self, ctx: WorkflowContext) -> StepResult:
        t0 = time.time()

        req = ctx.request
        price = req.target_price or req.price_limit or 0.0
        value = req.quantity * price

        plan = ExecutionPlan(
            execution_id=ctx.execution_id,
            request_id=req.request_id,
            estimated_quantity=req.quantity,
            estimated_price=price,
            estimated_value=value,
            estimated_commission=value * self._COMMISSION_RATE,
            estimated_slippage=value * self._SLIPPAGE_RATE,
            risk_check_passed=True,
            constraints=dict(req.constraints),
        )
        ctx.plan = plan

        if ctx.session.can_transition(ExecutionStatus.APPROVED):
            ctx.session.transition(ExecutionStatus.APPROVED, reason="plan generated")

        return StepResult(
            step_name=self.step_name,
            status=WorkflowStepStatus.COMPLETED,
            output=plan,
            duration_ms=(time.time() - t0) * 1_000.0,
        )


class QueueStep(WorkflowStep):
    """
    Step 4 — place session into the execution queue.

    For synchronous paper execution this is instant.
    Transitions: APPROVED → QUEUED.
    """

    step_name = "queue"

    def execute(self, ctx: WorkflowContext) -> StepResult:
        t0 = time.time()
        if ctx.session.can_transition(ExecutionStatus.QUEUED):
            ctx.session.transition(ExecutionStatus.QUEUED, reason="queued for execution")
        return StepResult(
            step_name=self.step_name,
            status=WorkflowStepStatus.COMPLETED,
            duration_ms=(time.time() - t0) * 1_000.0,
        )


class ExecuteStep(WorkflowStep):
    """
    Step 5 — simulate the execution.

    In PAPER / SIMULATION mode the order fills instantly at target_price
    (or 0.0 if no price is set) with 100 % fill ratio and no slippage.

    This step is the *hook point* for future Broker Adapters.  A live
    adapter would override this step and route to the actual broker API.

    Transitions: QUEUED → EXECUTING.
    """

    step_name = "execute"

    def execute(self, ctx: WorkflowContext) -> StepResult:
        t0 = time.time()

        if ctx.session.can_transition(ExecutionStatus.EXECUTING):
            ctx.session.transition(ExecutionStatus.EXECUTING, reason="execution started")

        req  = ctx.request
        plan = ctx.session.plan

        fill_price = req.target_price or (plan.estimated_price if plan else 0.0)
        qty_filled  = req.quantity
        total_value = qty_filled * fill_price
        commission  = (plan.estimated_commission if plan else 0.0)
        slippage    = (plan.estimated_slippage   if plan else 0.0)

        duration = (time.time() - t0) * 1_000.0

        return StepResult(
            step_name=self.step_name,
            status=WorkflowStepStatus.COMPLETED,
            output={
                "fill_price":   fill_price,
                "qty_filled":   qty_filled,
                "total_value":  total_value,
                "commission":   commission,
                "slippage":     slippage,
            },
            duration_ms=duration,
        )


class FinalizeStep(WorkflowStep):
    """
    Step 6 — build the ExecutionResult and mark the session COMPLETED.
    """

    step_name = "finalize"

    def execute(self, ctx: WorkflowContext) -> StepResult:
        t0 = time.time()

        execute_out = (ctx.step_results.get("execute") or StepResult(step_name="execute")).output or {}

        fill_price  = execute_out.get("fill_price",  0.0)
        qty_filled  = execute_out.get("qty_filled",  ctx.request.quantity)
        total_value = execute_out.get("total_value", qty_filled * fill_price)
        commission  = execute_out.get("commission",  0.0)
        slippage    = execute_out.get("slippage",    0.0)

        req  = ctx.request
        plan = ctx.session.plan

        result = ExecutionResult(
            execution_id=ctx.execution_id,
            request_id=req.request_id,
            plan_id=plan.plan_id if plan else "",
            status=ExecutionStatus.COMPLETED,
            execution_type=req.execution_type,
            ticker=req.ticker,
            exchange=req.exchange,
            quantity_requested=req.quantity,
            quantity_executed=qty_filled,
            avg_fill_price=fill_price,
            total_value=total_value,
            commission=commission,
            slippage=slippage,
            execution_time_ms=(time.time() - ctx.session.started_at) * 1_000.0,
            started_at=ctx.session.started_at,
        )

        ctx.result = result

        if ctx.session.can_transition(ExecutionStatus.COMPLETED):
            ctx.session.transition(ExecutionStatus.COMPLETED, reason="execution finalised")

        return StepResult(
            step_name=self.step_name,
            status=WorkflowStepStatus.COMPLETED,
            output=result,
            duration_ms=(time.time() - t0) * 1_000.0,
        )


# ── Default step sequence ──────────────────────────────────────────────────────

DEFAULT_WORKFLOW_STEPS: list[WorkflowStep] = [
    ValidateStep(),
    RiskCheckStep(),
    GeneratePlanStep(),
    QueueStep(),
    ExecuteStep(),
    FinalizeStep(),
]
