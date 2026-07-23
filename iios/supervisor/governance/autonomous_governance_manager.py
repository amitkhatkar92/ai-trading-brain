"""
autonomous_governance_manager.py — iios.supervisor.governance
--------------------------------------------------------------
Autonomous governance assessment orchestrator.

Pipeline (for every :meth:`run_governance` call):
  1.  Validate request
  2.  Orchestrate analytical agents
  3.  Assess platform health
  4.  Build dependency graph
  5.  Detect anomalies
  6.  Correlate incidents
  7.  Perform root cause analysis
  8.  Assess enterprise state
  9.  Score governance compliance
  10. Analyse subsystem coordination
  11. Generate self-healing plan
  12. Generate recommendations
  13. Make governance decision
  14. Produce enterprise reasoning summary
  15. Build AutonomousGovernanceSummary
  16. Update statistics and history
  17. Return summary

Never raises — any exception → create_failure summary with safe defaults.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

import time
from typing import Optional

from .constants import GovernanceDecision
from .agent_orchestration_engine import AgentOrchestrationEngine
from .anomaly_detection_engine import AnomalyDetectionEngine
from .autonomous_governance_history import AutonomousGovernanceHistory
from .autonomous_governance_request import AutonomousGovernanceRequest
from .autonomous_governance_response import AutonomousGovernanceSummary
from .autonomous_governance_statistics import AutonomousGovernanceStatistics
from .autonomous_governance_validator import AutonomousGovernanceValidator
from .dependency_analysis_engine import DependencyAnalysisEngine
from .enterprise_reasoning_engine import EnterpriseReasoningEngine
from .enterprise_state_engine import EnterpriseStateEngine
from .governance_decision_engine import GovernanceDecisionEngine
from .governance_score_engine import GovernanceScoreEngine
from .incident_analysis_engine import IncidentAnalysisEngine
from .platform_health_engine import PlatformHealthEngine
from .recommendation_engine import RecommendationEngine
from .root_cause_analysis_engine import RootCauseAnalysisEngine
from .self_healing_engine import SelfHealingEngine
from .subsystem_coordination_engine import SubsystemCoordinationEngine
from .supervision_strategy_engine import SupervisionStrategyEngine


class AutonomousGovernanceManager:
    """
    Orchestrates the full autonomous governance assessment pipeline.

    All subsystems are injectable for testability.
    """

    def __init__(
        self,
        platform_health_engine:    Optional[PlatformHealthEngine]       = None,
        dependency_engine:         Optional[DependencyAnalysisEngine]   = None,
        anomaly_engine:            Optional[AnomalyDetectionEngine]     = None,
        incident_engine:           Optional[IncidentAnalysisEngine]     = None,
        root_cause_engine:         Optional[RootCauseAnalysisEngine]    = None,
        enterprise_state_engine:   Optional[EnterpriseStateEngine]      = None,
        score_engine:              Optional[GovernanceScoreEngine]      = None,
        coordination_engine:       Optional[SubsystemCoordinationEngine] = None,
        self_healing_engine:       Optional[SelfHealingEngine]          = None,
        recommendation_engine:     Optional[RecommendationEngine]       = None,
        decision_engine:           Optional[GovernanceDecisionEngine]   = None,
        reasoning_engine:          Optional[EnterpriseReasoningEngine]  = None,
        strategy_engine:           Optional[SupervisionStrategyEngine]  = None,
        orchestration_engine:      Optional[AgentOrchestrationEngine]   = None,
        validator:                 Optional[AutonomousGovernanceValidator] = None,
        statistics:                Optional[AutonomousGovernanceStatistics] = None,
        history:                   Optional[AutonomousGovernanceHistory]    = None,
    ) -> None:
        self._health_engine      = platform_health_engine  or PlatformHealthEngine()
        self._dep_engine         = dependency_engine        or DependencyAnalysisEngine()
        self._anomaly_engine     = anomaly_engine           or AnomalyDetectionEngine()
        self._incident_engine    = incident_engine          or IncidentAnalysisEngine()
        self._rc_engine          = root_cause_engine        or RootCauseAnalysisEngine()
        self._state_engine       = enterprise_state_engine  or EnterpriseStateEngine()
        self._score_engine       = score_engine             or GovernanceScoreEngine()
        self._coord_engine       = coordination_engine      or SubsystemCoordinationEngine()
        self._heal_engine        = self_healing_engine      or SelfHealingEngine()
        self._rec_engine         = recommendation_engine    or RecommendationEngine()
        self._decision_engine    = decision_engine          or GovernanceDecisionEngine()
        self._reasoning_engine   = reasoning_engine         or EnterpriseReasoningEngine()
        self._strategy_engine    = strategy_engine          or SupervisionStrategyEngine()
        self._orch_engine        = orchestration_engine     or AgentOrchestrationEngine()
        self._validator          = validator                or AutonomousGovernanceValidator()
        self._statistics         = statistics               or AutonomousGovernanceStatistics()
        self._history            = history                  or AutonomousGovernanceHistory()

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def run_governance(
        self, request: AutonomousGovernanceRequest
    ) -> AutonomousGovernanceSummary:
        """
        Execute the full autonomous governance pipeline.

        Never raises.  On exception returns a create_failure summary.

        Parameters
        ----------
        request : AutonomousGovernanceRequest

        Returns
        -------
        AutonomousGovernanceSummary
        """
        self._statistics.record_session()
        self._history.record_request(request)
        t0 = time.perf_counter()

        try:
            summary = self._execute_pipeline(request)
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            self._statistics.record_failure()
            summary = AutonomousGovernanceSummary.create_failure(
                supervision_id = request.supervision_id,
                subsystem_id   = request.subsystem_id,
                workflow_type  = request.workflow_type,
                error_message  = str(exc),
                elapsed_s      = elapsed,
            )

        self._history.record_summary(summary)
        self._history.record_audit(summary.to_dict())
        return summary

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def _execute_pipeline(
        self, request: AutonomousGovernanceRequest
    ) -> AutonomousGovernanceSummary:
        t0  = time.perf_counter()
        ctx = request.context

        # Step 1: Orchestrate agents.
        self._orch_engine.orchestrate(request)

        # Step 2: Platform health.
        platform_health = self._health_engine.assess(ctx)

        # Step 3: Dependency analysis.
        dependency_report = self._dep_engine.analyze(ctx, platform_health)

        # Step 4: Anomaly detection.
        anomaly_report = self._anomaly_engine.detect(ctx, platform_health)

        # Step 5: Incident correlation.
        incident_report = self._incident_engine.correlate(anomaly_report)

        # Step 6: Root cause analysis.
        root_cause_report = self._rc_engine.analyze(incident_report, dependency_report, ctx)

        # Step 7: Enterprise state.
        enterprise_state = self._state_engine.assess(
            platform_health, anomaly_report, incident_report,
        )

        # Step 8: Governance scoring.
        governance_report = self._score_engine.score(ctx, enterprise_state)

        # Step 9: Subsystem coordination (enriches reasoning).
        self._coord_engine.analyze(platform_health, dependency_report)

        # Step 10: Self-healing plan.
        self_healing_plan = self._heal_engine.plan(incident_report, root_cause_report)

        # Step 11: Recommendations.
        recommendations = self._rec_engine.generate(
            enterprise_state, governance_report,
            anomaly_report, incident_report, self_healing_plan,
        )

        # Step 12: Final decision.
        final_decision = self._decision_engine.decide(
            governance_report, enterprise_state,
            anomaly_report, incident_report, self_healing_plan,
        )

        # Step 13: Enterprise reasoning summary.
        reasoning_summary = self._reasoning_engine.reason(
            platform_health, anomaly_report, incident_report,
            root_cause_report, dependency_report, enterprise_state,
            governance_report, recommendations, self_healing_plan,
            final_decision,
        )

        elapsed = time.perf_counter() - t0

        # Update statistics.
        self._statistics.record_success(elapsed)
        self._statistics.record_enterprise_assessment()
        self._statistics.record_anomalies(anomaly_report.total)
        self._statistics.record_incidents(incident_report.total)
        self._statistics.record_root_causes(root_cause_report.total)
        self._statistics.record_recommendations(recommendations.total)
        self._statistics.record_self_healing_plan()
        self._statistics.record_stability(enterprise_state.stability_score)

        return AutonomousGovernanceSummary.create_success(
            supervision_id    = request.supervision_id,
            subsystem_id      = request.subsystem_id,
            workflow_type     = request.workflow_type,
            governance_report = governance_report,
            platform_health   = platform_health,
            anomaly_report    = anomaly_report,
            incident_report   = incident_report,
            root_cause_report = root_cause_report,
            dependency_report = dependency_report,
            recommendations   = recommendations,
            self_healing_plan = self_healing_plan,
            enterprise_state  = enterprise_state,
            final_decision    = final_decision,
            reasoning_summary = reasoning_summary,
            elapsed_s         = elapsed,
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def statistics(self):
        return self._statistics.snapshot()

    def history_counts(self):
        return self._history.counts()
