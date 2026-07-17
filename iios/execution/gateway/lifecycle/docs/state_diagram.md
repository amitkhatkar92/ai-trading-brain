# Gateway State Diagram

## Lifecycle State Machine

```
                         ┌─────────┐
                         │ CREATED │  ← initial state
                         └────┬────┘
                              │ receive()
                              ▼
                         ┌──────────┐
                         │ RECEIVED │
                         └────┬─────┘
                              │ start_validation()
                              ▼
                        ┌────────────┐
                        │ VALIDATING │
                        └─────┬──────┘
                              │ mark_ready()
                              ▼
                          ┌───────┐
                          │ READY │
                          └───┬───┘
                              │ queue()
                              ▼
                          ┌────────┐
                          │ QUEUED │
                          └───┬────┘
                              │ start_routing()
                              ▼
                         ┌─────────┐
                         │ ROUTING │
                         └────┬────┘
                              │ dispatch()
                              ▼
                        ┌────────────┐
                        │ DISPATCHED │
                        └─────┬──────┘
                              │ complete()
                              ▼
                        ┌───────────┐
                        │ COMPLETED │
                        └─────┬─────┘
                              │ archive()
                              ▼
                        ┌──────────┐
                        │ ARCHIVED │  ← terminal
                        └──────────┘
```

## Failure and Cancellation Paths

```
Any active state ──► FAILED   ──► ARCHIVED
Any active state ──► CANCELLED ──► ARCHIVED
```

Active states: CREATED, RECEIVED, VALIDATING, READY, QUEUED, ROUTING, DISPATCHED

## VALID_TRANSITIONS Table

| From         | To (allowed targets)                    |
|--------------|-----------------------------------------|
| CREATED      | RECEIVED, FAILED, CANCELLED             |
| RECEIVED     | VALIDATING, FAILED, CANCELLED           |
| VALIDATING   | READY, FAILED, CANCELLED                |
| READY        | QUEUED, FAILED, CANCELLED               |
| QUEUED       | ROUTING, FAILED, CANCELLED              |
| ROUTING      | DISPATCHED, FAILED, CANCELLED           |
| DISPATCHED   | COMPLETED, FAILED, CANCELLED            |
| COMPLETED    | ARCHIVED                                |
| FAILED       | ARCHIVED                                |
| CANCELLED    | ARCHIVED                                |
| ARCHIVED     | (none — terminal)                       |

## State Sets

| Set               | States                                                              |
|-------------------|---------------------------------------------------------------------|
| ACTIVE_STATES     | CREATED, RECEIVED, VALIDATING, READY, QUEUED, ROUTING, DISPATCHED  |
| OUTCOME_STATES    | COMPLETED, FAILED, CANCELLED                                        |
| TERMINAL_STATES   | ARCHIVED                                                            |
| ENDED_STATES      | OUTCOME_STATES ∪ TERMINAL_STATES                                    |
| SUCCESS_STATES    | COMPLETED                                                           |
| FAILURE_STATES    | FAILED, CANCELLED                                                   |
