"""
iios/execution/recovery/failover/failover_manager.py
====================================================
FailoverManager — lifecycle-aware session manager.

Owns FailoverController, FailoverStrategyRegistry, and FailoverRegistry.
Provides idempotency: re-submitted decisions are detected and rejected.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Any

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import MANAGER_ID, VERSION
from .exceptions import FailoverNotRunningError, FailoverRegistryError
from .failover_context import FailoverContext
from .failover_controller import FailoverController
from .failover_registry import FailoverRegistry
from .failover_request import FailoverRequest
from .failover_response import FailoverResponse
from .failover_strategy_registry import FailoverStrategyRegistry

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class FailoverManager(LifecycleAwareMixin):
    """
    Lifecycle-aware manager for failover session orchestration.

    Responsibilities:
    - Session lifecycle (register active → complete)
    - Idempotency (same M3 decision not executed twice)
    - Plan lookup delegation to FailoverStrategyRegistry
    - Execution delegation to FailoverController
    """

    def __init__(self) -> None:
        super().__init__()
        self._strategy_registry = FailoverStrategyRegistry()
        self._session_registry  = FailoverRegistry()
        self._controller        = FailoverController(self._strategy_registry)

    def _on_start(self) -> None:
        self._strategy_registry.start()
        self._session_registry.start()
        self._controller.start()
        _audit.log_lifecycle_event(MANAGER_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("FailoverManager started")

    def _on_stop(self) -> None:
        self._controller.stop()
        self._session_registry.stop()
        self._strategy_registry.stop()
        _audit.log_lifecycle_event(MANAGER_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("FailoverManager stopped")

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise FailoverNotRunningError()

    # ── Primary session entry ─────────────────────────────────────────────────

    def start_failover(self, request: FailoverRequest) -> FailoverResponse:
        """
        Execute the failover for *request*.

        Raises FailoverRegistryError if the source decision has already been
        processed (idempotency guard).
        """
        self._assert_running()
        source_id = request.source_decision_id

        if self._session_registry.is_decision_processed(source_id):
            raise FailoverRegistryError(
                f"Source decision {source_id!r} has already been processed"
            )

        self._session_registry.register_active(request.failover_session_id)
        try:
            response = self._controller.execute_failover(request)
        finally:
            self._session_registry.complete(request.failover_session_id, source_id)

        return response

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def strategy_registry(self) -> FailoverStrategyRegistry:
        return self._strategy_registry

    @property
    def session_registry(self) -> FailoverRegistry:
        return self._session_registry

    @property
    def controller(self) -> FailoverController:
        return self._controller
