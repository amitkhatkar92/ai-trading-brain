"""
autonomous_governance_engine.py — iios.supervisor.governance
------------------------------------------------------------
PRIMARY PUBLIC INTERFACE for the Autonomous Governance Framework.

Responsibilities (this module ONLY):
  - Accept governance assessment requests via :meth:`govern`
  - Wire and coordinate all governance subsystems
  - Fire lifecycle audit events and dispatch domain events to listeners
  - Expose health(), statistics(), status() introspection

This module MUST NOT:
  - Evaluate governance policies (M3 responsibility)
  - Execute trades
  - Communicate with brokers
  - Modify live portfolios

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_GOVERNANCE_ENGINE,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    AUTONOMOUS_GOVERNANCE_SYSTEM_ID,
    AutonomousGovernanceEventType,
    GovernanceDecision,
    VERSION,
)
from .autonomous_governance_events import (
    AutonomousGovernanceEvent,
    make_anomaly_detected_event,
    make_dependency_graph_built_event,
    make_enterprise_assessment_completed_event,
    make_governance_engine_started_event,
    make_governance_engine_stopped_event,
    make_governance_published_event,
    make_governance_started_event,
    make_incident_correlated_event,
    make_recommendations_generated_event,
    make_root_cause_identified_event,
    make_self_healing_generated_event,
    make_snapshots_collected_event,
)
from .autonomous_governance_factory import AutonomousGovernanceFactory
from .autonomous_governance_history import AutonomousGovernanceHistory
from .autonomous_governance_manager import AutonomousGovernanceManager
from .autonomous_governance_registry import AutonomousGovernanceRegistry
from .autonomous_governance_request import AutonomousGovernanceRequest
from .autonomous_governance_response import AutonomousGovernanceSummary
from .autonomous_governance_statistics import AutonomousGovernanceStatistics
from .autonomous_governance_validator import AutonomousGovernanceValidator
from .exceptions import AutonomousGovernanceEngineNotRunningError

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=AUTONOMOUS_GOVERNANCE_SYSTEM_ID)


class AutonomousGovernanceEngine(LifecycleAwareMixin):
    """
    Institutional Autonomous Governance Engine.

    Orchestrates the full enterprise governance assessment pipeline:
    Collect → Validate → Analyse → Decide → Publish.

    Parameters
    ----------
    manager :    Injected AutonomousGovernanceManager (optional).
    registry :   Injected AutonomousGovernanceRegistry (optional).
    statistics : Injected AutonomousGovernanceStatistics (optional).
    history :    Injected AutonomousGovernanceHistory (optional).
    validator :  Injected AutonomousGovernanceValidator (optional).
    factory :    Injected AutonomousGovernanceFactory (optional).
    """

    def __init__(
        self,
        manager:    Optional[AutonomousGovernanceManager]    = None,
        registry:   Optional[AutonomousGovernanceRegistry]   = None,
        statistics: Optional[AutonomousGovernanceStatistics] = None,
        history:    Optional[AutonomousGovernanceHistory]    = None,
        validator:  Optional[AutonomousGovernanceValidator]  = None,
        factory:    Optional[AutonomousGovernanceFactory]    = None,
    ) -> None:
        super().__init__()
        # Engine-level statistics/history are separate from manager's internals.
        self._engine_statistics = statistics or AutonomousGovernanceStatistics()
        self._engine_history    = history    or AutonomousGovernanceHistory()
        self._registry          = registry   or AutonomousGovernanceRegistry()
        self._validator         = validator  or AutonomousGovernanceValidator()
        self._factory           = factory    or AutonomousGovernanceFactory()
        # Manager uses its own internal statistics/history.
        self._manager           = manager    or AutonomousGovernanceManager()

        self._listeners: List[Callable[[AutonomousGovernanceEvent], None]] = []
        self._listener_lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            engine_id  = AUTONOMOUS_GOVERNANCE_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = VERSION,
            actor      = ACTOR_OPERATOR,
        )
        _log.debug(f"AutonomousGovernanceEngine started (version={VERSION})")
        self._notify_listeners(make_governance_engine_started_event())

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            engine_id  = AUTONOMOUS_GOVERNANCE_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = VERSION,
            actor      = ACTOR_OPERATOR,
        )
        _log.debug("AutonomousGovernanceEngine stopped")
        self._notify_listeners(make_governance_engine_stopped_event())

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise AutonomousGovernanceEngineNotRunningError()

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def govern(self, request: AutonomousGovernanceRequest) -> AutonomousGovernanceSummary:
        """
        Execute the autonomous governance assessment pipeline.

        Parameters
        ----------
        request : AutonomousGovernanceRequest
            Governance assessment request.

        Returns
        -------
        AutonomousGovernanceSummary

        Raises
        ------
        AutonomousGovernanceEngineNotRunningError
            If the engine has not been started.
        """
        self._assert_running()

        # Fire GOVERNANCE_STARTED.
        self._notify_listeners(
            make_governance_started_event(
                request.supervision_id,
                request_id=request.request_id,
            )
        )

        # Fire SNAPSHOTS_COLLECTED.
        self._notify_listeners(
            make_snapshots_collected_event(
                request.supervision_id,
                snapshot_count=request.context.snapshot_count(),
            )
        )

        # Run the full pipeline (never raises).
        summary = self._manager.run_governance(request)

        # Dispatch domain events from the summary.
        self._dispatch_domain_events(summary)

        # Fire GOVERNANCE_PUBLISHED.
        self._notify_listeners(
            make_governance_published_event(
                summary.supervision_id,
                summary_id = summary.summary_id,
                is_success = summary.is_success,
                elapsed_s  = summary.elapsed_s,
            )
        )

        # Register in engine registry.
        try:
            self._registry.register(summary)
        except Exception:
            pass  # registry capacity exceeded — non-fatal

        # Record in engine history.
        self._engine_history.record_summary(summary)
        self._engine_statistics.record_session()
        if summary.is_success:
            self._engine_statistics.record_success(summary.elapsed_s)
        else:
            self._engine_statistics.record_failure()

        return summary

    # ------------------------------------------------------------------
    # Domain event dispatch
    # ------------------------------------------------------------------

    def _dispatch_domain_events(self, summary: AutonomousGovernanceSummary) -> None:
        sid = summary.supervision_id

        # Dependency graph built.
        self._notify_listeners(
            make_dependency_graph_built_event(
                sid,
                dependency_count = summary.dependency_report.total_dependencies,
                critical_paths   = len(summary.dependency_report.critical_paths),
            )
        )

        # Anomaly detected.
        if summary.anomaly_report.total:
            self._notify_listeners(
                make_anomaly_detected_event(
                    sid,
                    anomaly_count  = summary.anomaly_report.total,
                    critical_count = summary.anomaly_report.critical_count,
                )
            )

        # Incident correlated.
        if summary.incident_report.total:
            worst = ""
            if summary.incident_report.critical_count:
                worst = "critical"
            elif summary.incident_report.high_count:
                worst = "high"
            self._notify_listeners(
                make_incident_correlated_event(
                    sid,
                    incident_count = summary.incident_report.total,
                    severity       = worst,
                )
            )

        # Root cause identified.
        if summary.root_cause_report.total:
            self._notify_listeners(
                make_root_cause_identified_event(
                    sid,
                    root_cause_count = summary.root_cause_report.total,
                    identified_count = summary.root_cause_report.identified_count,
                )
            )

        # Self-healing generated.
        if summary.self_healing_plan.total:
            self._notify_listeners(
                make_self_healing_generated_event(
                    sid,
                    action_count     = summary.self_healing_plan.total,
                    can_auto_execute = summary.self_healing_plan.can_auto_execute,
                )
            )

        # Recommendations generated.
        if summary.recommendations.total:
            self._notify_listeners(
                make_recommendations_generated_event(
                    sid,
                    recommendation_count = summary.recommendations.total,
                    critical_count       = summary.recommendations.critical_count,
                )
            )

        # Enterprise assessment completed.
        self._notify_listeners(
            make_enterprise_assessment_completed_event(
                sid,
                enterprise_state = summary.enterprise_state.enterprise_state.value,
                final_decision   = summary.final_decision.value,
                elapsed_s        = summary.elapsed_s,
            )
        )

    # ------------------------------------------------------------------
    # Listener management
    # ------------------------------------------------------------------

    def add_listener(
        self, listener: Callable[[AutonomousGovernanceEvent], None]
    ) -> None:
        with self._listener_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(
        self, listener: Callable[[AutonomousGovernanceEvent], None]
    ) -> None:
        with self._listener_lock:
            self._listeners.remove(listener)

    def _notify_listeners(self, event: AutonomousGovernanceEvent) -> None:
        with self._listener_lock:
            listeners = list(self._listeners)
        self._engine_history.record_event(event)
        for fn in listeners:
            try:
                fn(event)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        snap = self._engine_statistics.snapshot()
        return {
            "status":             self.lifecycle_state().value,
            "sessions":           snap["sessions"],
            "successes":          snap["successes"],
            "failures":           snap["failures"],
            "success_rate":       snap["success_rate"],
            "ema_elapsed_s":      snap["ema_elapsed_s"],
            "platform_stability": snap["platform_stability_score"],
            "registry_count":     self._registry.count,
        }

    def statistics(self) -> Dict[str, Any]:
        return self._engine_statistics.snapshot()

    def status(self) -> Dict[str, Any]:
        return {
            "engine_id":  AUTONOMOUS_GOVERNANCE_SYSTEM_ID,
            "version":    VERSION,
            "health":     self.health(),
            "history":    self._engine_history.counts(),
            "manager":    self._manager.statistics(),
        }
