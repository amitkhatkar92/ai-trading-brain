# Integration Snapshot — README

**Package:** `iios.integration.snapshot`
**Module:** C15 M5 — Integration Snapshot
**Version:** 1.0.0

## Overview

The Integration Snapshot is the **immutable, versioned, canonical published
representation** of Enterprise Integration & Connectivity.

It consolidates validated outputs from:

| Module | Package |
|---|---|
| M1 — Integration Lifecycle | `iios.integration.lifecycle` |
| M2 — Integration Engine | `iios.integration.engine` |
| M3 — Integration Governance Policy Framework | `iios.integration.policies` |
| M4 — Integration Services Framework | `iios.integration.services` |

## Key Principle

> The Integration Snapshot is the **ONLY** published representation of
> Enterprise Integration & Connectivity.  All downstream IIOS components MUST
> consume `IntegrationSnapshot` rather than directly accessing M1/M2/M3/M4.

## What the Snapshot does NOT do

- No lifecycle management
- No orchestration
- No governance evaluation
- No protocol execution

## Package contents

| File | Responsibility |
|---|---|
| `constants.py` | Enums, type definitions, constants |
| `exceptions.py` | ISS-000 — ISS-010 exception hierarchy |
| `integration_snapshot.py` | `IntegrationSnapshot` frozen dataclass + summary objects |
| `integration_snapshot_builder.py` | Fluent builder |
| `integration_snapshot_factory.py` | Static factory methods |
| `integration_snapshot_validation.py` | 7-check integrity validator |
| `integration_snapshot_registry.py` | Thread-safe in-memory registry |
| `integration_snapshot_store.py` | Versioned persistent store (in-process) |
| `integration_snapshot_cache.py` | TTL + LRU cache |
| `integration_snapshot_history.py` | Bounded chronological log |
| `integration_snapshot_statistics.py` | Thread-safe counter set |
| `integration_snapshot_events.py` | In-process pub/sub event bus |
| `integration_snapshot_metadata.py` | `SnapshotMetadata` frozen dataclass |
| `integration_snapshot_bundle.py` | Ordered snapshot collection |
| `__init__.py` | Public API surface |

## Quick start

```python
from iios.integration.snapshot import (
    IntegrationSnapshotBuilder,
    IntegrationSnapshotFactory,
    SnapshotScope,
    SnapshotIntegrationType,
    LifecycleState,
    GovernanceState,
    ConnectivityState,
    SnapshotStatus,
)

# Build a snapshot
snapshot = (
    IntegrationSnapshotBuilder()
    .set_session_ids("sess-001", "wf-001", "ent-001")
    .set_scope(SnapshotScope.ENTERPRISE, SnapshotIntegrationType.FULL)
    .set_lifecycle_state(LifecycleState.ACTIVE)
    .set_governance_state(GovernanceState.COMPLIANT)
    .set_connectivity_state(ConnectivityState.CONNECTED)
    .set_status(SnapshotStatus.PUBLISHED)
    .set_service_summary(requests_processed=1000, average_latency_ms=12.5)
    .build()
)

# Or use the factory
snapshot = IntegrationSnapshotFactory.create_enterprise_snapshot(
    integration_session_id  = "sess-001",
    integration_workflow_id = "wf-001",
    enterprise_session_id   = "ent-001",
    connector_count         = 5,
)
```

## Error codes

| Code | Exception | Meaning |
|---|---|---|
| ISS-000 | `IntegrationSnapshotError` | Base error |
| ISS-001 | `SnapshotNotFoundError` | Snapshot not found |
| ISS-002 | `SnapshotBuildError` | Build failed (missing required field) |
| ISS-003 | `SnapshotValidationError` | Validation check failed |
| ISS-004 | `SnapshotRegistryError` | Registry operation failed |
| ISS-005 | `SnapshotStoreError` | Store operation failed |
| ISS-006 | `SnapshotCacheError` | Cache operation failed |
| ISS-007 | `SnapshotExpiredError` | Snapshot TTL exceeded |
| ISS-008 | `SnapshotSerializationError` | Serialization failed |
| ISS-009 | `SnapshotVersionError` | Version conflict |
| ISS-010 | `SnapshotBundleError` | Bundle operation failed |
