"""
supervisor_integration_manager.py — iios.supervisor.integration
----------------------------------------------------------------
Internal orchestrator that runs the full M1→M2→M3→M4→M5 integration
pipeline for each :class:`SupervisorIntegrationRequest`.

This module MUST NOT:
  - Evaluate governance policies (that is M3's job)
  - Perform AI reasoning or anomaly detection (that is M4's job)
  - Execute trades or communicate with brokers

It MUST:
  - Wire M1-M5 subsystems sequentially
  - NEVER raise an exception to callers — return a failure response instead
  - Record statistics and history for every request

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

import time
from typing import Any, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import ComponentType
from .supervisor_component_registry import SupervisorComponentRegistry
from .supervisor_integration_events import (
    make_integration_completed_event,
    make_integration_executed_event,
    make_integration_failed_event,
    make_integration_started_event,
    make_integration_validated_event,
    make_snapshot_published_event,
)
from .supervisor_integration_history import SupervisorIntegrationHistory
from .supervisor_integration_registry import SupervisorIntegrationRegistry
from .supervisor_integration_request import SupervisorIntegrationRequest
from .supervisor_integration_response import (
    EnterpriseAssessment,
    IntegrationGovernanceSummary,
    PlatformHealthSummary,
    SupervisorIntegrationResponse,
)
from .supervisor_integration_snapshot import SupervisorIntegrationSnapshot
from .supervisor_integration_statistics import SupervisorIntegrationStatistics
from .supervisor_integration_validation import SupervisorIntegrationValidator

_log = get_logger(__name__)


class SupervisorIntegrationManager:
    """
    Internal pipeline orchestrator for the AI Supervisor Integration layer.

    Each call to :meth:`run_integration` executes the following 7-step
    pipeline and returns a :class:`SupervisorIntegrationResponse`.  The
    method NEVER propagates exceptions — it catches all errors and returns a
    failure response with the error details.

    Pipeline
    --------
    1. Validate request (Validator)
    2. Register request (Registry)
    3. M1 Lifecycle — create & initialise a supervision session
    4. M2 Engine    — submit the supervisor request
    5. M3 Policy    — evaluate governance policies
    6. M4 Governance— execute autonomous governance
    7. M5 Snapshot  — generate the supervisor snapshot
    8. Build & register response
    """

    def __init__(
        self,
        component_registry: Optional[SupervisorComponentRegistry] = None,
        statistics:         Optional[SupervisorIntegrationStatistics] = None,
        history:            Optional[SupervisorIntegrationHistory]    = None,
        registry:           Optional[SupervisorIntegrationRegistry]   = None,
        validator:          Optional[SupervisorIntegrationValidator]  = None,
        event_listeners:    Optional[list] = None,
    ) -> None:
        self._components  = component_registry or SupervisorComponentRegistry()
        self._stats       = statistics or SupervisorIntegrationStatistics()
        self._history     = history    or SupervisorIntegrationHistory()
        self._registry    = registry   or SupervisorIntegrationRegistry()
        self._validator   = validator  or SupervisorIntegrationValidator()
        self._listeners   = event_listeners if event_listeners is not None else []

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    def run_integration(
        self, request: SupervisorIntegrationRequest
    ) -> SupervisorIntegrationResponse:
        """
        Execute the full integration pipeline and return a response.

        Never raises.  Any exception is caught and returned as a failure response.
        """
        start = time.time()
        self._stats.record_integration_started()
        self._history.record_request(request)
        self._fire(make_integration_started_event(
            request.integration_id, request.request_id,
            mode=request.mode.value,
        ))

        try:
            # Step 1 — Validate request
            validation = self._validator.validate_request(request)
            self._fire(make_integration_validated_event(
                request.integration_id, request.request_id,
                is_valid=validation.is_valid,
            ))
            if not validation.is_valid:
                error = "; ".join(validation.failure_messages) or "Validation failed"
                return self._fail(request, error, start)

            # Register in-flight
            self._registry.register_request(request)

            # Step 2 — M1 Lifecycle (non-fatal if unavailable)
            lc_session_id = self._run_lifecycle_step(request)

            # Step 3 — M2 Engine
            m2_response = self._run_engine_step(request)
            self._fire(make_integration_executed_event(
                request.integration_id, request.request_id,
                phase="engine", elapsed_s=time.time() - start,
            ))

            # Step 4 — M3 Policy evaluation
            m3_response = self._run_policy_step(request, m2_response)
            self._fire(make_integration_executed_event(
                request.integration_id, request.request_id,
                phase="policy", elapsed_s=time.time() - start,
            ))

            # Step 5 — M4 Autonomous governance
            m4_summary = self._run_governance_step(request, m3_response)
            self._fire(make_integration_executed_event(
                request.integration_id, request.request_id,
                phase="governance", elapsed_s=time.time() - start,
            ))

            # Step 6 — M5 Snapshot
            snapshot = self._run_snapshot_step(request, m4_summary)
            snap_id = getattr(snapshot, "snapshot_id", "") if snapshot else ""
            self._fire(make_snapshot_published_event(
                request.integration_id, request.request_id,
                snapshot_id=snap_id,
            ))
            self._stats.record_snapshot_publication()

            # Build response
            elapsed = time.time() - start
            response = self._build_success_response(
                request, m2_response, m3_response, m4_summary, snapshot,
                session_id=lc_session_id,
                processing_time_s=elapsed,
            )

        except Exception as exc:  # noqa: BLE001
            _log.info(f"Integration pipeline error: {exc}")
            return self._fail(request, str(exc), start)

        # Archive M1 session (best-effort)
        self._archive_lifecycle_session(request, lc_session_id)

        # Finalise
        elapsed = time.time() - start
        self._stats.record_success(elapsed)
        self._history.record_response(response)
        self._registry.register_response(response)
        self._fire(make_integration_completed_event(
            request.integration_id, request.request_id,
            processing_time_s=elapsed,
        ))
        return response

    # ------------------------------------------------------------------
    # Pipeline steps (each returns a result or None on non-fatal failure)
    # ------------------------------------------------------------------

    def _run_lifecycle_step(self, request: SupervisorIntegrationRequest) -> str:
        """Create an M1 supervisor session for this request.  Returns session_id."""
        try:
            lc = self._components.get_optional(ComponentType.LIFECYCLE)
            if lc is None:
                return request.session_id

            session_id = request.session_id or request.integration_id
            # M1 states: create → initialize → discover → validate → mark_ready → start_supervising
            session = lc.create(session_id)
            sid = session.session_id
            lc.initialize(sid)
            lc.discover(sid)
            lc.validate_session(sid)
            lc.mark_ready(sid)
            lc.start_supervising(sid)
            return sid
        except Exception as exc:  # noqa: BLE001
            _log.info(f"M1 lifecycle step non-fatal error: {exc}")
            return request.session_id

    def _run_engine_step(
        self, request: SupervisorIntegrationRequest
    ) -> Any:
        """Submit to M2 SupervisorEngine.  Returns SupervisorResponse."""
        try:
            engine = self._components.get_optional(ComponentType.ENGINE)
            if engine is None:
                return None

            from iios.supervisor.engine.supervisor_request import SupervisorRequest
            from iios.supervisor.engine.constants import SupervisorWorkflowType

            m2_req = SupervisorRequest.create(
                supervision_id = request.integration_id,
                subsystem_id   = "integration",
                workflow_type  = SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
                inputs         = request.inputs,
                metadata       = {"integration_request_id": request.request_id},
            )
            return engine.submit(m2_req)
        except Exception as exc:  # noqa: BLE001
            _log.info(f"M2 engine step non-fatal error: {exc}")
            return None

    def _run_policy_step(
        self,
        request:     SupervisorIntegrationRequest,
        m2_response: Any,
    ) -> Any:
        """Evaluate M3 governance policies.  Returns AIGovernancePolicyResponse."""
        try:
            policy_engine = self._components.get_optional(ComponentType.POLICY)
            if policy_engine is None:
                return None

            from iios.supervisor.policies.ai_governance_policy_request import (
                AIGovernancePolicyRequest,
            )

            # Merge M2 health summary into inputs for policy evaluation
            inputs = dict(request.inputs)
            if m2_response is not None:
                m2_health = getattr(m2_response, "health_summary", None) or {}
                inputs.update(m2_health)

            m3_req = AIGovernancePolicyRequest.create(
                supervision_id = request.integration_id,
                subsystem_id   = "integration",
                workflow_type  = "enterprise_health_review",
                inputs         = inputs,
            )
            return policy_engine.evaluate(m3_req)
        except Exception as exc:  # noqa: BLE001
            _log.info(f"M3 policy step non-fatal error: {exc}")
            return None

    def _run_governance_step(
        self,
        request:     SupervisorIntegrationRequest,
        m3_response: Any,
    ) -> Any:
        """Execute M4 autonomous governance.  Returns AutonomousGovernanceSummary."""
        try:
            gov_engine = self._components.get_optional(ComponentType.GOVERNANCE)
            if gov_engine is None:
                return None

            from iios.supervisor.governance.autonomous_governance_request import (
                AutonomousGovernanceRequest,
            )

            # Extract final_action from M3 response
            final_action = "APPROVE"
            if m3_response is not None:
                dec = getattr(m3_response, "governance_decision_summary", None)
                if dec is not None:
                    act = getattr(dec, "final_action", None)
                    if act is not None:
                        final_action = getattr(act, "value", str(act))

            m4_inputs = {
                **request.inputs,
                "governance_policy_response": {"final_action": final_action},
            }
            m4_req = AutonomousGovernanceRequest.create(
                supervision_id = request.integration_id,
                subsystem_id   = "integration",
                inputs         = m4_inputs,
            )
            return gov_engine.govern(m4_req)
        except Exception as exc:  # noqa: BLE001
            _log.info(f"M4 governance step non-fatal error: {exc}")
            return None

    def _run_snapshot_step(
        self,
        request:    SupervisorIntegrationRequest,
        m4_summary: Any,
    ) -> Any:
        """Generate an M5 supervisor snapshot.  Returns SupervisorSnapshot."""
        try:
            snap_factory = self._components.get_optional(ComponentType.SNAPSHOT)
            if snap_factory is None:
                return None

            if m4_summary is not None:
                return snap_factory.create_from_governance_summary(
                    session_id  = request.session_id or request.integration_id,
                    workflow_id = request.workflow_id or request.request_id,
                    summary     = m4_summary,
                )
            # Fallback: minimal snapshot
            return snap_factory.create_minimal(
                session_id  = request.session_id or request.integration_id,
                workflow_id = request.workflow_id or request.request_id,
            )
        except Exception as exc:  # noqa: BLE001
            _log.info(f"M5 snapshot step non-fatal error: {exc}")
            return None

    def _archive_lifecycle_session(
        self,
        request:    SupervisorIntegrationRequest,
        session_id: str,
    ) -> None:
        """Move the M1 session to completed+archived state.  Best-effort."""
        if not session_id:
            return
        try:
            lc = self._components.get_optional(ComponentType.LIFECYCLE)
            if lc is None:
                return
            lc.stop_monitoring(session_id)
            lc.complete(session_id)
            lc.archive(session_id)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Response builders
    # ------------------------------------------------------------------

    def _build_success_response(
        self,
        request:          SupervisorIntegrationRequest,
        m2_response:      Any,
        m3_response:      Any,
        m4_summary:       Any,
        snapshot:         Any,
        *,
        session_id:       str   = "",
        processing_time_s: float = 0.0,
    ) -> SupervisorIntegrationResponse:
        platform_health = self._extract_platform_health(m2_response)
        gov_summary     = self._extract_governance_summary(m3_response, m4_summary)
        assessment      = self._extract_enterprise_assessment(m4_summary)

        return SupervisorIntegrationResponse.create_success(
            integration_id          = request.integration_id,
            request_id              = request.request_id,
            session_id              = session_id or request.session_id,
            supervisor_snapshot     = snapshot,
            platform_health_summary = platform_health,
            governance_summary      = gov_summary,
            enterprise_assessment   = assessment,
            processing_time_s       = processing_time_s,
        )

    def _fail(
        self,
        request: SupervisorIntegrationRequest,
        error:   str,
        start:   float,
    ) -> SupervisorIntegrationResponse:
        elapsed = time.time() - start
        self._stats.record_failure(elapsed)
        response = SupervisorIntegrationResponse.create_failure(
            integration_id    = request.integration_id,
            request_id        = request.request_id,
            error             = error,
            session_id        = request.session_id,
            processing_time_s = elapsed,
        )
        self._history.record_response(response)
        try:
            self._registry.register_response(response)
        except Exception:  # noqa: BLE001
            pass
        self._fire(make_integration_failed_event(
            request.integration_id, request.request_id, error=error,
        ))
        return response

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_platform_health(self, m2_response: Any) -> PlatformHealthSummary:
        overall   = 1.0
        status    = "HEALTHY"
        alerts    = 0
        subsystems: dict = {}
        if m2_response is not None:
            health = getattr(m2_response, "health_summary", None) or {}
            overall    = float(health.get("overall_health_score", overall))
            status     = str(health.get("platform_status", status))
            alerts     = int(health.get("active_alerts", alerts))
            subsystems = health.get("subsystem_statuses", subsystems)
        return PlatformHealthSummary.create(
            overall_health     = overall,
            platform_status    = status,
            active_alerts      = alerts,
            subsystem_statuses = subsystems,
        )

    def _extract_governance_summary(
        self, m3_response: Any, m4_summary: Any
    ) -> IntegrationGovernanceSummary:
        final_action = "APPROVE"
        rationale    = ""
        violations: tuple = ()
        decision    = "CONTINUE"
        compliant   = True

        if m3_response is not None:
            dec = getattr(m3_response, "governance_decision_summary", None)
            if dec is not None:
                act = getattr(dec, "final_action", None)
                if act is not None:
                    final_action = getattr(act, "value", str(act))
                rationale = getattr(dec, "rationale", "") or ""

        if m4_summary is not None:
            gov_report = getattr(m4_summary, "governance_report", None)
            if gov_report is not None:
                gd = getattr(gov_report, "governance_decision", None)
                if gd is not None:
                    decision = getattr(gd, "value", str(gd))
                violations = tuple(getattr(gov_report, "violations", ()) or ())
                compliant  = getattr(gov_report, "is_compliant", compliant)

        return IntegrationGovernanceSummary.create(
            final_action        = final_action,
            governance_decision = decision,
            is_compliant        = compliant,
            violations          = violations,
            policy_rationale    = rationale,
        )

    def _extract_enterprise_assessment(self, m4_summary: Any) -> EnterpriseAssessment:
        state    = "STABLE"
        stability = 1.0
        confidence = 1.0
        anomaly_count  = 0
        incident_count = 0
        reasoning = ""

        if m4_summary is not None:
            er = getattr(m4_summary, "enterprise_state", None)
            if er is not None:
                es = getattr(er, "enterprise_state", None)
                if es is not None:
                    state = getattr(es, "value", str(es))
                stability = float(getattr(er, "stability_score", stability))

            ar = getattr(m4_summary, "anomaly_report", None)
            if ar is not None:
                anomaly_count = int(getattr(ar, "total", 0))

            ir = getattr(m4_summary, "incident_report", None)
            if ir is not None:
                incident_count = int(getattr(ir, "total", 0))

            reasoning = getattr(m4_summary, "reasoning_summary", "") or ""

        return EnterpriseAssessment.create(
            enterprise_state = state,
            stability_score  = stability,
            confidence       = confidence,
            anomaly_count    = anomaly_count,
            incident_count   = incident_count,
            reasoning        = reasoning,
        )

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def _fire(self, event: Any) -> None:
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception:  # noqa: BLE001
                pass
