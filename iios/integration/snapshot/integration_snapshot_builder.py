"""
integration_snapshot_builder.py — iios.integration.snapshot
-------------------------------------------------------------
IntegrationSnapshotBuilder — fluent, mutable builder that produces
an immutable IntegrationSnapshot.

Usage
-----
    snapshot = (
        IntegrationSnapshotBuilder()
        .set_session_ids(session_id, workflow_id, enterprise_id)
        .set_scope(SnapshotScope.ENTERPRISE, SnapshotIntegrationType.FULL)
        .set_lifecycle_state(LifecycleState.ACTIVE)
        .set_governance_state(GovernanceState.COMPLIANT)
        .set_connectivity_state(ConnectivityState.CONNECTED)
        .set_connectivity_summary(active_integrations=5, ...)
        .set_service_summary(requests_processed=1000, ...)
        .build()
    )

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    FRAMEWORK_VERSION,
    SNAPSHOT_ID_PREFIX,
    SNAPSHOT_VERSION,
    ConnectivityState,
    GovernanceState,
    LifecycleState,
    SnapshotIntegrationType,
    SnapshotScope,
    SnapshotStatus,
)
from .exceptions import SnapshotBuildError
from .integration_snapshot import (
    AdapterSummary,
    AuditSummary,
    ConnectivitySummary,
    ConnectorSummary,
    IntegrationSnapshot,
    ProtocolSummary,
    SecuritySummary,
    ServiceSummary,
    SnapshotStatisticsSummary,
)
from .integration_snapshot_metadata import SnapshotMetadata

_log = get_logger(__name__)


class IntegrationSnapshotBuilder:
    """
    Fluent builder for IntegrationSnapshot.

    Mutable during construction; produces an immutable snapshot
    via .build().  Raises SnapshotBuildError if required fields
    are missing.
    """

    def __init__(self) -> None:
        self._snapshot_id:              Optional[str]                       = None
        self._integration_session_id:   Optional[str]                       = None
        self._integration_workflow_id:  Optional[str]                       = None
        self._enterprise_session_id:    Optional[str]                       = None
        self._integration_version:      str                                 = "1.0.0"
        self._framework_version:        str                                 = FRAMEWORK_VERSION
        self._snapshot_version:         str                                 = SNAPSHOT_VERSION
        self._integration_scope:        SnapshotScope                       = SnapshotScope.ENTERPRISE
        self._integration_type:         SnapshotIntegrationType             = SnapshotIntegrationType.FULL
        self._lifecycle_state:          LifecycleState                      = LifecycleState.ACTIVE
        self._governance_state:         GovernanceState                     = GovernanceState.UNKNOWN
        self._connectivity_state:       ConnectivityState                   = ConnectivityState.UNKNOWN
        self._status:                   SnapshotStatus                      = SnapshotStatus.DRAFT
        self._snapshot_timestamp:       Optional[str]                       = None
        self._connectivity_summary:     ConnectivitySummary                 = ConnectivitySummary.default()
        self._connector_summary:        ConnectorSummary                    = ConnectorSummary.default()
        self._adapter_summary:          AdapterSummary                      = AdapterSummary.default()
        self._protocol_summary:         ProtocolSummary                     = ProtocolSummary.default()
        self._service_summary:          ServiceSummary                      = ServiceSummary.default()
        self._security_summary:         SecuritySummary                     = SecuritySummary.default()
        self._audit_summary:            AuditSummary                        = AuditSummary.default()
        self._statistics_summary:       SnapshotStatisticsSummary           = SnapshotStatisticsSummary.default()
        self._metadata:                 SnapshotMetadata                    = SnapshotMetadata.create()
        self._build_start_ns:           float                               = time.monotonic()

    # ── Session / ID setters ─────────────────────────────────────────

    def set_snapshot_id(self, snapshot_id: str) -> "IntegrationSnapshotBuilder":
        self._snapshot_id = snapshot_id
        return self

    def set_session_ids(
        self,
        integration_session_id:  str,
        integration_workflow_id: str,
        enterprise_session_id:   str,
    ) -> "IntegrationSnapshotBuilder":
        self._integration_session_id  = integration_session_id
        self._integration_workflow_id = integration_workflow_id
        self._enterprise_session_id   = enterprise_session_id
        return self

    # ── Version setters ───────────────────────────────────────────────

    def set_versions(
        self,
        *,
        integration_version: str,
        framework_version:   str = FRAMEWORK_VERSION,
        snapshot_version:    str = SNAPSHOT_VERSION,
    ) -> "IntegrationSnapshotBuilder":
        self._integration_version = integration_version
        self._framework_version   = framework_version
        self._snapshot_version    = snapshot_version
        return self

    # ── Scope / Classification setters ───────────────────────────────

    def set_scope(
        self,
        scope:            SnapshotScope,
        integration_type: SnapshotIntegrationType = SnapshotIntegrationType.FULL,
    ) -> "IntegrationSnapshotBuilder":
        self._integration_scope = scope
        self._integration_type  = integration_type
        return self

    # ── State setters ─────────────────────────────────────────────────

    def set_lifecycle_state(
        self, state: LifecycleState
    ) -> "IntegrationSnapshotBuilder":
        self._lifecycle_state = state
        return self

    def set_governance_state(
        self, state: GovernanceState
    ) -> "IntegrationSnapshotBuilder":
        self._governance_state = state
        return self

    def set_connectivity_state(
        self, state: ConnectivityState
    ) -> "IntegrationSnapshotBuilder":
        self._connectivity_state = state
        return self

    def set_status(self, status: SnapshotStatus) -> "IntegrationSnapshotBuilder":
        self._status = status
        return self

    def set_snapshot_timestamp(self, ts: str) -> "IntegrationSnapshotBuilder":
        self._snapshot_timestamp = ts
        return self

    # ── Summary setters ───────────────────────────────────────────────

    def set_connectivity_summary(
        self,
        *,
        active_integrations:        int   = 0,
        registered_connectors:      int   = 0,
        registered_adapters:        int   = 0,
        protocols_enabled:          int   = 0,
        connection_pool_status:     str   = "unknown",
        authentication_status:      str   = "unknown",
        authorization_status:       str   = "unknown",
        security_status:            str   = "unknown",
        compliance_status:          str   = "unknown",
        overall_integration_health: str   = "unknown",
    ) -> "IntegrationSnapshotBuilder":
        self._connectivity_summary = ConnectivitySummary(
            active_integrations        = active_integrations,
            registered_connectors      = registered_connectors,
            registered_adapters        = registered_adapters,
            protocols_enabled          = protocols_enabled,
            connection_pool_status     = connection_pool_status,
            authentication_status      = authentication_status,
            authorization_status       = authorization_status,
            security_status            = security_status,
            compliance_status          = compliance_status,
            overall_integration_health = overall_integration_health,
        )
        return self

    def set_connector_summary(
        self,
        *,
        connector_count:        int   = 0,
        connector_types:        Optional[List[str]] = None,
        connector_availability: float = 1.0,
        connector_health:       str   = "healthy",
        connector_versions:     Optional[Dict[str, str]] = None,
    ) -> "IntegrationSnapshotBuilder":
        self._connector_summary = ConnectorSummary(
            connector_count        = connector_count,
            connector_types        = tuple(connector_types or []),
            connector_availability = connector_availability,
            connector_health       = connector_health,
            connector_versions     = dict(connector_versions or {}),
        )
        return self

    def set_adapter_summary(
        self,
        *,
        adapter_count:        int   = 0,
        adapter_types:        Optional[List[str]] = None,
        adapter_versions:     Optional[Dict[str, str]] = None,
        compatibility_status: str   = "compatible",
    ) -> "IntegrationSnapshotBuilder":
        self._adapter_summary = AdapterSummary(
            adapter_count        = adapter_count,
            adapter_types        = tuple(adapter_types or []),
            adapter_versions     = dict(adapter_versions or {}),
            compatibility_status = compatibility_status,
        )
        return self

    def set_protocol_summary(
        self,
        *,
        rest:                str = "enabled",
        graphql:             str = "enabled",
        grpc:                str = "enabled",
        websocket:           str = "enabled",
        kafka:               str = "enabled",
        rabbitmq:            str = "enabled",
        redis_streams:       str = "enabled",
        database_connectors: str = "enabled",
        webhook_services:    str = "enabled",
        file_transfer:       str = "enabled",
        protocol_health:     str = "healthy",
    ) -> "IntegrationSnapshotBuilder":
        self._protocol_summary = ProtocolSummary(
            rest                = rest,
            graphql             = graphql,
            grpc                = grpc,
            websocket           = websocket,
            kafka               = kafka,
            rabbitmq            = rabbitmq,
            redis_streams       = redis_streams,
            database_connectors = database_connectors,
            webhook_services    = webhook_services,
            file_transfer       = file_transfer,
            protocol_health     = protocol_health,
        )
        return self

    def set_service_summary(
        self,
        *,
        requests_processed:  int   = 0,
        responses_received:  int   = 0,
        messages_published:  int   = 0,
        messages_consumed:   int   = 0,
        events_processed:    int   = 0,
        retries:             int   = 0,
        failures:            int   = 0,
        average_latency_ms:  float = 0.0,
        throughput_rps:      float = 0.0,
    ) -> "IntegrationSnapshotBuilder":
        self._service_summary = ServiceSummary(
            requests_processed = requests_processed,
            responses_received = responses_received,
            messages_published = messages_published,
            messages_consumed  = messages_consumed,
            events_processed   = events_processed,
            retries            = retries,
            failures           = failures,
            average_latency_ms = average_latency_ms,
            throughput_rps     = throughput_rps,
        )
        return self

    def set_security_summary(
        self,
        *,
        authentication_providers: int   = 0,
        authorization_providers:  int   = 0,
        certificates:             int   = 0,
        secrets:                  int   = 0,
        encryption_status:        str   = "enabled",
        credential_health:        str   = "healthy",
    ) -> "IntegrationSnapshotBuilder":
        self._security_summary = SecuritySummary(
            authentication_providers = authentication_providers,
            authorization_providers  = authorization_providers,
            certificates             = certificates,
            secrets                  = secrets,
            encryption_status        = encryption_status,
            credential_health        = credential_health,
        )
        return self

    def set_audit_summary(
        self,
        *,
        governance_version:         str = "1.0.0",
        connector_registry_version: str = "1.0.0",
        protocol_registry_version:  str = "1.0.0",
        validation_summary:         str = "passed",
        audit_trail:                Optional[List[str]] = None,
    ) -> "IntegrationSnapshotBuilder":
        self._audit_summary = AuditSummary(
            governance_version         = governance_version,
            connector_registry_version = connector_registry_version,
            protocol_registry_version  = protocol_registry_version,
            validation_summary         = validation_summary,
            audit_trail                = tuple(audit_trail or []),
        )
        return self

    def set_statistics_summary(
        self,
        *,
        processing_duration_ms: float = 0.0,
        snapshot_size_bytes:    int   = 0,
        connector_count:        int   = 0,
        adapter_count:          int   = 0,
        protocol_count:         int   = 0,
        connection_count:       int   = 0,
    ) -> "IntegrationSnapshotBuilder":
        self._statistics_summary = SnapshotStatisticsSummary(
            processing_duration_ms = processing_duration_ms,
            snapshot_size_bytes    = snapshot_size_bytes,
            connector_count        = connector_count,
            adapter_count          = adapter_count,
            protocol_count         = protocol_count,
            connection_count       = connection_count,
        )
        return self

    def set_metadata(self, metadata: SnapshotMetadata) -> "IntegrationSnapshotBuilder":
        self._metadata = metadata
        return self

    def set_metadata_fields(
        self,
        *,
        environment:       str                      = "production",
        framework_version: str                      = FRAMEWORK_VERSION,
        build_version:     str                      = "1.0.0",
        source_components: Optional[List[str]]      = None,
        correlation_ids:   Optional[List[str]]      = None,
        trace_ids:         Optional[List[str]]      = None,
        tags:              Optional[Dict[str, str]] = None,
    ) -> "IntegrationSnapshotBuilder":
        self._metadata = SnapshotMetadata.create(
            environment       = environment,
            framework_version = framework_version,
            build_version     = build_version,
            source_components = source_components,
            correlation_ids   = correlation_ids,
            trace_ids         = trace_ids,
            tags              = tags,
        )
        return self

    # ── Build ─────────────────────────────────────────────────────────

    def build(self) -> IntegrationSnapshot:
        """
        Validate all required fields and produce an immutable IntegrationSnapshot.

        Raises SnapshotBuildError if required fields are absent.
        """
        if not self._integration_session_id:
            raise SnapshotBuildError(
                "integration_session_id is required"
            )
        if not self._integration_workflow_id:
            raise SnapshotBuildError(
                "integration_workflow_id is required"
            )
        if not self._enterprise_session_id:
            raise SnapshotBuildError(
                "enterprise_session_id is required"
            )

        build_ms = (time.monotonic() - self._build_start_ns) * 1_000
        # Patch processing_duration into statistics if still default
        stats = self._statistics_summary
        if stats.processing_duration_ms == 0.0:
            stats = SnapshotStatisticsSummary(
                processing_duration_ms = build_ms,
                snapshot_size_bytes    = stats.snapshot_size_bytes,
                connector_count        = stats.connector_count,
                adapter_count          = stats.adapter_count,
                protocol_count         = stats.protocol_count,
                connection_count       = stats.connection_count,
            )

        snapshot_id = self._snapshot_id or f"{SNAPSHOT_ID_PREFIX}{uuid.uuid4().hex[:12]}"

        snapshot = IntegrationSnapshot.create(
            snapshot_id             = snapshot_id,
            integration_session_id  = self._integration_session_id,
            integration_workflow_id = self._integration_workflow_id,
            enterprise_session_id   = self._enterprise_session_id,
            integration_version     = self._integration_version,
            framework_version       = self._framework_version,
            snapshot_version        = self._snapshot_version,
            integration_scope       = self._integration_scope,
            integration_type        = self._integration_type,
            lifecycle_state         = self._lifecycle_state,
            governance_state        = self._governance_state,
            connectivity_state      = self._connectivity_state,
            status                  = self._status,
            snapshot_timestamp      = self._snapshot_timestamp,
            connectivity_summary    = self._connectivity_summary,
            connector_summary       = self._connector_summary,
            adapter_summary         = self._adapter_summary,
            protocol_summary        = self._protocol_summary,
            service_summary         = self._service_summary,
            security_summary        = self._security_summary,
            audit_summary           = self._audit_summary,
            statistics_summary      = stats,
            metadata                = self._metadata,
        )
        _log.info(f"IntegrationSnapshot built: {snapshot_id!r} status={self._status.value}")
        return snapshot
