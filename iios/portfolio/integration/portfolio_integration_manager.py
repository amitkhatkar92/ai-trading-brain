"""
portfolio_integration_manager.py — iios.portfolio.integration
==============================================================
PortfolioIntegrationManager — coordinates the integration workflow.

Receives an integration request, orchestrates all five subsystems,
publishes the snapshot, and returns the response.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    INTEGRATION_SYSTEM_ID,
    IntegrationServiceType,
    WorkflowStage,
    CREATION_SERVICES,
    READONLY_SERVICES,
)
from .exceptions import IntegrationSnapshotError
from .portfolio_component_registry import PortfolioComponentRegistry
from .portfolio_integration_context import IntegrationContext
from .portfolio_integration_request import PortfolioIntegrationRequest
from .portfolio_integration_response import PortfolioIntegrationResponse
from .portfolio_integration_snapshot import PortfolioIntegrationSnapshot
from .portfolio_integration_statistics import PortfolioIntegrationStatistics
from .portfolio_integration_validation import PortfolioIntegrationValidator

_log = get_logger(__name__)

# Service types that benefit from running the lifecycle
_LIFECYCLE_SERVICES = frozenset({
    IntegrationServiceType.PORTFOLIO_CREATION.value,
    IntegrationServiceType.PORTFOLIO_UPDATE.value,
    IntegrationServiceType.PORTFOLIO_REBALANCING.value,
    IntegrationServiceType.PORTFOLIO_SYNCHRONIZATION.value,
})

# Service types that need optimization
_OPTIMIZATION_SERVICES = frozenset({
    IntegrationServiceType.PORTFOLIO_OPTIMIZATION.value,
    IntegrationServiceType.PORTFOLIO_CREATION.value,
    IntegrationServiceType.PORTFOLIO_REBALANCING.value,
})

# Service types that need policy review
_POLICY_SERVICES = frozenset({
    IntegrationServiceType.PORTFOLIO_CREATION.value,
    IntegrationServiceType.PORTFOLIO_UPDATE.value,
    IntegrationServiceType.PORTFOLIO_REBALANCING.value,
    IntegrationServiceType.PORTFOLIO_OPTIMIZATION.value,
    IntegrationServiceType.PORTFOLIO_REVIEW.value,
})


class PortfolioIntegrationManager:
    """
    Coordinates the portfolio integration workflow.

    The manager receives a :class:`PortfolioIntegrationRequest`,
    orchestrates the five integrated subsystems in the correct sequence,
    and returns a :class:`PortfolioIntegrationResponse`.

    Workflow sequence::

        1. Validate integration context
        2. Initialize portfolio session (Lifecycle, creation services only)
        3. Submit to Portfolio Engine
        4. Submit to Policy Framework (selected services)
        5. Submit to Optimization Framework (selected services)
        6. Build and publish Portfolio Snapshot
        7. Return Portfolio Response

    Each step is independently guarded — failures result in partial
    responses rather than hard exceptions wherever possible.
    """

    def __init__(
        self,
        component_registry: PortfolioComponentRegistry,
        statistics:         PortfolioIntegrationStatistics,
    ) -> None:
        self._registry   = component_registry
        self._stats      = statistics
        self._validator  = PortfolioIntegrationValidator()
        self._snap_util  = PortfolioIntegrationSnapshot()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def execute(
        self, request: PortfolioIntegrationRequest
    ) -> PortfolioIntegrationResponse:
        """Execute the full integration workflow for the given request."""
        started_at = time.time()
        context    = request.context
        result: Dict[str, Any] = {}
        stage      = WorkflowStage.REQUEST_RECEIVED
        session_id = context.session_id or f"int-{uuid.uuid4().hex[:12]}"

        try:
            # ── Step 1: Validate ─────────────────────────────────────
            stage = WorkflowStage.CONTEXT_VALIDATED
            val = self._validator.validate(request, self._registry)
            result["validation"] = {
                "is_valid":    val.is_valid,
                "passed":      val.passed_count,
                "failed":      val.failed_count,
                "error_msgs":  list(val.error_messages),
            }
            if not val.is_valid:
                _log.debug(
                    f"Integration validation failed for {request.portfolio_id}: "
                    f"{val.error_messages}"
                )
                return PortfolioIntegrationResponse.failure(
                    request.request_id,
                    request.portfolio_id,
                    request.service_type,
                    f"Validation failed: {'; '.join(val.error_messages)}",
                    workflow_stage = stage.value,
                    started_at     = started_at,
                    result         = result,
                )

            # ── Step 2: Lifecycle session ─────────────────────────────
            if request.service_type in _LIFECYCLE_SERVICES:
                stage = WorkflowStage.SESSION_INITIALIZED
                session_id = self._try_lifecycle_init(request, result) or session_id
            stage = WorkflowStage.LIFECYCLE_COORDINATED

            # ── Step 3: Portfolio Engine ──────────────────────────────
            stage = WorkflowStage.ENGINE_INVOKED
            if request.service_type not in {
                IntegrationServiceType.PORTFOLIO_QUERY.value,
                IntegrationServiceType.PORTFOLIO_VALIDATION.value,
            }:
                self._try_engine(request, result)

            # ── Step 4: Policy Framework ──────────────────────────────
            stage = WorkflowStage.POLICY_COORDINATED
            if request.service_type in _POLICY_SERVICES:
                self._try_policy(request, result)

            # ── Step 5: Optimization Framework ───────────────────────
            stage = WorkflowStage.OPTIMIZATION_COORDINATED
            if request.service_type in _OPTIMIZATION_SERVICES:
                self._try_optimization(request, result)

            # ── Step 6: Build + publish snapshot ─────────────────────
            stage = WorkflowStage.SNAPSHOT_PUBLISHED
            snapshot = self._build_and_publish_snapshot(
                request, session_id, result
            )

            # ── Step 7: Record statistics and return ─────────────────
            stage = WorkflowStage.COMPLETED
            duration_ms = (time.time() - started_at) * 1000
            self._stats.record_snapshot_published()
            self._stats.record_success(duration_ms)
            if request.service_type == IntegrationServiceType.PORTFOLIO_OPTIMIZATION.value:
                self._stats.record_optimization()
            if request.service_type == IntegrationServiceType.PORTFOLIO_REVIEW.value:
                self._stats.record_review()

            return PortfolioIntegrationResponse.success(
                request.request_id,
                request.portfolio_id,
                request.service_type,
                snapshot       = snapshot,
                result         = result,
                workflow_stage = stage.value,
                started_at     = started_at,
            )

        except IntegrationSnapshotError as exc:
            duration_ms = (time.time() - started_at) * 1000
            self._stats.record_failure(duration_ms)
            return PortfolioIntegrationResponse.failure(
                request.request_id, request.portfolio_id, request.service_type,
                str(exc),
                workflow_stage = stage.value,
                started_at     = started_at,
                result         = result,
            )
        except Exception as exc:
            duration_ms = (time.time() - started_at) * 1000
            self._stats.record_failure(duration_ms)
            _log.debug(f"Integration workflow error at {stage}: {exc}")
            return PortfolioIntegrationResponse.failure(
                request.request_id, request.portfolio_id, request.service_type,
                f"Workflow error at stage {stage}: {exc}",
                workflow_stage = stage.value,
                started_at     = started_at,
                result         = result,
            )

    # ------------------------------------------------------------------
    # Private workflow steps
    # ------------------------------------------------------------------

    def _try_lifecycle_init(
        self,
        request: PortfolioIntegrationRequest,
        result:  Dict[str, Any],
    ) -> Optional[str]:
        """
        Attempt to create a lifecycle session.
        Returns session_id on success, None on failure.
        """
        lc = self._registry.get_lifecycle()
        if lc is None:
            return None
        try:
            from iios.portfolio.lifecycle.constants import (
                PortfolioType, PortfolioScope, PortfolioObjective, PortfolioStatus
            )
            inp = request.inputs
            session = lc.create(
                request.portfolio_id,
                portfolio_name = inp.get("portfolio_name", ""),
            )
            lc.initialize(session.session_id)
            result["lifecycle"] = {
                "session_id":    session.session_id,
                "state":         "initialized",
                "portfolio_id":  request.portfolio_id,
            }
            self._stats.record_session_created()
            return session.session_id
        except Exception as exc:
            _log.debug(f"Lifecycle init skipped for {request.portfolio_id}: {exc}")
            result["lifecycle"] = {"state": "skipped", "reason": str(exc)}
            return None

    def _try_engine(
        self,
        request: PortfolioIntegrationRequest,
        result:  Dict[str, Any],
    ) -> None:
        """Attempt to invoke the Portfolio Engine."""
        eng = self._registry.get_engine()
        if eng is None:
            return
        try:
            from iios.portfolio.engine import PortfolioRequest, PortfolioWorkflowType
            _SERVICE_TO_WORKFLOW = {
                IntegrationServiceType.PORTFOLIO_CREATION.value:        PortfolioWorkflowType.PORTFOLIO_CREATION,
                IntegrationServiceType.PORTFOLIO_UPDATE.value:          PortfolioWorkflowType.PORTFOLIO_UPDATE,
                IntegrationServiceType.PORTFOLIO_OPTIMIZATION.value:    PortfolioWorkflowType.PORTFOLIO_CREATION,
                IntegrationServiceType.PORTFOLIO_REBALANCING.value:     PortfolioWorkflowType.PORTFOLIO_REBALANCING,
                IntegrationServiceType.PORTFOLIO_SYNCHRONIZATION.value: PortfolioWorkflowType.PORTFOLIO_SYNCHRONIZATION,
                IntegrationServiceType.PORTFOLIO_REPORTING.value:       PortfolioWorkflowType.PORTFOLIO_CREATION,
            }
            wf_type = _SERVICE_TO_WORKFLOW.get(
                request.service_type, PortfolioWorkflowType.PORTFOLIO_CREATION
            )
            eng_req = PortfolioRequest.create(
                request.portfolio_id, wf_type,
                metadata = {"integration_request_id": request.request_id},
            )
            eng_resp = eng.submit(eng_req)
            result["engine"] = {
                "status": (
                    eng_resp.status.value
                    if hasattr(eng_resp.status, "value")
                    else str(eng_resp.status)
                ),
                "request_id": eng_req.request_id,
            }
        except Exception as exc:
            _log.debug(f"Engine step skipped: {exc}")
            result["engine"] = {"status": "skipped", "reason": str(exc)}

    def _try_policy(
        self,
        request: PortfolioIntegrationRequest,
        result:  Dict[str, Any],
    ) -> None:
        """Attempt to invoke the Policy Framework."""
        pol = self._registry.get_policy()
        if pol is None:
            return
        try:
            from iios.portfolio.policies import PortfolioPolicyRequest
            pol_req = PortfolioPolicyRequest.create(
                request.portfolio_id,
                metadata = {"integration_request_id": request.request_id},
            )
            pol_resp = pol.submit(pol_req)
            result["policy"] = {
                "approved": pol_resp.is_approved,
                "action":   (
                    pol_resp.final_action.value
                    if hasattr(pol_resp.final_action, "value")
                    else str(pol_resp.final_action)
                ),
            }
        except Exception as exc:
            _log.debug(f"Policy step skipped: {exc}")
            result["policy"] = {"status": "skipped", "reason": str(exc)}

    def _try_optimization(
        self,
        request: PortfolioIntegrationRequest,
        result:  Dict[str, Any],
    ) -> None:
        """Attempt to invoke the Optimization Framework."""
        opt = self._registry.get_optimization()
        if opt is None:
            return
        try:
            from iios.portfolio.optimization import (
                PortfolioOptimizationRequest, PortfolioCandidate
            )
            inp     = request.inputs
            opt_req = PortfolioOptimizationRequest.create(
                request.portfolio_id,
                metadata = {"integration_request_id": request.request_id},
            )
            opt_resp = opt.submit(opt_req)
            result["optimization"] = {
                "status": (
                    opt_resp.status.value
                    if hasattr(opt_resp.status, "value")
                    else str(opt_resp.status)
                ),
            }
        except Exception as exc:
            _log.debug(f"Optimization step skipped: {exc}")
            result["optimization"] = {"status": "skipped", "reason": str(exc)}

    def _build_and_publish_snapshot(
        self,
        request:    PortfolioIntegrationRequest,
        session_id: str,
        result:     Dict[str, Any],
    ) -> Any:
        """Build and publish a PortfolioSnapshot; return the published snapshot."""
        from iios.portfolio.snapshot import SnapshotStatus

        # Build snapshot from integration context
        snap = self._snap_util.build(
            request,
            session_id,
            result,
            snapshot_status = SnapshotStatus.DRAFT,
        )

        # Publish via snapshot registry
        snap_reg = self._registry.get_snapshot_registry()
        if snap_reg is None:
            # No registry — return draft snapshot as-is
            return snap
        try:
            registered  = snap_reg.register(snap)
            published   = snap_reg.publish(registered.snapshot_id)
            return published
        except Exception as exc:
            raise IntegrationSnapshotError(
                f"Snapshot publication failed: {exc}",
                portfolio_id = request.portfolio_id,
            ) from exc
