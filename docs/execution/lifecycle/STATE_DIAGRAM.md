# Order Lifecycle — State Diagram

All 14 states and all legal transitions.

```mermaid
stateDiagram-v2
    direction TB

    [*] --> CREATED : order created

    CREATED         --> VALIDATED           : validation passed
    CREATED         --> REJECTED            : validation failed
    CREATED         --> FAILED              : unexpected error

    VALIDATED       --> PENDING_SUBMISSION  : queued for submission
    VALIDATED       --> REJECTED            : pre-submit rejection
    VALIDATED       --> FAILED              : unexpected error

    PENDING_SUBMISSION --> SUBMITTED        : sent to broker
    PENDING_SUBMISSION --> CANCELLED        : cancelled before send
    PENDING_SUBMISSION --> FAILED           : transmission error

    SUBMITTED       --> ACKNOWLEDGED        : broker ACK received
    SUBMITTED       --> REJECTED            : broker refused
    SUBMITTED       --> CANCEL_PENDING      : cancel initiated
    SUBMITTED       --> EXPIRED             : TIF expired
    SUBMITTED       --> FAILED              : broker error

    ACKNOWLEDGED    --> PARTIALLY_FILLED    : partial fill received
    ACKNOWLEDGED    --> FILLED              : complete fill received
    ACKNOWLEDGED    --> CANCEL_PENDING      : cancel initiated
    ACKNOWLEDGED    --> REJECTED            : post-ack rejection
    ACKNOWLEDGED    --> EXPIRED             : TIF expired
    ACKNOWLEDGED    --> FAILED              : broker error

    PARTIALLY_FILLED --> PARTIALLY_FILLED   : additional partial fill
    PARTIALLY_FILLED --> FILLED             : final fill received
    PARTIALLY_FILLED --> CANCEL_PENDING     : cancel initiated
    PARTIALLY_FILLED --> CANCELLED          : cancelled (partial)
    PARTIALLY_FILLED --> EXPIRED            : TIF expired (partial)
    PARTIALLY_FILLED --> FAILED             : error during fill

    CANCEL_PENDING  --> CANCELLED           : exchange confirmed cancel
    CANCEL_PENDING  --> ACKNOWLEDGED        : exchange rejected cancel
    CANCEL_PENDING  --> PARTIALLY_FILLED    : filled during cancel race
    CANCEL_PENDING  --> FILLED              : fully filled during cancel race
    CANCEL_PENDING  --> FAILED              : cancel error

    FILLED          --> [*]

    %% Recovery paths
    CANCELLED       --> RECOVERING          : recovery initiated
    REJECTED        --> RECOVERING          : recovery initiated
    EXPIRED         --> RECOVERING          : recovery initiated
    FAILED          --> RECOVERING          : recovery initiated

    RECOVERING      --> RECOVERED           : recovery succeeded
    RECOVERING      --> FAILED              : recovery failed

    RECOVERED       --> PENDING_SUBMISSION  : resubmit
    RECOVERED       --> CANCELLED           : abandon after recovery
    RECOVERED       --> FAILED              : unexpected error
```

---

## State Groups

```mermaid
stateDiagram-v2
    state "Pre-Active" as PreActive {
        CREATED
        VALIDATED
    }
    state "Active" as Active {
        PENDING_SUBMISSION
        SUBMITTED
        ACKNOWLEDGED
        PARTIALLY_FILLED
        CANCEL_PENDING
    }
    state "Completed (non-terminal)" as Completed {
        CANCELLED
        REJECTED
        EXPIRED
        FAILED
    }
    state "Recovery" as RecoveryGroup {
        RECOVERING
        RECOVERED
    }
    state "Terminal" as Terminal {
        FILLED
    }

    PreActive --> Active
    Active --> Terminal
    Active --> Completed
    Completed --> RecoveryGroup
    RecoveryGroup --> Active
    RecoveryGroup --> Completed
```

---

## Transition Count Summary

| From State | Outgoing transitions |
|---|---|
| CREATED | 3 |
| VALIDATED | 3 |
| PENDING_SUBMISSION | 3 |
| SUBMITTED | 5 |
| ACKNOWLEDGED | 6 |
| PARTIALLY_FILLED | 6 |
| CANCEL_PENDING | 5 |
| FILLED | **0 — terminal** |
| CANCELLED | 1 |
| REJECTED | 1 |
| EXPIRED | 1 |
| FAILED | 1 |
| RECOVERING | 2 |
| RECOVERED | 3 |
