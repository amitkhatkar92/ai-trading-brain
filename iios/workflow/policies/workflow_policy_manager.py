"""
workflow_policy_manager.py — iios.workflow.policies
----------------------------------------------------
WorkflowPolicyManager — top-level public API for the Governance
Policy Framework.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Any, Dict

from iios.common.logging.logging_manager import get_logger

from .exceptions import WorkflowPolicyEngineError
from .workflow_policy import WorkflowPolicy
from .workflow_policy_engine import WorkflowPolicyEngine
from .workflow_policy_events import WorkflowPolicyEventBus
from .workflow_policy_history import WorkflowPolicyHistory
from .workflow_policy_request import WorkflowPolicyRequest
from .workflow_policy_response import WorkflowPolicyResponse

_log = get_logger(__name__)


class WorkflowPolicyManager:
    """
    Top-level public API for governance policy evaluation.

    Wraps the WorkflowPolicyEngine with explicit start/stop lifecycle
    management.  All public methods validate that the manager is started
    before delegating to the engine.
    """

    def __init__(self, engine: WorkflowPolicyEngine = None) -> None:
        self._engine  = engine or WorkflowPolicyEngine()
        self._started = False
        self._lock    = threading.Lock()

    # ----------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------

    def start(self) -> None:
        """Start the manager and initialise the engine."""
        with self._lock:
            if self._started:
                return
            self._engine.initialize()
            self._started = True
        _log.info(
            f"PolicyManager: started engine_id={self._engine.engine_id!r}"
        )

    def stop(self) -> None:
        """Stop the manager and the engine."""
        with self._lock:
            if not self._started:
                return
            self._engine.stop()
            self._started = False
        _log.info(
            f"PolicyManager: stopped engine_id={self._engine.engine_id!r}"
        )

    @property
    def is_started(self) -> bool:
        with self._lock:
            return self._started

    # ----------------------------------------------------------------
    # Policy registration
    # ----------------------------------------------------------------

    def register_policy(self, policy: WorkflowPolicy) -> None:
        """Register a governance policy.  Manager must be started."""
        self._require_started()
        self._engine.register_policy(policy)

    def validate_policy(self, policy: WorkflowPolicy) -> Dict[str, Any]:
        """Validate a policy without registering it."""
        return self._engine.validate_policy(policy)

    # ----------------------------------------------------------------
    # Governance evaluation
    # ----------------------------------------------------------------

    def evaluate(self, request: WorkflowPolicyRequest) -> WorkflowPolicyResponse:
        """
        Evaluate governance policies for a workflow request.

        Raises:
            WorkflowPolicyEngineError if the manager is not started.

        Returns:
            WorkflowPolicyResponse with governance decision.
        """
        self._require_started()
        return self._engine.evaluate_governance(request)

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        return self._engine.health()

    def statistics(self) -> Dict[str, Any]:
        return self._engine.statistics()

    def history(self) -> WorkflowPolicyHistory:
        return self._engine.history()

    def event_bus(self) -> WorkflowPolicyEventBus:
        return self._engine.event_bus()

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _require_started(self) -> None:
        with self._lock:
            started = self._started
        if not started:
            raise WorkflowPolicyEngineError(
                "WorkflowPolicyManager is not started — call start() first"
            )
