# Workflow Snapshot — README

**Module:** `iios.workflow.snapshot`
**Layer:** C16 M5 — Enterprise Workflow & Process Orchestration
**Build:** c16-m5

---

## Purpose

The Workflow Snapshot package provides an **immutable, enterprise-grade
representation of the completed state** of a workflow execution.  It is the
single publication point for all downstream consumers — dashboards, audit
systems, analytics engines, and integration gateways — that need a consistent
view of what happened inside the orchestration engine.

A `WorkflowSnapshot` is never a live view.  It is a point-in-time record,
built after a significant execution phase completes.

---

## Key Components

| Class | Responsibility |
|---|---|
| `WorkflowSnapshot` | Immutable domain object — the core snapshot |
| `WorkflowSnapshotMetadata` | Versioning, environment, correlation metadata |
| `WorkflowSnapshotBuilder` | Constructs validated snapshots |
| `WorkflowSnapshotValidation` | Validates snapshot consistency |
| `WorkflowSnapshotRegistry` | In-memory index by snapshot_id and workflow_id |
| `WorkflowSnapshotStore` | Bounded persistent-style store with auto-eviction |
| `WorkflowSnapshotCache` | LRU hot-path cache |
| `WorkflowSnapshotHistory` | Chronological bounded history per workflow |
| `WorkflowSnapshotStatistics` | Thread-safe quality metrics counters |
| `WorkflowSnapshotEvent` | Immutable domain events |
| `WorkflowSnapshotEventBus` | Per-event-type, thread-safe publish/subscribe |
| `WorkflowSnapshotBundle` | Grouped collection of related snapshots |
| `WorkflowSnapshotFactory` | Fluent factory for common patterns |

---

## Quick Start

```python
from iios.workflow.snapshot import WorkflowSnapshotFactory, WorkflowSnapshotValidation

# Create a completed-workflow snapshot
snap = WorkflowSnapshotFactory.create_completed(
    workflow_id   = "wf-order-processing-001",
    workflow_name = "Order Processing",
    execution_duration_ms = 312.4,
    completed_steps       = 5,
    total_steps           = 5,
)

# Validate it
WorkflowSnapshotValidation().validate_or_raise(snap)

# Inspect
print(snap.is_healthy)          # True
print(snap.is_completed)        # True
print(snap.execution_progress)  # 1.0
```

---

## Thread Safety

All service classes (`Registry`, `Store`, `Cache`, `History`, `Statistics`,
`EventBus`) use `threading.Lock()` internally and are safe for concurrent use
from multiple threads without external synchronisation.

---

## See Also

- [workflow_snapshot_guide.md](workflow_snapshot_guide.md)
- [snapshot_schema_guide.md](snapshot_schema_guide.md)
- [serialization_guide.md](serialization_guide.md)
- [versioning_guide.md](versioning_guide.md)
- [developer_guide.md](developer_guide.md)
