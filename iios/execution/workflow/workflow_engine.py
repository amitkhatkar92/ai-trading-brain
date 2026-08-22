"""iios/execution/workflow/workflow_engine.py"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from iios.execution.core.execution_result  import ExecutionResult
from iios.execution.core.execution_session import ExecutionSession
from iios.execution.execution_constants    import ExecutionStatus, WorkflowStepStatus
from iios.execution.execution_exceptions   import WorkflowCancelledError
from iios.execution.events.execution_event import ExecutionEvent
from iios.execution.events.event_bus       import ExecutionEventBus
from iios.execution.execution_constants    import ExecutionEventType
from iios.execution.workflow.execution_workflow import StepResult, WorkflowContext, WorkflowStep
from iios.execution.workflow.workflow_steps import DEFAULT_WORKFLOW_STEPS

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Orchestrates the ordered execution of workflow steps for a single
    ExecutionSession, producing an ExecutionResult.

    Thread-safe: each ``run()`` call operates on its own WorkflowContext.
    Cancel flags are per-execution_id.
    """

    def __init__(
        self,
        steps: list[WorkflowStep] | None = None,
        event_bus: ExecutionEventBus | None = None,
        step_hook: Callable[[str, StepResult], None] | None = None,
    ) -> None:
        self._steps: list[WorkflowStep] = steps if steps is not None else list(DEFAULT_WORKFLOW_STEPS)
        self._event_bus: ExecutionEventBus | None = event_bus
        self._step_hook = step_hook
        self._cancel_flags: dict[str, threading.Event] = {}
        self._lock: threading.RLock = threading.RLock()

    # ── Cancel flag management ─────────────────────────────────────────────────

    def request_cancel(self, execution_id: str) -> None:
        with self._lock:
            flag = self._cancel_flags.get(execution_id)
            if flag is None:
                flag = threading.Event()
                self._cancel_flags[execution_id] = flag
            flag.set()

    def _register(self, execution_id: str) -> threading.Event:
        with self._lock:
            # Preserve a pre-set cancel flag (request_cancel called before run).
            flag = self._cancel_flags.get(execution_id)
            if flag is None:
                flag = threading.Event()
                self._cancel_flags[execution_id] = flag
            return flag

    def _deregister(self, execution_id: str) -> None:
        with self._lock:
            self._cancel_flags.pop(execution_id, None)

    # ── Core ──────────────────────────────────────────────────────────────────

    def run(self, session: ExecutionSession) -> ExecutionResult:
        execution_id = session.execution_id
        cancel_flag  = self._register(execution_id)
        ctx = WorkflowContext(execution_id=execution_id, session=session)

        self._publish(execution_id, ExecutionEventType.STARTED, source="WorkflowEngine")
        logger.debug("WorkflowEngine: starting execution %s", execution_id)

        try:
            for step in self._steps:
                if cancel_flag.is_set():
                    self._handle_cancel(ctx, step.step_name)
                    raise WorkflowCancelledError(
                        f"Execution {execution_id} cancelled before step {step.step_name!r}",
                        execution_id=execution_id,
                    )

                step_result = self._run_step(step, ctx, cancel_flag)
                ctx.record(step_result)

                if self._step_hook:
                    try:
                        self._step_hook(execution_id, step_result)
                    except Exception:
                        logger.exception("WorkflowEngine: step_hook raised")

                if step_result.failed:
                    return self._build_failure(ctx, step.step_name, step_result.error)

        except WorkflowCancelledError:
            return self._build_cancellation(ctx)
        except Exception as exc:
            logger.exception("WorkflowEngine: unexpected error in execution %s", execution_id)
            return self._build_failure(ctx, "unknown", str(exc))
        finally:
            self._deregister(execution_id)

        result = ctx.result
        if result is None:
            # Shouldn't happen if FinalizeStep ran, but guard defensively.
            result = self._build_failure(ctx, "finalize", "FinalizeStep produced no result")

        logger.debug(
            "WorkflowEngine: completed %s status=%s", execution_id, result.status.value
        )
        self._publish(execution_id, ExecutionEventType.COMPLETED, source="WorkflowEngine")
        return result

    def _run_step(
        self,
        step: WorkflowStep,
        ctx: WorkflowContext,
        cancel_flag: threading.Event,
    ) -> StepResult:
        t0 = time.time()
        logger.debug("WorkflowEngine: step %r → %s", step.step_name, ctx.execution_id)
        self._publish(
            ctx.execution_id,
            ExecutionEventType.STEP_COMPLETED,
            source="WorkflowEngine",
            step=step.step_name,
        )
        try:
            result = step.execute(ctx)
        except Exception as exc:
            logger.exception("WorkflowEngine: step %r raised", step.step_name)
            result = StepResult(
                step_name=step.step_name,
                status=WorkflowStepStatus.FAILED,
                error=str(exc),
                duration_ms=(time.time() - t0) * 1_000.0,
            )
        return result

    # ── Failure / cancellation builders ───────────────────────────────────────

    def _build_failure(
        self, ctx: WorkflowContext, step_name: str, error: str
    ) -> ExecutionResult:
        session = ctx.session
        if session.can_transition(ExecutionStatus.FAILED):
            session.transition(ExecutionStatus.FAILED, reason=f"step {step_name!r} failed")
        self._publish(ctx.execution_id, ExecutionEventType.FAILED, source="WorkflowEngine")

        result = ExecutionResult(
            execution_id=ctx.execution_id,
            request_id=ctx.request.request_id,
            status=ExecutionStatus.FAILED,
            execution_type=ctx.request.execution_type,
            ticker=ctx.request.ticker,
            quantity_requested=ctx.request.quantity,
            execution_time_ms=(time.time() - session.started_at) * 1_000.0,
            started_at=session.started_at,
            error_message=error,
            error_code="WF-STEP-FAIL",
        )
        ctx.result = result
        return result

    def _handle_cancel(self, ctx: WorkflowContext, step_name: str) -> None:
        session = ctx.session
        if session.can_transition(ExecutionStatus.CANCELLED):
            session.transition(
                ExecutionStatus.CANCELLED, reason=f"cancelled before step {step_name!r}"
            )

    def _build_cancellation(self, ctx: WorkflowContext) -> ExecutionResult:
        self._publish(ctx.execution_id, ExecutionEventType.CANCELLED, source="WorkflowEngine")
        result = ExecutionResult(
            execution_id=ctx.execution_id,
            request_id=ctx.request.request_id,
            status=ExecutionStatus.CANCELLED,
            execution_type=ctx.request.execution_type,
            ticker=ctx.request.ticker,
            quantity_requested=ctx.request.quantity,
            execution_time_ms=(time.time() - ctx.session.started_at) * 1_000.0,
            started_at=ctx.session.started_at,
            error_message="Execution cancelled",
        )
        ctx.result = result
        return result

    # ── Event publishing ──────────────────────────────────────────────────────

    def _publish(
        self,
        execution_id: str,
        event_type: ExecutionEventType,
        *,
        source: str = "",
        step: str = "",
    ) -> None:
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(
                ExecutionEvent(
                    execution_id=execution_id,
                    event_type=event_type,
                    source=source,
                    step=step,
                )
            )
        except Exception:
            logger.exception("WorkflowEngine: event publish failed")
