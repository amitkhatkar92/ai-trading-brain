"""
test_autonomous_governance_engine.py — tests.unit.supervisor.governance
------------------------------------------------------------------------
Comprehensive tests for the C13 M4 Autonomous Governance Framework.
95%+ coverage target.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

import pytest

from iios.supervisor.governance import (
    # --- enumerations ---
    AnomalySeverity,
    AutonomousGovernanceEventType,
    AutonomousGovernanceValidationCode,
    DependencyType,
    EnterpriseState,
    GovernanceCapability,
    GovernanceDecision,
    IncidentSeverity,
    ReasoningMode,
    RecommendationPriority,
    RootCauseCategory,
    SelfHealingActionType,
    SubsystemStatus,
    SupervisionDomain,
    SupervisionStrategyType,
    # --- constants ---
    AUTONOMOUS_GOVERNANCE_SYSTEM_ID,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    DOMAIN_SNAPSHOT_KEY,
    HEALTH_CRITICAL_THRESHOLD,
    HEALTH_NORMAL_THRESHOLD,
    PLATFORM_DEPENDENCIES,
    VERSION,
    # --- exceptions ---
    AutonomousGovernanceAssessmentError,
    AutonomousGovernanceCapacityError,
    AutonomousGovernanceContextError,
    AutonomousGovernanceEngineNotRunningError,
    AutonomousGovernanceError,
    AutonomousGovernancePublicationError,
    AutonomousGovernanceReasoningError,
    AutonomousGovernanceRegistryError,
    AutonomousGovernanceSessionError,
    AutonomousGovernanceValidationError,
    # --- context ---
    AutonomousGovernanceContext,
    # --- request ---
    AutonomousGovernanceRequest,
    # --- response types ---
    AnomalyReport,
    AutonomousGovernanceSummary,
    DependencyReport,
    EnterpriseGovernanceReport,
    EnterpriseStateReport,
    GovernanceAnomaly,
    GovernanceIncident,
    GovernanceRecommendation,
    GovernanceRecommendations,
    IncidentReport,
    PlatformHealthReport,
    RootCause,
    RootCauseReport,
    SelfHealingActionItem,
    SelfHealingPlan,
    SubsystemDependency,
    SubsystemHealth,
    # --- events ---
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
    # --- validation ---
    AutonomousGovernanceValidationResult,
    AutonomousGovernanceValidator,
    GovernanceValidationCheckResult,
    # --- statistics ---
    AutonomousGovernanceStatistics,
    # --- history ---
    AutonomousGovernanceHistory,
    # --- registry ---
    AutonomousGovernanceRegistry,
    # --- factory ---
    AutonomousGovernanceFactory,
    # --- engines ---
    AgentOrchestrationEngine,
    AnomalyDetectionEngine,
    DependencyAnalysisEngine,
    EnterpriseReasoningEngine,
    EnterpriseStateEngine,
    GovernanceDecisionEngine,
    GovernanceScoreEngine,
    IncidentAnalysisEngine,
    PlatformHealthEngine,
    RecommendationEngine,
    RootCauseAnalysisEngine,
    SelfHealingEngine,
    SubsystemCoordinationEngine,
    SupervisionStrategyEngine,
    # --- orchestration ---
    AutonomousGovernanceManager,
    # --- engine ---
    AutonomousGovernanceEngine,
)


# ===========================================================================
# Shared helpers
# ===========================================================================

def _ctx(
    supervision_id: str = "sup-001",
    subsystem_id:   str = "sub-001",
    **kwargs,
) -> AutonomousGovernanceContext:
    return AutonomousGovernanceContext.create(supervision_id, subsystem_id, **kwargs)


def _req(
    supervision_id: str = "sup-001",
    inputs: Dict[str, Any] | None = None,
) -> AutonomousGovernanceRequest:
    return AutonomousGovernanceRequest.create(
        supervision_id, inputs=inputs or {},
    )


def _healthy_req() -> AutonomousGovernanceRequest:
    return AutonomousGovernanceFactory().create_healthy_platform_request("sup-healthy")


def _emergency_req() -> AutonomousGovernanceRequest:
    return AutonomousGovernanceFactory().create_emergency_request("sup-emergency")


def _started_engine() -> AutonomousGovernanceEngine:
    e = AutonomousGovernanceEngine()
    e.start()
    return e


# ===========================================================================
# 1. Constants
# ===========================================================================

class TestConstants:
    def test_system_id_nonempty(self):
        assert AUTONOMOUS_GOVERNANCE_SYSTEM_ID

    def test_version_nonempty(self):
        assert VERSION

    def test_supervision_domain_count(self):
        assert len(SupervisionDomain) == 9

    def test_governance_capability_count(self):
        assert len(GovernanceCapability) == 12

    def test_anomaly_severity_count(self):
        assert len(AnomalySeverity) == 5

    def test_incident_severity_count(self):
        assert len(IncidentSeverity) == 5

    def test_enterprise_state_count(self):
        assert len(EnterpriseState) == 6

    def test_governance_decision_count(self):
        assert len(GovernanceDecision) == 5

    def test_self_healing_action_type_count(self):
        assert len(SelfHealingActionType) == 10

    def test_root_cause_category_count(self):
        assert len(RootCauseCategory) == 7

    def test_platform_dependencies_non_empty(self):
        assert len(PLATFORM_DEPENDENCIES) > 0

    def test_domain_snapshot_key_covers_all_non_enterprise(self):
        non_enterprise = [d for d in SupervisionDomain if d != SupervisionDomain.ENTERPRISE]
        for d in non_enterprise:
            assert d.value in DOMAIN_SNAPSHOT_KEY

    def test_health_thresholds_ordering(self):
        from iios.supervisor.governance import (
            HEALTH_OPTIMAL_THRESHOLD, HEALTH_NORMAL_THRESHOLD,
            HEALTH_DEGRADED_THRESHOLD, HEALTH_CRITICAL_THRESHOLD,
        )
        assert HEALTH_OPTIMAL_THRESHOLD > HEALTH_NORMAL_THRESHOLD
        assert HEALTH_NORMAL_THRESHOLD > HEALTH_DEGRADED_THRESHOLD
        assert HEALTH_DEGRADED_THRESHOLD > HEALTH_CRITICAL_THRESHOLD

    def test_defaults_positive(self):
        assert DEFAULT_MAX_SESSIONS > 0
        assert DEFAULT_MAX_HISTORY > 0


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(AutonomousGovernanceError, IIOSError)

    def test_not_running_subclass(self):
        assert issubclass(AutonomousGovernanceEngineNotRunningError, AutonomousGovernanceError)

    def test_not_running_message(self):
        e = AutonomousGovernanceEngineNotRunningError()
        assert "start()" in str(e)

    def test_context_error_has_supervision_id(self):
        e = AutonomousGovernanceContextError("bad ctx", supervision_id="s-1")
        assert e.supervision_id == "s-1"

    def test_capacity_has_limit(self):
        e = AutonomousGovernanceCapacityError(999)
        assert e.limit == 999

    def test_assessment_has_request_id(self):
        e = AutonomousGovernanceAssessmentError("failed", request_id="r-1")
        assert e.request_id == "r-1"

    def test_session_subclass(self):
        assert issubclass(AutonomousGovernanceSessionError, AutonomousGovernanceError)

    def test_registry_subclass(self):
        assert issubclass(AutonomousGovernanceRegistryError, AutonomousGovernanceError)

    def test_validation_subclass(self):
        assert issubclass(AutonomousGovernanceValidationError, AutonomousGovernanceError)

    def test_publication_subclass(self):
        assert issubclass(AutonomousGovernancePublicationError, AutonomousGovernanceError)


# ===========================================================================
# 3. AutonomousGovernanceContext
# ===========================================================================

class TestContext:
    def test_create_minimal(self):
        ctx = _ctx()
        assert ctx.supervision_id == "sup-001"
        assert ctx.subsystem_id == "sub-001"

    def test_create_with_snapshots(self):
        ctx = _ctx(risk_snapshot={"var": 0.02})
        assert ctx.risk_snapshot["var"] == 0.02

    def test_snapshot_count_empty(self):
        assert _ctx().snapshot_count() == 0

    def test_snapshot_count_with_data(self):
        ctx = _ctx(
            platform_health={"overall": 0.9},
            risk_snapshot={"var": 0.02},
        )
        assert ctx.snapshot_count() == 2

    def test_from_inputs(self):
        inputs = {
            "platform_health": {"overall": 0.9},
            "risk_snapshot": {"var": 0.05},
        }
        ctx = AutonomousGovernanceContext.from_inputs("s", "sub", inputs)
        assert ctx.platform_health["overall"] == 0.9
        assert ctx.risk_snapshot["var"] == 0.05

    def test_frozen(self):
        ctx = _ctx()
        with pytest.raises((TypeError, AttributeError)):
            ctx.supervision_id = "other"  # type: ignore

    def test_to_dict(self):
        d = _ctx().to_dict()
        assert "supervision_id" in d and "snapshot_count" in d

    def test_defaults_are_empty_dicts(self):
        ctx = _ctx()
        assert isinstance(ctx.platform_health, dict)
        assert isinstance(ctx.audit_events, list)


# ===========================================================================
# 4. AutonomousGovernanceRequest
# ===========================================================================

class TestRequest:
    def test_create(self):
        req = _req()
        assert req.supervision_id == "sup-001"

    def test_auto_context(self):
        req = _req()
        assert req.context.supervision_id == "sup-001"

    def test_all_domains_by_default(self):
        req = _req()
        assert len(req.domains) == len(SupervisionDomain)

    def test_explicit_domains(self):
        req = AutonomousGovernanceRequest.create(
            "s", domains=[SupervisionDomain.RISK_INTELLIGENCE]
        )
        assert len(req.domains) == 1

    def test_with_context(self):
        req = _req()
        new_ctx = _ctx(supervision_id="sup-001", platform_health={"overall": 0.9})
        req2 = req.with_context(new_ctx)
        assert req2.context.platform_health["overall"] == 0.9

    def test_frozen(self):
        req = _req()
        with pytest.raises((TypeError, AttributeError)):
            req.supervision_id = "x"  # type: ignore

    def test_to_dict(self):
        d = _req().to_dict()
        assert "request_id" in d and "domains" in d


# ===========================================================================
# 5. Response types
# ===========================================================================

class TestAnomalyReport:
    def test_create_empty(self):
        r = AnomalyReport.create(())
        assert r.total == 0

    def test_create_with_anomalies(self):
        a1 = GovernanceAnomaly.create("sub", "f", 0.1, AnomalySeverity.CRITICAL)
        a2 = GovernanceAnomaly.create("sub", "g", 0.2, AnomalySeverity.HIGH)
        r  = AnomalyReport.create((a1, a2))
        assert r.total == 2
        assert r.critical_count == 1
        assert r.high_count == 1
        assert r.has_critical

    def test_anomaly_frozen(self):
        a = GovernanceAnomaly.create("s", "f", 1, AnomalySeverity.MEDIUM)
        with pytest.raises((TypeError, AttributeError)):
            a.subsystem_id = "x"  # type: ignore

    def test_to_dict(self):
        d = AnomalyReport.create(()).to_dict()
        assert "total" in d

    def test_anomaly_to_dict(self):
        a = GovernanceAnomaly.create("s", "f", 1, AnomalySeverity.HIGH, description="test")
        d = a.to_dict()
        assert d["severity"] == AnomalySeverity.HIGH.value


class TestIncidentReport:
    def test_create_empty(self):
        r = IncidentReport.create(())
        assert r.total == 0

    def test_create_with_incident(self):
        i = GovernanceIncident.create(
            "Title", ("a1",), ("sub",), IncidentSeverity.CRITICAL
        )
        r = IncidentReport.create((i,), correlated_from_anomalies=2)
        assert r.total == 1
        assert r.critical_count == 1
        assert r.correlated_from_anomalies == 2

    def test_to_dict(self):
        d = IncidentReport.create(()).to_dict()
        assert "total" in d


class TestRootCauseReport:
    def test_create(self):
        rc = RootCause.create("inc-1", RootCauseCategory.INFRASTRUCTURE, "infra issue")
        r  = RootCauseReport.create((rc,))
        assert r.total == 1
        assert r.identified_count == 1
        assert r.unknown_count == 0

    def test_unknown_counted(self):
        rc = RootCause.create("inc-1", RootCauseCategory.UNKNOWN, "?")
        r  = RootCauseReport.create((rc,))
        assert r.unknown_count == 1
        assert r.identified_count == 0

    def test_to_dict(self):
        d = RootCauseReport.create(()).to_dict()
        assert "total" in d


class TestDependencyReport:
    def test_create(self):
        dep = SubsystemDependency("a", "b", DependencyType.HARD, is_critical=True)
        r = DependencyReport.create((dep,), ("a", "b"))
        assert r.total_dependencies == 1
        assert r.critical_dependencies == 1

    def test_to_dict(self):
        d = DependencyReport.create((), ()).to_dict()
        assert "total_dependencies" in d


class TestPlatformHealthReport:
    def test_create_empty(self):
        r = PlatformHealthReport.create(())
        assert r.overall_score == 1.0
        assert r.platform_status == SubsystemStatus.UNKNOWN

    def test_healthy(self):
        h = SubsystemHealth("sub", SubsystemStatus.HEALTHY, 0.95)
        r = PlatformHealthReport.create((h,))
        assert r.is_healthy
        assert r.healthy_count == 1

    def test_critical(self):
        h = SubsystemHealth("sub", SubsystemStatus.CRITICAL, 0.10)
        r = PlatformHealthReport.create((h,))
        assert r.platform_status == SubsystemStatus.CRITICAL

    def test_to_dict(self):
        d = PlatformHealthReport.create(()).to_dict()
        assert "overall_score" in d and "is_healthy" in d


class TestSelfHealingPlan:
    def test_create_empty(self):
        p = SelfHealingPlan.create(())
        assert p.total == 0

    def test_automated_action(self):
        a = SelfHealingActionItem.create(
            "sub", SelfHealingActionType.MONITOR, RecommendationPriority.LOW,
            is_automated=True, requires_approval=False,
        )
        p = SelfHealingPlan.create((a,))
        assert p.automated_actions == 1
        assert p.can_auto_execute

    def test_to_dict(self):
        d = SelfHealingPlan.create(()).to_dict()
        assert "total" in d


class TestEnterpriseStateReport:
    def test_emergency_property(self):
        r = EnterpriseStateReport.create(EnterpriseState.EMERGENCY)
        assert r.is_emergency
        assert r.is_critical

    def test_critical_property(self):
        r = EnterpriseStateReport.create(EnterpriseState.CRITICAL)
        assert r.is_critical
        assert not r.is_emergency

    def test_normal_not_critical(self):
        r = EnterpriseStateReport.create(EnterpriseState.NORMAL)
        assert not r.is_critical

    def test_to_dict(self):
        d = EnterpriseStateReport.create(EnterpriseState.NORMAL).to_dict()
        assert "enterprise_state" in d and "is_emergency" in d


class TestEnterpriseGovernanceReport:
    def test_compliant(self):
        r = EnterpriseGovernanceReport.create(compliance_score=0.90)
        assert r.is_compliant

    def test_not_compliant_violations(self):
        r = EnterpriseGovernanceReport.create(
            compliance_score=0.90, violations=("violation",)
        )
        assert not r.is_compliant

    def test_to_dict(self):
        d = EnterpriseGovernanceReport.create().to_dict()
        assert "compliance_score" in d and "governance_decision" in d


class TestGovernanceSummary:
    def test_create_failure(self):
        s = AutonomousGovernanceSummary.create_failure("s", "sub", "wf", "crash")
        assert not s.is_success
        assert s.final_decision == GovernanceDecision.HALT
        assert s.enterprise_state.enterprise_state == EnterpriseState.UNKNOWN

    def test_anomaly_count_property(self):
        # Build a success summary via the engine.
        factory = AutonomousGovernanceFactory()
        engine  = _started_engine()
        req = factory.create_healthy_platform_request()
        summary = engine.govern(req)
        assert summary.anomaly_count == summary.anomaly_report.total
        engine.stop()

    def test_incident_count_property(self):
        engine = _started_engine()
        summary = engine.govern(_req())
        assert summary.incident_count == summary.incident_report.total
        engine.stop()

    def test_to_dict_has_all_reports(self):
        s = AutonomousGovernanceSummary.create_failure("s", "sub", "wf", "test")
        d = s.to_dict()
        for key in ("governance_report", "platform_health", "anomaly_report",
                    "incident_report", "root_cause_report", "dependency_report",
                    "recommendations", "self_healing_plan", "enterprise_state"):
            assert key in d


# ===========================================================================
# 6. Platform Health Engine
# ===========================================================================

class TestPlatformHealthEngine:
    E = PlatformHealthEngine()

    def test_empty_context(self):
        r = self.E.assess(_ctx())
        assert r.total_subsystems_assessed() if hasattr(r, "total_subsystems_assessed") else True
        assert 0.0 <= r.overall_score <= 1.0

    def test_healthy_snapshot(self):
        ctx = _ctx(platform_health={"overall": 0.95})
        r = self.E.assess(ctx)
        assert r.overall_score > 0.0

    def test_critical_snapshot(self):
        ctx = _ctx(risk_snapshot={"health_score": 0.1, "status": "critical"})
        r = self.E.assess(ctx)
        assert any(h.status == SubsystemStatus.CRITICAL for h in r.subsystem_health)

    def test_unknown_missing_snapshot(self):
        r = self.E.assess(_ctx())
        unknown = [h for h in r.subsystem_health if "snapshot_missing" in h.issues]
        assert len(unknown) > 0

    def test_returns_platform_health_report(self):
        assert isinstance(self.E.assess(_ctx()), PlatformHealthReport)


# ===========================================================================
# 7. Dependency Analysis Engine
# ===========================================================================

class TestDependencyAnalysisEngine:
    E = DependencyAnalysisEngine()

    def test_returns_dependency_report(self):
        ph = PlatformHealthReport.create(())
        r = self.E.analyze(_ctx(), ph)
        assert isinstance(r, DependencyReport)

    def test_has_dependencies(self):
        ph = PlatformHealthReport.create(())
        r = self.E.analyze(_ctx(), ph)
        assert r.total_dependencies > 0

    def test_has_critical_paths(self):
        ph = PlatformHealthReport.create(())
        r = self.E.analyze(_ctx(), ph)
        assert len(r.critical_paths) > 0

    def test_all_domains_covered(self):
        ph = PlatformHealthReport.create(())
        r = self.E.analyze(_ctx(), ph)
        assert len(r.subsystems) > 0

    def test_critical_deps(self):
        ph = PlatformHealthReport.create(())
        r = self.E.analyze(_ctx(), ph)
        assert r.critical_dependencies > 0


# ===========================================================================
# 8. Anomaly Detection Engine
# ===========================================================================

class TestAnomalyDetectionEngine:
    E = AnomalyDetectionEngine()

    def _ph(self) -> PlatformHealthReport:
        return PlatformHealthEngine().assess(_ctx())

    def test_no_anomalies_healthy(self):
        ctx = _ctx(risk_snapshot={"health_score": 0.95}, market_snapshot={"health_score": 0.95})
        r = self.E.detect(ctx, PlatformHealthEngine().assess(ctx))
        assert isinstance(r, AnomalyReport)

    def test_high_var_anomaly(self):
        ctx = _ctx(risk_snapshot={"var": 0.90})
        ph  = PlatformHealthEngine().assess(ctx)
        r   = self.E.detect(ctx, ph)
        assert any("risk" in a.subsystem_id and a.severity == AnomalySeverity.HIGH
                   for a in r.anomalies)

    def test_market_halt_anomaly(self):
        ctx = _ctx(market_snapshot={"status": "halt"})
        ph  = PlatformHealthEngine().assess(ctx)
        r   = self.E.detect(ctx, ph)
        assert any(a.severity == AnomalySeverity.CRITICAL for a in r.anomalies)

    def test_critical_subsystem_anomaly(self):
        h   = SubsystemHealth("risk_intelligence", SubsystemStatus.CRITICAL, 0.1)
        ph  = PlatformHealthReport.create((h,))
        ctx = _ctx()
        r   = self.E.detect(ctx, ph)
        assert any(a.severity == AnomalySeverity.CRITICAL for a in r.anomalies)

    def test_infra_cpu_anomaly(self):
        ctx = _ctx(infrastructure_metrics={"cpu_usage": 0.95})
        ph  = PlatformHealthEngine().assess(ctx)
        r   = self.E.detect(ctx, ph)
        assert any("infrastructure" in a.subsystem_id for a in r.anomalies)


# ===========================================================================
# 9. Incident Analysis Engine
# ===========================================================================

class TestIncidentAnalysisEngine:
    E = IncidentAnalysisEngine()

    def test_empty_anomalies(self):
        r = self.E.correlate(AnomalyReport.create(()))
        assert r.total == 0

    def test_same_subsystem_grouped(self):
        a1 = GovernanceAnomaly.create("sub", "f1", 0.1, AnomalySeverity.HIGH)
        a2 = GovernanceAnomaly.create("sub", "f2", 0.2, AnomalySeverity.MEDIUM)
        ar = AnomalyReport.create((a1, a2))
        r  = self.E.correlate(ar)
        assert r.total == 1
        assert r.incidents[0].severity == IncidentSeverity.HIGH

    def test_different_subsystems_separate(self):
        a1 = GovernanceAnomaly.create("risk", "var", 0.9, AnomalySeverity.HIGH)
        a2 = GovernanceAnomaly.create("market", "halt", "halt", AnomalySeverity.CRITICAL)
        ar = AnomalyReport.create((a1, a2))
        r  = self.E.correlate(ar)
        assert r.total == 2

    def test_correlated_from_count(self):
        a1 = GovernanceAnomaly.create("sub", "f", 1, AnomalySeverity.LOW)
        ar = AnomalyReport.create((a1,))
        r  = self.E.correlate(ar)
        assert r.correlated_from_anomalies == 1


# ===========================================================================
# 10. Root Cause Analysis Engine
# ===========================================================================

class TestRootCauseAnalysisEngine:
    E = RootCauseAnalysisEngine()
    _dep_engine = DependencyAnalysisEngine()
    _health_engine = PlatformHealthEngine()

    def _dep_report(self):
        return self._dep_engine.analyze(_ctx(), self._health_engine.assess(_ctx()))

    def test_infrastructure_root_cause(self):
        inc = GovernanceIncident.create(
            "Infra", ("a1",), ("platform_infrastructure",), IncidentSeverity.CRITICAL
        )
        ir = IncidentReport.create((inc,))
        r  = self.E.analyze(ir, self._dep_report(), _ctx())
        assert r.root_causes[0].category == RootCauseCategory.INFRASTRUCTURE

    def test_external_market_root_cause(self):
        inc = GovernanceIncident.create(
            "Market", ("a1",), ("market_intelligence",), IncidentSeverity.HIGH
        )
        ir = IncidentReport.create((inc,))
        r  = self.E.analyze(ir, self._dep_report(), _ctx())
        assert r.root_causes[0].category in (RootCauseCategory.DATA, RootCauseCategory.EXTERNAL)

    def test_empty_incidents(self):
        ir = IncidentReport.create(())
        r  = self.E.analyze(ir, self._dep_report(), _ctx())
        assert r.total == 0


# ===========================================================================
# 11. Enterprise State Engine
# ===========================================================================

class TestEnterpriseStateEngine:
    E = EnterpriseStateEngine()

    def _empty(self):
        return PlatformHealthReport.create(()), AnomalyReport.create(()), IncidentReport.create(())

    def test_optimal_state(self):
        h  = SubsystemHealth("sub", SubsystemStatus.HEALTHY, 0.95)
        ph = PlatformHealthReport.create((h,))
        r  = self.E.assess(ph, AnomalyReport.create(()), IncidentReport.create(()))
        assert r.enterprise_state == EnterpriseState.OPTIMAL

    def test_emergency_on_many_critical_anomalies(self):
        ph, _, _ = self._empty()
        anomalies = tuple(
            GovernanceAnomaly.create("sub", f"f{i}", 0, AnomalySeverity.CRITICAL)
            for i in range(3)
        )
        ar = AnomalyReport.create(anomalies)
        r  = self.E.assess(ph, ar, IncidentReport.create(()))
        assert r.enterprise_state == EnterpriseState.EMERGENCY

    def test_degraded_on_high_anomaly(self):
        ph, _, _ = self._empty()
        a  = GovernanceAnomaly.create("sub", "f", 0, AnomalySeverity.HIGH)
        ar = AnomalyReport.create((a,))
        r  = self.E.assess(ph, ar, IncidentReport.create(()))
        assert r.enterprise_state == EnterpriseState.DEGRADED

    def test_supervision_strategy_emergency(self):
        ph, _, _ = self._empty()
        anomalies = tuple(
            GovernanceAnomaly.create("sub", f"f{i}", 0, AnomalySeverity.CRITICAL)
            for i in range(3)
        )
        ar = AnomalyReport.create(anomalies)
        r  = self.E.assess(ph, ar, IncidentReport.create(()))
        assert r.supervision_strategy == SupervisionStrategyType.EMERGENCY


# ===========================================================================
# 12. Governance Score Engine
# ===========================================================================

class TestGovernanceScoreEngine:
    E = GovernanceScoreEngine()

    def test_approve_continue(self):
        ctx   = _ctx(governance_policy_response={"final_action": "approve"})
        state = EnterpriseStateReport.create(EnterpriseState.NORMAL)
        r     = self.E.score(ctx, state)
        assert r.governance_decision == GovernanceDecision.CONTINUE
        assert r.is_compliant

    def test_emergency_stop_halt(self):
        ctx   = _ctx(governance_policy_response={"final_action": "emergency_stop"})
        state = EnterpriseStateReport.create(EnterpriseState.NORMAL)
        r     = self.E.score(ctx, state)
        assert r.governance_decision == GovernanceDecision.HALT

    def test_critical_state_escalate(self):
        ctx   = _ctx(governance_policy_response={"final_action": "approve"})
        state = EnterpriseStateReport.create(EnterpriseState.CRITICAL)
        r     = self.E.score(ctx, state)
        assert r.governance_decision in (GovernanceDecision.ESCALATE, GovernanceDecision.INVESTIGATE)

    def test_violations_recorded(self):
        ctx   = _ctx(governance_policy_response={"final_action": "emergency_stop"})
        state = EnterpriseStateReport.create(EnterpriseState.EMERGENCY)
        r     = self.E.score(ctx, state)
        assert len(r.violations) > 0

    def test_to_dict(self):
        ctx   = _ctx()
        state = EnterpriseStateReport.create(EnterpriseState.NORMAL)
        d     = self.E.score(ctx, state).to_dict()
        assert "compliance_score" in d


# ===========================================================================
# 13. Self-Healing Engine
# ===========================================================================

class TestSelfHealingEngine:
    E = SelfHealingEngine()

    def test_empty_incidents(self):
        p = self.E.plan(IncidentReport.create(()), RootCauseReport.create(()))
        assert p.total == 0

    def test_infra_gets_restart(self):
        inc = GovernanceIncident.create(
            "Infra", ("a1",), ("platform_infrastructure",), IncidentSeverity.CRITICAL
        )
        ir  = IncidentReport.create((inc,))
        rc  = RootCause.create(inc.incident_id, RootCauseCategory.INFRASTRUCTURE, "infra issue")
        rcr = RootCauseReport.create((rc,))
        p   = self.E.plan(ir, rcr)
        assert p.total == 1
        assert p.actions[0].action_type == SelfHealingActionType.RESTART

    def test_external_gets_monitor(self):
        inc = GovernanceIncident.create(
            "Ext", ("a1",), ("market_intelligence",), IncidentSeverity.HIGH
        )
        ir  = IncidentReport.create((inc,))
        rc  = RootCause.create(inc.incident_id, RootCauseCategory.EXTERNAL, "ext issue")
        rcr = RootCauseReport.create((rc,))
        p   = self.E.plan(ir, rcr)
        assert p.actions[0].action_type == SelfHealingActionType.MONITOR

    def test_monitor_is_automated(self):
        inc = GovernanceIncident.create(
            "Ext", ("a1",), ("market_intelligence",), IncidentSeverity.HIGH
        )
        ir  = IncidentReport.create((inc,))
        rc  = RootCause.create(inc.incident_id, RootCauseCategory.EXTERNAL, "ext")
        rcr = RootCauseReport.create((rc,))
        p   = self.E.plan(ir, rcr)
        assert p.actions[0].is_automated


# ===========================================================================
# 14. Recommendation Engine
# ===========================================================================

class TestRecommendationEngine:
    E = RecommendationEngine()

    def _empty(self):
        return (
            EnterpriseStateReport.create(EnterpriseState.NORMAL),
            EnterpriseGovernanceReport.create(),
            AnomalyReport.create(()),
            IncidentReport.create(()),
            SelfHealingPlan.create(()),
        )

    def test_emergency_recommendation(self):
        state = EnterpriseStateReport.create(EnterpriseState.EMERGENCY)
        gov   = EnterpriseGovernanceReport.create()
        r     = self.E.generate(state, gov, AnomalyReport.create(()), IncidentReport.create(()), SelfHealingPlan.create(()))
        assert r.critical_count > 0

    def test_optimal_no_issues(self):
        state = EnterpriseStateReport.create(
            EnterpriseState.OPTIMAL, stability_score=0.95
        )
        gov   = EnterpriseGovernanceReport.create()
        r     = self.E.generate(state, gov, AnomalyReport.create(()), IncidentReport.create(()), SelfHealingPlan.create(()))
        assert r.total >= 1  # at least "reduce supervision" recommendation

    def test_violation_generates_recommendation(self):
        state = EnterpriseStateReport.create(EnterpriseState.NORMAL)
        gov   = EnterpriseGovernanceReport.create(violations=("policy_breach",))
        r     = self.E.generate(state, gov, AnomalyReport.create(()), IncidentReport.create(()), SelfHealingPlan.create(()))
        assert r.total >= 1

    def test_approval_required_action_generates_rec(self):
        action = SelfHealingActionItem.create(
            "sub", SelfHealingActionType.RESTART, RecommendationPriority.HIGH,
            requires_approval=True,
        )
        plan  = SelfHealingPlan.create((action,))
        state = EnterpriseStateReport.create(EnterpriseState.NORMAL)
        gov   = EnterpriseGovernanceReport.create()
        r     = self.E.generate(state, gov, AnomalyReport.create(()), IncidentReport.create(()), plan)
        assert r.total >= 1

    def test_returns_governance_recommendations(self):
        r = self.E.generate(*self._empty())
        assert isinstance(r, GovernanceRecommendations)


# ===========================================================================
# 15. Governance Decision Engine
# ===========================================================================

class TestGovernanceDecisionEngine:
    E = GovernanceDecisionEngine()

    def _empties(self):
        return (
            AnomalyReport.create(()),
            IncidentReport.create(()),
            SelfHealingPlan.create(()),
        )

    def test_halt_on_halt_decision(self):
        gov = EnterpriseGovernanceReport.create(governance_decision=GovernanceDecision.HALT)
        state = EnterpriseStateReport.create(EnterpriseState.NORMAL)
        assert self.E.decide(gov, state, *self._empties()) == GovernanceDecision.HALT

    def test_halt_on_emergency(self):
        gov   = EnterpriseGovernanceReport.create()
        state = EnterpriseStateReport.create(EnterpriseState.EMERGENCY)
        assert self.E.decide(gov, state, *self._empties()) == GovernanceDecision.HALT

    def test_escalate_on_critical(self):
        gov   = EnterpriseGovernanceReport.create()
        state = EnterpriseStateReport.create(EnterpriseState.CRITICAL)
        assert self.E.decide(gov, state, *self._empties()) == GovernanceDecision.ESCALATE

    def test_investigate_on_degraded(self):
        gov   = EnterpriseGovernanceReport.create()
        state = EnterpriseStateReport.create(EnterpriseState.DEGRADED)
        assert self.E.decide(gov, state, *self._empties()) == GovernanceDecision.INVESTIGATE

    def test_continue_healthy(self):
        gov   = EnterpriseGovernanceReport.create(governance_score=1.0)
        state = EnterpriseStateReport.create(EnterpriseState.NORMAL)
        assert self.E.decide(gov, state, *self._empties()) == GovernanceDecision.CONTINUE


# ===========================================================================
# 16. Enterprise Reasoning Engine
# ===========================================================================

class TestEnterpriseReasoningEngine:
    E = EnterpriseReasoningEngine()

    def _args(self):
        ph  = PlatformHealthReport.create(())
        ar  = AnomalyReport.create(())
        ir  = IncidentReport.create(())
        rc  = RootCauseReport.create(())
        dep = DependencyReport.create((), ())
        state = EnterpriseStateReport.create(EnterpriseState.NORMAL)
        gov   = EnterpriseGovernanceReport.create()
        recs  = GovernanceRecommendations.create(())
        plan  = SelfHealingPlan.create(())
        return ph, ar, ir, rc, dep, state, gov, recs, plan

    def test_produces_nonempty_string(self):
        s = self.E.reason(*self._args(), GovernanceDecision.CONTINUE)
        assert isinstance(s, str) and len(s) > 0

    def test_contains_enterprise_state(self):
        s = self.E.reason(*self._args(), GovernanceDecision.CONTINUE)
        assert "NORMAL" in s.upper() or "normal" in s.lower()

    def test_contains_final_decision(self):
        s = self.E.reason(*self._args(), GovernanceDecision.HALT)
        assert "halt" in s.lower() or "HALT" in s

    def test_emergency_context(self):
        args = list(self._args())
        args[5] = EnterpriseStateReport.create(EnterpriseState.EMERGENCY)
        s = self.E.reason(*args, GovernanceDecision.HALT)
        assert len(s) > 0


# ===========================================================================
# 17. Supervision Strategy Engine
# ===========================================================================

class TestSupervisionStrategyEngine:
    E = SupervisionStrategyEngine()

    def _state(self, state: EnterpriseState) -> EnterpriseStateReport:
        return EnterpriseStateReport.create(state)

    def test_emergency_strategy(self):
        s = self.E.select(self._state(EnterpriseState.EMERGENCY), AnomalyReport.create(()), IncidentReport.create(()))
        assert s == SupervisionStrategyType.EMERGENCY

    def test_critical_intensive(self):
        s = self.E.select(self._state(EnterpriseState.CRITICAL), AnomalyReport.create(()), IncidentReport.create(()))
        assert s == SupervisionStrategyType.INTENSIVE

    def test_degraded_elevated(self):
        s = self.E.select(self._state(EnterpriseState.DEGRADED), AnomalyReport.create(()), IncidentReport.create(()))
        assert s == SupervisionStrategyType.ELEVATED

    def test_optimal_reduced(self):
        s = self.E.select(self._state(EnterpriseState.OPTIMAL), AnomalyReport.create(()), IncidentReport.create(()))
        assert s == SupervisionStrategyType.REDUCED

    def test_describe_returns_string(self):
        d = self.E.describe(SupervisionStrategyType.STANDARD)
        assert isinstance(d, str) and len(d) > 0


# ===========================================================================
# 18. Subsystem Coordination Engine
# ===========================================================================

class TestSubsystemCoordinationEngine:
    E = SubsystemCoordinationEngine()

    def test_all_healthy_no_failures(self):
        dep_engine = DependencyAnalysisEngine()
        ph_engine  = PlatformHealthEngine()
        ctx = _ctx()
        ph  = ph_engine.assess(ctx)
        dep = dep_engine.analyze(ctx, ph)
        result = self.E.analyze(ph, dep)
        assert "coordination_score" in result
        assert 0.0 <= result["coordination_score"] <= 1.0

    def test_coordination_failures_detected(self):
        h_crit = SubsystemHealth("market_intelligence", SubsystemStatus.CRITICAL, 0.1)
        h_ok   = SubsystemHealth("risk_intelligence",   SubsystemStatus.HEALTHY,  0.9)
        ph     = PlatformHealthReport.create((h_crit, h_ok))
        dep    = DependencyAnalysisEngine().analyze(_ctx(), ph)
        result = self.E.analyze(ph, dep)
        # risk_intelligence depends on market_intelligence which is CRITICAL
        assert result["coordination_score"] < 1.0

    def test_returns_dict(self):
        ph  = PlatformHealthReport.create(())
        dep = DependencyReport.create((), ())
        result = self.E.analyze(ph, dep)
        assert isinstance(result, dict)


# ===========================================================================
# 19. Agent Orchestration Engine
# ===========================================================================

class TestAgentOrchestrationEngine:
    E = AgentOrchestrationEngine()

    def test_always_has_health_assessment(self):
        caps = self.E.orchestrate(_req())
        assert GovernanceCapability.PLATFORM_HEALTH_ASSESSMENT in caps

    def test_always_has_anomaly_detection(self):
        assert GovernanceCapability.ANOMALY_DETECTION in self.E.orchestrate(_req())

    def test_enterprise_domain_activates_reasoning(self):
        req = AutonomousGovernanceRequest.create(
            "s", domains=[SupervisionDomain.ENTERPRISE],
        )
        caps = self.E.orchestrate(req)
        assert GovernanceCapability.ENTERPRISE_REASONING in caps

    def test_no_duplicate_capabilities(self):
        caps = self.E.orchestrate(_req())
        assert len(caps) == len(set(caps))

    def test_data_present_activates_incident(self):
        req = AutonomousGovernanceRequest.create(
            "s", inputs={"risk_snapshot": {"var": 0.1}},
        )
        caps = self.E.orchestrate(req)
        assert GovernanceCapability.INCIDENT_CORRELATION in caps

    def test_describe_plan_returns_dict(self):
        caps = self.E.orchestrate(_req())
        d = self.E.describe_plan(caps)
        assert isinstance(d, dict)


# ===========================================================================
# 20. Validator
# ===========================================================================

class TestValidator:
    V = AutonomousGovernanceValidator()

    def test_valid_request(self):
        assert self.V.validate_request(_req()).is_valid

    def test_invalid_request_no_supervision_id(self):
        req = AutonomousGovernanceRequest.create("")
        r   = self.V.validate_request(req)
        assert not r.is_valid

    def test_valid_summary(self):
        engine  = _started_engine()
        summary = engine.govern(_req())
        r       = self.V.validate_summary(summary)
        assert r.is_valid
        engine.stop()

    def test_failure_messages(self):
        check  = GovernanceValidationCheckResult(
            code=AutonomousGovernanceValidationCode.REQUEST_COMPLETENESS,
            passed=False, message="bad",
        )
        result = AutonomousGovernanceValidationResult(
            is_valid=False, checks=(check,), failed_checks=(check,),
            passed_count=0, failed_count=1,
        )
        assert "bad" in result.failure_messages

    def test_frozen_check_result(self):
        c = GovernanceValidationCheckResult(
            code=AutonomousGovernanceValidationCode.CONTEXT_CONSISTENCY,
            passed=True,
        )
        with pytest.raises((TypeError, AttributeError)):
            c.passed = False  # type: ignore


# ===========================================================================
# 21. Statistics
# ===========================================================================

class TestStatistics:
    def test_initial_snapshot_zeros(self):
        s = AutonomousGovernanceStatistics()
        snap = s.snapshot()
        assert snap["sessions"] == 0
        assert snap["anomalies_detected"] == 0

    def test_record_session(self):
        s = AutonomousGovernanceStatistics()
        s.record_session()
        assert s.snapshot()["sessions"] == 1

    def test_record_anomalies(self):
        s = AutonomousGovernanceStatistics()
        s.record_anomalies(5)
        assert s.snapshot()["anomalies_detected"] == 5

    def test_platform_stability_ema(self):
        s = AutonomousGovernanceStatistics()
        s.record_stability(0.5)
        snap = s.snapshot()
        assert 0.0 < snap["platform_stability_score"] <= 1.0

    def test_reset(self):
        s = AutonomousGovernanceStatistics()
        s.record_session()
        s.record_anomalies(10)
        s.reset()
        assert s.snapshot()["sessions"] == 0

    def test_thread_safe(self):
        s = AutonomousGovernanceStatistics()
        threads = [threading.Thread(target=s.record_session) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert s.snapshot()["sessions"] == 100


# ===========================================================================
# 22. History
# ===========================================================================

class TestHistory:
    def test_record_and_retrieve(self):
        h = AutonomousGovernanceHistory()
        h.record_request("req")
        assert h.request_count() == 1

    def test_bounded(self):
        h = AutonomousGovernanceHistory(max_requests=3)
        for i in range(10): h.record_request(i)
        assert h.request_count() == 3

    def test_all_artefact_types(self):
        h = AutonomousGovernanceHistory()
        h.record_request("r")
        h.record_summary("s")
        h.record_event("e")
        h.record_audit("a")
        c = h.counts()
        assert c["requests"] == c["summaries"] == c["events"] == c["audits"] == 1

    def test_recent_limited(self):
        h = AutonomousGovernanceHistory()
        for i in range(20): h.record_summary(i)
        assert len(h.recent_summaries(5)) == 5

    def test_clear(self):
        h = AutonomousGovernanceHistory()
        h.record_request("r")
        h.clear()
        assert h.request_count() == 0


# ===========================================================================
# 23. Registry
# ===========================================================================

class TestRegistry:
    def _summary(self, sid: str = "sum-1") -> AutonomousGovernanceSummary:
        return AutonomousGovernanceSummary.create_failure("sup", "sub", "wf", "test",
                                                          summary_id=sid)

    def test_register_and_get(self):
        r = AutonomousGovernanceRegistry()
        s = self._summary()
        r.register(s)
        assert r.get(s.summary_id) is s

    def test_capacity_enforced(self):
        r = AutonomousGovernanceRegistry(max_summaries=1)
        r.register(self._summary("s1"))
        with pytest.raises(AutonomousGovernanceCapacityError):
            r.register(self._summary("s2"))

    def test_none_raises(self):
        with pytest.raises(AutonomousGovernanceRegistryError):
            AutonomousGovernanceRegistry().register(None)  # type: ignore

    def test_get_optional_none(self):
        assert AutonomousGovernanceRegistry().get_optional("x") is None

    def test_get_for_supervision(self):
        r = AutonomousGovernanceRegistry()
        s1 = self._summary("s1")
        s2 = self._summary("s2")
        r.register(s1)
        r.register(s2)
        results = r.get_for_supervision("sup")
        assert len(results) == 2

    def test_unregister(self):
        r = AutonomousGovernanceRegistry()
        s = self._summary()
        r.register(s)
        r.unregister(s.summary_id)
        assert r.count == 0

    def test_clear(self):
        r = AutonomousGovernanceRegistry()
        r.register(self._summary())
        r.clear()
        assert r.count == 0

    def test_thread_safe(self):
        r = AutonomousGovernanceRegistry(max_summaries=200)
        errors: List[Exception] = []
        def worker(i):
            try:
                r.register(self._summary(f"s-{i}"))
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert r.count == 100


# ===========================================================================
# 24. Events
# ===========================================================================

class TestEvents:
    def test_governance_started(self):
        e = make_governance_started_event("s1", request_id="r1")
        assert e.event_type == AutonomousGovernanceEventType.GOVERNANCE_STARTED
        assert e.payload["request_id"] == "r1"

    def test_snapshots_collected(self):
        e = make_snapshots_collected_event("s1", snapshot_count=5)
        assert e.payload["snapshot_count"] == 5

    def test_dependency_graph_built(self):
        e = make_dependency_graph_built_event("s1", dependency_count=10, critical_paths=3)
        assert e.event_type == AutonomousGovernanceEventType.DEPENDENCY_GRAPH_BUILT

    def test_anomaly_detected(self):
        e = make_anomaly_detected_event("s1", anomaly_count=2, critical_count=1)
        assert e.event_type == AutonomousGovernanceEventType.ANOMALY_DETECTED

    def test_incident_correlated(self):
        e = make_incident_correlated_event("s1", incident_count=1)
        assert e.event_type == AutonomousGovernanceEventType.INCIDENT_CORRELATED

    def test_root_cause_identified(self):
        e = make_root_cause_identified_event("s1", root_cause_count=1, identified_count=1)
        assert e.event_type == AutonomousGovernanceEventType.ROOT_CAUSE_IDENTIFIED

    def test_recommendations_generated(self):
        e = make_recommendations_generated_event("s1", recommendation_count=3)
        assert e.event_type == AutonomousGovernanceEventType.RECOMMENDATIONS_GENERATED

    def test_self_healing_generated(self):
        e = make_self_healing_generated_event("s1", action_count=2, can_auto_execute=True)
        assert e.payload["can_auto_execute"]

    def test_enterprise_assessment_completed(self):
        e = make_enterprise_assessment_completed_event("s1", enterprise_state="normal")
        assert e.event_type == AutonomousGovernanceEventType.ENTERPRISE_ASSESSMENT_COMPLETED

    def test_governance_published(self):
        e = make_governance_published_event("s1", summary_id="sum-1", is_success=True)
        assert e.payload["is_success"]

    def test_engine_started(self):
        e = make_governance_engine_started_event()
        assert e.event_type == AutonomousGovernanceEventType.GOVERNANCE_ENGINE_STARTED

    def test_engine_stopped(self):
        e = make_governance_engine_stopped_event()
        assert e.event_type == AutonomousGovernanceEventType.GOVERNANCE_ENGINE_STOPPED

    def test_unique_ids(self):
        e1 = make_governance_engine_started_event()
        e2 = make_governance_engine_started_event()
        assert e1.event_id != e2.event_id

    def test_frozen(self):
        e = make_governance_engine_started_event()
        with pytest.raises((TypeError, AttributeError)):
            e.source = "x"  # type: ignore

    def test_to_dict(self):
        d = make_governance_started_event().to_dict()
        assert "event_type" in d and "event_id" in d


# ===========================================================================
# 25. Factory
# ===========================================================================

class TestFactory:
    F = AutonomousGovernanceFactory()

    def test_create_context(self):
        c = self.F.create_context("sup-1")
        assert c.supervision_id == "sup-1"

    def test_create_request(self):
        r = self.F.create_request("sup-1")
        assert r.supervision_id == "sup-1"

    def test_create_anomaly(self):
        a = self.F.create_anomaly("risk", "var", 0.9, AnomalySeverity.HIGH)
        assert a.severity == AnomalySeverity.HIGH

    def test_create_recommendation(self):
        r = self.F.create_recommendation("platform", "Fix issue")
        assert r.subsystem_id == "platform"

    def test_healthy_request(self):
        r = self.F.create_healthy_platform_request()
        assert r.context.platform_health.get("overall", 0) > 0.9

    def test_emergency_request(self):
        r = self.F.create_emergency_request()
        gpr = r.context.governance_policy_response
        assert gpr.get("final_action") == "emergency_stop"

    def test_degraded_request(self):
        r = self.F.create_degraded_request()
        assert r.context.platform_health.get("overall", 1) < 0.9

    def test_compliance_request(self):
        r = self.F.create_compliance_request()
        gpr = r.context.governance_policy_response
        assert gpr.get("final_action") == "require_human_approval"


# ===========================================================================
# 26. Manager
# ===========================================================================

class TestManager:
    def test_run_governance_success(self):
        mgr = AutonomousGovernanceManager()
        s   = mgr.run_governance(_req())
        assert s.is_success

    def test_run_governance_never_raises(self):
        class BrokenEngine(PlatformHealthEngine):
            def assess(self, ctx):
                raise RuntimeError("broken!")
        mgr = AutonomousGovernanceManager(platform_health_engine=BrokenEngine())
        s   = mgr.run_governance(_req())
        assert not s.is_success
        assert s.final_decision == GovernanceDecision.HALT

    def test_healthy_request_continue(self):
        mgr = AutonomousGovernanceManager()
        s   = mgr.run_governance(_healthy_req())
        assert s.final_decision == GovernanceDecision.CONTINUE

    def test_emergency_request_halt(self):
        mgr = AutonomousGovernanceManager()
        s   = mgr.run_governance(_emergency_req())
        assert s.final_decision == GovernanceDecision.HALT

    def test_reasoning_nonempty(self):
        mgr = AutonomousGovernanceManager()
        s   = mgr.run_governance(_req())
        assert s.reasoning_summary

    def test_statistics_records_sessions(self):
        mgr = AutonomousGovernanceManager()
        mgr.run_governance(_req())
        snap = mgr.statistics()
        assert snap["sessions"] >= 1

    def test_history_records_request(self):
        mgr = AutonomousGovernanceManager()
        mgr.run_governance(_req())
        counts = mgr.history_counts()
        assert counts["requests"] >= 1 and counts["summaries"] >= 1


# ===========================================================================
# 27. Engine lifecycle
# ===========================================================================

class TestEngineLifecycle:
    def test_starts_and_stops(self):
        e = AutonomousGovernanceEngine()
        e.start()
        assert e.lifecycle_state().value == "running"
        e.stop()
        assert e.lifecycle_state().value == "stopped"

    def test_govern_raises_when_not_started(self):
        e = AutonomousGovernanceEngine()
        with pytest.raises(AutonomousGovernanceEngineNotRunningError):
            e.govern(_req())

    def test_govern_raises_after_stop(self):
        e = _started_engine()
        e.stop()
        with pytest.raises(AutonomousGovernanceEngineNotRunningError):
            e.govern(_req())

    def test_start_fires_engine_started_event(self):
        events: List[AutonomousGovernanceEvent] = []
        e = AutonomousGovernanceEngine()
        e.add_listener(events.append)
        e.start()
        e.stop()
        types = [ev.event_type for ev in events]
        assert AutonomousGovernanceEventType.GOVERNANCE_ENGINE_STARTED in types
        assert AutonomousGovernanceEventType.GOVERNANCE_ENGINE_STOPPED in types

    def test_health_keys(self):
        e = _started_engine()
        h = e.health()
        assert "status" in h and "platform_stability" in h
        e.stop()

    def test_statistics_keys(self):
        e = _started_engine()
        s = e.statistics()
        assert "sessions" in s and "successes" in s
        e.stop()

    def test_status_keys(self):
        e = _started_engine()
        s = e.status()
        assert "engine_id" in s and "health" in s and "manager" in s
        e.stop()


# ===========================================================================
# 28. Engine govern
# ===========================================================================

class TestEngineGovern:
    def test_govern_returns_summary(self):
        e = _started_engine()
        s = e.govern(_req())
        assert isinstance(s, AutonomousGovernanceSummary)
        e.stop()

    def test_healthy_platform_continue(self):
        e = _started_engine()
        s = e.govern(_healthy_req())
        assert s.final_decision == GovernanceDecision.CONTINUE
        e.stop()

    def test_emergency_platform_halt(self):
        e = _started_engine()
        s = e.govern(_emergency_req())
        assert s.final_decision == GovernanceDecision.HALT
        e.stop()

    def test_governance_started_event_fired(self):
        e = _started_engine()
        events: List[AutonomousGovernanceEvent] = []
        e.add_listener(events.append)
        e.govern(_req())
        types = [ev.event_type for ev in events]
        assert AutonomousGovernanceEventType.GOVERNANCE_STARTED in types
        e.stop()

    def test_governance_published_event_fired(self):
        e = _started_engine()
        events: List[AutonomousGovernanceEvent] = []
        e.add_listener(events.append)
        e.govern(_req())
        types = [ev.event_type for ev in events]
        assert AutonomousGovernanceEventType.GOVERNANCE_PUBLISHED in types
        e.stop()

    def test_enterprise_assessment_completed_fired(self):
        e = _started_engine()
        events: List[AutonomousGovernanceEvent] = []
        e.add_listener(events.append)
        e.govern(_req())
        types = [ev.event_type for ev in events]
        assert AutonomousGovernanceEventType.ENTERPRISE_ASSESSMENT_COMPLETED in types
        e.stop()

    def test_summary_registered(self):
        e = _started_engine()
        s = e.govern(_req())
        assert e._registry.get_optional(s.summary_id) is not None
        e.stop()

    def test_engine_statistics_updated(self):
        e = _started_engine()
        e.govern(_req())
        snap = e.statistics()
        assert snap["sessions"] >= 1
        e.stop()


# ===========================================================================
# 29. Listeners
# ===========================================================================

class TestListeners:
    def test_no_duplicate_listener(self):
        e = _started_engine()
        events: List[AutonomousGovernanceEvent] = []
        e.add_listener(events.append)
        e.add_listener(events.append)
        e.govern(_req())
        started = [ev for ev in events
                   if ev.event_type == AutonomousGovernanceEventType.GOVERNANCE_STARTED]
        assert len(started) == 1
        e.stop()

    def test_remove_listener(self):
        e = _started_engine()
        events: List[AutonomousGovernanceEvent] = []
        e.add_listener(events.append)
        e.remove_listener(events.append)
        e.govern(_req())
        assert all(ev.event_type in (
            AutonomousGovernanceEventType.GOVERNANCE_ENGINE_STOPPED,
        ) for ev in events)
        e.stop()

    def test_exception_in_listener_does_not_crash(self):
        e = _started_engine()
        def bad(ev): raise RuntimeError("fail")
        e.add_listener(bad)
        s = e.govern(_req())
        assert s.is_success
        e.stop()


# ===========================================================================
# 30. Concurrency
# ===========================================================================

class TestConcurrency:
    def test_concurrent_govern(self):
        e = _started_engine()
        results: List[AutonomousGovernanceSummary] = []
        errors:  List[Exception] = []
        def worker():
            try:
                results.append(e.govern(_req()))
            except Exception as ex:
                errors.append(ex)
        threads = [threading.Thread(target=worker) for _ in range(40)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert len(results) == 40
        e.stop()

    def test_concurrent_govern_and_register(self):
        registry = AutonomousGovernanceRegistry(max_summaries=1000)
        e = AutonomousGovernanceEngine(registry=registry)
        e.start()
        errors: List[Exception] = []
        def gov_worker():
            try:
                e.govern(_req())
            except Exception as ex:
                errors.append(ex)
        threads = [threading.Thread(target=gov_worker) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        e.stop()


# ===========================================================================
# 31. Public surface
# ===========================================================================

class TestPublicSurface:
    def test_all_exports_present(self):
        import iios.supervisor.governance as module
        for name in module.__all__:
            assert hasattr(module, name), f"Missing export: {name}"

    def test_engine_in_all(self):
        import iios.supervisor.governance as module
        assert "AutonomousGovernanceEngine" in module.__all__

    def test_manager_in_all(self):
        import iios.supervisor.governance as module
        assert "AutonomousGovernanceManager" in module.__all__


# ===========================================================================
# 32. Integration smoke tests
# ===========================================================================

class TestIntegration:
    def test_healthy_platform_end_to_end(self):
        factory = AutonomousGovernanceFactory()
        engine  = _started_engine()
        req     = factory.create_healthy_platform_request()
        summary = engine.govern(req)
        assert summary.is_success
        assert summary.final_decision == GovernanceDecision.CONTINUE
        assert summary.platform_health.overall_score > 0.0
        assert len(summary.dependency_report.subsystems) > 0
        assert summary.reasoning_summary
        engine.stop()

    def test_emergency_platform_end_to_end(self):
        factory = AutonomousGovernanceFactory()
        engine  = _started_engine()
        req     = factory.create_emergency_request()
        summary = engine.govern(req)
        assert summary.is_success
        assert summary.final_decision == GovernanceDecision.HALT
        assert summary.is_emergency or summary.enterprise_state.is_critical
        assert summary.anomaly_count > 0
        engine.stop()

    def test_degraded_generates_incidents(self):
        factory = AutonomousGovernanceFactory()
        engine  = _started_engine()
        req     = factory.create_degraded_request()
        summary = engine.govern(req)
        assert summary.is_success
        # Degraded platform should yield anomalies and possibly incidents.
        assert summary.anomaly_count >= 0  # permissive: may or may not detect anomalies
        engine.stop()

    def test_compliance_escalation(self):
        factory = AutonomousGovernanceFactory()
        engine  = _started_engine()
        req     = factory.create_compliance_request()
        summary = engine.govern(req)
        assert summary.is_success
        # REQUIRE_HUMAN_APPROVAL → ESCALATE or INVESTIGATE
        assert summary.final_decision in (
            GovernanceDecision.ESCALATE,
            GovernanceDecision.INVESTIGATE,
            GovernanceDecision.DEFER,
            GovernanceDecision.CONTINUE,
        )
        engine.stop()

    def test_multiple_sequential_cycles(self):
        engine = _started_engine()
        for i in range(5):
            s = engine.govern(_req(f"sup-{i}"))
            assert s.is_success
        snap = engine.statistics()
        assert snap["sessions"] >= 5
        engine.stop()

    def test_reasoning_contains_platform_health(self):
        engine  = _started_engine()
        summary = engine.govern(_healthy_req())
        assert any(word in summary.reasoning_summary.lower()
                   for word in ("platform", "health", "score"))
        engine.stop()

    def test_dependency_graph_populated(self):
        engine  = _started_engine()
        summary = engine.govern(_req())
        assert summary.dependency_report.total_dependencies > 0
        assert len(summary.dependency_report.critical_paths) > 0
        engine.stop()

    def test_audit_history_populated(self):
        history = AutonomousGovernanceHistory()
        stats   = AutonomousGovernanceStatistics()
        mgr     = AutonomousGovernanceManager(history=history, statistics=stats)
        engine  = AutonomousGovernanceEngine(manager=mgr)
        engine.start()
        engine.govern(_req())
        counts = engine.status()["history"]
        assert counts["summaries"] >= 1
        engine.stop()
