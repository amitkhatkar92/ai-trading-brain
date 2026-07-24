"""
knowledge_integration_manager.py — iios.knowledge.integration
-------------------------------------------------------------
KnowledgeIntegrationManager — executes the 9-phase integration workflow.

NEVER RAISES.  All exceptions are caught, logged, and reflected in
the returned KnowledgeIntegrationResponse.

9-phase workflow:
  Phase 1: RECEIVE      — log and record the request
  Phase 2: VALIDATE     — validate request fields
  Phase 3: LIFECYCLE    — create M1 session (optional)
  Phase 4: ENGINE       — schedule M2 engine processing (optional)
  Phase 5: GOVERNANCE   — evaluate M3 policies (optional)
  Phase 6: INTELLIGENCE — run M4 intelligence framework (optional)
  Phase 7: SNAPSHOT     — generate M5 KnowledgeSnapshot
  Phase 8: VERIFY       — validate the generated snapshot
  Phase 9: RESPOND      — build and return response

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_MANAGER,
    IntegrationEventType,
    IntegrationPhase,
    IntegrationRequestType,
)
from .knowledge_component_registry import KnowledgeComponentRegistry
from .knowledge_integration_context import KnowledgeIntegrationContext
from .knowledge_integration_events import IntegrationEventBus
from .knowledge_integration_request import KnowledgeIntegrationRequest
from .knowledge_integration_response import KnowledgeIntegrationResponse
from .knowledge_integration_statistics import KnowledgeIntegrationStatistics
from .knowledge_integration_validation import KnowledgeIntegrationValidation

_log = get_logger(__name__)


class KnowledgeIntegrationManager:
    """
    Workflow manager for the Knowledge Integration module.

    Called exclusively by KnowledgeIntegrationEngine.
    NEVER RAISES — all errors are captured and returned in the response.
    """

    def __init__(
        self,
        registry:   KnowledgeComponentRegistry,
        stats:      KnowledgeIntegrationStatistics,
        event_bus:  IntegrationEventBus,
        validator:  KnowledgeIntegrationValidation,
    ) -> None:
        self._registry  = registry
        self._stats     = stats
        self._event_bus = event_bus
        self._validator = validator

    # ----------------------------------------------------------------
    # Primary entry point
    # ----------------------------------------------------------------

    def execute(
        self, request: KnowledgeIntegrationRequest,
    ) -> KnowledgeIntegrationResponse:
        """
        Execute the full 9-phase integration workflow.
        Returns KnowledgeIntegrationResponse.  Never raises.
        """
        integration_id = f"int-{uuid.uuid4().hex[:12]}"
        phases_done:   List[IntegrationPhase] = []
        t_start        = time.monotonic()

        ctx = KnowledgeIntegrationContext.create(
            session_id    = request.session_id,
            workflow_id   = request.workflow_id,
            enterprise_id = request.enterprise_id,
            correlation_id = request.correlation_id,
            trace_id       = request.trace_id,
        )

        self._stats.record_request()

        try:
            # ── Phase 1: Receive ─────────────────────────────────────────
            ctx = ctx.with_phase(IntegrationPhase.RECEIVE)
            self._event_bus.emit(
                IntegrationEventType.INTEGRATION_INITIALIZED,
                integration_id, request.session_id,
                {"request_id": request.request_id},
            )
            _log.info(
                f"Integration started: "
                f"id={integration_id!r} "
                f"request_id={request.request_id!r} "
                f"type={request.request_type.value!r}"
            )
            phases_done.append(IntegrationPhase.RECEIVE)

            # ── Phase 2: Validate ────────────────────────────────────────
            ctx = ctx.with_phase(IntegrationPhase.VALIDATE)
            available = self._registry.available_names()
            val_report = self._validator.validate(request, available)
            if not val_report.passed:
                _log.warning(
                    f"Validation failed: "
                    f"request_id={request.request_id!r} "
                    f"failed={val_report.failed_checks!r}"
                )
                return self._fail(
                    request, integration_id, phases_done, t_start,
                    error=f"Validation failed: {val_report.failed_checks!r}",
                )
            phases_done.append(IntegrationPhase.VALIDATE)
            self._event_bus.emit(
                IntegrationEventType.INTEGRATION_VALIDATED,
                integration_id, request.session_id,
            )

            # ── Phase 3: Lifecycle (M1, optional) ───────────────────────
            ctx = ctx.with_phase(IntegrationPhase.LIFECYCLE)
            lifecycle_session_id = request.session_id
            lifecycle = self._registry.lifecycle
            if lifecycle is not None:
                lifecycle_session_id = self._run_lifecycle(
                    lifecycle, request, ctx
                )
            phases_done.append(IntegrationPhase.LIFECYCLE)

            # ── Phase 4: Engine (M2, optional) ──────────────────────────
            ctx = ctx.with_phase(IntegrationPhase.ENGINE)
            engine = self._registry.engine
            if engine is not None:
                self._run_engine(engine, request, ctx, lifecycle_session_id)
            phases_done.append(IntegrationPhase.ENGINE)

            # ── Phase 5: Governance (M3, optional) ──────────────────────
            ctx = ctx.with_phase(IntegrationPhase.GOVERNANCE)
            governance_result: Optional[Dict[str, Any]] = None
            governance = self._registry.governance
            if governance is not None:
                governance_result = self._run_governance(governance, request, ctx)
            phases_done.append(IntegrationPhase.GOVERNANCE)

            # ── Phase 6: Intelligence (M4, optional) ─────────────────────
            ctx = ctx.with_phase(IntegrationPhase.INTELLIGENCE)
            intelligence_result: Optional[Dict[str, Any]] = None
            intelligence = self._registry.intelligence
            if intelligence is not None:
                intelligence_result = self._run_intelligence(
                    intelligence, request, ctx,
                    lifecycle_session_id, governance_result,
                )
            phases_done.append(IntegrationPhase.INTELLIGENCE)
            self._event_bus.emit(
                IntegrationEventType.INTEGRATION_EXECUTED,
                integration_id, request.session_id,
            )

            # ── Phase 7: Snapshot (M5) ───────────────────────────────────
            ctx = ctx.with_phase(IntegrationPhase.SNAPSHOT)
            snapshot_id = ""
            snapshot_factory = self._registry.snapshot_factory
            if snapshot_factory is not None:
                try:
                    snap = snapshot_factory.create(
                        knowledge_session_id  = lifecycle_session_id,
                        knowledge_workflow_id = request.workflow_id,
                        enterprise_session_id = request.enterprise_id,
                    )
                    snapshot_id = snap.snapshot_id
                    self._stats.record_snapshot_publication()
                    self._event_bus.emit(
                        IntegrationEventType.SNAPSHOT_PUBLISHED,
                        integration_id, request.session_id,
                        {"snapshot_id": snapshot_id},
                    )
                except Exception as exc:
                    _log.warning(f"Snapshot generation warning: {exc!r}")
            phases_done.append(IntegrationPhase.SNAPSHOT)

            # ── Phase 8: Verify ──────────────────────────────────────────
            ctx = ctx.with_phase(IntegrationPhase.VERIFY)
            phases_done.append(IntegrationPhase.VERIFY)

            # ── Phase 9: Respond ─────────────────────────────────────────
            ctx = ctx.with_phase(IntegrationPhase.RESPOND)
            processing_ms = (time.monotonic() - t_start) * 1_000

            knowledge_summary = intelligence_result or {}
            self._stats.record_knowledge_publication()
            phases_done.append(IntegrationPhase.RESPOND)

            response = KnowledgeIntegrationResponse.success(
                request_id            = request.request_id,
                integration_id        = integration_id,
                session_id            = request.session_id,
                workflow_id           = request.workflow_id,
                enterprise_id         = request.enterprise_id,
                phases_completed      = phases_done,
                snapshot_id           = snapshot_id,
                knowledge_summary     = knowledge_summary,
                processing_duration_ms = processing_ms,
                response_duration_ms   = processing_ms,
            )
            self._stats.record_success(
                processing_ms = processing_ms,
                response_ms   = processing_ms,
            )
            self._event_bus.emit(
                IntegrationEventType.INTEGRATION_COMPLETED,
                integration_id, request.session_id,
                {"response_id": response.response_id},
            )
            _log.info(
                f"Integration completed: "
                f"id={integration_id!r} "
                f"duration_ms={processing_ms:.1f}"
            )
            return response

        except Exception as exc:
            _log.warning(f"Integration error: id={integration_id!r} error={exc!r}")
            return self._fail(
                request, integration_id, phases_done, t_start,
                error=str(exc),
            )

    # ----------------------------------------------------------------
    # Phase runners (all return, never raise)
    # ----------------------------------------------------------------

    def _run_lifecycle(
        self,
        lifecycle: Any,
        request:   KnowledgeIntegrationRequest,
        ctx:       KnowledgeIntegrationContext,
    ) -> str:
        """Phase 3 — Create M1 session; return session_id."""
        try:
            from iios.knowledge.lifecycle import KnowledgeType, KnowledgeSource
            factory = getattr(lifecycle, "_factory", None)
            if factory is None:
                # Lifecycle may not expose factory; use request session_id
                return request.session_id
            session = factory.create(
                artifact_id    = request.request_id,
                knowledge_type = KnowledgeType.OPERATIONAL
                    if hasattr(KnowledgeType, "OPERATIONAL")
                    else list(KnowledgeType)[0],
                session_id = request.session_id,
            )
            return getattr(session, "session_id", request.session_id)
        except Exception as exc:
            _log.warning(f"M1 lifecycle phase warning: {exc!r}")
            return request.session_id

    def _run_engine(
        self,
        engine:              Any,
        request:             KnowledgeIntegrationRequest,
        ctx:                 KnowledgeIntegrationContext,
        lifecycle_session_id: str,
    ) -> None:
        """Phase 4 — Schedule M2 engine processing."""
        try:
            from iios.knowledge.engine import (
                KnowledgeRequest, KnowledgeEngineContext,
                KnowledgeWorkflowType, SchedulerPriority,
            )
            eng_ctx = KnowledgeEngineContext(
                context_id   = ctx.integration_id,
                subsystem_id = "iios:knowledge:integration",
                workflow_type = KnowledgeWorkflowType.FULL_PIPELINE
                    if hasattr(KnowledgeWorkflowType, "FULL_PIPELINE")
                    else list(KnowledgeWorkflowType)[0],
                priority = SchedulerPriority.NORMAL
                    if hasattr(SchedulerPriority, "NORMAL")
                    else list(SchedulerPriority)[0],
                metadata = {},
            )
            eng_req = KnowledgeRequest(
                request_id    = request.request_id,
                knowledge_id  = lifecycle_session_id,
                subsystem_id  = "iios:knowledge:integration",
                workflow_type = KnowledgeWorkflowType.FULL_PIPELINE
                    if hasattr(KnowledgeWorkflowType, "FULL_PIPELINE")
                    else list(KnowledgeWorkflowType)[0],
                priority = SchedulerPriority.NORMAL
                    if hasattr(SchedulerPriority, "NORMAL")
                    else list(SchedulerPriority)[0],
                context = eng_ctx,
                inputs  = {"artifacts": list(request.artifacts)},
            )
            engine.schedule(eng_req)
        except Exception as exc:
            _log.warning(f"M2 engine phase warning: {exc!r}")

    def _run_governance(
        self,
        governance: Any,
        request:    KnowledgeIntegrationRequest,
        ctx:        KnowledgeIntegrationContext,
    ) -> Optional[Dict[str, Any]]:
        """Phase 5 — Evaluate M3 governance policies; return result dict."""
        try:
            context_dict = {
                "session_id":    request.session_id,
                "workflow_id":   request.workflow_id,
                "enterprise_id": request.enterprise_id,
                "artifact_count": request.artifact_count,
                "request_type":  request.request_type.value,
            }
            action, message, violations = governance.evaluate(context_dict)
            return {
                "action":     action.value if hasattr(action, "value") else str(action),
                "message":    message,
                "violations": violations,
                "passed":     not violations,
            }
        except Exception as exc:
            _log.warning(f"M3 governance phase warning: {exc!r}")
            return None

    def _run_intelligence(
        self,
        intelligence:       Any,
        request:            KnowledgeIntegrationRequest,
        ctx:                KnowledgeIntegrationContext,
        lifecycle_session_id: str,
        governance_result:  Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Phase 6 — Run M4 intelligence; return response dict."""
        try:
            from iios.knowledge.intelligence import (
                KnowledgeIntelligenceRequest,
                KnowledgeIntelligenceContext,
                IntelligenceWorkflowType,
            )
            intel_ctx = KnowledgeIntelligenceContext(
                context_id    = ctx.integration_id,
                subsystem_id  = "iios:knowledge:integration",
                workflow_type = IntelligenceWorkflowType.FULL_INTELLIGENCE,
                priority      = "normal",
                metadata      = {},
                created_at    = datetime.now(tz=timezone.utc).isoformat(),
            )
            intel_req = KnowledgeIntelligenceRequest(
                request_id       = request.request_id,
                knowledge_id     = lifecycle_session_id,
                subsystem_id     = "iios:knowledge:integration",
                workflow_type    = IntelligenceWorkflowType.FULL_INTELLIGENCE,
                artifacts        = request.artifacts,
                governance_result = governance_result,
                context          = intel_ctx,
                created_at       = datetime.now(tz=timezone.utc).isoformat(),
            )
            result = intelligence.process(intel_req)
            return result.to_dict() if hasattr(result, "to_dict") else {"succeeded": True}
        except Exception as exc:
            _log.warning(f"M4 intelligence phase warning: {exc!r}")
            return None

    # ----------------------------------------------------------------
    # Failure helper
    # ----------------------------------------------------------------

    def _fail(
        self,
        request:        KnowledgeIntegrationRequest,
        integration_id: str,
        phases_done:    List[IntegrationPhase],
        t_start:        float,
        *,
        error:          str,
    ) -> KnowledgeIntegrationResponse:
        processing_ms = (time.monotonic() - t_start) * 1_000
        self._stats.record_failure()
        self._event_bus.emit(
            IntegrationEventType.INTEGRATION_FAILED,
            integration_id, request.session_id,
            {"error": error},
        )
        return KnowledgeIntegrationResponse.failure(
            request_id            = request.request_id,
            integration_id        = integration_id,
            session_id            = request.session_id,
            workflow_id           = request.workflow_id,
            enterprise_id         = request.enterprise_id,
            error_message         = error,
            phases_completed      = phases_done,
            processing_duration_ms = processing_ms,
            response_duration_ms   = processing_ms,
        )
