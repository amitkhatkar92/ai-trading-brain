# Knowledge Lifecycle — Developer Guide

## Architecture

```
KnowledgeLifecycle (LifecycleAwareMixin)
    │
    ├── KnowledgeRegistry   — thread-safe session storage
    ├── KnowledgeHistory    — bounded chronological transition log
    ├── KnowledgeStatistics — 6 atomic counters
    ├── KnowledgeFactory    — session construction
    ├── KnowledgeValidator  — 5-check structural validation
    └── KnowledgeEventBus   — synchronous event dispatch
```

## Immutability Contract

| Object | Mutable? |
|---|---|
| `KnowledgeSession` | ✅ Yes — state advances via `transition_to()` |
| `KnowledgeStateRecord` | ❌ No — frozen dataclass |
| `KnowledgeTransition` | ❌ No — frozen dataclass |
| `KnowledgeMetadata` | ❌ No — frozen dataclass |
| `KnowledgeContext` | ❌ No — frozen dataclass |
| `KnowledgeEvent` | ❌ No — frozen dataclass |

## Thread Safety

`KnowledgeRegistry`, `KnowledgeHistory`, and `KnowledgeStatistics` are all
thread-safe (protected by `threading.Lock`).  `KnowledgeSession.transition_to()`
is NOT internally locked — callers that share sessions across threads must
coordinate externally (typically via the registry lock).

## State Machine Guard

The state machine is enforced inside `KnowledgeSession.transition_to()`:

```python
# Archived sessions are immutable
if self._state in IMMUTABLE_STATES:
    raise KnowledgeSessionTerminatedError(...)

# Validate the requested transition
allowed = VALID_TRANSITIONS.get(self._state, frozenset())
if new_state not in allowed:
    raise KnowledgeInvalidTransitionError(...)
```

## Adding a New Lifecycle State

1. Add the state to `KnowledgeLifecycleState` in `constants.py`
2. Update `VALID_TRANSITIONS`, `ACTIVE_STATES`, `TERMINAL_STATES`, etc.
3. Add a corresponding `KnowledgeEventType` if an event should fire
4. Update `_STATE_TO_EVENT` in `knowledge_lifecycle.py`
5. Add a transition method to `KnowledgeLifecycle`
6. Update documentation and tests

## Validation Checks

| Check | Code |
|---|---|
| Identifier consistency | `IDENTIFIER_CONSISTENCY` |
| Lifecycle state validity | `LIFECYCLE_CONSISTENCY` |
| All transitions valid per state machine | `TRANSITION_VALIDITY` |
| Timestamp ordering | `TIMESTAMP_CONSISTENCY` |
| History non-empty, first entry is CREATED | `HISTORY_INTEGRITY` |

## Logging Convention

Use only f-strings with the `StructuredLogger`:

```python
# CORRECT
self._log.info(f"Session created: session_id={session_id!r}")

# WRONG — positional args not supported
self._log.info("Session created: %s", session_id)
```
