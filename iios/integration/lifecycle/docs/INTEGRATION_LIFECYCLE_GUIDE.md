# Integration Lifecycle Guide — C15 M1

## Purpose

The Integration Lifecycle module enforces the correct operational lifecycle for enterprise
integration sessions.  Every integration session — REST API, gRPC, WebSocket, message queue,
database, file transfer, event stream, or internal — follows the same 13-state machine.

---

## Design Principles

1. **Single source of truth** — `VALID_TRANSITIONS` in `constants.py` defines all permitted moves.
2. **Immutable audit trail** — `IntegrationTransition` and `IntegrationStateRecord` are frozen.
3. **Thread safety** — `IntegrationSession` and all subsystems hold `threading.Lock()`.
4. **No orchestration** — this module only moves state; it never calls external systems.
5. **Typed exceptions** — every failure raises a typed ILC-00x exception.

---

## Module Layers

```
IntegrationLifecycle          ← public API (one method per lifecycle event)
  ├── IntegrationRegistry     ← stores active IntegrationSession objects
  ├── IntegrationHistory      ← append-only bounded transition log
  ├── IntegrationLifecycleEventBus  ← synchronous, listener-based events
  └── IntegrationLifecycleStatistics ← 6 counters
```

---

## Session Lifecycle

A session progresses through 13 states:

```
CREATED → INITIALIZING → DISCOVERING → CONFIGURING → VALIDATING
        → READY → CONNECTING → ACTIVE
                             ↗ (resume)
        ↕ PAUSED → RESUMING ↗
        ↓
    COMPLETED → ARCHIVED
    FAILED    → ARCHIVED   (or retry → INITIALIZING)
```

---

## Error Codes

| Code | Exception | Meaning |
|---|---|---|
| ILC-000 | `IntegrationLifecycleError` | Base exception |
| ILC-001 | `IntegrationSessionNotFoundError` | Session ID unknown |
| ILC-002 | `IntegrationInvalidTransitionError` | Transition not in VALID_TRANSITIONS |
| ILC-003 | `IntegrationSessionTerminatedError` | Operation on ARCHIVED session |
| ILC-004 | `IntegrationValidationError` | 5-check validator failed |
| ILC-005 | `IntegrationCapacityError` | Registry at max_sessions |
| ILC-006 | `IntegrationHistoryError` | History subsystem error |

---

## Retry Pattern

A FAILED session may be retried by calling `lifecycle.retry(session_id)`.
This transitions FAILED → INITIALIZING and increments the transition counter.
The session then follows the full lifecycle again.

---

## Statistics

The `IntegrationLifecycleStatistics` class tracks:
- `integration_sessions_created`
- `integration_sessions_completed`
- `integration_sessions_failed`
- `integration_sessions_archived`
- `transition_count`
- `average_session_duration_ms`

Call `lifecycle.stats.report()` to get an `IntegrationLifecycleStatisticsReport`.
