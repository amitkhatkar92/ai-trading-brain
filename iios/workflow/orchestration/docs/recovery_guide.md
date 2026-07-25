# Recovery Guide

## What is recovered?

After a crash or restart, `WorkflowRecoveryEngine` can restore a
workflow runtime to the state it held at its last checkpoint:

- Step statuses for all steps present in the checkpoint
- Full workflow context snapshot
- Runtime status set to `RECOVERING`

Execution can then resume from the first non-completed step.

---

## Checkpoint creation

Checkpoints are created automatically after each execution wave
when `definition.enable_checkpointing = True`.

Each checkpoint records:

| Field | Description |
|-------|-------------|
| `checkpoint_id` | Unique ID (prefix `wchk-`) |
| `runtime_id` | Parent runtime |
| `step_statuses` | All current step statuses |
| `completed_steps` | Set of completed step IDs |
| `failed_steps` | Set of failed step IDs |
| `context_snapshot` | Deep copy of workflow context |
| `retry_total` | Retry count at checkpoint time |

---

## Recovery example

```python
from iios.workflow.orchestration import (
    WorkflowRecoveryEngine,
    WorkflowCheckpointManager,
)

recovery = WorkflowRecoveryEngine(checkpoint_manager=chk_mgr)

if recovery.can_recover(runtime.runtime_id):
    checkpoint = recovery.recover(runtime, ctx_mgr)
    # runtime status is now RECOVERING
    # ctx_mgr is restored to checkpoint state
```

---

## Bounded checkpoint storage

`WorkflowCheckpointManager` keeps the last N checkpoints per runtime
(default: 10).  Older entries are evicted automatically.

---

## What is NOT recovered

- In-flight step threads (cancelled by process exit)
- Event engine signals (`WorkflowEventEngine`)
- Scheduler timers (`WorkflowScheduler`)

These must be re-armed after recovery.
