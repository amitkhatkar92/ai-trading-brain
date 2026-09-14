# Position Lifecycle — State Diagram

**C6 Execution Intelligence · Phase 3 · Module 1**

---

## Full state machine

```mermaid
stateDiagram-v2
    [*] --> CREATED : PositionFactory.create()

    CREATED          --> OPENING          : transition_to(OPENING)

    OPENING          --> OPEN             : fills confirmed
    OPENING          --> CLOSED           : immediate rejection

    OPEN             --> PARTIALLY_CLOSED : partial fill closed
    OPEN             --> CLOSING          : start close
    OPEN             --> SUSPENDED        : suspend

    PARTIALLY_CLOSED --> CLOSING          : start close remainder
    PARTIALLY_CLOSED --> OPEN             : closed portion reversed
    PARTIALLY_CLOSED --> SUSPENDED        : suspend

    CLOSING          --> CLOSED           : all closed
    CLOSING          --> SUSPENDED        : suspend during close
    CLOSING          --> RECOVERING       : closure failed

    CLOSED           --> ARCHIVED         : archive

    SUSPENDED        --> RECOVERING       : start recovery
    SUSPENDED        --> CLOSED           : abandon

    RECOVERING       --> RECOVERED        : recovery succeeded
    RECOVERING       --> CLOSED           : recovery abandoned

    RECOVERED        --> OPEN             : resume
    RECOVERED        --> CLOSING          : close after recovery

    ARCHIVED         --> [*]
```

---

## State groups

| Group | States |
|-------|--------|
| Active | OPENING, OPEN, PARTIALLY_CLOSED, CLOSING |
| Suspended | SUSPENDED, RECOVERING, RECOVERED |
| Closed | CLOSED, ARCHIVED |
| Terminal | ARCHIVED |

---

## Transition table

| From | Allowed targets |
|------|----------------|
| CREATED | OPENING |
| OPENING | OPEN, CLOSED |
| OPEN | PARTIALLY_CLOSED, CLOSING, SUSPENDED |
| PARTIALLY_CLOSED | CLOSING, OPEN, SUSPENDED |
| CLOSING | CLOSED, SUSPENDED, RECOVERING |
| CLOSED | ARCHIVED |
| SUSPENDED | RECOVERING, CLOSED |
| RECOVERING | RECOVERED, CLOSED |
| RECOVERED | OPEN, CLOSING |
| ARCHIVED | *(terminal — no outgoing edges)* |
