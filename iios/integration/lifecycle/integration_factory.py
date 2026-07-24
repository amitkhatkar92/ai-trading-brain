"""
integration_factory.py — iios.integration.lifecycle
-----------------------------------------------------
Factory for creating IntegrationSession objects with consistent defaults.

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
"""
from __future__ import annotations

import uuid
from typing import Optional

from iios.common.logging.logging_manager import get_logger

from .integration_context import IntegrationContext
from .integration_metadata import IntegrationMetadata
from .integration_session import IntegrationSession

_log = get_logger(__name__)


class IntegrationFactory:
    """Creates IntegrationSession objects with correct structure."""

    # ----------------------------------------------------------------
    # Construction
    # ----------------------------------------------------------------

    def create(
        self,
        workflow_id: str,
        *,
        metadata:   Optional[IntegrationMetadata]  = None,
        context:    Optional[IntegrationContext]   = None,
        session_id: Optional[str]                  = None,
    ) -> IntegrationSession:
        """
        Create a new IntegrationSession.

        Args:
            workflow_id: Identifies the owning workflow.
            metadata:    Integration metadata.  Defaults to IntegrationMetadata.default().
            context:     Integration context.   Auto-generated if not supplied.
            session_id:  Custom session ID.     Auto-generated (UUID) if not supplied.

        Returns:
            IntegrationSession in CREATED state.
        """
        sid      = session_id or f"is-{uuid.uuid4().hex[:16]}"
        meta     = metadata or IntegrationMetadata.default()
        ctx      = context  or IntegrationContext.create(session_id=sid)

        session  = IntegrationSession(
            session_id  = sid,
            workflow_id = workflow_id,
            context     = ctx,
            metadata    = meta,
        )
        _log.debug(
            f"Factory created session: id={sid!r} workflow={workflow_id!r}"
        )
        return session

    def create_default(self, workflow_id: str) -> IntegrationSession:
        """
        Create an IntegrationSession with all default values.

        Args:
            workflow_id: Identifies the owning workflow.

        Returns:
            IntegrationSession in CREATED state.
        """
        return self.create(workflow_id)
