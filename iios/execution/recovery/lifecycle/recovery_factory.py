"""iios/execution/recovery/lifecycle/recovery_factory.py
==================================================
RecoveryFactory — LifecycleAwareMixin factory for RecoverySession
creation.

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import FACTORY_SYSTEM_ID, RecoveryTrigger, VERSION
from .exceptions import RecoveryNotRunningError
from .recovery_context import RecoveryContext
from .recovery_session import RecoverySession

_log = get_logger(__name__)


class RecoveryFactory(LifecycleAwareMixin):
    """
    Lifecycle-aware factory for RecoverySession objects.

    Converts a RecoveryContext into a fully initialised RecoverySession
    in CREATED state.  The factory does NOT store sessions; that is the
    responsibility of RecoveryRegistry.
    """

    def _on_start(self) -> None:
        _log.info(
            "RecoveryFactory started.",
            system_id=FACTORY_SYSTEM_ID,
            version=VERSION,
        )

    def _on_stop(self) -> None:
        _log.info("RecoveryFactory stopped.", system_id=FACTORY_SYSTEM_ID)

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        from iios.investment.workflow.engine_lifecycle import EngineState
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryNotRunningError()

    # ── Factory methods ───────────────────────────────────────────────────────

    def create(self, context: RecoveryContext) -> RecoverySession:
        """
        Create a new RecoverySession from a RecoveryContext.

        Returns the session in CREATED state.
        """
        self._assert_running()
        session = RecoverySession(
            execution_session_id = context.execution_session_id,
            subsystem_id         = context.subsystem_id,
            recovery_trigger     = context.recovery_trigger,
            recovery_reason      = context.recovery_reason,
            workflow_id          = context.workflow_id,
            failure_id           = context.failure_id,
            recovery_plan_id     = context.recovery_plan_id,
            recovery_version     = context.recovery_version,
            metadata             = dict(context.metadata),
        )
        _log.info(
            "RecoverySession created.",
            session_id           = session.session_id,
            execution_session_id = session.execution_session_id,
            subsystem_id         = session.subsystem_id,
            recovery_trigger     = session.recovery_trigger.value,
        )
        return session

    def create_from_params(
        self,
        execution_session_id: str,
        subsystem_id:         str,
        recovery_trigger:     RecoveryTrigger,
        recovery_reason:      str,
        *,
        workflow_id:       Optional[str]            = None,
        failure_id:        Optional[str]            = None,
        recovery_plan_id:  Optional[str]            = None,
        recovery_version:  int                      = 1,
        metadata:          Optional[Dict[str, Any]] = None,
        session_id:        Optional[str]            = None,
    ) -> RecoverySession:
        """
        Create a RecoverySession from individual parameters
        (convenience wrapper — bypasses context object).
        """
        self._assert_running()
        session = RecoverySession(
            session_id           = session_id,
            execution_session_id = execution_session_id,
            subsystem_id         = subsystem_id,
            recovery_trigger     = recovery_trigger,
            recovery_reason      = recovery_reason,
            workflow_id          = workflow_id,
            failure_id           = failure_id,
            recovery_plan_id     = recovery_plan_id,
            recovery_version     = recovery_version,
            metadata             = metadata,
        )
        _log.info(
            "RecoverySession created from params.",
            session_id           = session.session_id,
            execution_session_id = session.execution_session_id,
            subsystem_id         = session.subsystem_id,
        )
        return session
