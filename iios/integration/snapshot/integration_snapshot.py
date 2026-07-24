"""
integration_snapshot.py — iios.integration.snapshot
-----------------------------------------------------
IntegrationSnapshot — immutable, versioned, canonical published
representation of Enterprise Integration & Connectivity.

Consolidates validated outputs from:
  - Integration Lifecycle  (M1)
  - Integration Engine     (M2)
  - Integration Governance Policy Framework (M3)
  - Integration Services Framework (M4)

Performs NO lifecycle management, NO orchestration,
NO governance evaluation, NO protocol execution.

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

from .constants import (
    SNAPSHOT_ID_PREFIX,
    SNAPSHOT_VERSION,
    FRAMEWORK_VERSION,
    ConnectivityState,
    GovernanceState,
    LifecycleState,
    SnapshotIntegrationType,
    SnapshotScope,
    SnapshotStatus,
)
from .integration_snapshot_metadata import SnapshotMetadata

_log = get_logger(__name__)


# ════════════════════════════════════════════════════════════════════════
# Summary sub-objects (all frozen)
# ════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ConnectivitySummary:
    """Connectivity-layer summary captured in the snapshot."""
    active_integrations:     int
    registered_connectors:   int
    registered_adapters:     int
    protocols_enabled:       int
    connection_pool_status:  str        # "healthy" | "degraded" | "exhausted" | "unknown"
    authentication_status:   str        # "active" | "inactive" | "unknown"
    authorization_status:    str        # "active" | "inactive" | "unknown"
    security_status:         str        # "secure" | "at_risk" | "unknown"
    compliance_status:       str        # "compliant" | "non_compliant" | "unknown"
    overall_integration_health: str     # "healthy" | "degraded" | "unhealthy" | "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_integrations":        self.active_integrations,
            "registered_connectors":      self.registered_connectors,
            "registered_adapters":        self.registered_adapters,
            "protocols_enabled":          self.protocols_enabled,
            "connection_pool_status":     self.connection_pool_status,
            "authentication_status":      self.authentication_status,
            "authorization_status":       self.authorization_status,
            "security_status":            self.security_status,
            "compliance_status":          self.compliance_status,
            "overall_integration_health": self.overall_integration_health,
        }

    @classmethod
    def default(cls) -> "ConnectivitySummary":
        return cls(
            active_integrations        = 0,
            registered_connectors      = 0,
            registered_adapters        = 0,
            protocols_enabled          = 0,
            connection_pool_status     = "unknown",
            authentication_status      = "unknown",
            authorization_status       = "unknown",
            security_status            = "unknown",
            compliance_status          = "unknown",
            overall_integration_health = "unknown",
        )


@dataclass(frozen=True)
class ConnectorSummary:
    """Connector-layer summary captured in the snapshot."""
    connector_count:       int
    connector_types:       Tuple[str, ...]
    connector_availability: float           # 0.0 – 1.0
    connector_health:      str             # "healthy" | "degraded" | "unhealthy" | "unknown"
    connector_versions:    Dict[str, str]  # connector_name → version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connector_count":        self.connector_count,
            "connector_types":        list(self.connector_types),
            "connector_availability": round(self.connector_availability, 4),
            "connector_health":       self.connector_health,
            "connector_versions":     dict(self.connector_versions),
        }

    @classmethod
    def default(cls) -> "ConnectorSummary":
        return cls(
            connector_count        = 0,
            connector_types        = (),
            connector_availability = 0.0,
            connector_health       = "unknown",
            connector_versions     = {},
        )


@dataclass(frozen=True)
class AdapterSummary:
    """Adapter-layer summary captured in the snapshot."""
    adapter_count:       int
    adapter_types:       Tuple[str, ...]
    adapter_versions:    Dict[str, str]    # adapter_name → version
    compatibility_status: str             # "compatible" | "partial" | "incompatible" | "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_count":       self.adapter_count,
            "adapter_types":       list(self.adapter_types),
            "adapter_versions":    dict(self.adapter_versions),
            "compatibility_status": self.compatibility_status,
        }

    @classmethod
    def default(cls) -> "AdapterSummary":
        return cls(
            adapter_count        = 0,
            adapter_types        = (),
            adapter_versions     = {},
            compatibility_status = "unknown",
        )


@dataclass(frozen=True)
class ProtocolSummary:
    """Protocol-layer summary captured in the snapshot."""
    rest:               str     # "enabled" | "disabled" | "unknown"
    graphql:            str
    grpc:               str
    websocket:          str
    kafka:              str
    rabbitmq:           str
    redis_streams:      str
    database_connectors: str
    webhook_services:   str
    file_transfer:      str
    protocol_health:    str     # overall protocol health

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rest":                self.rest,
            "graphql":             self.graphql,
            "grpc":                self.grpc,
            "websocket":           self.websocket,
            "kafka":               self.kafka,
            "rabbitmq":            self.rabbitmq,
            "redis_streams":       self.redis_streams,
            "database_connectors": self.database_connectors,
            "webhook_services":    self.webhook_services,
            "file_transfer":       self.file_transfer,
            "protocol_health":     self.protocol_health,
        }

    @classmethod
    def default(cls) -> "ProtocolSummary":
        return cls(
            rest                = "unknown",
            graphql             = "unknown",
            grpc                = "unknown",
            websocket           = "unknown",
            kafka               = "unknown",
            rabbitmq            = "unknown",
            redis_streams       = "unknown",
            database_connectors = "unknown",
            webhook_services    = "unknown",
            file_transfer       = "unknown",
            protocol_health     = "unknown",
        )


@dataclass(frozen=True)
class ServiceSummary:
    """Service-layer metrics captured in the snapshot."""
    requests_processed:  int
    responses_received:  int
    messages_published:  int
    messages_consumed:   int
    events_processed:    int
    retries:             int
    failures:            int
    average_latency_ms:  float
    throughput_rps:      float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_processed": self.requests_processed,
            "responses_received": self.responses_received,
            "messages_published": self.messages_published,
            "messages_consumed":  self.messages_consumed,
            "events_processed":   self.events_processed,
            "retries":            self.retries,
            "failures":           self.failures,
            "average_latency_ms": round(self.average_latency_ms, 3),
            "throughput_rps":     round(self.throughput_rps, 3),
        }

    @classmethod
    def default(cls) -> "ServiceSummary":
        return cls(
            requests_processed = 0,
            responses_received = 0,
            messages_published = 0,
            messages_consumed  = 0,
            events_processed   = 0,
            retries            = 0,
            failures           = 0,
            average_latency_ms = 0.0,
            throughput_rps     = 0.0,
        )


@dataclass(frozen=True)
class SecuritySummary:
    """Security-layer summary captured in the snapshot."""
    authentication_providers: int
    authorization_providers:  int
    certificates:             int
    secrets:                  int
    encryption_status:        str    # "enabled" | "disabled" | "partial" | "unknown"
    credential_health:        str    # "healthy" | "degraded" | "unhealthy" | "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authentication_providers": self.authentication_providers,
            "authorization_providers":  self.authorization_providers,
            "certificates":             self.certificates,
            "secrets":                  self.secrets,
            "encryption_status":        self.encryption_status,
            "credential_health":        self.credential_health,
        }

    @classmethod
    def default(cls) -> "SecuritySummary":
        return cls(
            authentication_providers = 0,
            authorization_providers  = 0,
            certificates             = 0,
            secrets                  = 0,
            encryption_status        = "unknown",
            credential_health        = "unknown",
        )


@dataclass(frozen=True)
class AuditSummary:
    """Governance and audit information captured in the snapshot."""
    governance_version:         str
    connector_registry_version: str
    protocol_registry_version:  str
    validation_summary:         str     # human-readable outcome
    audit_trail:                Tuple[str, ...]  # ordered audit events

    def to_dict(self) -> Dict[str, Any]:
        return {
            "governance_version":         self.governance_version,
            "connector_registry_version": self.connector_registry_version,
            "protocol_registry_version":  self.protocol_registry_version,
            "validation_summary":         self.validation_summary,
            "audit_trail":                list(self.audit_trail),
        }

    @classmethod
    def default(cls) -> "AuditSummary":
        return cls(
            governance_version         = "1.0.0",
            connector_registry_version = "1.0.0",
            protocol_registry_version  = "1.0.0",
            validation_summary         = "not validated",
            audit_trail                = (),
        )


@dataclass(frozen=True)
class SnapshotStatisticsSummary:
    """Performance and sizing statistics for the snapshot itself."""
    processing_duration_ms: float
    snapshot_size_bytes:     int
    connector_count:         int
    adapter_count:           int
    protocol_count:          int
    connection_count:        int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "processing_duration_ms": round(self.processing_duration_ms, 3),
            "snapshot_size_bytes":    self.snapshot_size_bytes,
            "connector_count":        self.connector_count,
            "adapter_count":          self.adapter_count,
            "protocol_count":         self.protocol_count,
            "connection_count":       self.connection_count,
        }

    @classmethod
    def default(cls) -> "SnapshotStatisticsSummary":
        return cls(
            processing_duration_ms = 0.0,
            snapshot_size_bytes    = 0,
            connector_count        = 0,
            adapter_count          = 0,
            protocol_count         = 0,
            connection_count       = 0,
        )


# ════════════════════════════════════════════════════════════════════════
# IntegrationSnapshot
# ════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class IntegrationSnapshot:
    """
    Immutable, versioned, canonical published representation of
    Enterprise Integration & Connectivity.

    This is the ONLY published representation.  All downstream IIOS
    components MUST consume IntegrationSnapshot rather than directly
    accessing M1/M2/M3/M4 subsystems.

    Responsibilities
    ----------------
    - Aggregate subsystem outputs (read-only)
    - Carry all connectivity, connector, adapter, protocol, service,
      security, audit, and statistics summaries
    - Remain fully immutable after creation
    - Support serialization to/from dict
    """

    # ── Core identifiers ─────────────────────────────────────────────
    snapshot_id:              str
    integration_session_id:   str
    integration_workflow_id:  str
    enterprise_session_id:    str

    # ── Version information ──────────────────────────────────────────
    integration_version: str
    framework_version:   str
    snapshot_version:    str

    # ── Scope and classification ─────────────────────────────────────
    integration_scope: SnapshotScope
    integration_type:  SnapshotIntegrationType

    # ── State at time of snapshot ────────────────────────────────────
    lifecycle_state:   LifecycleState
    governance_state:  GovernanceState
    connectivity_state: ConnectivityState
    status:            SnapshotStatus

    # ── Timestamps ───────────────────────────────────────────────────
    snapshot_timestamp: str     # ISO-8601 UTC — when the data was captured
    created_at:         str     # ISO-8601 UTC — when the object was created
    updated_at:         str     # ISO-8601 UTC — when the object was last versioned

    # ── Content summaries ────────────────────────────────────────────
    connectivity_summary:    ConnectivitySummary
    connector_summary:       ConnectorSummary
    adapter_summary:         AdapterSummary
    protocol_summary:        ProtocolSummary
    service_summary:         ServiceSummary
    security_summary:        SecuritySummary
    audit_summary:           AuditSummary
    statistics_summary:      SnapshotStatisticsSummary
    metadata:                SnapshotMetadata

    # ── Factory ──────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        *,
        integration_session_id:  str,
        integration_workflow_id: str,
        enterprise_session_id:   str,
        integration_version:     str                        = "1.0.0",
        framework_version:       str                        = FRAMEWORK_VERSION,
        snapshot_version:        str                        = SNAPSHOT_VERSION,
        integration_scope:       SnapshotScope              = SnapshotScope.ENTERPRISE,
        integration_type:        SnapshotIntegrationType    = SnapshotIntegrationType.FULL,
        lifecycle_state:         LifecycleState             = LifecycleState.ACTIVE,
        governance_state:        GovernanceState            = GovernanceState.UNKNOWN,
        connectivity_state:      ConnectivityState          = ConnectivityState.UNKNOWN,
        status:                  SnapshotStatus             = SnapshotStatus.DRAFT,
        snapshot_timestamp:      Optional[str]              = None,
        connectivity_summary:    Optional[ConnectivitySummary]       = None,
        connector_summary:       Optional[ConnectorSummary]          = None,
        adapter_summary:         Optional[AdapterSummary]            = None,
        protocol_summary:        Optional[ProtocolSummary]           = None,
        service_summary:         Optional[ServiceSummary]            = None,
        security_summary:        Optional[SecuritySummary]           = None,
        audit_summary:           Optional[AuditSummary]              = None,
        statistics_summary:      Optional[SnapshotStatisticsSummary] = None,
        metadata:                Optional[SnapshotMetadata]          = None,
        snapshot_id:             Optional[str]              = None,
    ) -> "IntegrationSnapshot":
        """Create an IntegrationSnapshot with defaults for missing fields."""
        now = datetime.now(tz=timezone.utc).isoformat()
        sid = snapshot_id or f"{SNAPSHOT_ID_PREFIX}{uuid.uuid4().hex[:12]}"
        return cls(
            snapshot_id             = sid,
            integration_session_id  = integration_session_id,
            integration_workflow_id = integration_workflow_id,
            enterprise_session_id   = enterprise_session_id,
            integration_version     = integration_version,
            framework_version       = framework_version,
            snapshot_version        = snapshot_version,
            integration_scope       = integration_scope,
            integration_type        = integration_type,
            lifecycle_state         = lifecycle_state,
            governance_state        = governance_state,
            connectivity_state      = connectivity_state,
            status                  = status,
            snapshot_timestamp      = snapshot_timestamp or now,
            created_at              = now,
            updated_at              = now,
            connectivity_summary    = connectivity_summary    or ConnectivitySummary.default(),
            connector_summary       = connector_summary       or ConnectorSummary.default(),
            adapter_summary         = adapter_summary         or AdapterSummary.default(),
            protocol_summary        = protocol_summary        or ProtocolSummary.default(),
            service_summary         = service_summary         or ServiceSummary.default(),
            security_summary        = security_summary        or SecuritySummary.default(),
            audit_summary           = audit_summary           or AuditSummary.default(),
            statistics_summary      = statistics_summary      or SnapshotStatisticsSummary.default(),
            metadata                = metadata                or SnapshotMetadata.create(),
        )

    # ── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the snapshot to a JSON-safe dict."""
        return {
            "snapshot_id":              self.snapshot_id,
            "integration_session_id":   self.integration_session_id,
            "integration_workflow_id":  self.integration_workflow_id,
            "enterprise_session_id":    self.enterprise_session_id,
            "integration_version":      self.integration_version,
            "framework_version":        self.framework_version,
            "snapshot_version":         self.snapshot_version,
            "integration_scope":        self.integration_scope.value,
            "integration_type":         self.integration_type.value,
            "lifecycle_state":          self.lifecycle_state.value,
            "governance_state":         self.governance_state.value,
            "connectivity_state":       self.connectivity_state.value,
            "status":                   self.status.value,
            "snapshot_timestamp":       self.snapshot_timestamp,
            "created_at":               self.created_at,
            "updated_at":               self.updated_at,
            "connectivity_summary":     self.connectivity_summary.to_dict(),
            "connector_summary":        self.connector_summary.to_dict(),
            "adapter_summary":          self.adapter_summary.to_dict(),
            "protocol_summary":         self.protocol_summary.to_dict(),
            "service_summary":          self.service_summary.to_dict(),
            "security_summary":         self.security_summary.to_dict(),
            "audit_summary":            self.audit_summary.to_dict(),
            "statistics_summary":       self.statistics_summary.to_dict(),
            "metadata":                 self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IntegrationSnapshot":
        """Deserialize a snapshot from a dict (reverse of to_dict)."""
        return cls(
            snapshot_id             = d["snapshot_id"],
            integration_session_id  = d["integration_session_id"],
            integration_workflow_id = d["integration_workflow_id"],
            enterprise_session_id   = d["enterprise_session_id"],
            integration_version     = d.get("integration_version", "1.0.0"),
            framework_version       = d.get("framework_version", FRAMEWORK_VERSION),
            snapshot_version        = d.get("snapshot_version", SNAPSHOT_VERSION),
            integration_scope       = SnapshotScope(d.get("integration_scope", "enterprise")),
            integration_type        = SnapshotIntegrationType(d.get("integration_type", "full")),
            lifecycle_state         = LifecycleState(d.get("lifecycle_state", "unknown")),
            governance_state        = GovernanceState(d.get("governance_state", "unknown")),
            connectivity_state      = ConnectivityState(d.get("connectivity_state", "unknown")),
            status                  = SnapshotStatus(d.get("status", "draft")),
            snapshot_timestamp      = d.get("snapshot_timestamp", ""),
            created_at              = d.get("created_at", ""),
            updated_at              = d.get("updated_at", ""),
            connectivity_summary    = _connectivity_from_dict(d.get("connectivity_summary", {})),
            connector_summary       = _connector_from_dict(d.get("connector_summary", {})),
            adapter_summary         = _adapter_from_dict(d.get("adapter_summary", {})),
            protocol_summary        = _protocol_from_dict(d.get("protocol_summary", {})),
            service_summary         = _service_from_dict(d.get("service_summary", {})),
            security_summary        = _security_from_dict(d.get("security_summary", {})),
            audit_summary           = _audit_from_dict(d.get("audit_summary", {})),
            statistics_summary      = _stats_from_dict(d.get("statistics_summary", {})),
            metadata                = SnapshotMetadata.from_dict(d.get("metadata", {})),
        )


# ════════════════════════════════════════════════════════════════════════
# Private deserialization helpers
# ════════════════════════════════════════════════════════════════════════


def _connectivity_from_dict(d: Dict[str, Any]) -> ConnectivitySummary:
    if not d:
        return ConnectivitySummary.default()
    return ConnectivitySummary(
        active_integrations        = d.get("active_integrations",        0),
        registered_connectors      = d.get("registered_connectors",      0),
        registered_adapters        = d.get("registered_adapters",        0),
        protocols_enabled          = d.get("protocols_enabled",          0),
        connection_pool_status     = d.get("connection_pool_status",     "unknown"),
        authentication_status      = d.get("authentication_status",      "unknown"),
        authorization_status       = d.get("authorization_status",       "unknown"),
        security_status            = d.get("security_status",            "unknown"),
        compliance_status          = d.get("compliance_status",          "unknown"),
        overall_integration_health = d.get("overall_integration_health", "unknown"),
    )


def _connector_from_dict(d: Dict[str, Any]) -> ConnectorSummary:
    if not d:
        return ConnectorSummary.default()
    return ConnectorSummary(
        connector_count        = d.get("connector_count",        0),
        connector_types        = tuple(d.get("connector_types",  [])),
        connector_availability = d.get("connector_availability", 0.0),
        connector_health       = d.get("connector_health",       "unknown"),
        connector_versions     = dict(d.get("connector_versions", {})),
    )


def _adapter_from_dict(d: Dict[str, Any]) -> AdapterSummary:
    if not d:
        return AdapterSummary.default()
    return AdapterSummary(
        adapter_count        = d.get("adapter_count",        0),
        adapter_types        = tuple(d.get("adapter_types",  [])),
        adapter_versions     = dict(d.get("adapter_versions", {})),
        compatibility_status = d.get("compatibility_status", "unknown"),
    )


def _protocol_from_dict(d: Dict[str, Any]) -> ProtocolSummary:
    if not d:
        return ProtocolSummary.default()
    return ProtocolSummary(
        rest                = d.get("rest",                "unknown"),
        graphql             = d.get("graphql",             "unknown"),
        grpc                = d.get("grpc",                "unknown"),
        websocket           = d.get("websocket",           "unknown"),
        kafka               = d.get("kafka",               "unknown"),
        rabbitmq            = d.get("rabbitmq",            "unknown"),
        redis_streams       = d.get("redis_streams",       "unknown"),
        database_connectors = d.get("database_connectors", "unknown"),
        webhook_services    = d.get("webhook_services",    "unknown"),
        file_transfer       = d.get("file_transfer",       "unknown"),
        protocol_health     = d.get("protocol_health",     "unknown"),
    )


def _service_from_dict(d: Dict[str, Any]) -> ServiceSummary:
    if not d:
        return ServiceSummary.default()
    return ServiceSummary(
        requests_processed = d.get("requests_processed", 0),
        responses_received = d.get("responses_received", 0),
        messages_published = d.get("messages_published", 0),
        messages_consumed  = d.get("messages_consumed",  0),
        events_processed   = d.get("events_processed",   0),
        retries            = d.get("retries",            0),
        failures           = d.get("failures",           0),
        average_latency_ms = d.get("average_latency_ms", 0.0),
        throughput_rps     = d.get("throughput_rps",     0.0),
    )


def _security_from_dict(d: Dict[str, Any]) -> SecuritySummary:
    if not d:
        return SecuritySummary.default()
    return SecuritySummary(
        authentication_providers = d.get("authentication_providers", 0),
        authorization_providers  = d.get("authorization_providers",  0),
        certificates             = d.get("certificates",             0),
        secrets                  = d.get("secrets",                  0),
        encryption_status        = d.get("encryption_status",        "unknown"),
        credential_health        = d.get("credential_health",        "unknown"),
    )


def _audit_from_dict(d: Dict[str, Any]) -> AuditSummary:
    if not d:
        return AuditSummary.default()
    return AuditSummary(
        governance_version         = d.get("governance_version",         "1.0.0"),
        connector_registry_version = d.get("connector_registry_version", "1.0.0"),
        protocol_registry_version  = d.get("protocol_registry_version",  "1.0.0"),
        validation_summary         = d.get("validation_summary",         "not validated"),
        audit_trail                = tuple(d.get("audit_trail",          [])),
    )


def _stats_from_dict(d: Dict[str, Any]) -> SnapshotStatisticsSummary:
    if not d:
        return SnapshotStatisticsSummary.default()
    return SnapshotStatisticsSummary(
        processing_duration_ms = d.get("processing_duration_ms", 0.0),
        snapshot_size_bytes    = d.get("snapshot_size_bytes",    0),
        connector_count        = d.get("connector_count",        0),
        adapter_count          = d.get("adapter_count",          0),
        protocol_count         = d.get("protocol_count",         0),
        connection_count       = d.get("connection_count",       0),
    )
