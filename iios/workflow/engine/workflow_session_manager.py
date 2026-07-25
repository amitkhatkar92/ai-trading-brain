"""
workflow_session_manager.py — iios.workflow.engine
---------------------------------------------------
WorkflowSessionManager — bridges M2 Workflow Engine to
M1 Workflow Lifecycle.

Manages lifecycle sessions on behalf of the engine.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.workflow.lifecycle import (
    WorkflowLifecycle,
    WorkflowMetadata,
    WorkflowSession,
)

from .exceptions import WorkflowSessionError

_log = get_logger(__name__)


class WorkflowSessionManager:
    """
    Thread-safe bridge from M2 Workflow Engine to M1 Workflow Lifecycle.

    Creates sessions, walks them through the lifecycle, and tracks
    which sessions belong to the engine's active workflows.
    """

    def __init__(
        self,
        lifecycle: Optional[WorkflowLifecycle] = None,
        engine_id: str                         = "iios-workflow-engine",
    ) -> None:
        self._lifecycle  = lifecycle or WorkflowLifecycle()
        self._engine_id  = engine_id
        self._active:    Dict[str, str] = {}   # session_id → workflow_id
        self._lock       = threading.Lock()

    # ----------------------------------------------------------------
    # Session creation and lifecycle coordination
    # ----------------------------------------------------------------

    def create_session(
        self,
        workflow_id: str,
        *,
        metadata: Optional[WorkflowMetadata] = None,
    ) -> str:
        """
        Create a new M1 lifecycle session for the workflow.

        Returns:
            session_id
        """
        try:
            session = self._lifecycle.create_session(
                workflow_id, metadata=metadata
            )
            sid = session.session_id
            with self._lock:
                self._active[sid] = workflow_id
            _log.debug(
                f"SessionManager: created session={sid!r} "
                f"workflow={workflow_id!r}"
            )
            return sid
        except Exception as exc:
            raise WorkflowSessionError(
                f"Failed to create session for workflow {workflow_id!r}: {exc}"
            ) from exc

    def initialize_session(
        self,
        session_id: str,
        *,
        reason: str = "engine initialized session",
    ) -> None:
        try:
            self._lifecycle.initialize(session_id, reason=reason)
        except Exception as exc:
            raise WorkflowSessionError(
                f"Failed to initialize session {session_id!r}: {exc}"
            ) from exc

    def validate_session(
        self,
        session_id: str,
        *,
        reason: str = "engine validated session",
    ) -> None:
        try:
            self._lifecycle.validate_workflow(session_id, reason=reason)
        except Exception as exc:
            raise WorkflowSessionError(
                f"Failed to validate session {session_id!r}: {exc}"
            ) from exc

    def mark_ready(
        self,
        session_id: str,
        *,
        reason: str = "session ready",
    ) -> None:
        try:
            self._lifecycle.mark_ready(session_id, reason=reason)
        except Exception as exc:
            raise WorkflowSessionError(
                f"Failed to mark session {session_id!r} ready: {exc}"
            ) from exc

    def start_session(
        self,
        session_id: str,
        *,
        reason: str = "engine started workflow",
    ) -> None:
        try:
            self._lifecycle.start(session_id, reason=reason)
        except Exception as exc:
            raise WorkflowSessionError(
                f"Failed to start session {session_id!r}: {exc}"
            ) from exc

    def complete_session(
        self,
        session_id:            str,
        *,
        runtime_ms:            float = 0.0,
        lifecycle_duration_ms: float = 0.0,
        reason:                str   = "engine completed session",
    ) -> None:
        try:
            self._lifecycle.complete(
                session_id,
                runtime_ms=runtime_ms,
                lifecycle_duration_ms=lifecycle_duration_ms,
                reason=reason,
            )
        except Exception as exc:
            _log.warning(
                f"Could not complete session {session_id!r}: {exc!r}"
            )
        finally:
            with self._lock:
                self._active.pop(session_id, None)

    def fail_session(
        self,
        session_id: str,
        reason:     str = "engine error",
    ) -> None:
        try:
            self._lifecycle.fail(session_id, reason=reason)
        except Exception as exc:
            _log.warning(
                f"Could not fail session {session_id!r}: {exc!r}"
            )
        finally:
            with self._lock:
                self._active.pop(session_id, None)

    def cancel_session(
        self,
        session_id: str,
        reason:     str = "cancelled by engine",
    ) -> None:
        try:
            self._lifecycle.cancel(session_id, reason=reason)
        except Exception as exc:
            _log.warning(
                f"Could not cancel session {session_id!r}: {exc!r}"
            )
        finally:
            with self._lock:
                self._active.pop(session_id, None)

    def archive_session(
        self,
        session_id: str,
        *,
        reason: str = "archived by engine",
    ) -> None:
        try:
            self._lifecycle.archive(session_id, reason=reason)
            with self._lock:
                self._active.pop(session_id, None)
        except Exception as exc:
            _log.warning(
                f"Could not archive session {session_id!r}: {exc!r}"
            )

    def get_session(self, session_id: str) -> Optional[WorkflowSession]:
        return self._lifecycle.get_session(session_id)

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def active_session_ids(self) -> List[str]:
        with self._lock:
            return list(self._active.keys())

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def lifecycle(self) -> WorkflowLifecycle:
        return self._lifecycle
