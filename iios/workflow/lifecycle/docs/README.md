# Workflow Lifecycle — C16 M1

**Package**: `iios.workflow.lifecycle`  
**Component**: C16 Enterprise Workflow & Process Orchestration  
**Phase**: Phase 1 — Enterprise Workflow  
**Module**: M1 — Workflow Lifecycle

---

## Overview

The Workflow Lifecycle governs the complete state transition of enterprise
workflows, business processes, and orchestration jobs throughout IIOS.

It manages **ONLY workflow lifecycle states**.

It does **NOT**:
- Execute workflows
- Perform orchestration
- Evaluate governance
- Run business logic
- Invoke AI

---

## 14 Lifecycle States

| State         | Description                                      |
|---------------|--------------------------------------------------|
| `CREATED`     | Session created, awaiting initialization         |
| `INITIALIZING`| Initialization in progress                       |
| `VALIDATING`  | Validation step in progress                      |
| `READY`       | Validated and ready for scheduling or execution  |
| `SCHEDULED`   | Scheduled for future execution                   |
| `QUEUED`      | In execution queue, awaiting a slot              |
| `RUNNING`     | Actively running                                 |
| `WAITING`     | Paused awaiting external event or dependency     |
| `PAUSED`      | Paused by operator                               |
| `RESUMING`    | Transitioning from PAUSED back to RUNNING        |
| `COMPLETED`   | Successfully completed (terminal)                |
| `FAILED`      | Failed (retryable — may return to INITIALIZING)  |
| `CANCELLED`   | Cancelled by operator (terminal)                 |
| `ARCHIVED`    | Archived — fully terminal, no further transitions|

---

## 12 Transitions

| Name             | From                     | To            |
|------------------|--------------------------|---------------|
| Create           | —                        | CREATED       |
| Initialize       | CREATED                  | INITIALIZING  |
| Validate         | INITIALIZING             | VALIDATING    |
| Ready            | VALIDATING               | READY         |
| Schedule         | READY                    | SCHEDULED     |
| Queue            | READY / SCHEDULED        | QUEUED        |
| Start            | QUEUED / READY           | RUNNING       |
| Wait             | RUNNING                  | WAITING       |
| Pause            | RUNNING / WAITING        | PAUSED        |
| Resume           | PAUSED                   | RESUMING      |
| Complete         | RUNNING / WAITING        | COMPLETED     |
| Fail             | Most active states       | FAILED        |
| Cancel           | Most non-terminal states | CANCELLED     |
| Archive          | COMPLETED/FAILED/CANCELLED| ARCHIVED     |
| Retry            | FAILED                   | INITIALIZING  |

---

## Source Files

| File                        | Purpose                                       |
|-----------------------------|-----------------------------------------------|
| `constants.py`              | Enums, transition table, capacity defaults    |
| `exceptions.py`             | WLC-000 — WLC-006 exception hierarchy         |
| `workflow_session.py`       | Mutable session entity (thread-safe)          |
| `workflow_lifecycle.py`     | State machine manager (14 named methods)      |
| `workflow_state.py`         | Immutable `WorkflowStateRecord`               |
| `workflow_transition.py`    | Immutable `WorkflowTransition`                |
| `workflow_context.py`       | Immutable per-session `WorkflowContext`       |
| `workflow_metadata.py`      | Immutable `WorkflowMetadata`                  |
| `workflow_history.py`       | Bounded append-only dual-buffer history       |
| `workflow_statistics.py`    | 7-metric thread-safe statistics               |
| `workflow_registry.py`      | Thread-safe session registry                  |
| `workflow_factory.py`       | Session factory with defaults                 |
| `workflow_validation.py`    | 5-check session validator                     |
| `workflow_events.py`        | Immutable events + synchronous event bus      |
| `__init__.py`               | Public API — 50 exports                       |

---

## Quick Start

```python
from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowMetadata, WorkflowType

lc = WorkflowLifecycle()

# Create a session
session = lc.create_session("my-workflow-001")

# Walk through the lifecycle
lc.initialize(session.session_id)
lc.validate_workflow(session.session_id)
lc.mark_ready(session.session_id)
lc.start(session.session_id)
lc.complete(session.session_id, runtime_ms=1250.0, lifecycle_duration_ms=3000.0)
lc.archive(session.session_id)

# Observe
stats = lc.statistics()
print(stats.to_dict())
```
