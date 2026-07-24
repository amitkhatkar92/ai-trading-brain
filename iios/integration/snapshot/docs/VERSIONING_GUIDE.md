# Versioning Guide

## Overview

The Integration Snapshot supports two orthogonal versioning concepts:

1. **Snapshot version** (`snapshot_version`) — schema version of the snapshot format
2. **Integration version** (`integration_version`) — version of the integration configuration being captured

## Snapshot schema versioning

The current schema version is `1.0.0`.  The `snapshot_version` field is baked
into every snapshot at creation time via the builder or factory.

Schema versions follow SemVer:
- **MAJOR** bump: breaking schema change (fields renamed, removed, or type-changed)
- **MINOR** bump: additive schema change (new optional fields)
- **PATCH** bump: non-breaking clarification

## Creating a new version of a snapshot

Use `IntegrationSnapshotFactory.bump_version()` to produce a new snapshot with
updated status and an optional audit trail entry, without mutating the original:

```python
from iios.integration.snapshot import (
    IntegrationSnapshotFactory,
    SnapshotStatus,
)

# Publish a draft snapshot
published = IntegrationSnapshotFactory.bump_version(
    snapshot    = draft_snapshot,
    new_status  = SnapshotStatus.PUBLISHED,
    audit_entry = "published by integration_engine at 09:00 UTC",
)

# Archive an old snapshot
archived = IntegrationSnapshotFactory.bump_version(
    snapshot    = old_snapshot,
    new_status  = SnapshotStatus.ARCHIVED,
    audit_entry = "archived after 24h retention period",
)
```

Each call to `bump_version()`:
- Creates a new `snapshot_id` (original is preserved)
- Updates `updated_at` to now
- Appends the `audit_entry` to `audit_summary.audit_trail`
- Does NOT modify the original snapshot

## Versioned storage

The `IntegrationSnapshotStore` maintains a list of versions per `snapshot_id`:

```python
from iios.integration.snapshot import IntegrationSnapshotStore

store = IntegrationSnapshotStore()

# Save multiple versions
v1 = store.save(snap_v1)   # returns snapshot_id
v2 = store.save(snap_v2)   # same snapshot_id, new version entry

# List versions
versions = store.list_versions(snapshot_id)  # ["v1", "v2"]

# Load latest
latest = store.load(snapshot_id)

# Load specific version
original = store.load(snapshot_id, version_tag="v1")
```

## Registry status overrides

The `IntegrationSnapshotRegistry` maintains an independent status map so a
snapshot's publication status can evolve without creating a new snapshot object:

```python
registry.register(snapshot)                           # status = DRAFT
registry.set_status(snapshot_id, SnapshotStatus.PUBLISHED)
registry.set_status(snapshot_id, SnapshotStatus.ARCHIVED)
```

This is appropriate for lightweight status transitions.  For auditable version
history, prefer `bump_version()` + `store.save()`.

## Framework version compatibility

The `metadata.framework_version` records the IIOS framework version at
snapshot creation time.  Consumers SHOULD check this if they implement
version-specific behaviour:

```python
if snapshot.metadata.framework_version != "1.0.0":
    raise SnapshotVersionError(
        f"Unsupported framework version: {snapshot.metadata.framework_version}"
    )
```
