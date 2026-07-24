"""
test_supervisor_snapshot.py — tests.unit.supervisor.snapshot
--------------------------------------------------------------
Comprehensive tests for the C13 M5 AI Supervisor Snapshot.

95%+ coverage target.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

import pytest

from iios.supervisor.snapshot import (
    # --- constants ---
    SUPERVISOR_SNAPSHOT_SYSTEM_ID,
    VERSION,
    PLATFORM_VERSION,
    PLATFORM_DEPENDENCIES,
    DEFAULT_MAX_SNAPSHOTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_CACHE_TTL_S,
    HEALTH_OPTIMAL_THRESHOLD,
    HEALTH_NORMAL_THRESHOLD,
    HEALTH_DEGRADED_THRESHOLD,
    HEALTH_CRITICAL_THRESHOLD,
    # --- enumerations ---
    AutomationReadiness,
    GovernanceStatus,
    OperationalStatus,
    PlatformStatus,
    SnapshotEnterpriseState,
    SnapshotEventType,
    SnapshotGovernanceState,
    SnapshotLifecycleState,
    SnapshotStatus,
    SnapshotValidationCode,
    SubsystemSummaryStatus,
    SupervisorScope,
    SupervisorType,
    # --- exceptions ---
    SupervisorSnapshotBuildError,
    SupervisorSnapshotBundleError,
    SupervisorSnapshotCacheError,
    SupervisorSnapshotCapacityError,
    SupervisorSnapshotError,
    SupervisorSnapshotNotFoundError,
    SupervisorSnapshotRegistryError,
    SupervisorSnapshotStoreError,
    SupervisorSnapshotValidationError,
    # --- metadata ---
    SupervisorSnapshotMetadata,
    # --- sections ---
    AnomalySummary,
    AuditSummary,
    DependencySummary,
    EnterpriseSummary,
    GovernanceSummary,
    SelfHealingSummary,
    SnapshotStatistics,
    SubsystemSummaryItem,
    SubsystemsSummary,
    SupervisionSummary,
    # --- snapshot ---
    SupervisorSnapshot,
    # --- builder ---
    SupervisorSnapshotBuilder,
    # --- validation ---
    SnapshotValidationCheckResult,
    SupervisorSnapshotValidationResult,
    SupervisorSnapshotValidator,
    # --- factory ---
    SupervisorSnapshotFactory,
    # --- registry ---
    SupervisorSnapshotRegistry,
    # --- cache ---
    SupervisorSnapshotCache,
    # --- store ---
    SupervisorSnapshotStore,
    # --- history ---
    SupervisorSnapshotHistory,
    # --- statistics ---
    SupervisorSnapshotStatistics,
    # --- events ---
    SupervisorSnapshotEvent,
    make_bundle_created_event,
    make_snapshot_archived_event,
    make_snapshot_built_event,
    make_snapshot_cached_event,
    make_snapshot_expired_event,
    make_snapshot_invalidated_event,
    make_snapshot_published_event,
    make_snapshot_registered_event,
    make_snapshot_retrieved_event,
    make_snapshot_started_event,
    make_snapshot_validated_event,
    make_store_saved_event,
    # --- bundle ---
    SupervisorSnapshotBundle,
    SupervisorSnapshotBundleBuilder,
)


# ===========================================================================
# Shared helpers
# ===========================================================================

_F = SupervisorSnapshotFactory()
_V = SupervisorSnapshotValidator()


def _minimal(session_id: str = "sess-001") -> SupervisorSnapshot:
    return _F.create_minimal(session_id)


def _healthy(session_id: str = "") -> SupervisorSnapshot:
    return _F.create_healthy(session_id)


def _emergency(session_id: str = "") -> SupervisorSnapshot:
    return _F.create_emergency(session_id)


def _degraded(session_id: str = "") -> SupervisorSnapshot:
    return _F.create_degraded(session_id)


# ===========================================================================
# 1. Constants
# ===========================================================================

class TestConstants:
    def test_system_id_nonempty(self):
        assert SUPERVISOR_SNAPSHOT_SYSTEM_ID

    def test_version_nonempty(self):
        assert VERSION

    def test_platform_version(self):
        assert PLATFORM_VERSION

    def test_health_threshold_ordering(self):
        assert HEALTH_OPTIMAL_THRESHOLD > HEALTH_NORMAL_THRESHOLD
        assert HEALTH_NORMAL_THRESHOLD  > HEALTH_DEGRADED_THRESHOLD
        assert HEALTH_DEGRADED_THRESHOLD > HEALTH_CRITICAL_THRESHOLD

    def test_platform_dependencies_nonempty(self):
        assert len(PLATFORM_DEPENDENCIES) > 0

    def test_snapshot_status_count(self):
        assert len(SnapshotStatus) == 7

    def test_supervisor_scope_count(self):
        assert len(SupervisorScope) == 5

    def test_supervisor_type_count(self):
        assert len(SupervisorType) == 5

    def test_lifecycle_state_count(self):
        assert len(SnapshotLifecycleState) == 7

    def test_governance_state_count(self):
        assert len(SnapshotGovernanceState) == 6

    def test_enterprise_state_count(self):
        assert len(SnapshotEnterpriseState) == 6

    def test_event_type_count(self):
        assert len(SnapshotEventType) == 12

    def test_validation_code_count(self):
        assert len(SnapshotValidationCode) == 7

    def test_defaults_positive(self):
        assert DEFAULT_MAX_SNAPSHOTS > 0
        assert DEFAULT_MAX_HISTORY   > 0


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(SupervisorSnapshotError, IIOSError)

    def test_not_found_has_snapshot_id(self):
        e = SupervisorSnapshotNotFoundError("snap-1")
        assert e.snapshot_id == "snap-1"
        assert "snap-1" in str(e)

    def test_not_found_empty_id(self):
        e = SupervisorSnapshotNotFoundError()
        assert e.snapshot_id == ""

    def test_capacity_has_limit(self):
        e = SupervisorSnapshotCapacityError(500)
        assert e.limit == 500

    def test_build_error(self):
        assert issubclass(SupervisorSnapshotBuildError, SupervisorSnapshotError)

    def test_registry_error(self):
        assert issubclass(SupervisorSnapshotRegistryError, SupervisorSnapshotError)

    def test_store_error(self):
        assert issubclass(SupervisorSnapshotStoreError, SupervisorSnapshotError)

    def test_cache_error(self):
        assert issubclass(SupervisorSnapshotCacheError, SupervisorSnapshotError)

    def test_bundle_error(self):
        assert issubclass(SupervisorSnapshotBundleError, SupervisorSnapshotError)

    def test_validation_error(self):
        assert issubclass(SupervisorSnapshotValidationError, SupervisorSnapshotError)


# ===========================================================================
# 3. Metadata
# ===========================================================================

class TestMetadata:
    def test_create_defaults(self):
        m = SupervisorSnapshotMetadata.create()
        assert m.environment == "production"
        assert m.framework_version == VERSION
        assert len(m.source_components) > 0

    def test_create_custom(self):
        m = SupervisorSnapshotMetadata.create(
            environment="test",
            build_version="2.0.0",
            correlation_ids=("c-1", "c-2"),
        )
        assert m.environment == "test"
        assert "c-1" in m.correlation_ids

    def test_with_correlation_id(self):
        m  = SupervisorSnapshotMetadata.create()
        m2 = m.with_correlation_id("corr-999")
        assert "corr-999" in m2.correlation_ids
        assert len(m2.correlation_ids) == len(m.correlation_ids) + 1

    def test_with_trace_id(self):
        m  = SupervisorSnapshotMetadata.create()
        m2 = m.with_trace_id("trace-1")
        assert "trace-1" in m2.trace_ids

    def test_frozen(self):
        m = SupervisorSnapshotMetadata.create()
        with pytest.raises((TypeError, AttributeError)):
            m.environment = "other"  # type: ignore

    def test_to_dict(self):
        d = SupervisorSnapshotMetadata.create().to_dict()
        for key in ("metadata_id", "environment", "framework_version",
                    "schema_version", "source_components"):
            assert key in d


# ===========================================================================
# 4. EnterpriseSummary
# ===========================================================================

class TestEnterpriseSummary:
    def test_defaults(self):
        e = EnterpriseSummary()
        assert e.enterprise_health == 1.0
        assert e.platform_status   == PlatformStatus.UNKNOWN

    def test_create_clamps(self):
        e = EnterpriseSummary.create(enterprise_health=1.5)
        assert e.enterprise_health == 1.0
        e2 = EnterpriseSummary.create(enterprise_health=-0.1)
        assert e2.enterprise_health == 0.0

    def test_to_dict(self):
        d = EnterpriseSummary.create().to_dict()
        assert "enterprise_health" in d and "platform_status" in d

    def test_frozen(self):
        e = EnterpriseSummary.create()
        with pytest.raises((TypeError, AttributeError)):
            e.enterprise_health = 0.5  # type: ignore


# ===========================================================================
# 5. SubsystemSummaryItem
# ===========================================================================

class TestSubsystemSummaryItem:
    def test_create(self):
        s = SubsystemSummaryItem.create(
            "risk_intelligence",
            status      = SubsystemSummaryStatus.HEALTHY,
            health_score = 0.95,
        )
        assert s.subsystem_id == "risk_intelligence"
        assert s.status        == SubsystemSummaryStatus.HEALTHY

    def test_clamps_health(self):
        s = SubsystemSummaryItem.create("s", health_score=2.0)
        assert s.health_score == 1.0

    def test_to_dict(self):
        d = SubsystemSummaryItem.create("s").to_dict()
        assert "subsystem_id" in d and "status" in d

    def test_frozen(self):
        s = SubsystemSummaryItem.create("s")
        with pytest.raises((TypeError, AttributeError)):
            s.subsystem_id = "other"  # type: ignore


# ===========================================================================
# 6. SubsystemsSummary
# ===========================================================================

class TestSubsystemsSummary:
    def test_unknown_factory(self):
        ss = SubsystemsSummary.unknown()
        for item in ss.all_items():
            assert item.status == SubsystemSummaryStatus.UNKNOWN

    def test_all_items_count(self):
        assert len(SubsystemsSummary.unknown().all_items()) == 9

    def test_healthy_count(self):
        from iios.supervisor.snapshot.supervisor_snapshot_factory import _uniform_subsystems
        ss = _uniform_subsystems(SubsystemSummaryStatus.HEALTHY, 0.95)
        assert ss.healthy_count() == 9

    def test_critical_count(self):
        from iios.supervisor.snapshot.supervisor_snapshot_factory import _uniform_subsystems
        ss = _uniform_subsystems(SubsystemSummaryStatus.CRITICAL, 0.1)
        assert ss.critical_count() == 9

    def test_to_dict(self):
        d = SubsystemsSummary.unknown().to_dict()
        assert "execution_intelligence" in d and "risk_intelligence" in d


# ===========================================================================
# 7. GovernanceSummary
# ===========================================================================

class TestGovernanceSummary:
    def test_create(self):
        g = GovernanceSummary.create(governance_decision="continue")
        assert g.governance_decision == "continue"

    def test_has_violations(self):
        g = GovernanceSummary.create(policy_violations=("breach",))
        assert g.has_violations

    def test_no_violations(self):
        assert not GovernanceSummary.create().has_violations

    def test_requires_escalation(self):
        g = GovernanceSummary.create(escalations=1)
        assert g.requires_escalation

    def test_to_dict(self):
        d = GovernanceSummary.create(governance_decision="halt").to_dict()
        assert d["governance_decision"] == "halt"

    def test_frozen(self):
        g = GovernanceSummary.create()
        with pytest.raises((TypeError, AttributeError)):
            g.governance_decision = "x"  # type: ignore


# ===========================================================================
# 8. SupervisionSummary
# ===========================================================================

class TestSupervisionSummary:
    def test_create(self):
        s = SupervisionSummary.create(platform_health=0.9, active_alerts=2)
        assert s.platform_health == 0.9
        assert s.active_alerts   == 2

    def test_clamps_health(self):
        s = SupervisionSummary.create(platform_health=1.5)
        assert s.platform_health == 1.0

    def test_to_dict(self):
        d = SupervisionSummary.create().to_dict()
        assert "supervision_status" in d and "platform_health" in d


# ===========================================================================
# 9. AnomalySummary
# ===========================================================================

class TestAnomalySummary:
    def test_defaults(self):
        a = AnomalySummary.create()
        assert a.detected_anomalies    == 0
        assert a.incident_correlations == 0

    def test_with_data(self):
        a = AnomalySummary.create(
            detected_anomalies    = 3,
            severity_distribution = {"critical": 2, "high": 1},
            affected_subsystems   = ("risk", "market"),
            root_causes           = ("infrastructure",),
            incident_correlations = 2,
        )
        assert a.detected_anomalies == 3
        assert len(a.affected_subsystems) == 2

    def test_to_dict(self):
        d = AnomalySummary.create().to_dict()
        assert "detected_anomalies" in d


# ===========================================================================
# 10. SelfHealingSummary
# ===========================================================================

class TestSelfHealingSummary:
    def test_defaults(self):
        s = SelfHealingSummary.create()
        assert s.automation_readiness == AutomationReadiness.UNKNOWN

    def test_with_data(self):
        s = SelfHealingSummary.create(
            recommended_actions  = 5,
            automation_readiness = AutomationReadiness.READY,
        )
        assert s.recommended_actions == 5
        assert s.automation_readiness == AutomationReadiness.READY

    def test_to_dict(self):
        d = SelfHealingSummary.create().to_dict()
        assert "automation_readiness" in d


# ===========================================================================
# 11. DependencySummary
# ===========================================================================

class TestDependencySummary:
    def test_defaults(self):
        d = DependencySummary.create()
        assert d.critical_dependencies  == 0
        assert d.unavailable_components == ()

    def test_with_graph(self):
        graph = {"risk": ("market",)}
        d = DependencySummary.create(
            dependency_graph      = graph,
            critical_dependencies = 2,
        )
        assert d.critical_dependencies == 2
        assert "risk" in d.dependency_graph

    def test_to_dict(self):
        td = DependencySummary.create(
            dependency_graph={"a": ("b",)}
        ).to_dict()
        assert "dependency_graph" in td
        assert td["dependency_graph"]["a"] == ["b"]


# ===========================================================================
# 12. AuditSummary
# ===========================================================================

class TestAuditSummary:
    def test_defaults(self):
        a = AuditSummary.create()
        assert a.governance_version == VERSION

    def test_with_data(self):
        a = AuditSummary.create(
            validation_summary = "all passed",
            audit_trail        = ("entry1", "entry2"),
        )
        assert a.validation_summary == "all passed"
        assert len(a.audit_trail)   == 2

    def test_to_dict(self):
        d = AuditSummary.create().to_dict()
        assert "governance_version" in d and "audit_trail" in d


# ===========================================================================
# 13. SnapshotStatistics
# ===========================================================================

class TestSnapshotStatistics:
    def test_defaults(self):
        s = SnapshotStatistics.create()
        assert s.assessment_duration == 0.0
        assert s.component_count     == 0

    def test_create_clamps(self):
        s = SnapshotStatistics.create(assessment_duration=-1.0, snapshot_size=-5)
        assert s.assessment_duration == 0.0
        assert s.snapshot_size       == 0

    def test_to_dict(self):
        d = SnapshotStatistics.create(assessment_duration=0.5, component_count=9).to_dict()
        assert d["assessment_duration"] == 0.5
        assert d["component_count"]     == 9


# ===========================================================================
# 14. SupervisorSnapshot
# ===========================================================================

class TestSupervisorSnapshot:
    def test_is_valid_when_published(self):
        s = _healthy()
        assert s.is_valid and s.is_published

    def test_is_emergency(self):
        s = _emergency()
        assert s.is_emergency

    def test_is_critical(self):
        s = _emergency()
        assert s.is_critical

    def test_degraded_not_emergency(self):
        s = _degraded()
        assert not s.is_emergency

    def test_healthy_is_healthy(self):
        s = _healthy()
        assert s.is_healthy

    def test_anomaly_count_property(self):
        s = _healthy()
        assert s.anomaly_count == 0

    def test_governance_decision_property(self):
        s = _healthy()
        assert s.governance_decision == "continue"

    def test_to_dict_has_all_sections(self):
        d = _healthy().to_dict()
        for section in ("enterprise_summary", "subsystems_summary", "governance_summary",
                        "supervision_summary", "anomaly_summary", "self_healing_summary",
                        "dependency_summary", "audit_summary", "snapshot_statistics",
                        "metadata"):
            assert section in d

    def test_to_json(self):
        j = _healthy().to_json()
        assert isinstance(j, str) and len(j) > 100

    def test_estimated_size_bytes(self):
        assert _healthy().estimated_size_bytes() > 0

    def test_frozen(self):
        s = _healthy()
        with pytest.raises((TypeError, AttributeError)):
            s.snapshot_id = "other"  # type: ignore

    def test_is_valid_when_valid_status(self):
        snap = (
            SupervisorSnapshotBuilder("sess-x")
            .with_status(SnapshotStatus.VALID)
            .with_governance_summary(GovernanceSummary.create(governance_decision="continue"))
            .build()
        )
        assert snap.is_valid
        assert not snap.is_published

    def test_not_valid_when_invalid(self):
        snap = (
            SupervisorSnapshotBuilder("sess-x")
            .with_status(SnapshotStatus.INVALID)
            .with_governance_summary(GovernanceSummary.create(governance_decision="halt"))
            .build()
        )
        assert not snap.is_valid


# ===========================================================================
# 15. Builder
# ===========================================================================

class TestBuilder:
    def test_requires_session_id(self):
        with pytest.raises(SupervisorSnapshotBuildError):
            SupervisorSnapshotBuilder("")

    def test_builds_minimal(self):
        snap = SupervisorSnapshotBuilder("sess-1").build()
        assert snap.supervisor_session_id == "sess-1"

    def test_fluent_setters(self):
        snap = (
            SupervisorSnapshotBuilder("sess-2")
            .with_lifecycle_state(SnapshotLifecycleState.RUNNING)
            .with_governance_state(SnapshotGovernanceState.ACTIVE)
            .with_enterprise_state(SnapshotEnterpriseState.NORMAL)
            .with_status(SnapshotStatus.PUBLISHED)
            .with_supervisor_version("2.0.0")
            .build()
        )
        assert snap.lifecycle_state   == SnapshotLifecycleState.RUNNING
        assert snap.governance_state  == SnapshotGovernanceState.ACTIVE
        assert snap.enterprise_state  == SnapshotEnterpriseState.NORMAL
        assert snap.snapshot_status   == SnapshotStatus.PUBLISHED
        assert snap.supervisor_version == "2.0.0"

    def test_section_setters(self):
        meta  = SupervisorSnapshotMetadata.create(environment="ci")
        stats = SnapshotStatistics.create(assessment_duration=0.1, component_count=9)
        snap  = (
            SupervisorSnapshotBuilder("sess-3")
            .with_enterprise_summary(EnterpriseSummary.create(enterprise_health=0.9))
            .with_governance_summary(GovernanceSummary.create(governance_decision="continue"))
            .with_anomaly_summary(AnomalySummary.create(detected_anomalies=2))
            .with_audit_summary(AuditSummary.create(validation_summary="ok"))
            .with_statistics(stats)
            .with_metadata(meta)
            .build()
        )
        assert snap.enterprise_summary.enterprise_health == 0.9
        assert snap.anomaly_summary.detected_anomalies  == 2
        assert snap.metadata.environment                == "ci"

    def test_statistics_auto_fill(self):
        snap = SupervisorSnapshotBuilder("sess-4").build()
        assert snap.snapshot_statistics.assessment_duration > 0.0

    def test_custom_snapshot_id(self):
        snap = SupervisorSnapshotBuilder("sess-5", snapshot_id="snap-custom").build()
        assert snap.snapshot_id == "snap-custom"


# ===========================================================================
# 16. Validation
# ===========================================================================

class TestValidation:
    def test_healthy_snapshot_passes(self):
        r = _V.validate(_healthy())
        assert r.is_valid
        assert r.failed_count == 0
        assert r.passed_count == 7

    def test_invalid_empty_snapshot_id(self):
        # Build a snapshot then hack fields via object replacement
        snap = _healthy()
        # Can't mutate frozen, so test via builder with mock
        bad  = SupervisorSnapshotBuilder("sess-bad")
        bad._snapshot_id = ""
        bad_snap = bad.build()
        r = _V.validate(bad_snap)
        assert not r.is_valid
        assert any(c.code == SnapshotValidationCode.IDENTIFIER_CONSISTENCY
                   for c in r.failed_checks)

    def test_validation_result_failure_messages(self):
        bad = SupervisorSnapshotBuilder("sess-bad")
        bad._snapshot_id = ""
        r = _V.validate(bad.build())
        assert len(r.failure_messages) > 0

    def test_all_7_checks_run(self):
        r = _V.validate(_healthy())
        assert len(r.checks) == 7

    def test_check_result_frozen(self):
        c = SnapshotValidationCheckResult(
            code=SnapshotValidationCode.VERSION_CONSISTENCY, passed=True
        )
        with pytest.raises((TypeError, AttributeError)):
            c.passed = False  # type: ignore

    def test_invalid_governance_decision(self):
        snap = (
            SupervisorSnapshotBuilder("sess-gov")
            .with_governance_summary(GovernanceSummary.create(governance_decision=""))
            .build()
        )
        r = _V.validate(snap)
        assert not r.is_valid
        assert any(c.code == SnapshotValidationCode.GOVERNANCE_CONSISTENCY
                   for c in r.failed_checks)

    def test_emergency_snapshot_passes(self):
        r = _V.validate(_emergency())
        assert r.is_valid


# ===========================================================================
# 17. Factory
# ===========================================================================

class TestFactory:
    def test_create_minimal(self):
        s = _F.create_minimal("sess-1")
        assert s.supervisor_session_id == "sess-1"

    def test_create_minimal_auto_id(self):
        s = _F.create_minimal()
        assert s.supervisor_session_id

    def test_create_healthy(self):
        s = _F.create_healthy("sess-h")
        assert s.enterprise_state  == SnapshotEnterpriseState.OPTIMAL
        assert s.governance_decision == "continue"
        assert s.is_published

    def test_create_emergency(self):
        s = _F.create_emergency()
        assert s.is_emergency
        assert s.governance_decision == "halt"
        assert s.governance_summary.emergency_actions == 1

    def test_create_degraded(self):
        s = _F.create_degraded()
        assert s.enterprise_state == SnapshotEnterpriseState.DEGRADED

    def test_create_from_components(self):
        s = _F.create_from_components(
            "sess-comp", "wf-comp",
            enterprise_state    = SnapshotEnterpriseState.NORMAL,
            governance_decision = "continue",
            platform_health     = 0.85,
        )
        assert s.enterprise_state == SnapshotEnterpriseState.NORMAL
        assert s.enterprise_summary.enterprise_health == 0.85

    def test_create_from_components_degraded_status(self):
        s = _F.create_from_components(
            "sess-deg", platform_health=0.4
        )
        assert s.enterprise_summary.operational_status == OperationalStatus.DEGRADED

    def test_create_builder(self):
        b = _F.create_builder("sess-b", "wf-b")
        assert isinstance(b, SupervisorSnapshotBuilder)

    def test_create_from_governance_summary_healthy(self):
        # Use M4 factory to get a real summary, then convert
        from iios.supervisor.governance import AutonomousGovernanceFactory, AutonomousGovernanceEngine
        m4_factory = AutonomousGovernanceFactory()
        engine     = AutonomousGovernanceEngine()
        engine.start()
        req     = m4_factory.create_healthy_platform_request()
        summary = engine.govern(req)
        engine.stop()

        snap = _F.create_from_governance_summary("sess-gov", "wf-gov", summary)
        assert isinstance(snap, SupervisorSnapshot)
        assert snap.governance_decision in ("continue", "defer", "investigate", "escalate", "halt")

    def test_create_from_governance_summary_emergency(self):
        from iios.supervisor.governance import AutonomousGovernanceFactory, AutonomousGovernanceEngine
        m4_factory = AutonomousGovernanceFactory()
        engine     = AutonomousGovernanceEngine()
        engine.start()
        req     = m4_factory.create_emergency_request()
        summary = engine.govern(req)
        engine.stop()

        snap = _F.create_from_governance_summary("sess-emg", "wf-emg", summary)
        assert snap.governance_decision == "halt"

    def test_create_from_governance_summary_duck_typing(self):
        """Factory must work via duck-typing — no import of M4 types."""
        class FakeSummary:
            is_success       = True
            is_emergency     = False
            reasoning_summary = "ok"
            final_decision   = type("D", (), {"value": "continue"})()
            enterprise_state = type("E", (), {
                "enterprise_state": type("S", (), {"value": "normal"})()
            })()
            platform_health  = type("P", (), {"overall_score": 0.9})()
            anomaly_report   = type("A", (), {
                "total": 0, "critical_count": 0, "high_count": 0,
                "medium_count": 0, "anomalies": (),
            })()
            incident_report  = type("I", (), {"total": 0})()
            dependency_report = type("D2", (), {
                "total_dependencies": 5, "critical_dependencies": 2,
                "critical_paths": (),
            })()
            self_healing_plan = type("SH", (), {"total": 0, "can_auto_execute": True})()
            governance_report = type("G", (), {"is_compliant": True, "violations": ()})()
            root_cause_report = type("RC", (), {"root_causes": ()})()
            recommendations   = type("R", (), {"total": 0})()

        snap = _F.create_from_governance_summary("sess-duck", "wf-duck", FakeSummary())
        assert snap.governance_decision == "continue"
        assert snap.enterprise_state    == SnapshotEnterpriseState.NORMAL


# ===========================================================================
# 18. Registry
# ===========================================================================

class TestRegistry:
    def test_register_and_get(self):
        r = SupervisorSnapshotRegistry()
        s = _minimal()
        r.register(s)
        assert r.get(s.snapshot_id) is s

    def test_get_not_found(self):
        r = SupervisorSnapshotRegistry()
        with pytest.raises(SupervisorSnapshotNotFoundError):
            r.get("missing")

    def test_get_optional_none(self):
        assert SupervisorSnapshotRegistry().get_optional("x") is None

    def test_capacity_enforced(self):
        r = SupervisorSnapshotRegistry(max_snapshots=1)
        r.register(_minimal("s1"))
        with pytest.raises(SupervisorSnapshotCapacityError):
            r.register(_minimal("s2"))

    def test_register_none_raises(self):
        with pytest.raises(SupervisorSnapshotRegistryError):
            SupervisorSnapshotRegistry().register(None)  # type: ignore

    def test_unregister(self):
        r = SupervisorSnapshotRegistry()
        s = _minimal()
        r.register(s)
        r.unregister(s.snapshot_id)
        assert r.count == 0

    def test_unregister_missing_raises(self):
        with pytest.raises(SupervisorSnapshotRegistryError):
            SupervisorSnapshotRegistry().unregister("missing")

    def test_get_for_session(self):
        r  = SupervisorSnapshotRegistry()
        s1 = _minimal("sess-A")
        s2 = _minimal("sess-A")
        r.register(s1)
        r.register(s2)
        snaps = r.get_for_session("sess-A")
        assert len(snaps) == 2

    def test_latest_for_session(self):
        r  = SupervisorSnapshotRegistry()
        s1 = _minimal("sess-B")
        time.sleep(0.01)
        s2 = _minimal("sess-B")
        r.register(s1)
        r.register(s2)
        latest = r.latest_for_session("sess-B")
        assert latest is not None
        assert latest.snapshot_id == s2.snapshot_id

    def test_latest_for_session_empty(self):
        assert SupervisorSnapshotRegistry().latest_for_session("nobody") is None

    def test_all_snapshots(self):
        r = SupervisorSnapshotRegistry()
        r.register(_minimal("s-1"))
        r.register(_minimal("s-2"))
        assert len(r.all_snapshots()) == 2

    def test_published_count(self):
        r = SupervisorSnapshotRegistry()
        r.register(_healthy())
        r.register(_minimal())   # VALID not PUBLISHED
        assert r.published_count == 1

    def test_clear(self):
        r = SupervisorSnapshotRegistry()
        r.register(_minimal())
        r.clear()
        assert r.count == 0

    def test_thread_safe(self):
        r      = SupervisorSnapshotRegistry(max_snapshots=500)
        errors: List[Exception] = []
        def worker(i: int):
            try:
                r.register(_minimal(f"sess-thread-{i}"))
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert r.count == 100


# ===========================================================================
# 19. Cache
# ===========================================================================

class TestCache:
    def test_put_and_get(self):
        c = SupervisorSnapshotCache()
        s = _healthy()
        c.put(s.snapshot_id, s)
        assert c.get(s.snapshot_id) is s

    def test_miss_returns_none(self):
        assert SupervisorSnapshotCache().get("missing") is None

    def test_hit_rate(self):
        c = SupervisorSnapshotCache()
        s = _healthy()
        c.put(s.snapshot_id, s)
        c.get(s.snapshot_id)
        c.get("miss")
        assert c.hit_rate == pytest.approx(0.5)

    def test_ttl_expiry(self):
        c = SupervisorSnapshotCache(ttl_s=0.05)
        s = _healthy()
        c.put(s.snapshot_id, s)
        time.sleep(0.12)
        assert c.get(s.snapshot_id) is None

    def test_invalidate(self):
        c = SupervisorSnapshotCache()
        s = _healthy()
        c.put(s.snapshot_id, s)
        c.invalidate(s.snapshot_id)
        assert c.get(s.snapshot_id) is None

    def test_clear_resets_stats(self):
        c = SupervisorSnapshotCache()
        s = _healthy()
        c.put(s.snapshot_id, s)
        c.get(s.snapshot_id)
        c.clear()
        assert c.hit_count  == 0
        assert c.miss_count == 0
        assert c.size       == 0

    def test_capacity_evicts_oldest(self):
        c = SupervisorSnapshotCache(max_size=2, ttl_s=100)
        s1 = _healthy("a")
        s2 = _healthy("b")
        s3 = _healthy("c")
        c.put(s1.snapshot_id, s1)
        c.put(s2.snapshot_id, s2)
        c.put(s3.snapshot_id, s3)
        assert c.size == 2

    def test_stats_dict(self):
        d = SupervisorSnapshotCache().stats()
        assert "size" in d and "hit_rate" in d

    def test_custom_ttl_per_put(self):
        c = SupervisorSnapshotCache(ttl_s=100)
        s = _healthy()
        c.put(s.snapshot_id, s, ttl_s=0.05)
        time.sleep(0.12)
        assert c.get(s.snapshot_id) is None


# ===========================================================================
# 20. Store
# ===========================================================================

class TestStore:
    def test_save_and_load(self):
        st = SupervisorSnapshotStore()
        s  = _healthy()
        st.save(s)
        assert st.load(s.snapshot_id) is s

    def test_load_missing_returns_none(self):
        assert SupervisorSnapshotStore().load("missing") is None

    def test_load_or_raise(self):
        st = SupervisorSnapshotStore()
        with pytest.raises(SupervisorSnapshotNotFoundError):
            st.load_or_raise("missing")

    def test_save_none_raises(self):
        with pytest.raises(SupervisorSnapshotStoreError):
            SupervisorSnapshotStore().save(None)  # type: ignore

    def test_capacity_enforced(self):
        st = SupervisorSnapshotStore(max_snapshots=1)
        st.save(_minimal("s1"))
        with pytest.raises(SupervisorSnapshotCapacityError):
            st.save(_minimal("s2"))

    def test_delete(self):
        st = SupervisorSnapshotStore()
        s  = _healthy()
        st.save(s)
        st.delete(s.snapshot_id)
        assert st.count == 0

    def test_delete_missing_raises(self):
        with pytest.raises(SupervisorSnapshotNotFoundError):
            SupervisorSnapshotStore().delete("nope")

    def test_list_ids(self):
        st = SupervisorSnapshotStore()
        st.save(_minimal("a"))
        st.save(_minimal("b"))
        ids = st.list_snapshot_ids()
        assert len(ids) == 2

    def test_all_snapshots(self):
        st = SupervisorSnapshotStore()
        st.save(_minimal())
        assert len(st.all_snapshots()) == 1

    def test_clear(self):
        st = SupervisorSnapshotStore()
        st.save(_minimal())
        st.clear()
        assert st.count == 0


# ===========================================================================
# 21. History
# ===========================================================================

class TestHistory:
    def test_record_snapshot(self):
        h = SupervisorSnapshotHistory()
        h.record_snapshot("snap")
        assert h.snapshot_count() == 1

    def test_record_event(self):
        h = SupervisorSnapshotHistory()
        h.record_event("evt")
        assert h.event_count() == 1

    def test_bounded(self):
        h = SupervisorSnapshotHistory(max_snapshots=3)
        for i in range(10):
            h.record_snapshot(i)
        assert h.snapshot_count() == 3

    def test_recent_limited(self):
        h = SupervisorSnapshotHistory()
        for i in range(20):
            h.record_snapshot(i)
        assert len(h.recent_snapshots(5)) == 5

    def test_counts(self):
        h = SupervisorSnapshotHistory()
        h.record_snapshot("s")
        h.record_event("e")
        c = h.counts()
        assert c["snapshots"] == 1 and c["events"] == 1

    def test_clear(self):
        h = SupervisorSnapshotHistory()
        h.record_snapshot("x")
        h.clear()
        assert h.snapshot_count() == 0 and h.event_count() == 0


# ===========================================================================
# 22. Statistics (SupervisorSnapshotStatistics)
# ===========================================================================

class TestSnapshotStatisticsClass:
    def test_initial_zeros(self):
        s = SupervisorSnapshotStatistics()
        snap = s.snapshot()
        assert snap["builds"]    == 0
        assert snap["publishes"] == 0

    def test_record_build(self):
        s = SupervisorSnapshotStatistics()
        s.record_build(elapsed_s=0.5, size_bytes=1000)
        snap = s.snapshot()
        assert snap["builds"]           == 1
        assert snap["total_size_bytes"] == 1000
        assert snap["avg_build_s"]      == pytest.approx(0.5)

    def test_record_validation_pass(self):
        s = SupervisorSnapshotStatistics()
        s.record_validation(True)
        snap = s.snapshot()
        assert snap["validation_passes"] == 1

    def test_record_validation_fail(self):
        s = SupervisorSnapshotStatistics()
        s.record_validation(False)
        snap = s.snapshot()
        assert snap["validation_failures"] == 1

    def test_record_publish(self):
        s = SupervisorSnapshotStatistics()
        s.record_publish()
        assert s.snapshot()["publishes"] == 1

    def test_cache_hit_rate(self):
        s = SupervisorSnapshotStatistics()
        s.record_cache_hit()
        s.record_cache_miss()
        snap = s.snapshot()
        assert snap["cache_hit_rate"] == pytest.approx(0.5)

    def test_reset(self):
        s = SupervisorSnapshotStatistics()
        s.record_build()
        s.record_publish()
        s.reset()
        snap = s.snapshot()
        assert snap["builds"]    == 0
        assert snap["publishes"] == 0

    def test_thread_safe(self):
        s = SupervisorSnapshotStatistics()
        threads = [threading.Thread(target=s.record_build) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert s.snapshot()["builds"] == 100

    def test_ema_build(self):
        s = SupervisorSnapshotStatistics()
        s.record_build(elapsed_s=1.0)
        s.record_build(elapsed_s=0.5)
        snap = s.snapshot()
        assert 0.0 < snap["ema_build_s"] <= 1.0


# ===========================================================================
# 23. Events
# ===========================================================================

class TestEvents:
    def test_snapshot_started(self):
        e = make_snapshot_started_event("sess-1", "wf-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_STARTED
        assert e.payload["session_id"] == "sess-1"

    def test_snapshot_built(self):
        e = make_snapshot_built_event("snap-1", size_bytes=2048, elapsed_s=0.1)
        assert e.event_type == SnapshotEventType.SNAPSHOT_BUILT
        assert e.payload["size_bytes"] == 2048

    def test_snapshot_validated(self):
        e = make_snapshot_validated_event("snap-1", is_valid=True, failed_count=0)
        assert e.payload["is_valid"]

    def test_snapshot_published(self):
        e = make_snapshot_published_event("snap-1", is_emergency=True)
        assert e.payload["is_emergency"]

    def test_snapshot_registered(self):
        e = make_snapshot_registered_event("snap-1", "sess-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_REGISTERED

    def test_snapshot_retrieved(self):
        e = make_snapshot_retrieved_event("snap-1", from_cache=True)
        assert e.payload["from_cache"]

    def test_snapshot_invalidated(self):
        e = make_snapshot_invalidated_event("snap-1", reason="TTL expired")
        assert e.payload["reason"] == "TTL expired"

    def test_snapshot_cached(self):
        e = make_snapshot_cached_event("snap-1", ttl_s=300.0)
        assert e.payload["ttl_s"] == 300.0

    def test_snapshot_expired(self):
        e = make_snapshot_expired_event("snap-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_EXPIRED

    def test_snapshot_archived(self):
        e = make_snapshot_archived_event("snap-1")
        assert e.event_type == SnapshotEventType.SNAPSHOT_ARCHIVED

    def test_bundle_created(self):
        e = make_bundle_created_event("bundle-1", snapshot_count=5)
        assert e.payload["snapshot_count"] == 5

    def test_store_saved(self):
        e = make_store_saved_event("snap-1", store="in_memory")
        assert e.payload["store"] == "in_memory"

    def test_unique_ids(self):
        e1 = make_snapshot_started_event()
        e2 = make_snapshot_started_event()
        assert e1.event_id != e2.event_id

    def test_frozen(self):
        e = make_snapshot_started_event()
        with pytest.raises((TypeError, AttributeError)):
            e.source = "other"  # type: ignore

    def test_to_dict(self):
        d = make_snapshot_started_event().to_dict()
        assert "event_type" in d and "event_id" in d and "occurred_at" in d


# ===========================================================================
# 24. Bundle
# ===========================================================================

class TestBundle:
    def _builder(self, sid: str = "sess-1") -> SupervisorSnapshotBundleBuilder:
        return SupervisorSnapshotBundleBuilder(sid)

    def test_requires_session_id(self):
        with pytest.raises(SupervisorSnapshotBundleError):
            SupervisorSnapshotBundleBuilder("")

    def test_add_and_build(self):
        b = self._builder()
        b.add(_healthy())
        b.add(_emergency())
        bundle = b.build()
        assert bundle.count == 2

    def test_add_none_raises(self):
        b = self._builder()
        with pytest.raises(SupervisorSnapshotBundleError):
            b.add(None)  # type: ignore

    def test_remove(self):
        b  = self._builder()
        s  = _healthy()
        b.add(s)
        b.remove(s.snapshot_id)
        assert b.count == 0

    def test_remove_missing_raises(self):
        b = self._builder()
        with pytest.raises(SupervisorSnapshotNotFoundError):
            b.remove("missing")

    def test_latest(self):
        b  = self._builder()
        s1 = _healthy("sess-A")
        time.sleep(0.01)
        s2 = _healthy("sess-A")
        b.add(s1); b.add(s2)
        bundle = b.build()
        assert bundle.latest is s2

    def test_oldest(self):
        b = self._builder()
        s1 = _healthy("sess-A")
        time.sleep(0.01)
        s2 = _healthy("sess-A")
        b.add(s1); b.add(s2)
        bundle = b.build()
        assert bundle.oldest is s1

    def test_get(self):
        b = self._builder()
        s = _healthy()
        b.add(s)
        bundle = b.build()
        assert bundle.get(s.snapshot_id) is s

    def test_get_missing_returns_none(self):
        bundle = self._builder().build()
        assert bundle.get("nope") is None

    def test_emergency_snapshots(self):
        b = self._builder()
        b.add(_healthy())
        b.add(_emergency())
        bundle = b.build()
        assert len(bundle.emergency_snapshots()) == 1

    def test_to_dict(self):
        b = self._builder()
        b.add(_healthy())
        d = b.build().to_dict()
        assert "bundle_id" in d and "snapshot_ids" in d

    def test_empty_latest_oldest(self):
        bundle = self._builder().build()
        assert bundle.latest is None
        assert bundle.oldest is None

    def test_frozen(self):
        bundle = self._builder().build()
        with pytest.raises((TypeError, AttributeError)):
            bundle.session_id = "other"  # type: ignore


# ===========================================================================
# 25. Public surface
# ===========================================================================

class TestPublicSurface:
    def test_all_exports_present(self):
        import iios.supervisor.snapshot as module
        for name in module.__all__:
            assert hasattr(module, name), f"Missing export: {name}"

    def test_snapshot_in_all(self):
        import iios.supervisor.snapshot as m
        assert "SupervisorSnapshot" in m.__all__

    def test_factory_in_all(self):
        import iios.supervisor.snapshot as m
        assert "SupervisorSnapshotFactory" in m.__all__


# ===========================================================================
# 26. Concurrency
# ===========================================================================

class TestConcurrency:
    def test_concurrent_registry_register(self):
        r      = SupervisorSnapshotRegistry(max_snapshots=1000)
        errors: List[Exception] = []
        def worker(i: int):
            try:
                r.register(_minimal(f"t-{i}"))
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert r.count == 50

    def test_concurrent_cache_put_get(self):
        c      = SupervisorSnapshotCache(max_size=500)
        errors: List[Exception] = []
        snaps  = [_healthy(f"cs-{i}") for i in range(40)]
        def writer(s):
            try:
                c.put(s.snapshot_id, s)
            except Exception as e:
                errors.append(e)
        def reader(s):
            try:
                c.get(s.snapshot_id)
            except Exception as e:
                errors.append(e)
        threads = (
            [threading.Thread(target=writer, args=(s,)) for s in snaps]
            + [threading.Thread(target=reader, args=(s,)) for s in snaps]
        )
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors

    def test_concurrent_store_save(self):
        st     = SupervisorSnapshotStore(max_snapshots=200)
        errors: List[Exception] = []
        def worker(i: int):
            try:
                st.save(_minimal(f"st-{i}"))
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert st.count == 50


# ===========================================================================
# 27. Integration
# ===========================================================================

class TestIntegration:
    def test_factory_valid_healthy(self):
        s = _F.create_healthy()
        r = _V.validate(s)
        assert r.is_valid

    def test_factory_valid_emergency(self):
        s = _F.create_emergency()
        r = _V.validate(s)
        assert r.is_valid

    def test_factory_valid_degraded(self):
        s = _F.create_degraded()
        r = _V.validate(s)
        assert r.is_valid

    def test_round_trip_json(self):
        import json
        s = _F.create_healthy()
        d = json.loads(s.to_json())
        assert d["snapshot_id"] == s.snapshot_id
        assert d["enterprise_state"] == "optimal"

    def test_register_then_retrieve(self):
        r = SupervisorSnapshotRegistry()
        s = _F.create_healthy("integ-sess")
        r.register(s)
        retrieved = r.get(s.snapshot_id)
        assert retrieved.enterprise_state == SnapshotEnterpriseState.OPTIMAL

    def test_store_then_retrieve(self):
        st = SupervisorSnapshotStore()
        s  = _F.create_healthy("integ-st")
        st.save(s)
        loaded = st.load(s.snapshot_id)
        assert loaded is s

    def test_cache_then_retrieve(self):
        c = SupervisorSnapshotCache()
        s = _F.create_healthy()
        c.put(s.snapshot_id, s)
        assert c.get(s.snapshot_id) is s
        assert c.hit_count == 1

    def test_history_records_snapshots(self):
        h = SupervisorSnapshotHistory()
        for _ in range(5):
            h.record_snapshot(_minimal())
        assert h.snapshot_count() == 5

    def test_bundle_from_mixed_scenarios(self):
        bb = SupervisorSnapshotBundleBuilder("integ-bundle")
        bb.add(_F.create_healthy())
        bb.add(_F.create_emergency())
        bb.add(_F.create_degraded())
        bundle = bb.build()
        assert bundle.count == 3
        assert len(bundle.emergency_snapshots()) == 1
        assert bundle.latest is not None

    def test_m4_to_snapshot_pipeline(self):
        """Full pipeline: M4 governance → M5 snapshot."""
        from iios.supervisor.governance import (
            AutonomousGovernanceEngine,
            AutonomousGovernanceFactory as M4Factory,
        )
        m4f    = M4Factory()
        engine = AutonomousGovernanceEngine()
        engine.start()
        try:
            summary = engine.govern(m4f.create_healthy_platform_request())
        finally:
            engine.stop()

        snap = _F.create_from_governance_summary("sess-pipeline", "wf-pipe", summary)
        result = _V.validate(snap)
        assert result.is_valid
        assert snap.enterprise_summary.enterprise_health > 0.0

    def test_statistics_tracks_full_cycle(self):
        stats = SupervisorSnapshotStatistics()
        s     = _F.create_healthy()
        size  = s.estimated_size_bytes()
        stats.record_build(elapsed_s=0.05, size_bytes=size)
        stats.record_validation(passed=True)
        stats.record_publish()
        snap = stats.snapshot()
        assert snap["builds"]            == 1
        assert snap["validation_passes"] == 1
        assert snap["publishes"]         == 1
        assert snap["total_size_bytes"]  == size
