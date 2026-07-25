# Serialization Guide

## `to_dict()` Contract

Every domain object in `iios.workflow.snapshot` implements `.to_dict()` which
returns a plain `dict` safe for JSON serialisation, structured logging, and
inter-process transport.

### Rules

1. All enum fields are serialized as their `.value` string.
2. Timestamps are ISO-8601 UTC strings (`datetime.isoformat()`).
3. `tuple` fields (e.g. `audit_trail`, `governance_notes`) become `list`.
4. Nested objects (`metadata`) become nested `dict`.
5. Computed properties (`is_healthy`, `is_completed`, …) are **included**.
6. `extra` is copied shallowly — deep objects inside it must be
   independently serialisable.

---

## WorkflowSnapshot Serialization

```python
snap = WorkflowSnapshotFactory.create_completed("wf-1", "Order Approval")
d    = snap.to_dict()

# d is a plain dict, all values are JSON-compatible primitives
import json
json.dumps(d)   # ✅ no error
```

### Included Computed Keys

```python
d["is_healthy"]             # bool
d["is_completed"]           # bool
d["is_failed"]              # bool
d["is_governance_approved"] # bool
d["is_published"]           # bool
```

---

## WorkflowSnapshotMetadata Serialization

```python
m = WorkflowSnapshotMetadata.create(environment="staging")
d = m.to_dict()
# {"metadata_id": "wsmeta-...", "environment": "staging", ...}
```

---

## WorkflowSnapshotEvent Serialization

```python
from iios.workflow.snapshot import WorkflowSnapshotEvent, SnapshotEventType

evt = WorkflowSnapshotEvent.create(
    SnapshotEventType.SNAPSHOT_PUBLISHED, "snap-1", "wf-1"
)
d = evt.to_dict()
# {"event_id": "wsevt-...", "event_type": "snapshot_published", ...}
```

---

## WorkflowSnapshotBundle Serialization

```python
bundle = WorkflowSnapshotFactory.create_bundle("Batch", snaps)
d      = bundle.to_dict()
# Contains bundle_id, bundle_name, snapshot_count, snapshot_ids, workflow_ids
```

---

## WorkflowSnapshotStatisticsReport Serialization

```python
stats  = WorkflowSnapshotStatistics()
report = stats.report()
d      = report.to_dict()
# All counters and rates as plain numbers
```

---

## Reconstructing from dict

The snapshot module does NOT provide a `from_dict()` deserialiser by design.
`WorkflowSnapshot` is a write-once publication artifact.  If you need to
reconstruct a snapshot from a dict (e.g. after reading from a message queue),
use `WorkflowSnapshotBuilder.build(**d)` with the fields your system persisted.

```python
snap = WorkflowSnapshotBuilder().build(
    workflow_id        = d["workflow_id"],
    workflow_name      = d["workflow_name"],
    execution_status   = ExecutionStatus(d["execution_status"]),
    governance_decision = GovernanceDecision(d["governance_decision"]),
    snapshot_id        = d.get("snapshot_id"),
)
```
