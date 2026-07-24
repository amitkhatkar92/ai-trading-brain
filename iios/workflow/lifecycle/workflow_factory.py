"""
workflow_factory.py — iios.workflow.lifecycle
----------------------------------------------
Factory for creating WorkflowSession objects with consistent defaults.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

import uuid
from typing import Optional

from iios.common.logging.logging_manager import get_logger

from .workflow_context import WorkflowContext
from .workflow_metadata import WorkflowMetadata
from .workflow_session import WorkflowSession

_log = get_logger(__name__)


class WorkflowFactory:
    """Creates WorkflowSession objects with correct structure."""

    # ----------------------------------------------------------------
    # Construction
    # ----------------------------------------------------------------

    def create(
        self,
        workflow_id: str,
        *,
        metadata:   Optional[WorkflowMetadata] = None,
        context:    Optional[WorkflowContext]  = None,
        session_id: Optional[str]              = None,
    ) -> WorkflowSession:
        """
        Create a new WorkflowSession.

        Args:
            workflow_id: Identifies the workflow definition.
            metadata:    Workflow metadata.  Defaults to WorkflowMetadata.default().
            context:     Workflow context.   Auto-generated if not supplied.
            session_id:  Custom session ID.  Auto-generated (UUID) if not supplied.

        Returns:
            WorkflowSession in CREATED state.
        """
        sid  = session_id or f"ws-{uuid.uuid4().hex[:16]}"
        meta = metadata or WorkflowMetadata.default()
        ctx  = context  or WorkflowContext.create(session_id=sid)

        session = WorkflowSession(
            session_id  = sid,
            workflow_id = workflow_id,
            context     = ctx,
            metadata    = meta,
        )
        _log.debug(
            f"Factory created workflow session: id={sid!r} workflow={workflow_id!r}"
        )
        return session

    def create_default(self, workflow_id: str) -> WorkflowSession:
        """
        Create a WorkflowSession with all default values.

        Args:
            workflow_id: Identifies the workflow definition.

        Returns:
            WorkflowSession in CREATED state.
        """
        return self.create(workflow_id)
