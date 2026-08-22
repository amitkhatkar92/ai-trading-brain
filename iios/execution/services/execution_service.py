"""iios/execution/services/execution_service.py"""
from __future__ import annotations

import logging
from typing import Any

from iios.execution.core.execution_request import ExecutionRequest
from iios.execution.core.execution_result  import ExecutionResult
from iios.execution.core.execution_session import ExecutionSession
from iios.execution.execution_constants    import ExecutionStatus
from iios.execution.execution_exceptions   import (
    ExecutionNotFoundError,
    ExecutionStateError,
)
from iios.execution.sessions.session_manager import SessionManager
from iios.execution.workflow.workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)


class ExecutionService:
    """
    High-level CRUD + lifecycle service for executions.

    Sits between ExecutionManager (public API) and the lower-level
    SessionManager / WorkflowEngine.  All mutation is delegated to
    SessionManager so the store remains consistent.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        workflow_engine: WorkflowEngine,
    ) -> None:
        self._sessions  = session_manager
        self._workflow  = workflow_engine

    # ── Create ────────────────────────────────────────────────────────────────

    def create(self, request: ExecutionRequest) -> ExecutionSession:
        session = self._sessions.create_session(request)
        logger.debug("ExecutionService.create: %s", session.execution_id)
        return session

    # ── Execute ───────────────────────────────────────────────────────────────

    def execute(self, execution_id: str) -> ExecutionResult:
        session = self._get_or_raise(execution_id)
        result  = self._workflow.run(session)
        self._sessions.update_session(session)
        return result

    # ── Retrieve ──────────────────────────────────────────────────────────────

    def get(self, execution_id: str) -> ExecutionSession:
        return self._get_or_raise(execution_id)

    def list_active(self) -> list[ExecutionSession]:
        return self._sessions.list_active()

    def list_all(self) -> list[ExecutionSession]:
        return self._sessions.list_all()

    # ── Cancel ────────────────────────────────────────────────────────────────

    def cancel(self, execution_id: str, *, reason: str = "cancelled by user") -> bool:
        session = self._get_or_raise(execution_id)
        if not session.can_transition(ExecutionStatus.CANCELLED):
            logger.warning(
                "ExecutionService.cancel: cannot cancel %s (status=%s)",
                execution_id,
                session.status.value,
            )
            return False
        # Signal workflow engine (no-op if not running).
        self._workflow.request_cancel(execution_id)
        # Optimistically transition if session is not yet executing.
        if session.status not in (ExecutionStatus.EXECUTING, ExecutionStatus.RESUMED):
            session.transition(ExecutionStatus.CANCELLED, reason=reason)
            self._sessions.update_session(session)
        return True

    # ── Pause ─────────────────────────────────────────────────────────────────

    def pause(self, execution_id: str, *, reason: str = "paused by user") -> bool:
        session = self._get_or_raise(execution_id)
        if not session.can_transition(ExecutionStatus.PAUSED):
            return False
        session.transition(ExecutionStatus.PAUSED, reason=reason)
        self._sessions.update_session(session)
        return True

    # ── Resume ────────────────────────────────────────────────────────────────

    def resume(self, execution_id: str, *, reason: str = "resumed by user") -> bool:
        session = self._get_or_raise(execution_id)
        if not session.can_transition(ExecutionStatus.RESUMED):
            return False
        session.transition(ExecutionStatus.RESUMED, reason=reason)
        self._sessions.update_session(session)
        return True

    # ── Replay ────────────────────────────────────────────────────────────────

    def replay(self, execution_id: str) -> ExecutionResult:
        """
        Re-run a completed or failed execution using the original request.

        A new execution_id is allocated so the replay is a distinct record.
        """
        original = self._get_or_raise(execution_id)
        if original.status not in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        ):
            raise ExecutionStateError(
                f"Replay requires COMPLETED/FAILED/CANCELLED status "
                f"(current={original.status.value})",
                from_status=original.status.value,
                to_status="replay",
            )
        # Create a fresh session from the same request.
        new_session = self._sessions.create_session(original.request)
        logger.info(
            "ExecutionService.replay: %s → new_id=%s",
            execution_id,
            new_session.execution_id,
        )
        new_session.metadata["replayed_from"] = execution_id
        result = self._workflow.run(new_session)
        self._sessions.update_session(new_session)
        return result

    # ── Archive ───────────────────────────────────────────────────────────────

    def archive(self, execution_id: str) -> None:
        self._sessions.archive_session(execution_id)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_raise(self, execution_id: str) -> ExecutionSession:
        try:
            return self._sessions.get_session(execution_id)
        except Exception:
            raise ExecutionNotFoundError(
                f"Execution not found: {execution_id}",
                execution_id=execution_id,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_count": self._sessions.session_count(),
        }
