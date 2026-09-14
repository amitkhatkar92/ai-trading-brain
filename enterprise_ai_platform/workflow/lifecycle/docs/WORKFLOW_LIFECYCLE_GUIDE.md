# Workflow Lifecycle Guide — C16 M1

## State Transition Diagram

```
CREATED ──────────────────────────────────────────────────────► CANCELLED
   │
   ▼
INITIALIZING ────────────────────────────────────────────────► FAILED
   │                                                              │
   ▼                                                             (retry)
VALIDATING ──────────────────────────────────────────────────► FAILED
   │
   ▼
READY ──────────────────────────────────────────────────────── CANCELLED
   │                │               │
   ▼                ▼               ▼
SCHEDULED        QUEUED          RUNNING ◄──────────────────── RESUMING
   │               │                │                              │
   ▼               ▼                ├──► WAITING ────────────────►┘
QUEUED ────────► RUNNING            │
                   │                ├──► PAUSED ──────────────────► RESUMING
                   │                │
                   ├──► COMPLETED ──┼──► FAILED ──► INITIALIZING (retry)
                   │                │                    │
                   └──► CANCELLED   └──► CANCELLED       └──► ARCHIVED
                           │                │
                           └───────────────►└──► ARCHIVED (terminal)
```

## State Classification

### Active States
Sessions in active states are in-flight and counted toward capacity:
- INITIALIZING, VALIDATING, READY, SCHEDULED, QUEUED
- RUNNING, WAITING, PAUSED, RESUMING

### Terminal States
Terminal states cannot accept most transitions:
- COMPLETED → only ARCHIVED
- FAILED → only INITIALIZING (retry) or ARCHIVED
- CANCELLED → only ARCHIVED
- ARCHIVED → no transitions (fully terminal)

### Immutable State
Only ARCHIVED is immutable — all operations on an ARCHIVED session
raise `WorkflowSessionTerminatedError`.

## Retry Semantics

FAILED → INITIALIZING is the only "reverse" transition in the state machine.
This supports supervised retry workflows without creating a new session,
preserving the audit trail across retry attempts.

## Priority Routing

`WorkflowPriority` is a metadata label only — it does not affect lifecycle
state transitions. Scheduling and queuing logic in later C16 modules uses it.

## Thread Safety

All public methods on `WorkflowLifecycle`, `WorkflowRegistry`,
`WorkflowHistory`, `WorkflowLifecycleStatistics`, and
`WorkflowLifecycleEventBus` are thread-safe using `threading.Lock()`.

`WorkflowSession.transition_to()` is atomic — the state change and audit
record creation happen inside a single lock acquisition.
