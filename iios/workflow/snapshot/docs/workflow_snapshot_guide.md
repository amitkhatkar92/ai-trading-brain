# Workflow Snapshot Guide

## What is a WorkflowSnapshot?

A `WorkflowSnapshot` is an **immutable, frozen-dataclass record** of the
execution state of a single enterprise workflow at a specific point in time.

It aggregates:

- Identity and correlation context
- Execution status (RUNNING / COMPLETED / FAILED / TIMED_OUT / …)
- Governance decision (APPROVED / REJECTED / BLOCKED / …)
- Step progress (completed / remaining / total / progress %)
- Execution timings (total, queue, scheduling, execution)
- Resource utilisation summary
- Dependency health
- Audit trail
- Metadata (version, environment, tags)

Once created it **cannot be mutated**.  All downstream processing must create a
new snapshot rather than patching an existing one.

---

## Life Cycle of a Snapshot

```
Workflow Execution Phase
        │
        ▼
WorkflowSnapshotBuilder.build(...)
        │
        ▼
WorkflowSnapshotValidation.validate_or_raise(snap)
        │
        ├──► WorkflowSnapshotRegistry.register(snap)     ← live index
        ├──► WorkflowSnapshotStore.save(snap)             ← bounded store
        ├──► WorkflowSnapshotCache.put(snap)              ← hot-path read
        ├──► WorkflowSnapshotHistory.record(snap)         ← audit log
        ├──► WorkflowSnapshotStatistics.record_snapshot() ← metrics
        └──► WorkflowSnapshotEventBus.emit(event)         ← notifications
```

---

## Creating a Snapshot

### Via Builder (full control)

```python
from iios.workflow.snapshot import WorkflowSnapshotBuilder, ExecutionStatus

snap = WorkflowSnapshotBuilder().build(
    workflow_id        = "wf-123",
    workflow_name      = "Invoice Approval",
    execution_status   = ExecutionStatus.COMPLETED,
    total_steps        = 4,
    completed_steps    = 4,
    execution_progress = 1.0,
    execution_duration_ms = 512.0,
    audit_trail        = ["step-1 ok", "step-2 ok", "step-3 ok", "step-4 ok"],
)
```

### Via Factory (common patterns)

```python
from iios.workflow.snapshot import WorkflowSnapshotFactory

# Completed
snap = WorkflowSnapshotFactory.create_completed("wf-123", "Invoice Approval",
    execution_duration_ms=512.0, completed_steps=4, total_steps=4)

# Failed
snap = WorkflowSnapshotFactory.create_failed("wf-123", "Invoice Approval",
    error_note="approval timeout")

# In-progress
snap = WorkflowSnapshotFactory.create_running("wf-123", "Invoice Approval",
    current_step="step-3", completed_steps=2, total_steps=4)
```

---

## Reading Properties

| Property | Type | Description |
|---|---|---|
| `is_healthy` | bool | `health_status == HEALTHY` |
| `is_completed` | bool | `execution_status == COMPLETED` |
| `is_failed` | bool | `execution_status` in {FAILED, TIMED_OUT} |
| `is_governance_approved` | bool | APPROVED or APPROVED_WITH_CONDITIONS |
| `is_published` | bool | `snapshot_status == PUBLISHED` |

---

## Health Status Mapping

| Execution Status | Governance Decision | Health |
|---|---|---|
| Any | REJECTED / BLOCKED / EMERGENCY_STOPPED | FAILED |
| FAILED / TIMED_OUT | Any | FAILED |
| COMPLETED | APPROVED / APPROVED_WITH_CONDITIONS / NOT_EVALUATED | HEALTHY |
| RUNNING | APPROVED / NOT_EVALUATED | HEALTHY |
| Other | Other | DEGRADED |
