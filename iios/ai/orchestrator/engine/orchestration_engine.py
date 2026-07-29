"""
orchestration_engine.py -- iios.ai.orchestrator.engine
========================================================
:class:`OrchestrationManager` and :class:`Orchestrator`.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from ..core.orchestration_context import (
    OrchestrationContext,
    OrchestrationResult,
    OrchestrationSession,
)
from ..core.orchestration_types import ObjectiveStatus
from ..core.plan_types import ExecutionPlan, PlanningContext
from ..exceptions.orchestrator_exceptions import (
    AIObjectiveNotFoundError,
    AIObjectiveValidationError,
)
from .planning_engine import PlanningEngine


class OrchestrationManager:
    """
    Thread-safe store and lifecycle manager for orchestration sessions.

    Responsibilities
    ----------------
    - Create sessions from :class:`OrchestrationContext` objects
    - Retrieve sessions by session_id
    - Update session status and state
    - Close sessions
    """

    def __init__(self) -> None:
        self._lock:     threading.Lock                   = threading.Lock()
        self._sessions: Dict[str, OrchestrationSession] = {}

    def create_session(self, context: OrchestrationContext) -> OrchestrationSession:
        session = OrchestrationSession.create(context)
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> OrchestrationSession:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise AIObjectiveNotFoundError(f"Session '{session_id}' not found")
        return session

    def update_status(self, session_id: str, status: ObjectiveStatus) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise AIObjectiveNotFoundError(f"Session '{session_id}' not found")
            self._sessions[session_id] = session.with_status(status)

    def set_state(self, session_id: str, key: str, value: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise AIObjectiveNotFoundError(f"Session '{session_id}' not found")
            self._sessions[session_id] = session.with_state(key, value)

    def close_session(self, session_id: str) -> None:
        with self._lock:
            if session_id not in self._sessions:
                raise AIObjectiveNotFoundError(f"Session '{session_id}' not found")
            del self._sessions[session_id]

    def active_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def list_sessions(self) -> List[OrchestrationSession]:
        with self._lock:
            return list(self._sessions.values())


class Orchestrator:
    """
    Executive controller — accepts objectives, generates plans, and drives execution.

    The Orchestrator is infrastructure only.  It does not perform analysis,
    implement strategies, or call broker APIs.  All execution is delegated
    to registered step handlers.

    Usage::

        orch = Orchestrator(manager, planning_engine)
        orch.register_step_handler("execute", lambda p: "done")

        ctx        = OrchestrationContext.create("my objective", "agent-1")
        session_id = orch.submit_objective(ctx)
        result     = orch.execute(session_id)
    """

    def __init__(
        self,
        manager:         OrchestrationManager,
        planning_engine: PlanningEngine,
    ) -> None:
        self._manager         = manager
        self._planning_engine = planning_engine
        self._lock:     threading.Lock                      = threading.Lock()
        self._handlers: Dict[str, Callable[[Dict], Any]]   = {}
        self._plans:    Dict[str, ExecutionPlan]            = {}
        self._cancelled: set                               = set()

    # ── handler registry ──────────────────────────────────────────────────────

    def register_step_handler(self, action: str, handler_fn: Callable[[Dict], Any]) -> None:
        with self._lock:
            self._handlers[action] = handler_fn

    def has_handler(self, action: str) -> bool:
        with self._lock:
            return action in self._handlers

    # ── objective submission ──────────────────────────────────────────────────

    def submit_objective(self, context: OrchestrationContext) -> str:
        """
        Create an orchestration session for *context*.  Returns the session_id.
        """
        if not context.objective.strip():
            raise AIObjectiveValidationError("Objective must not be empty")
        session = self._manager.create_session(context)
        return session.session_id

    # ── planning ──────────────────────────────────────────────────────────────

    def generate_plan(self, session_id: str) -> ExecutionPlan:
        """Generate an :class:`ExecutionPlan` for the session's objective."""
        session = self._manager.get_session(session_id)
        self._manager.update_status(session_id, ObjectiveStatus.PLANNING)

        ctx  = PlanningContext.create(objective=session.context.objective)
        plan = self._planning_engine.create_plan(ctx)

        with self._lock:
            self._plans[session_id] = plan

        self._manager.set_state(session_id, "plan_id", plan.plan_id)
        return plan

    def get_plan(self, session_id: str) -> Optional[ExecutionPlan]:
        with self._lock:
            return self._plans.get(session_id)

    # ── execution ─────────────────────────────────────────────────────────────

    def execute(self, session_id: str) -> OrchestrationResult:
        """
        Execute the plan for *session_id* and return the final result.

        If no plan exists, one is generated automatically.
        Steps without a registered handler are silently skipped.
        """
        session    = self._manager.get_session(session_id)
        started_at = session.started_at

        with self._lock:
            plan = self._plans.get(session_id)
        if plan is None:
            plan = self.generate_plan(session_id)

        self._manager.update_status(session_id, ObjectiveStatus.EXECUTING)

        batches    = self._planning_engine.get_execution_order(plan)
        completed  = 0
        failed_cnt = 0
        outputs: List[str] = []

        step_map = {s.step_id: s for s in plan.steps}

        for batch in batches:
            if session_id in self._cancelled:
                self._manager.update_status(session_id, ObjectiveStatus.CANCELLED)
                return OrchestrationResult.cancelled(
                    session_id = session_id,
                    objective  = session.context.objective,
                    started_at = started_at,
                )

            for step_id in batch:
                step = step_map.get(step_id)
                if step is None:
                    continue

                with self._lock:
                    handler = self._handlers.get(step.action)

                if handler is None:
                    self._manager.set_state(session_id, f"skip_{step_id}", step.action)
                    continue

                success  = False
                last_exc: Optional[Exception] = None

                for attempt in range(step.max_retries + 1):
                    try:
                        result = handler(dict(step.parameters))
                        outputs.append(str(result) if result is not None else "")
                        completed += 1
                        success    = True
                        break
                    except Exception as exc:
                        last_exc = exc

                if not success:
                    failed_cnt += 1
                    self._manager.update_status(session_id, ObjectiveStatus.FAILED)
                    return OrchestrationResult.failure(
                        session_id      = session_id,
                        objective       = session.context.objective,
                        started_at      = started_at,
                        error_message   = str(last_exc),
                        steps_completed = completed,
                        steps_failed    = failed_cnt,
                    )

        self._manager.update_status(session_id, ObjectiveStatus.COMPLETED)
        return OrchestrationResult.success(
            session_id      = session_id,
            objective       = session.context.objective,
            started_at      = started_at,
            output          = "; ".join(outputs) if outputs else None,
            steps_completed = completed,
        )

    def cancel(self, session_id: str) -> None:
        """Mark a session for cancellation on the next execution cycle."""
        with self._lock:
            self._cancelled.add(session_id)
        self._manager.update_status(session_id, ObjectiveStatus.CANCELLED)

    def session_count(self) -> int:
        return self._manager.active_count()
