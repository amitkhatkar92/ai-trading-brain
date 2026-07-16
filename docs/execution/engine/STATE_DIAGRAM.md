# Execution Engine — State Diagram

All 9 engine execution states and all legal transitions.

```mermaid
stateDiagram-v2
    direction TB

    [*] --> IDLE : execution registered

    IDLE       --> VALIDATING  : start processing
    IDLE       --> CANCELLED   : cancelled before validation

    VALIDATING --> PREPARING   : request validation passed
    VALIDATING --> FAILED      : request validation failed
    VALIDATING --> CANCELLED   : cancelled during validation

    PREPARING  --> READY       : context assembled and validated
    PREPARING  --> FAILED      : context preparation or validation failed
    PREPARING  --> CANCELLED   : cancelled during preparation

    READY      --> EXECUTING   : execution phase started
    READY      --> CANCELLED   : cancelled before execution

    EXECUTING  --> WAITING     : awaiting external signal (broker ACK)
    EXECUTING  --> COMPLETED   : execution workflow complete
    EXECUTING  --> FAILED      : execution error
    EXECUTING  --> CANCELLED   : cancelled during execution

    WAITING    --> EXECUTING   : signal received — resuming
    WAITING    --> COMPLETED   : signal confirms completion
    WAITING    --> FAILED      : signal indicates failure
    WAITING    --> CANCELLED   : cancelled while waiting

    COMPLETED  --> [*]
    FAILED     --> [*]
    CANCELLED  --> [*]
```

---

## Event Emitted on State Entry

| State entered | Event type |
|---|---|
| IDLE | *(no event)* |
| VALIDATING | `EXECUTION_STARTED` |
| PREPARING | `EXECUTION_VALIDATED` |
| READY | `EXECUTION_PREPARED` |
| EXECUTING | `EXECUTION_READY` |
| WAITING | *(no event)* |
| COMPLETED | `EXECUTION_COMPLETED` |
| FAILED | `EXECUTION_FAILED` |
| CANCELLED | `EXECUTION_CANCELLED` |

---

## State Groups

```mermaid
stateDiagram-v2
    state "Pre-Processing" as Pre {
        IDLE
    }
    state "Active" as Active {
        VALIDATING
        PREPARING
        READY
        EXECUTING
        WAITING
    }
    state "Terminal" as Terminal {
        COMPLETED
        FAILED
        CANCELLED
    }

    Pre    --> Active
    Active --> Terminal
```

---

## Transition Count Summary

| From State | Outgoing transitions |
|---|---|
| IDLE | 2 |
| VALIDATING | 3 |
| PREPARING | 3 |
| READY | 2 |
| EXECUTING | 4 |
| WAITING | 4 |
| COMPLETED | 0 *(terminal)* |
| FAILED | 0 *(terminal)* |
| CANCELLED | 0 *(terminal)* |
