"""
supervisor_factory.py — iios.supervisor.lifecycle
--------------------------------------------------
Factory for constructing supervisor session domain objects.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 1
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .constants import (
    SupervisorPriority,
    SupervisorScope,
    SupervisorType,
)
from .supervisor_session import SupervisorSession


class SupervisorFactory:
    """
    Factory for constructing :class:`SupervisorSession` instances.

    Enforces all mandatory fields and applies sensible defaults.
    Application code should use this factory rather than instantiating
    :class:`SupervisorSession` directly.
    """

    def create(
        self,
        supervisor_id: str,
        *,
        session_id:          Optional[str]            = None,
        workflow_id:         str                       = "",
        supervisor_scope:    SupervisorScope           = SupervisorScope.SYSTEM,
        supervisor_type:     SupervisorType            = SupervisorType.CUSTOM,
        supervisor_priority: SupervisorPriority        = SupervisorPriority.MEDIUM,
        supervisor_version:  int                       = 1,
        metadata:            Optional[Dict[str, Any]]  = None,
    ) -> SupervisorSession:
        """
        Construct a new :class:`SupervisorSession` in CREATED state.

        Parameters
        ----------
        supervisor_id :       Supervised entity identifier.
        session_id :          Optional explicit session ID (auto-generated if None).
        workflow_id :         Workflow routing context.
        supervisor_scope :    Institutional scope of the supervision.
        supervisor_type :     Classification of the supervisor.
        supervisor_priority : Priority level.
        supervisor_version :  Initial version counter.
        metadata :            Supplementary metadata.

        Returns
        -------
        SupervisorSession
            Session in CREATED state.

        Raises
        ------
        ValueError
            If ``supervisor_id`` is empty.
        """
        if not supervisor_id:
            raise ValueError("supervisor_id must be a non-empty string")

        return SupervisorSession(
            session_id          = session_id,
            supervisor_id       = supervisor_id,
            workflow_id         = workflow_id,
            supervisor_scope    = supervisor_scope,
            supervisor_type     = supervisor_type,
            supervisor_priority = supervisor_priority,
            supervisor_version  = supervisor_version,
            metadata            = metadata,
        )
