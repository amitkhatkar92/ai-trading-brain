# Integration Snapshot Guide

## Purpose

The `IntegrationSnapshot` is the single canonical published view of Enterprise
Integration & Connectivity state at a point in time.

## Snapshot content

### Core identifiers
| Field | Description |
|---|---|
| `snapshot_id` | Unique snapshot identifier (prefix `snap-`) |
| `integration_session_id` | Source integration session |
| `integration_workflow_id` | Source workflow |
| `enterprise_session_id` | Enterprise session context |

### Version information
| Field | Description |
|---|---|
| `integration_version` | Version of the integration being captured |
| `framework_version` | IIOS framework version |
| `snapshot_version` | Snapshot schema version |

### State at capture time
| Field | Type | Description |
|---|---|---|
| `integration_scope` | `SnapshotScope` | COMPONENT / SUBSYSTEM / ENTERPRISE / GLOBAL |
| `integration_type` | `SnapshotIntegrationType` | REST_API / MESSAGING / STREAMING / … |
| `lifecycle_state` | `LifecycleState` | Lifecycle state at capture time |
| `governance_state` | `GovernanceState` | Governance evaluation outcome |
| `connectivity_state` | `ConnectivityState` | CONNECTED / DEGRADED / DISCONNECTED |
| `status` | `SnapshotStatus` | DRAFT / PUBLISHED / ARCHIVED / EXPIRED |

### Timestamps
| Field | Description |
|---|---|
| `snapshot_timestamp` | When the data was captured |
| `created_at` | When the snapshot object was created |
| `updated_at` | When the snapshot was last versioned |

### Summary objects
| Object | Key fields |
|---|---|
| `connectivity_summary` | active_integrations, registered_connectors, registered_adapters, protocols_enabled, overall_integration_health |
| `connector_summary` | connector_count, connector_types, connector_availability, connector_health |
| `adapter_summary` | adapter_count, adapter_types, compatibility_status |
| `protocol_summary` | rest, graphql, grpc, websocket, kafka, rabbitmq, redis_streams, database_connectors, webhook_services, file_transfer, protocol_health |
| `service_summary` | requests_processed, responses_received, messages_published, messages_consumed, events_processed, retries, failures, average_latency_ms, throughput_rps |
| `security_summary` | authentication_providers, authorization_providers, certificates, secrets, encryption_status, credential_health |
| `audit_summary` | governance_version, connector_registry_version, protocol_registry_version, validation_summary, audit_trail |
| `statistics_summary` | processing_duration_ms, snapshot_size_bytes, connector_count, adapter_count, protocol_count, connection_count |
| `metadata` | environment, framework_version, build_version, source_components, correlation_ids, trace_ids, tags |

## Snapshot lifecycle

```
[Builder] → build() → DRAFT snapshot
    ↓
[Validator] → validate() → SnapshotValidationReport
    ↓
[Registry] → register() → published to registry
    ↓ set_status(PUBLISHED)
PUBLISHED snapshot (canonical state)
    ↓
[Store] → save() → versioned persistence
    ↓
[Cache] → put() → fast retrieval layer
    ↓
[History] → record() → audit trail
    ↓
[EventBus] → emit(SNAPSHOT_PUBLISHED) → downstream notification
    ↓
[Bundle] → add() → grouped for batch operations
    ↓
(time passes) → set_status(ARCHIVED) / EXPIRED
```

## Building snapshots

Use `IntegrationSnapshotBuilder` for full control:

```python
snapshot = (
    IntegrationSnapshotBuilder()
    .set_session_ids("sess-001", "wf-001", "ent-001")
    .set_versions(integration_version="2.1.0")
    .set_scope(SnapshotScope.ENTERPRISE, SnapshotIntegrationType.FULL)
    .set_lifecycle_state(LifecycleState.ACTIVE)
    .set_governance_state(GovernanceState.COMPLIANT)
    .set_connectivity_state(ConnectivityState.CONNECTED)
    .set_connectivity_summary(
        active_integrations        = 10,
        registered_connectors      = 8,
        registered_adapters        = 12,
        protocols_enabled          = 10,
        overall_integration_health = "healthy",
    )
    .set_service_summary(
        requests_processed = 50_000,
        average_latency_ms = 8.3,
        throughput_rps     = 120.0,
    )
    .build()
)
```

Use `IntegrationSnapshotFactory` for common patterns:

```python
# REST API snapshot
rest_snap = IntegrationSnapshotFactory.create_rest_snapshot(
    integration_session_id  = "sess-001",
    integration_workflow_id = "wf-001",
    enterprise_session_id   = "ent-001",
    requests_processed      = 5_000,
    average_latency_ms      = 12.5,
)

# Full enterprise snapshot
ent_snap = IntegrationSnapshotFactory.create_enterprise_snapshot(
    integration_session_id  = "sess-001",
    integration_workflow_id = "wf-001",
    enterprise_session_id   = "ent-001",
    connector_count         = 15,
    adapter_count           = 15,
    requests_processed      = 100_000,
)
```

## Consuming downstream

All IIOS downstream components should accept `IntegrationSnapshot` as their
input:

```python
def process(snapshot: IntegrationSnapshot) -> None:
    # Read-only access to all subsystem state
    health  = snapshot.connectivity_summary.overall_integration_health
    latency = snapshot.service_summary.average_latency_ms
    gov     = snapshot.governance_state
    ...
```

Never bypass the snapshot to access M1/M2/M3/M4 directly.
