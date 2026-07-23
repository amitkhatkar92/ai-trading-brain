"""
supervisor_dispatcher.py — iios.supervisor.engine
--------------------------------------------------
Supervisor workflow dispatcher.

Routes supervisor pipelines to the appropriate governance frameworks:
  - AI Governance Policy Framework (M3 — registered when available)
  - Autonomous Governance Framework (M4 — registered when available)

When frameworks are not registered the dispatcher proceeds with a
pass-through dispatch (no policy evaluation, no autonomous governance).

The dispatcher NEVER:
  - Evaluates governance policies (M3 responsibility)
  - Performs AI reasoning or autonomous governance (M4 responsibility)
  - Makes trading decisions
  - Executes trades
  - Communicates with brokers

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    DISPATCHER_SYSTEM_ID,
    EngineState,
    PipelineStatus,
    SupervisorWorkflowType,
    SUPERVISION_WORKFLOWS,
    MONITORING_WORKFLOWS,
)
from .supervisor_pipeline import SupervisorPipeline, PipelineStage
from .supervisor_request import SupervisorRequest
from .exceptions import SupervisorDispatchError

_log = get_logger(__name__)


class SupervisorDispatcher:
    """
    Routes supervisor pipelines to external governance frameworks.

    Frameworks are optional plugins — the dispatcher runs without them and
    they can be registered at any time via
    :meth:`register_governance_framework` and
    :meth:`register_autonomous_framework`.

    The dispatcher NEVER evaluates policies or performs AI reasoning.
    Those responsibilities belong to M3 and M4 respectively.
    """

    def __init__(self) -> None:
        self._governance_framework: Optional[Callable] = None  # M3 hook
        self._autonomous_framework: Optional[Callable] = None  # M4 hook
        self._dispatch_count: int = 0
        self._failure_count:  int = 0

    # ------------------------------------------------------------------
    # Framework registration
    # ------------------------------------------------------------------

    def register_governance_framework(self, framework: Callable) -> None:
        """Register the AI Governance Policy Framework (M3)."""
        self._governance_framework = framework
        _log.info("AI Governance Policy Framework registered with dispatcher")

    def register_autonomous_framework(self, framework: Callable) -> None:
        """Register the Autonomous Governance Framework (M4)."""
        self._autonomous_framework = framework
        _log.info("Autonomous Governance Framework registered with dispatcher")

    def unregister_governance_framework(self) -> None:
        self._governance_framework = None

    def unregister_autonomous_framework(self) -> None:
        self._autonomous_framework = None

    @property
    def has_governance_framework(self) -> bool:
        return self._governance_framework is not None

    @property
    def has_autonomous_framework(self) -> bool:
        return self._autonomous_framework is not None

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------

    def next_engine_state(
        self,
        workflow_type: SupervisorWorkflowType,
    ) -> EngineState:
        """
        Determine the target engine state after DISPATCHING.

        Full supervision workflows → SUPERVISING.
        Monitoring workflows       → MONITORING.
        """
        if workflow_type in SUPERVISION_WORKFLOWS:
            return EngineState.SUPERVISING
        return EngineState.MONITORING

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(
        self,
        pipeline: SupervisorPipeline,
        request:  SupervisorRequest,
    ) -> SupervisorPipeline:
        """
        Dispatch a pipeline through available governance frameworks.

        Workflow routing:
        1. Delegate to AI Governance Policy Framework (M3) if registered.
        2. Delegate to Autonomous Governance Framework (M4) if registered.
        3. Return the pipeline for post-dispatch handling.

        Returns
        -------
        SupervisorPipeline
            The same pipeline instance (mutated in-place).
        """
        try:
            # Delegate to Governance Framework (M3)
            if self._governance_framework is not None:
                stage_start = time.time()
                try:
                    self._governance_framework(pipeline, request)
                    pipeline.add_stage(PipelineStage(
                        stage_name   = "governance_framework",
                        engine_state = EngineState.DISPATCHING,
                        status       = PipelineStatus.COMPLETED,
                        started_at   = stage_start,
                        completed_at = time.time(),
                    ))
                except Exception as exc:
                    pipeline.add_stage(PipelineStage(
                        stage_name   = "governance_framework",
                        engine_state = EngineState.DISPATCHING,
                        status       = PipelineStatus.FAILED,
                        started_at   = stage_start,
                        completed_at = time.time(),
                        error        = str(exc),
                    ))
                    _log.warning(
                        f"Governance framework hook raised: {exc}"
                    )

            # Delegate to Autonomous Framework (M4)
            if self._autonomous_framework is not None:
                stage_start = time.time()
                try:
                    self._autonomous_framework(pipeline, request)
                    pipeline.add_stage(PipelineStage(
                        stage_name   = "autonomous_framework",
                        engine_state = EngineState.DISPATCHING,
                        status       = PipelineStatus.COMPLETED,
                        started_at   = stage_start,
                        completed_at = time.time(),
                    ))
                except Exception as exc:
                    pipeline.add_stage(PipelineStage(
                        stage_name   = "autonomous_framework",
                        engine_state = EngineState.DISPATCHING,
                        status       = PipelineStatus.FAILED,
                        started_at   = stage_start,
                        completed_at = time.time(),
                        error        = str(exc),
                    ))
                    _log.warning(
                        f"Autonomous framework hook raised: {exc}"
                    )

            self._dispatch_count += 1
            return pipeline

        except Exception as exc:
            self._failure_count += 1
            raise SupervisorDispatchError(
                str(exc),
                workflow_type=request.workflow_type.value,
            ) from exc

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def statistics(self) -> dict:
        return {
            "dispatch_count":            self._dispatch_count,
            "failure_count":             self._failure_count,
            "has_governance_framework":  self.has_governance_framework,
            "has_autonomous_framework":  self.has_autonomous_framework,
        }
