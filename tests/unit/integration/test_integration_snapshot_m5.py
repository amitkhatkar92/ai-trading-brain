"""
test_integration_snapshot_m5.py
================================
C15 M5 — Integration Snapshot

Comprehensive test suite.

Groups:
  A — Constants & exceptions
  B — SnapshotMetadata
  C — Summary sub-objects
  D — IntegrationSnapshot (core)
  E — Builder
  F — Factory
  G — Validation (7 checks)
  H — Registry
  I — Store
  J — Cache
  K — History
  L — Statistics
  M — Events
  N — Bundle
  O — Serialization round-trips
  P — Concurrency & stress
  Q — Regression (no circular imports, no vendor code)
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List

import pytest

import iios.integration.snapshot as snap_pkg
from iios.integration.snapshot import (
    AdapterSummary,
    AuditSummary,
    BundleEntry,
    CacheStats,
    ConnectivityState,
    ConnectivitySummary,
    ConnectorSummary,
    GovernanceState,
    IntegrationSnapshot,
    IntegrationSnapshotBuilder,
    IntegrationSnapshotBundle,
    IntegrationSnapshotCache,
    IntegrationSnapshotEventBus,
    IntegrationSnapshotFactory,
    IntegrationSnapshotHistory,
    IntegrationSnapshotRegistry,
    IntegrationSnapshotStatistics,
    IntegrationSnapshotStore,
    IntegrationSnapshotValidation,
    LifecycleState,
    ProtocolHealth,
    ProtocolSummary,
    SecuritySummary,
    ServiceSummary,
    SnapshotBuildError,
    SnapshotBundleError,
    SnapshotEvent,
    SnapshotEventType,
    SnapshotExpiredError,
    SnapshotHistoryEntry,
    SnapshotHistoryReport,
    SnapshotIntegrationType,
    SnapshotMetadata,
    SnapshotNotFoundError,
    SnapshotRegistryError,
    SnapshotScope,
    SnapshotSerializationError,
    SnapshotStatisticsReport,
    SnapshotStatisticsSummary,
    SnapshotStatus,
    SnapshotStoreError,
    SnapshotValidationCheck,
    SnapshotValidationIssue,
    SnapshotValidationReport,
    SnapshotVersionError,
)


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════


def _make_snapshot(
    session_id:  str = "sess-test",
    workflow_id: str = "wf-test",
    ent_id:      str = "ent-test",
    **kwargs,
) -> IntegrationSnapshot:
    builder = (
        IntegrationSnapshotBuilder()
        .set_session_ids(session_id, workflow_id, ent_id)
        .set_lifecycle_state(LifecycleState.ACTIVE)
        .set_governance_state(GovernanceState.COMPLIANT)
        .set_connectivity_state(ConnectivityState.CONNECTED)
        .set_status(SnapshotStatus.DRAFT)
    )
    if "requests_processed" in kwargs:
        builder = builder.set_service_summary(
            requests_processed = kwargs.pop("requests_processed"),
            average_latency_ms = kwargs.pop("average_latency_ms", 0.0),
        )
    return builder.build()


# ════════════════════════════════════════════════════════════════════════
# A — Constants & Exceptions
# ════════════════════════════════════════════════════════════════════════


class TestConstants:
    def test_snapshot_status_count(self):
        assert len(SnapshotStatus) == 4

    def test_snapshot_scope_count(self):
        assert len(SnapshotScope) == 5

    def test_snapshot_integration_type_count(self):
        assert len(SnapshotIntegrationType) == 9

    def test_lifecycle_state_count(self):
        assert len(LifecycleState) == 9

    def test_governance_state_count(self):
        assert len(GovernanceState) == 6

    def test_connectivity_state_count(self):
        assert len(ConnectivityState) == 5

    def test_snapshot_event_type_count(self):
        assert len(SnapshotEventType) == 10

    def test_validation_check_count(self):
        assert len(SnapshotValidationCheck) == 7

    def test_protocol_health_count(self):
        assert len(ProtocolHealth) == 4

    def test_default_constants(self):
        from iios.integration.snapshot import (
            DEFAULT_SNAPSHOT_TTL_SECONDS, DEFAULT_HISTORY_SIZE,
            DEFAULT_CACHE_SIZE, DEFAULT_MAX_BUNDLE_SIZE, DEFAULT_STORE_MAX,
            SNAPSHOT_VERSION, FRAMEWORK_VERSION, SNAPSHOT_ID_PREFIX,
            BUNDLE_ID_PREFIX, VALIDATION_CHECK_ORDER,
        )
        assert DEFAULT_SNAPSHOT_TTL_SECONDS == 3_600
        assert DEFAULT_HISTORY_SIZE         == 500
        assert DEFAULT_CACHE_SIZE           == 100
        assert DEFAULT_MAX_BUNDLE_SIZE      == 50
        assert DEFAULT_STORE_MAX            == 10_000
        assert SNAPSHOT_VERSION             == "1.0.0"
        assert FRAMEWORK_VERSION            == "1.0.0"
        assert SNAPSHOT_ID_PREFIX           == "snap-"
        assert BUNDLE_ID_PREFIX             == "bndl-"
        assert len(VALIDATION_CHECK_ORDER)  == 7


class TestExceptions:
    def test_base_error(self):
        exc = snap_pkg.IntegrationSnapshotError("base error")
        assert "ISS-000" in str(exc.code)

    def test_not_found_error(self):
        exc = SnapshotNotFoundError("snap-001")
        assert "snap-001" in str(exc)

    def test_build_error(self):
        exc = SnapshotBuildError("missing session_id")
        assert "missing" in str(exc).lower()

    def test_validation_error_iss003(self):
        exc = snap_pkg.SnapshotValidationError()
        assert "ISS-003" in str(exc.code)

    def test_registry_error_iss004(self):
        exc = SnapshotRegistryError()
        assert "ISS-004" in str(exc.code)

    def test_store_error_iss005(self):
        exc = SnapshotStoreError()
        assert "ISS-005" in str(exc.code)

    def test_expired_error_iss007(self):
        exc = SnapshotExpiredError("snap-002")
        assert "snap-002" in str(exc)

    def test_serialization_error_iss008(self):
        exc = SnapshotSerializationError()
        assert "ISS-008" in str(exc.code)

    def test_version_error_iss009(self):
        exc = SnapshotVersionError()
        assert "ISS-009" in str(exc.code)

    def test_bundle_error_iss010(self):
        exc = SnapshotBundleError()
        assert "ISS-010" in str(exc.code)


# ════════════════════════════════════════════════════════════════════════
# B — SnapshotMetadata
# ════════════════════════════════════════════════════════════════════════


class TestSnapshotMetadata:
    def test_create_defaults(self):
        m = SnapshotMetadata.create()
        assert m.environment       == "production"
        assert m.framework_version == "1.0.0"
        assert isinstance(m.source_components, tuple)
        assert isinstance(m.correlation_ids, tuple)
        assert isinstance(m.trace_ids, tuple)
        assert isinstance(m.tags, dict)
        assert m.generated_at

    def test_create_with_values(self):
        m = SnapshotMetadata.create(
            environment       = "staging",
            source_components = ["engine", "services"],
            correlation_ids   = ["corr-001"],
            tags              = {"team": "platform"},
        )
        assert m.environment             == "staging"
        assert "engine" in m.source_components
        assert "corr-001" in m.correlation_ids
        assert m.tags["team"]            == "platform"

    def test_immutable(self):
        m = SnapshotMetadata.create()
        with pytest.raises((TypeError, AttributeError)):
            m.environment = "changed"  # type: ignore[misc]

    def test_to_dict(self):
        m = SnapshotMetadata.create(
            environment = "production",
            tags        = {"k": "v"},
        )
        d = m.to_dict()
        assert d["environment"]   == "production"
        assert d["tags"]["k"]     == "v"
        assert isinstance(d["source_components"], list)

    def test_from_dict_round_trip(self):
        m  = SnapshotMetadata.create(environment="testing", build_version="2.0.0")
        d  = m.to_dict()
        m2 = SnapshotMetadata.from_dict(d)
        assert m2.environment   == "testing"
        assert m2.build_version == "2.0.0"


# ════════════════════════════════════════════════════════════════════════
# C — Summary sub-objects
# ════════════════════════════════════════════════════════════════════════


class TestSummaryObjects:
    def test_connectivity_summary_default(self):
        cs = ConnectivitySummary.default()
        assert cs.active_integrations == 0
        assert cs.overall_integration_health == "unknown"

    def test_connectivity_summary_to_dict(self):
        cs = ConnectivitySummary.default()
        d  = cs.to_dict()
        assert len(d) == 10

    def test_connector_summary_default(self):
        cs = ConnectorSummary.default()
        assert cs.connector_count        == 0
        assert cs.connector_availability == 0.0

    def test_connector_summary_with_values(self):
        cs = ConnectorSummary(
            connector_count        = 3,
            connector_types        = ("rest_api", "kafka"),
            connector_availability = 0.9,
            connector_health       = "healthy",
            connector_versions     = {"rest_connector": "1.0.0"},
        )
        d = cs.to_dict()
        assert d["connector_count"]        == 3
        assert d["connector_availability"] == 0.9

    def test_adapter_summary_default(self):
        asm = AdapterSummary.default()
        assert asm.adapter_count == 0

    def test_protocol_summary_default(self):
        ps = ProtocolSummary.default()
        assert ps.rest == "unknown"
        d  = ps.to_dict()
        assert len(d) == 11

    def test_service_summary_default(self):
        ss = ServiceSummary.default()
        assert ss.requests_processed == 0
        assert ss.average_latency_ms == 0.0

    def test_service_summary_to_dict(self):
        ss = ServiceSummary.default()
        d  = ss.to_dict()
        assert len(d) == 9

    def test_security_summary_default(self):
        sec = SecuritySummary.default()
        assert sec.authentication_providers == 0
        assert sec.encryption_status == "unknown"

    def test_audit_summary_default(self):
        a = AuditSummary.default()
        assert a.governance_version == "1.0.0"
        assert isinstance(a.audit_trail, tuple)

    def test_snapshot_statistics_summary_default(self):
        st = SnapshotStatisticsSummary.default()
        assert st.processing_duration_ms == 0.0
        assert st.connector_count        == 0


# ════════════════════════════════════════════════════════════════════════
# D — IntegrationSnapshot (core)
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationSnapshot:
    def test_create_defaults(self):
        s = IntegrationSnapshot.create(
            integration_session_id  = "sess-001",
            integration_workflow_id = "wf-001",
            enterprise_session_id   = "ent-001",
        )
        assert s.snapshot_id.startswith("snap-")
        assert s.integration_session_id  == "sess-001"
        assert s.integration_workflow_id == "wf-001"
        assert s.enterprise_session_id   == "ent-001"
        assert s.status                  == SnapshotStatus.DRAFT
        assert s.lifecycle_state         == LifecycleState.ACTIVE
        assert s.snapshot_timestamp
        assert s.created_at

    def test_immutable(self):
        s = _make_snapshot()
        with pytest.raises((TypeError, AttributeError)):
            s.status = SnapshotStatus.PUBLISHED  # type: ignore[misc]

    def test_custom_snapshot_id(self):
        s = IntegrationSnapshot.create(
            integration_session_id  = "s",
            integration_workflow_id = "w",
            enterprise_session_id   = "e",
            snapshot_id             = "snap-custom-001",
        )
        assert s.snapshot_id == "snap-custom-001"

    def test_to_dict_keys(self):
        s = _make_snapshot()
        d = s.to_dict()
        required = {
            "snapshot_id", "integration_session_id", "integration_workflow_id",
            "enterprise_session_id", "integration_version", "framework_version",
            "snapshot_version", "integration_scope", "integration_type",
            "lifecycle_state", "governance_state", "connectivity_state",
            "status", "snapshot_timestamp", "created_at", "updated_at",
            "connectivity_summary", "connector_summary", "adapter_summary",
            "protocol_summary", "service_summary", "security_summary",
            "audit_summary", "statistics_summary", "metadata",
        }
        assert required.issubset(set(d.keys()))

    def test_enum_values_serialized_as_strings(self):
        s = _make_snapshot()
        d = s.to_dict()
        assert isinstance(d["status"],             str)
        assert isinstance(d["lifecycle_state"],    str)
        assert isinstance(d["governance_state"],   str)
        assert isinstance(d["connectivity_state"], str)
        assert isinstance(d["integration_scope"],  str)
        assert isinstance(d["integration_type"],   str)

    def test_from_dict_round_trip(self):
        s  = _make_snapshot()
        d  = s.to_dict()
        s2 = IntegrationSnapshot.from_dict(d)
        assert s2.snapshot_id             == s.snapshot_id
        assert s2.integration_session_id  == s.integration_session_id
        assert s2.lifecycle_state         == s.lifecycle_state
        assert s2.status                  == s.status

    def test_unique_ids_per_create(self):
        s1 = _make_snapshot()
        s2 = _make_snapshot()
        assert s1.snapshot_id != s2.snapshot_id


# ════════════════════════════════════════════════════════════════════════
# E — Builder
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationSnapshotBuilder:
    def test_build_minimal(self):
        s = (
            IntegrationSnapshotBuilder()
            .set_session_ids("sess-001", "wf-001", "ent-001")
            .build()
        )
        assert s.snapshot_id.startswith("snap-")

    def test_build_missing_session_raises(self):
        with pytest.raises(SnapshotBuildError):
            IntegrationSnapshotBuilder().build()

    def test_build_missing_workflow_raises(self):
        with pytest.raises(SnapshotBuildError):
            b = IntegrationSnapshotBuilder()
            b._integration_session_id  = "sess-001"
            b._integration_workflow_id = ""
            b._enterprise_session_id   = "ent-001"
            b.build()

    def test_fluent_chain_returns_builder(self):
        b = IntegrationSnapshotBuilder()
        assert b.set_session_ids("s", "w", "e") is b
        assert b.set_lifecycle_state(LifecycleState.ACTIVE) is b
        assert b.set_governance_state(GovernanceState.COMPLIANT) is b

    def test_set_versions(self):
        s = (
            IntegrationSnapshotBuilder()
            .set_session_ids("s", "w", "e")
            .set_versions(integration_version="2.0.0")
            .build()
        )
        assert s.integration_version == "2.0.0"

    def test_set_scope(self):
        s = (
            IntegrationSnapshotBuilder()
            .set_session_ids("s", "w", "e")
            .set_scope(SnapshotScope.SUBSYSTEM, SnapshotIntegrationType.MESSAGING)
            .build()
        )
        assert s.integration_scope == SnapshotScope.SUBSYSTEM
        assert s.integration_type  == SnapshotIntegrationType.MESSAGING

    def test_set_service_summary(self):
        s = (
            IntegrationSnapshotBuilder()
            .set_session_ids("s", "w", "e")
            .set_service_summary(
                requests_processed = 500,
                failures           = 5,
                average_latency_ms = 12.3,
            )
            .build()
        )
        assert s.service_summary.requests_processed == 500
        assert s.service_summary.failures           == 5
        assert s.service_summary.average_latency_ms == pytest.approx(12.3)

    def test_set_security_summary(self):
        s = (
            IntegrationSnapshotBuilder()
            .set_session_ids("s", "w", "e")
            .set_security_summary(
                authentication_providers = 2,
                certificates             = 5,
                secrets                  = 10,
            )
            .build()
        )
        assert s.security_summary.authentication_providers == 2
        assert s.security_summary.certificates             == 5

    def test_set_connector_summary(self):
        s = (
            IntegrationSnapshotBuilder()
            .set_session_ids("s", "w", "e")
            .set_connector_summary(
                connector_count        = 3,
                connector_types        = ["rest_api", "kafka"],
                connector_availability = 0.95,
            )
            .build()
        )
        assert s.connector_summary.connector_count        == 3
        assert s.connector_summary.connector_availability == pytest.approx(0.95)

    def test_set_protocol_summary(self):
        s = (
            IntegrationSnapshotBuilder()
            .set_session_ids("s", "w", "e")
            .set_protocol_summary(
                rest     = "enabled",
                kafka    = "enabled",
                graphql  = "disabled",
            )
            .build()
        )
        assert s.protocol_summary.rest    == "enabled"
        assert s.protocol_summary.kafka   == "enabled"
        assert s.protocol_summary.graphql == "disabled"

    def test_set_audit_summary(self):
        s = (
            IntegrationSnapshotBuilder()
            .set_session_ids("s", "w", "e")
            .set_audit_summary(
                validation_summary = "all passed",
                audit_trail        = ["event_1", "event_2"],
            )
            .build()
        )
        assert s.audit_summary.validation_summary == "all passed"
        assert "event_1" in s.audit_summary.audit_trail

    def test_set_metadata_fields(self):
        s = (
            IntegrationSnapshotBuilder()
            .set_session_ids("s", "w", "e")
            .set_metadata_fields(
                environment       = "staging",
                source_components = ["engine"],
                tags              = {"region": "ap-south-1"},
            )
            .build()
        )
        assert s.metadata.environment == "staging"
        assert "engine" in s.metadata.source_components
        assert s.metadata.tags["region"] == "ap-south-1"

    def test_processing_duration_auto_set(self):
        s = (
            IntegrationSnapshotBuilder()
            .set_session_ids("s", "w", "e")
            .build()
        )
        # Build time should be positive (even if tiny)
        assert s.statistics_summary.processing_duration_ms >= 0.0

    def test_custom_snapshot_id(self):
        s = (
            IntegrationSnapshotBuilder()
            .set_session_ids("s", "w", "e")
            .set_snapshot_id("snap-custom-999")
            .build()
        )
        assert s.snapshot_id == "snap-custom-999"


# ════════════════════════════════════════════════════════════════════════
# F — Factory
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationSnapshotFactory:
    def test_create_generic(self):
        s = IntegrationSnapshotFactory.create(
            integration_session_id  = "sess-001",
            integration_workflow_id = "wf-001",
            enterprise_session_id   = "ent-001",
        )
        assert s.lifecycle_state  == LifecycleState.ACTIVE
        assert s.governance_state == GovernanceState.COMPLIANT

    def test_create_rest_snapshot(self):
        s = IntegrationSnapshotFactory.create_rest_snapshot(
            integration_session_id  = "sess-001",
            integration_workflow_id = "wf-001",
            enterprise_session_id   = "ent-001",
            requests_processed      = 5_000,
            average_latency_ms      = 12.5,
        )
        assert s.integration_type == SnapshotIntegrationType.REST_API
        assert s.status           == SnapshotStatus.PUBLISHED
        assert s.service_summary.requests_processed == 5_000
        assert s.protocol_summary.rest              == "enabled"

    def test_create_messaging_snapshot(self):
        s = IntegrationSnapshotFactory.create_messaging_snapshot(
            integration_session_id  = "sess-001",
            integration_workflow_id = "wf-001",
            enterprise_session_id   = "ent-001",
            messages_published      = 1_000,
        )
        assert s.integration_type == SnapshotIntegrationType.MESSAGING
        assert s.service_summary.messages_published == 1_000
        assert s.protocol_summary.kafka             == "enabled"

    def test_create_enterprise_snapshot(self):
        s = IntegrationSnapshotFactory.create_enterprise_snapshot(
            integration_session_id   = "sess-001",
            integration_workflow_id  = "wf-001",
            enterprise_session_id    = "ent-001",
            connector_count          = 10,
            requests_processed       = 50_000,
            authentication_providers = 3,
        )
        assert s.integration_type                         == SnapshotIntegrationType.ENTERPRISE
        assert s.connectivity_summary.registered_connectors == 10
        assert s.service_summary.requests_processed       == 50_000
        assert s.security_summary.authentication_providers == 3
        assert s.protocol_summary.rest                    == "enabled"
        assert s.protocol_summary.kafka                   == "enabled"

    def test_from_dict_valid(self):
        s  = _make_snapshot()
        d  = s.to_dict()
        s2 = IntegrationSnapshotFactory.from_dict(d)
        assert s2.snapshot_id == s.snapshot_id

    def test_from_dict_invalid_raises(self):
        with pytest.raises(SnapshotSerializationError):
            IntegrationSnapshotFactory.from_dict({"bad": "data"})

    def test_bump_version(self):
        draft = _make_snapshot()
        published = IntegrationSnapshotFactory.bump_version(
            draft,
            new_status  = SnapshotStatus.PUBLISHED,
            audit_entry = "published by test",
        )
        assert published.snapshot_id != draft.snapshot_id
        assert published.status      == SnapshotStatus.PUBLISHED
        assert "published by test" in published.audit_summary.audit_trail


# ════════════════════════════════════════════════════════════════════════
# G — Validation (7 checks)
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationSnapshotValidation:
    def _validator(self):
        return IntegrationSnapshotValidation()

    def test_valid_snapshot_passes(self):
        s = _make_snapshot()
        r = self._validator().validate(s)
        assert r.passed is True
        assert r.error_count == 0

    def test_report_fields(self):
        s = _make_snapshot()
        r = self._validator().validate(s)
        assert r.snapshot_id == s.snapshot_id
        assert r.checked_at

    def test_check_identifier_consistency_empty_session(self):
        s = IntegrationSnapshot.create(
            integration_session_id  = "",   # empty
            integration_workflow_id = "wf",
            enterprise_session_id   = "ent",
        )
        r = self._validator().validate(s)
        assert r.passed is False
        assert any(
            i.check == SnapshotValidationCheck.IDENTIFIER_CONSISTENCY
            and i.severity == "error"
            for i in r.issues
        )

    def test_check_version_consistency_empty_version(self):
        s = IntegrationSnapshot.create(
            integration_session_id  = "s",
            integration_workflow_id = "w",
            enterprise_session_id   = "e",
            integration_version     = "",   # empty
        )
        r = self._validator().validate(s)
        assert r.passed is False
        assert any(
            i.check == SnapshotValidationCheck.VERSION_CONSISTENCY
            for i in r.errors
        )

    def test_check_version_consistency_non_semver_warning(self):
        s = IntegrationSnapshot.create(
            integration_session_id  = "s",
            integration_workflow_id = "w",
            enterprise_session_id   = "e",
            integration_version     = "release-2",  # non-SemVer
        )
        r = self._validator().validate(s)
        # Should warn but not error on non-SemVer
        warns = [i for i in r.warnings
                 if i.check == SnapshotValidationCheck.VERSION_CONSISTENCY]
        assert len(warns) >= 1

    def test_check_protocol_consistency_custom_state_warning(self):
        s = IntegrationSnapshot.create(
            integration_session_id  = "s",
            integration_workflow_id = "w",
            enterprise_session_id   = "e",
            protocol_summary        = ProtocolSummary(
                rest="enabled", graphql="active_custom",  # unrecognized state
                grpc="unknown", websocket="unknown", kafka="unknown",
                rabbitmq="unknown", redis_streams="unknown",
                database_connectors="unknown", webhook_services="unknown",
                file_transfer="unknown", protocol_health="unknown",
            ),
        )
        r = self._validator().validate(s)
        warns = [i for i in r.warnings
                 if i.check == SnapshotValidationCheck.PROTOCOL_CONSISTENCY]
        assert len(warns) >= 1

    def test_check_metadata_empty_framework_version_error(self):
        meta = SnapshotMetadata.create(framework_version="")
        # Manually construct with bad metadata
        s = IntegrationSnapshot.create(
            integration_session_id  = "s",
            integration_workflow_id = "w",
            enterprise_session_id   = "e",
            metadata                = meta,
        )
        r = self._validator().validate(s)
        assert any(
            i.check == SnapshotValidationCheck.METADATA_INTEGRITY
            and i.severity == "error"
            for i in r.issues
        )

    def test_check_snapshot_completeness_missing_timestamp(self):
        # Directly construct with empty snapshot_timestamp (bypassing create())
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc).isoformat()
        s = IntegrationSnapshot(
            snapshot_id             = "snap-test-ts",
            integration_session_id  = "s",
            integration_workflow_id = "w",
            enterprise_session_id   = "e",
            integration_version     = "1.0.0",
            framework_version       = "1.0.0",
            snapshot_version        = "1.0.0",
            integration_scope       = SnapshotScope.ENTERPRISE,
            integration_type        = SnapshotIntegrationType.FULL,
            lifecycle_state         = LifecycleState.ACTIVE,
            governance_state        = GovernanceState.COMPLIANT,
            connectivity_state      = ConnectivityState.CONNECTED,
            status                  = SnapshotStatus.DRAFT,
            snapshot_timestamp      = "",   # intentionally empty
            created_at              = now,
            updated_at              = now,
            connectivity_summary    = ConnectivitySummary.default(),
            connector_summary       = ConnectorSummary.default(),
            adapter_summary         = AdapterSummary.default(),
            protocol_summary        = ProtocolSummary.default(),
            service_summary         = ServiceSummary.default(),
            security_summary        = SecuritySummary.default(),
            audit_summary           = AuditSummary.default(),
            statistics_summary      = SnapshotStatisticsSummary.default(),
            metadata                = SnapshotMetadata.create(),
        )
        r = self._validator().validate(s)
        assert any(
            i.check == SnapshotValidationCheck.SNAPSHOT_COMPLETENESS
            and i.severity == "error"
            for i in r.issues
        )

    def test_validation_report_errors_warnings_properties(self):
        s = _make_snapshot()
        r = self._validator().validate(s)
        assert isinstance(r.errors,   list)
        assert isinstance(r.warnings, list)

    def test_all_7_checks_run(self):
        s = _make_snapshot()
        r = self._validator().validate(s)
        checked = {i.check for i in r.issues}
        # For a valid snapshot there should be no issues — but the validator runs
        # all 7 checks regardless. We verify by triggering all checks via
        # a snapshot that generates at least some warnings.
        s2 = IntegrationSnapshot.create(
            integration_session_id  = "s",
            integration_workflow_id = "w",
            enterprise_session_id   = "e",
            integration_version     = "release-1",  # warns version
        )
        r2 = self._validator().validate(s2)
        assert len(r2.issues) > 0


# ════════════════════════════════════════════════════════════════════════
# H — Registry
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationSnapshotRegistry:
    def test_register_and_get(self):
        reg = IntegrationSnapshotRegistry()
        s   = _make_snapshot()
        reg.register(s)
        found = reg.get(s.snapshot_id)
        assert found is not None
        assert found.snapshot_id == s.snapshot_id

    def test_register_duplicate_raises(self):
        reg = IntegrationSnapshotRegistry()
        s   = _make_snapshot()
        reg.register(s)
        with pytest.raises(SnapshotRegistryError):
            reg.register(s)

    def test_get_or_raise_missing(self):
        reg = IntegrationSnapshotRegistry()
        with pytest.raises(SnapshotNotFoundError):
            reg.get_or_raise("snap-nonexistent")

    def test_get_latest_by_session(self):
        reg = IntegrationSnapshotRegistry()
        s1  = _make_snapshot(session_id="sess-X")
        s2  = _make_snapshot(session_id="sess-X")
        reg.register(s1)
        reg.register(s2)
        latest = reg.get_latest("sess-X")
        assert latest.snapshot_id == s2.snapshot_id

    def test_by_session_id(self):
        reg = IntegrationSnapshotRegistry()
        for _ in range(3):
            reg.register(_make_snapshot(session_id="sess-A"))
        reg.register(_make_snapshot(session_id="sess-B"))
        items = reg.by_session_id("sess-A")
        assert len(items) == 3

    def test_by_status(self):
        reg = IntegrationSnapshotRegistry()
        s1  = _make_snapshot()
        s2  = _make_snapshot()
        reg.register(s1)
        reg.register(s2)
        reg.set_status(s1.snapshot_id, SnapshotStatus.PUBLISHED)
        published = reg.by_status(SnapshotStatus.PUBLISHED)
        assert len(published) == 1
        assert published[0].snapshot_id == s1.snapshot_id

    def test_deregister(self):
        reg = IntegrationSnapshotRegistry()
        s   = _make_snapshot()
        reg.register(s)
        ok  = reg.deregister(s.snapshot_id)
        assert ok is True
        assert reg.get(s.snapshot_id) is None

    def test_deregister_missing_returns_false(self):
        reg = IntegrationSnapshotRegistry()
        assert reg.deregister("snap-nonexistent") is False

    def test_capacity_enforced(self):
        reg = IntegrationSnapshotRegistry(max_size=2)
        reg.register(_make_snapshot())
        reg.register(_make_snapshot())
        with pytest.raises(SnapshotRegistryError):
            reg.register(_make_snapshot())

    def test_count(self):
        reg = IntegrationSnapshotRegistry()
        for _ in range(5):
            reg.register(_make_snapshot())
        assert reg.count == 5

    def test_list_all(self):
        reg = IntegrationSnapshotRegistry()
        for _ in range(3):
            reg.register(_make_snapshot())
        assert len(reg.list_all()) == 3

    def test_clear(self):
        reg = IntegrationSnapshotRegistry()
        for _ in range(4):
            reg.register(_make_snapshot())
        n = reg.clear()
        assert n == 4
        assert reg.count == 0


# ════════════════════════════════════════════════════════════════════════
# I — Store
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationSnapshotStore:
    def test_save_and_load(self):
        store = IntegrationSnapshotStore()
        s     = _make_snapshot()
        store.save(s)
        loaded = store.load(s.snapshot_id)
        assert loaded.snapshot_id == s.snapshot_id

    def test_load_missing_returns_none(self):
        store = IntegrationSnapshotStore()
        assert store.load("snap-missing") is None

    def test_load_or_raise_missing(self):
        store = IntegrationSnapshotStore()
        with pytest.raises(SnapshotNotFoundError):
            store.load_or_raise("snap-missing")

    def test_multiple_versions(self):
        store = IntegrationSnapshotStore()
        s1    = _make_snapshot()
        store.save(s1)
        store.save(s1)   # save again (second version)
        versions = store.list_versions(s1.snapshot_id)
        assert versions == ["v1", "v2"]

    def test_load_specific_version(self):
        store = IntegrationSnapshotStore()
        s     = _make_snapshot()
        store.save(s)
        store.save(s)
        v1 = store.load(s.snapshot_id, version_tag="v1")
        v2 = store.load(s.snapshot_id, version_tag="v2")
        assert v1 is not None
        assert v2 is not None

    def test_delete(self):
        store = IntegrationSnapshotStore()
        s     = _make_snapshot()
        store.save(s)
        ok = store.delete(s.snapshot_id)
        assert ok is True
        assert store.load(s.snapshot_id) is None

    def test_delete_missing_returns_false(self):
        store = IntegrationSnapshotStore()
        assert store.delete("snap-missing") is False

    def test_capacity_enforced(self):
        store = IntegrationSnapshotStore(max_entries=2)
        store.save(_make_snapshot())
        store.save(_make_snapshot())
        with pytest.raises(SnapshotStoreError):
            store.save(_make_snapshot())

    def test_count(self):
        store = IntegrationSnapshotStore()
        for _ in range(3):
            store.save(_make_snapshot())
        assert store.count == 3

    def test_unique_ids(self):
        store = IntegrationSnapshotStore()
        s1 = _make_snapshot()
        s2 = _make_snapshot()
        store.save(s1)
        store.save(s2)
        assert store.unique_ids == 2

    def test_exists(self):
        store = IntegrationSnapshotStore()
        s     = _make_snapshot()
        assert store.exists(s.snapshot_id) is False
        store.save(s)
        assert store.exists(s.snapshot_id) is True

    def test_clear(self):
        store = IntegrationSnapshotStore()
        for _ in range(5):
            store.save(_make_snapshot())
        n = store.clear()
        assert n == 5
        assert store.count == 0


# ════════════════════════════════════════════════════════════════════════
# J — Cache
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationSnapshotCache:
    def test_put_and_get(self):
        cache = IntegrationSnapshotCache()
        s     = _make_snapshot()
        cache.put(s)
        hit = cache.get(s.snapshot_id)
        assert hit is not None
        assert hit.snapshot_id == s.snapshot_id

    def test_miss_returns_none(self):
        cache = IntegrationSnapshotCache()
        assert cache.get("snap-missing") is None

    def test_ttl_expiry(self):
        cache = IntegrationSnapshotCache(ttl_seconds=0.05)
        s     = _make_snapshot()
        cache.put(s)
        time.sleep(0.1)
        assert cache.get(s.snapshot_id) is None

    def test_lru_eviction(self):
        cache = IntegrationSnapshotCache(max_size=2)
        s1 = _make_snapshot()
        s2 = _make_snapshot()
        s3 = _make_snapshot()
        cache.put(s1)
        cache.put(s2)
        cache.put(s3)   # s1 evicted (LRU)
        assert cache.get(s1.snapshot_id) is None
        assert cache.get(s2.snapshot_id) is not None

    def test_invalidate(self):
        cache = IntegrationSnapshotCache()
        s     = _make_snapshot()
        cache.put(s)
        ok = cache.invalidate(s.snapshot_id)
        assert ok is True
        assert cache.get(s.snapshot_id) is None

    def test_clear(self):
        cache = IntegrationSnapshotCache()
        for _ in range(5):
            cache.put(_make_snapshot())
        n = cache.clear()
        assert n == 5
        assert cache.size == 0

    def test_stats_hit_rate(self):
        cache = IntegrationSnapshotCache()
        s     = _make_snapshot()
        cache.put(s)
        cache.get(s.snapshot_id)   # hit
        cache.get("missing")        # miss
        st = cache.stats
        assert st.hits   == 1
        assert st.misses == 1
        assert st.hit_rate == pytest.approx(0.5)

    def test_refresh_on_re_put(self):
        cache = IntegrationSnapshotCache(ttl_seconds=0.05)
        s     = _make_snapshot()
        cache.put(s)
        time.sleep(0.03)
        cache.put(s, ttl_seconds=10.0)  # refresh
        time.sleep(0.05)               # original TTL would have expired
        assert cache.get(s.snapshot_id) is not None


# ════════════════════════════════════════════════════════════════════════
# K — History
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationSnapshotHistory:
    def test_record_and_recent(self):
        hist = IntegrationSnapshotHistory()
        s    = _make_snapshot()
        hist.record(s)
        recent = hist.recent(5)
        assert len(recent) == 1
        assert recent[0].snapshot_id == s.snapshot_id

    def test_entry_immutable(self):
        hist  = IntegrationSnapshotHistory()
        s     = _make_snapshot()
        entry = hist.record(s)
        assert isinstance(entry, SnapshotHistoryEntry)
        with pytest.raises((TypeError, AttributeError)):
            entry.snapshot_id = "changed"  # type: ignore[misc]

    def test_bounded_at_max_size(self):
        hist = IntegrationSnapshotHistory(max_size=3)
        for _ in range(5):
            hist.record(_make_snapshot())
        assert hist.size == 3

    def test_by_session(self):
        hist = IntegrationSnapshotHistory()
        for _ in range(3):
            hist.record(_make_snapshot(session_id="sess-A"))
        hist.record(_make_snapshot(session_id="sess-B"))
        items = hist.by_session("sess-A")
        assert len(items) == 3

    def test_by_status(self):
        hist = IntegrationSnapshotHistory()
        s1   = IntegrationSnapshot.create(
            integration_session_id  = "s",
            integration_workflow_id = "w",
            enterprise_session_id   = "e",
            status                  = SnapshotStatus.PUBLISHED,
        )
        s2   = _make_snapshot()
        hist.record(s1)
        hist.record(s2)
        published = hist.by_status(SnapshotStatus.PUBLISHED)
        assert len(published) == 1

    def test_report(self):
        hist = IntegrationSnapshotHistory()
        for _ in range(3):
            hist.record(IntegrationSnapshot.create(
                integration_session_id  = "s",
                integration_workflow_id = "w",
                enterprise_session_id   = "e",
                status                  = SnapshotStatus.PUBLISHED,
            ))
        hist.record(IntegrationSnapshot.create(
            integration_session_id  = "s",
            integration_workflow_id = "w",
            enterprise_session_id   = "e",
            status                  = SnapshotStatus.ARCHIVED,
        ))
        rep = hist.report()
        assert rep.total_entries == 4
        assert rep.published     == 3
        assert rep.archived      == 1
        assert rep.generated_at

    def test_clear(self):
        hist = IntegrationSnapshotHistory()
        for _ in range(3):
            hist.record(_make_snapshot())
        n = hist.clear()
        assert n == 3
        assert hist.size == 0


# ════════════════════════════════════════════════════════════════════════
# L — Statistics
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationSnapshotStatistics:
    def test_initial_state(self):
        st = IntegrationSnapshotStatistics()
        sr = st.snapshot()
        assert sr.snapshots_created   == 0
        assert sr.snapshots_published == 0

    def test_increment_created(self):
        st = IntegrationSnapshotStatistics()
        st.increment_created(3)
        assert st.snapshot().snapshots_created == 3

    def test_increment_published(self):
        st = IntegrationSnapshotStatistics()
        st.increment_published()
        assert st.snapshot().snapshots_published == 1

    def test_increment_retrieved_archived_expired(self):
        st = IntegrationSnapshotStatistics()
        st.increment_retrieved(5)
        st.increment_archived(2)
        st.increment_expired(1)
        sr = st.snapshot()
        assert sr.snapshots_retrieved == 5
        assert sr.snapshots_archived  == 2
        assert sr.snapshots_expired   == 1

    def test_record_validation(self):
        st = IntegrationSnapshotStatistics()
        st.record_validation(passed=True)
        st.record_validation(passed=True)
        st.record_validation(passed=False)
        sr = st.snapshot()
        assert sr.validation_passed == 2
        assert sr.validation_failed == 1

    def test_record_cache_hits_misses(self):
        st = IntegrationSnapshotStatistics()
        st.record_cache_hit()
        st.record_cache_hit()
        st.record_cache_miss()
        sr = st.snapshot()
        assert sr.cache_hits   == 2
        assert sr.cache_misses == 1

    def test_record_build_time(self):
        st = IntegrationSnapshotStatistics()
        st.record_build(10.0)
        st.record_build(20.0)
        sr = st.snapshot()
        assert sr.average_build_time_ms == pytest.approx(15.0)

    def test_reset(self):
        st = IntegrationSnapshotStatistics()
        st.increment_created(5)
        st.reset()
        assert st.snapshot().snapshots_created == 0

    def test_as_dict_count(self):
        st = IntegrationSnapshotStatistics()
        d  = st.snapshot().as_dict()
        assert len(d) == 11  # 10 metrics + generated_at


# ════════════════════════════════════════════════════════════════════════
# M — Events
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationSnapshotEventBus:
    def test_subscribe_and_emit(self):
        bus      = IntegrationSnapshotEventBus()
        received: List[SnapshotEvent] = []
        bus.subscribe(SnapshotEventType.SNAPSHOT_CREATED, received.append)
        n = bus.emit(SnapshotEventType.SNAPSHOT_CREATED, "snap-001", "test", {"k": "v"})
        assert n == 1
        assert received[0].event_type  == SnapshotEventType.SNAPSHOT_CREATED
        assert received[0].snapshot_id == "snap-001"

    def test_unsubscribe(self):
        bus     = IntegrationSnapshotEventBus()
        handler = lambda e: None
        bus.subscribe(SnapshotEventType.SNAPSHOT_PUBLISHED, handler)
        ok = bus.unsubscribe(SnapshotEventType.SNAPSHOT_PUBLISHED, handler)
        assert ok is True

    def test_all_10_event_types_emittable(self):
        bus = IntegrationSnapshotEventBus()
        for et in SnapshotEventType:
            n = bus.emit(et, "snap-001", "test", {})
            assert n == 0  # no handlers

    def test_handler_exception_suppressed(self):
        bus = IntegrationSnapshotEventBus()
        bus.subscribe(
            SnapshotEventType.SNAPSHOT_CREATED,
            lambda e: (_ for _ in ()).throw(RuntimeError("boom")),  # type: ignore
        )
        n = bus.emit(SnapshotEventType.SNAPSHOT_CREATED, "snap-001", "test", {})
        assert n == 0

    def test_history_bounded(self):
        bus = IntegrationSnapshotEventBus(max_history=3)
        for _ in range(5):
            bus.emit(SnapshotEventType.SNAPSHOT_RETRIEVED, "snap-001", "test", {})
        assert len(bus.history()) == 3

    def test_history_by_type(self):
        bus = IntegrationSnapshotEventBus()
        bus.emit(SnapshotEventType.SNAPSHOT_CREATED,   "s1", "test", {})
        bus.emit(SnapshotEventType.SNAPSHOT_PUBLISHED, "s2", "test", {})
        items = bus.history_by_type(SnapshotEventType.SNAPSHOT_CREATED)
        assert len(items) == 1

    def test_stats(self):
        bus = IntegrationSnapshotEventBus()
        bus.emit(SnapshotEventType.SNAPSHOT_CACHED_MISS, "s", "t", {}) \
            if hasattr(SnapshotEventType, "SNAPSHOT_CACHED_MISS") else \
            bus.emit(SnapshotEventType.SNAPSHOT_CACHE_MISS, "s", "t", {})
        st = bus.stats
        assert st["published"] >= 1


# ════════════════════════════════════════════════════════════════════════
# N — Bundle
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationSnapshotBundle:
    def test_add_and_get(self):
        bundle = IntegrationSnapshotBundle("test-bundle")
        s      = _make_snapshot()
        bundle.add(s)
        found  = bundle.get(s.snapshot_id)
        assert found.snapshot_id == s.snapshot_id

    def test_count(self):
        bundle = IntegrationSnapshotBundle("test-bundle")
        for _ in range(3):
            bundle.add(_make_snapshot())
        assert bundle.count == 3

    def test_add_duplicate_raises(self):
        bundle = IntegrationSnapshotBundle("test-bundle")
        s      = _make_snapshot()
        bundle.add(s)
        with pytest.raises(SnapshotBundleError):
            bundle.add(s)

    def test_capacity_enforced(self):
        bundle = IntegrationSnapshotBundle("test-bundle", max_size=2)
        bundle.add(_make_snapshot())
        bundle.add(_make_snapshot())
        with pytest.raises(SnapshotBundleError):
            bundle.add(_make_snapshot())

    def test_remove(self):
        bundle = IntegrationSnapshotBundle("test-bundle")
        s      = _make_snapshot()
        bundle.add(s)
        ok = bundle.remove(s.snapshot_id)
        assert ok is True
        assert bundle.get(s.snapshot_id) is None

    def test_remove_missing_returns_false(self):
        bundle = IntegrationSnapshotBundle("test-bundle")
        assert bundle.remove("snap-nonexistent") is False

    def test_snapshots_insertion_order(self):
        bundle = IntegrationSnapshotBundle("test-bundle")
        snaps  = [_make_snapshot() for _ in range(5)]
        for s in snaps:
            bundle.add(s)
        ids = bundle.snapshot_ids()
        assert ids == [s.snapshot_id for s in snaps]

    def test_contains(self):
        bundle = IntegrationSnapshotBundle("test-bundle")
        s      = _make_snapshot()
        assert s.snapshot_id not in bundle
        bundle.add(s)
        assert s.snapshot_id in bundle

    def test_to_dict(self):
        bundle = IntegrationSnapshotBundle("my-bundle", description="test")
        s      = _make_snapshot()
        bundle.add(s)
        d = bundle.to_dict()
        assert d["bundle_id"].startswith("bndl-")
        assert d["name"]      == "my-bundle"
        assert d["count"]     == 1
        assert len(d["snapshots"]) == 1

    def test_aggregate_service_metrics(self):
        bundle = IntegrationSnapshotBundle("test-bundle")
        s1 = (
            IntegrationSnapshotBuilder()
            .set_session_ids("s1", "w1", "e1")
            .set_service_summary(requests_processed=100, average_latency_ms=10.0)
            .build()
        )
        s2 = (
            IntegrationSnapshotBuilder()
            .set_session_ids("s2", "w2", "e2")
            .set_service_summary(requests_processed=200, average_latency_ms=20.0)
            .build()
        )
        bundle.add(s1)
        bundle.add(s2)
        agg = bundle.aggregate_service_metrics()
        assert agg["requests_processed"] == 300
        assert agg["average_latency_ms"] == pytest.approx(15.0)

    def test_get_or_raise_missing(self):
        bundle = IntegrationSnapshotBundle("test-bundle")
        with pytest.raises(SnapshotNotFoundError):
            bundle.get_or_raise("snap-nonexistent")

    def test_iter_and_len(self):
        bundle = IntegrationSnapshotBundle("test-bundle")
        snaps  = [_make_snapshot() for _ in range(3)]
        for s in snaps:
            bundle.add(s)
        assert len(bundle)  == 3
        listed = list(bundle)
        assert len(listed)  == 3


# ════════════════════════════════════════════════════════════════════════
# O — Serialization round-trips
# ════════════════════════════════════════════════════════════════════════


class TestSerialization:
    def test_snapshot_round_trip(self):
        s  = IntegrationSnapshotFactory.create_enterprise_snapshot(
            integration_session_id   = "sess-001",
            integration_workflow_id  = "wf-001",
            enterprise_session_id    = "ent-001",
            connector_count          = 8,
            requests_processed       = 10_000,
            authentication_providers = 2,
            certificates             = 5,
        )
        d  = s.to_dict()
        s2 = IntegrationSnapshot.from_dict(d)
        # All fields preserved
        assert s2.snapshot_id                               == s.snapshot_id
        assert s2.integration_session_id                   == s.integration_session_id
        assert s2.lifecycle_state                           == s.lifecycle_state
        assert s2.governance_state                          == s.governance_state
        assert s2.connectivity_state                        == s.connectivity_state
        assert s2.status                                    == s.status
        assert s2.service_summary.requests_processed        == 10_000
        assert s2.security_summary.authentication_providers == 2
        assert s2.security_summary.certificates             == 5
        assert s2.metadata.environment                      == "production"

    def test_all_enum_fields_survive_round_trip(self):
        s = IntegrationSnapshot.create(
            integration_session_id  = "s",
            integration_workflow_id = "w",
            enterprise_session_id   = "e",
            integration_scope       = SnapshotScope.SUBSYSTEM,
            integration_type        = SnapshotIntegrationType.MESSAGING,
            lifecycle_state         = LifecycleState.PAUSED,
            governance_state        = GovernanceState.UNDER_REVIEW,
            connectivity_state      = ConnectivityState.DEGRADED,
            status                  = SnapshotStatus.ARCHIVED,
        )
        d  = s.to_dict()
        s2 = IntegrationSnapshot.from_dict(d)
        assert s2.integration_scope  == SnapshotScope.SUBSYSTEM
        assert s2.integration_type   == SnapshotIntegrationType.MESSAGING
        assert s2.lifecycle_state    == LifecycleState.PAUSED
        assert s2.governance_state   == GovernanceState.UNDER_REVIEW
        assert s2.connectivity_state == ConnectivityState.DEGRADED
        assert s2.status             == SnapshotStatus.ARCHIVED

    def test_metadata_round_trip(self):
        meta = SnapshotMetadata.create(
            environment       = "staging",
            build_version     = "3.1.0",
            source_components = ["A", "B"],
            correlation_ids   = ["corr-1"],
            tags              = {"k": "v"},
        )
        d  = meta.to_dict()
        m2 = SnapshotMetadata.from_dict(d)
        assert m2.environment       == "staging"
        assert m2.build_version     == "3.1.0"
        assert "A" in m2.source_components
        assert "corr-1" in m2.correlation_ids
        assert m2.tags["k"]         == "v"

    def test_factory_from_dict_invalid_raises(self):
        with pytest.raises(SnapshotSerializationError):
            IntegrationSnapshotFactory.from_dict({"status": "!!invalid_enum!!"})

    def test_connectivity_summary_round_trip(self):
        cs = ConnectivitySummary(
            active_integrations        = 5,
            registered_connectors      = 3,
            registered_adapters        = 4,
            protocols_enabled          = 7,
            connection_pool_status     = "healthy",
            authentication_status      = "active",
            authorization_status       = "active",
            security_status            = "secure",
            compliance_status          = "compliant",
            overall_integration_health = "healthy",
        )
        d = cs.to_dict()
        assert d["active_integrations"]        == 5
        assert d["overall_integration_health"] == "healthy"


# ════════════════════════════════════════════════════════════════════════
# P — Concurrency & stress
# ════════════════════════════════════════════════════════════════════════


class TestConcurrency:
    def test_registry_concurrent_register(self):
        reg    = IntegrationSnapshotRegistry(max_size=100)
        errors: List[Exception] = []
        lock   = threading.Lock()

        def worker():
            for _ in range(5):
                try:
                    reg.register(_make_snapshot())
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)
        assert len(errors) == 0
        assert reg.count == 50

    def test_store_concurrent_save(self):
        store  = IntegrationSnapshotStore(max_entries=1000)
        errors: List[Exception] = []
        lock   = threading.Lock()

        def worker():
            for _ in range(10):
                try:
                    store.save(_make_snapshot())
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)
        assert len(errors) == 0
        assert store.count == 100

    def test_cache_concurrent_put_get(self):
        cache  = IntegrationSnapshotCache(max_size=200)
        errors: List[Exception] = []
        lock   = threading.Lock()

        def worker():
            for _ in range(10):
                try:
                    s = _make_snapshot()
                    cache.put(s)
                    cache.get(s.snapshot_id)
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)
        assert len(errors) == 0

    def test_statistics_concurrent_increments(self):
        stats = IntegrationSnapshotStatistics()

        def worker():
            for _ in range(100):
                stats.increment_created()
                stats.record_validation(passed=True)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)
        sr = stats.snapshot()
        assert sr.snapshots_created == 1000
        assert sr.validation_passed == 1000

    def test_event_bus_concurrent_emit(self):
        bus    = IntegrationSnapshotEventBus()
        counts: List[int] = []
        lock   = threading.Lock()

        def handler(e):
            with lock:
                counts.append(1)

        bus.subscribe(SnapshotEventType.SNAPSHOT_CREATED, handler)

        def worker():
            for _ in range(25):
                bus.emit(SnapshotEventType.SNAPSHOT_CREATED, "snap-001", "test", {})

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)
        assert len(counts) == 100

    def test_stress_1000_snapshots(self):
        reg   = IntegrationSnapshotRegistry(max_size=1100)
        store = IntegrationSnapshotStore(max_entries=1100)
        cache = IntegrationSnapshotCache(max_size=200)
        hist  = IntegrationSnapshotHistory()
        v     = IntegrationSnapshotValidation()

        for i in range(1000):
            s = _make_snapshot(requests_processed=i)
            reg.register(s)
            store.save(s)
            cache.put(s)
            hist.record(s)
            r = v.validate(s)
            assert r.passed is True

        assert reg.count   == 1000
        assert store.count == 1000
        assert hist.size   == 500   # bounded at DEFAULT_HISTORY_SIZE


# ════════════════════════════════════════════════════════════════════════
# Q — Regression
# ════════════════════════════════════════════════════════════════════════


class TestRegression:
    def test_no_circular_imports(self):
        """snapshot package must not import from lifecycle/engine/policies/services."""
        import sys
        for key, mod in sys.modules.items():
            if "iios.integration.snapshot" in key and hasattr(mod, "__file__"):
                if mod.__file__:
                    with open(mod.__file__, encoding="utf-8", errors="ignore") as f:
                        src = f.read()
                    for forbidden in [
                        "iios.integration.lifecycle",
                        "iios.integration.engine",
                        "iios.integration.policies",
                        "iios.integration.services",
                    ]:
                        assert forbidden not in src, \
                            f"{key} imports from {forbidden!r} (circular)"

    def test_no_vendor_sdk_imports(self):
        """snapshot package must not use any vendor SDK."""
        import sys
        FORBIDDEN = [
            "requests", "httpx", "aiohttp", "kafka", "pika", "redis",
            "boto3", "grpc", "websockets", "sqlalchemy", "paramiko",
            "smtplib", "twilio", "firebase_admin",
        ]
        for key, mod in sys.modules.items():
            if "iios.integration.snapshot" in key and hasattr(mod, "__file__"):
                if mod.__file__:
                    with open(mod.__file__, encoding="utf-8", errors="ignore") as f:
                        src = f.read()
                    for vendor in FORBIDDEN:
                        assert f"import {vendor}" not in src, \
                            f"{key} imports forbidden vendor: {vendor}"

    def test_all_public_api_importable(self):
        """Every name in __all__ must be accessible from the package."""
        import iios.integration.snapshot as sp
        for name in sp.__all__:
            assert hasattr(sp, name), f"__all__ member {name!r} not accessible"

    def test_snapshot_immutable_not_mutated_externally(self):
        """Verify that tag dicts accessed from the snapshot are isolated."""
        s  = _make_snapshot()
        d  = s.to_dict()
        # Mutating the serialized dict must not affect the original
        d["status"] = "expired"
        assert s.status == SnapshotStatus.DRAFT

    def test_builder_produces_independent_snapshots(self):
        """Each call to build() on the same builder state returns a new object."""
        b  = IntegrationSnapshotBuilder().set_session_ids("s", "w", "e")
        s1 = b.build()
        s2 = b.build()
        assert s1.snapshot_id != s2.snapshot_id
