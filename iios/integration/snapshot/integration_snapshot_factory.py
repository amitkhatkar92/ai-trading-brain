"""
integration_snapshot_factory.py — iios.integration.snapshot
-------------------------------------------------------------
IntegrationSnapshotFactory — static factory methods for creating
IntegrationSnapshot objects using common patterns.

All methods return fully built, immutable IntegrationSnapshot instances.
The factory uses IntegrationSnapshotBuilder internally.

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    FRAMEWORK_VERSION,
    SNAPSHOT_VERSION,
    ConnectivityState,
    GovernanceState,
    LifecycleState,
    SnapshotIntegrationType,
    SnapshotScope,
    SnapshotStatus,
)
from .exceptions import SnapshotBuildError, SnapshotSerializationError
from .integration_snapshot import IntegrationSnapshot
from .integration_snapshot_builder import IntegrationSnapshotBuilder
from .integration_snapshot_metadata import SnapshotMetadata

_log = get_logger(__name__)


class IntegrationSnapshotFactory:
    """
    Static factory for common IntegrationSnapshot creation patterns.

    No state. All methods are classmethods.
    """

    # ── Generic factory ───────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        *,
        integration_session_id:  str,
        integration_workflow_id: str,
        enterprise_session_id:   str,
        integration_scope:       SnapshotScope           = SnapshotScope.ENTERPRISE,
        integration_type:        SnapshotIntegrationType = SnapshotIntegrationType.FULL,
        lifecycle_state:         LifecycleState          = LifecycleState.ACTIVE,
        governance_state:        GovernanceState         = GovernanceState.COMPLIANT,
        connectivity_state:      ConnectivityState       = ConnectivityState.CONNECTED,
        status:                  SnapshotStatus          = SnapshotStatus.DRAFT,
        integration_version:     str                     = "1.0.0",
        tags:                    Optional[Dict[str, str]] = None,
    ) -> IntegrationSnapshot:
        """Create a generic snapshot with default summaries."""
        return (
            IntegrationSnapshotBuilder()
            .set_session_ids(
                integration_session_id,
                integration_workflow_id,
                enterprise_session_id,
            )
            .set_scope(integration_scope, integration_type)
            .set_lifecycle_state(lifecycle_state)
            .set_governance_state(governance_state)
            .set_connectivity_state(connectivity_state)
            .set_status(status)
            .set_versions(integration_version=integration_version)
            .set_metadata_fields(tags=tags)
            .build()
        )

    # ── Domain-specific factories ─────────────────────────────────────

    @classmethod
    def create_rest_snapshot(
        cls,
        *,
        integration_session_id:  str,
        integration_workflow_id: str,
        enterprise_session_id:   str,
        requests_processed:      int   = 0,
        average_latency_ms:      float = 0.0,
        connector_count:         int   = 1,
        tags:                    Optional[Dict[str, str]] = None,
    ) -> IntegrationSnapshot:
        """Create a REST-API-focused integration snapshot."""
        return (
            IntegrationSnapshotBuilder()
            .set_session_ids(
                integration_session_id,
                integration_workflow_id,
                enterprise_session_id,
            )
            .set_scope(SnapshotScope.ENTERPRISE, SnapshotIntegrationType.REST_API)
            .set_lifecycle_state(LifecycleState.ACTIVE)
            .set_governance_state(GovernanceState.COMPLIANT)
            .set_connectivity_state(ConnectivityState.CONNECTED)
            .set_status(SnapshotStatus.PUBLISHED)
            .set_connectivity_summary(
                active_integrations        = 1,
                registered_connectors      = connector_count,
                registered_adapters        = 1,
                protocols_enabled          = 1,
                connection_pool_status     = "healthy",
                authentication_status      = "active",
                authorization_status       = "active",
                security_status            = "secure",
                compliance_status          = "compliant",
                overall_integration_health = "healthy",
            )
            .set_connector_summary(
                connector_count        = connector_count,
                connector_types        = ["rest_api"],
                connector_availability = 1.0,
                connector_health       = "healthy",
            )
            .set_adapter_summary(
                adapter_count        = 1,
                adapter_types        = ["rest"],
                compatibility_status = "compatible",
            )
            .set_protocol_summary(
                rest            = "enabled",
                protocol_health = "healthy",
            )
            .set_service_summary(
                requests_processed = requests_processed,
                responses_received = requests_processed,
                average_latency_ms = average_latency_ms,
            )
            .set_metadata_fields(
                source_components = ["integration_services_engine"],
                tags              = tags,
            )
            .build()
        )

    @classmethod
    def create_messaging_snapshot(
        cls,
        *,
        integration_session_id:  str,
        integration_workflow_id: str,
        enterprise_session_id:   str,
        messages_published:      int   = 0,
        messages_consumed:       int   = 0,
        connector_count:         int   = 2,
        tags:                    Optional[Dict[str, str]] = None,
    ) -> IntegrationSnapshot:
        """Create a messaging-focused integration snapshot (Kafka/RabbitMQ/Redis)."""
        return (
            IntegrationSnapshotBuilder()
            .set_session_ids(
                integration_session_id,
                integration_workflow_id,
                enterprise_session_id,
            )
            .set_scope(SnapshotScope.ENTERPRISE, SnapshotIntegrationType.MESSAGING)
            .set_lifecycle_state(LifecycleState.ACTIVE)
            .set_governance_state(GovernanceState.COMPLIANT)
            .set_connectivity_state(ConnectivityState.CONNECTED)
            .set_status(SnapshotStatus.PUBLISHED)
            .set_connectivity_summary(
                active_integrations        = 1,
                registered_connectors      = connector_count,
                registered_adapters        = connector_count,
                protocols_enabled          = 3,
                connection_pool_status     = "healthy",
                authentication_status      = "active",
                authorization_status       = "active",
                security_status            = "secure",
                compliance_status          = "compliant",
                overall_integration_health = "healthy",
            )
            .set_connector_summary(
                connector_count        = connector_count,
                connector_types        = ["kafka", "rabbitmq", "redis_stream"],
                connector_availability = 1.0,
                connector_health       = "healthy",
            )
            .set_protocol_summary(
                kafka          = "enabled",
                rabbitmq       = "enabled",
                redis_streams  = "enabled",
                protocol_health= "healthy",
            )
            .set_service_summary(
                messages_published = messages_published,
                messages_consumed  = messages_consumed,
            )
            .set_metadata_fields(
                source_components = ["message_bus_engine"],
                tags              = tags,
            )
            .build()
        )

    @classmethod
    def create_enterprise_snapshot(
        cls,
        *,
        integration_session_id:  str,
        integration_workflow_id: str,
        enterprise_session_id:   str,
        connector_count:         int   = 5,
        adapter_count:           int   = 5,
        requests_processed:      int   = 0,
        messages_published:      int   = 0,
        authentication_providers: int  = 2,
        certificates:            int   = 0,
        secrets:                 int   = 0,
        tags:                    Optional[Dict[str, str]] = None,
    ) -> IntegrationSnapshot:
        """Create a full enterprise snapshot covering all integration layers."""
        return (
            IntegrationSnapshotBuilder()
            .set_session_ids(
                integration_session_id,
                integration_workflow_id,
                enterprise_session_id,
            )
            .set_scope(SnapshotScope.ENTERPRISE, SnapshotIntegrationType.ENTERPRISE)
            .set_lifecycle_state(LifecycleState.ACTIVE)
            .set_governance_state(GovernanceState.COMPLIANT)
            .set_connectivity_state(ConnectivityState.CONNECTED)
            .set_status(SnapshotStatus.PUBLISHED)
            .set_connectivity_summary(
                active_integrations        = connector_count,
                registered_connectors      = connector_count,
                registered_adapters        = adapter_count,
                protocols_enabled          = 10,
                connection_pool_status     = "healthy",
                authentication_status      = "active",
                authorization_status       = "active",
                security_status            = "secure",
                compliance_status          = "compliant",
                overall_integration_health = "healthy",
            )
            .set_connector_summary(
                connector_count        = connector_count,
                connector_types        = [
                    "rest_api", "kafka", "rabbitmq",
                    "database", "webhook",
                ],
                connector_availability = 1.0,
                connector_health       = "healthy",
            )
            .set_adapter_summary(
                adapter_count        = adapter_count,
                adapter_types        = ["rest", "kafka", "grpc", "database", "email"],
                compatibility_status = "compatible",
            )
            .set_protocol_summary(
                rest                = "enabled",
                graphql             = "enabled",
                grpc                = "enabled",
                websocket           = "enabled",
                kafka               = "enabled",
                rabbitmq            = "enabled",
                redis_streams       = "enabled",
                database_connectors = "enabled",
                webhook_services    = "enabled",
                file_transfer       = "enabled",
                protocol_health     = "healthy",
            )
            .set_service_summary(
                requests_processed = requests_processed,
                responses_received = requests_processed,
                messages_published = messages_published,
                messages_consumed  = messages_published,
            )
            .set_security_summary(
                authentication_providers = authentication_providers,
                authorization_providers  = 1,
                certificates             = certificates,
                secrets                  = secrets,
                encryption_status        = "enabled",
                credential_health        = "healthy",
            )
            .set_audit_summary(
                validation_summary = "all checks passed",
                audit_trail        = [
                    "connector_registry_validated",
                    "protocol_registry_validated",
                    "security_validated",
                ],
            )
            .set_metadata_fields(
                source_components = [
                    "integration_lifecycle",
                    "integration_engine",
                    "integration_policies",
                    "integration_services",
                ],
                tags = tags,
            )
            .build()
        )

    # ── Deserialization factory ────────────────────────────────────────

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> IntegrationSnapshot:
        """
        Deserialize an IntegrationSnapshot from a previously serialized dict.

        Raises SnapshotSerializationError on invalid input.
        """
        try:
            return IntegrationSnapshot.from_dict(d)
        except (KeyError, ValueError, TypeError) as exc:
            raise SnapshotSerializationError(
                f"Failed to deserialize snapshot: {exc}"
            ) from exc

    # ── Version bump factory ──────────────────────────────────────────

    @classmethod
    def bump_version(
        cls,
        snapshot:        IntegrationSnapshot,
        new_status:      SnapshotStatus   = SnapshotStatus.PUBLISHED,
        audit_entry:     Optional[str]    = None,
    ) -> IntegrationSnapshot:
        """
        Create a new snapshot from an existing one with updated status,
        updated_at, and an optional audit trail entry appended.

        The new snapshot receives a fresh snapshot_id.
        """
        from datetime import datetime, timezone
        import uuid

        old_d = snapshot.to_dict()
        new_id = f"snap-{uuid.uuid4().hex[:12]}"
        old_d["snapshot_id"] = new_id
        old_d["status"]      = new_status.value
        old_d["updated_at"]  = datetime.now(tz=timezone.utc).isoformat()

        # Append audit entry if provided
        if audit_entry:
            trail = list(old_d.get("audit_summary", {}).get("audit_trail", []))
            trail.append(audit_entry)
            old_d.setdefault("audit_summary", {})["audit_trail"] = trail

        _log.info(
            f"Snapshot version bumped: {snapshot.snapshot_id!r} "
            f"→ {new_id!r} status={new_status.value}"
        )
        return IntegrationSnapshot.from_dict(old_d)
