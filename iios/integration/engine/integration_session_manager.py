"""
integration_session_manager.py — iios.integration.engine
----------------------------------------------------------
IntegrationSessionManager — bridges M2 Integration Engine to
M1 Integration Lifecycle.

Manages lifecycle sessions on behalf of the engine.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import uuid
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.integration.lifecycle import (
    IntegrationLifecycle,
    IntegrationMetadata,
    IntegrationSession,
)

from .exceptions import IntegrationSessionError

_log = get_logger(__name__)


class IntegrationSessionManager:
    """
    Thread-safe bridge from M2 Integration Engine to M1 Integration Lifecycle.

    Creates sessions, walks them through the lifecycle, and tracks
    which sessions belong to the engine's current workflow.
    """

    def __init__(
        self,
        lifecycle:      Optional[IntegrationLifecycle] = None,
        engine_id:      str                            = "iios-engine",
    ) -> None:
        self._lifecycle  = lifecycle or IntegrationLifecycle()
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
        metadata: Optional[IntegrationMetadata] = None,
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
            return sid
        except Exception as exc:
            raise IntegrationSessionError(
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
            raise IntegrationSessionError(
                f"Failed to initialize session {session_id!r}: {exc}"
            ) from exc

    def complete_session(
        self,
        session_id: str,
        *,
        reason: str = "engine completed session",
    ) -> None:
        try:
            # Walk to COMPLETED: need to be in ACTIVE state
            # (caller may have already walked through states)
            self._lifecycle.complete(session_id, reason=reason)
        except Exception as exc:
            _log.warning(
                f"Could not complete session {session_id!r}: {exc!r}"
            )

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

    # ----------------------------------------------------------------
    # Full lifecycle walk (create → initialize → ... → active)
    # ----------------------------------------------------------------

    def create_and_initialize(self, workflow_id: str) -> str:
        """
        Create a session and walk it through to ACTIVE state.

        Returns:
            session_id of the active session.
        """
        sid = self.create_session(workflow_id)
        lifecycle = self._lifecycle
        try:
            lifecycle.initialize(sid)
            lifecycle.discover(sid)
            lifecycle.configure(sid)
            lifecycle.validate_session(sid)
            lifecycle.mark_ready(sid)
            lifecycle.connect(sid)
            lifecycle.activate(sid)
        except Exception as exc:
            self.fail_session(sid, reason=str(exc))
            raise IntegrationSessionError(
                f"Failed to walk session {sid!r} to ACTIVE: {exc}"
            ) from exc
        return sid

    # ----------------------------------------------------------------
    # Read
    # ----------------------------------------------------------------

    def get_session(self, session_id: str) -> Optional[IntegrationSession]:
        return self._lifecycle.get_session(session_id)

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def active_session_ids(self) -> List[str]:
        with self._lock:
            return list(self._active.keys())

    @property
    def lifecycle(self) -> IntegrationLifecycle:
        return self._lifecycle
