# Position Lifecycle — Developer Guide

**C6 Execution Intelligence · Phase 3 · Module 1**

---

## Design principles

### 1. Lifecycle only

`Position` is a domain object. It tracks state, quantities, prices, and PnL. It has no knowledge of brokers, order routing, or risk limits.

### 2. State machine is the single source of truth

Every state change goes through `Position.transition_to()`. Direct field mutation of `_state` is never allowed. The state machine is defined once in `constants.py`:

```python
VALID_TRANSITIONS: dict[PositionState, frozenset[PositionState]] = {
    PositionState.CREATED:          frozenset({PositionState.OPENING}),
    PositionState.OPENING:          frozenset({PositionState.OPEN, PositionState.CLOSED}),
    PositionState.OPEN:             frozenset({PositionState.PARTIALLY_CLOSED, PositionState.CLOSING, PositionState.SUSPENDED}),
    ...
}
```

### 3. Immutability at the record level

`PositionTransition`, `PositionStateRecord`, `PositionEvent`, `PositionContext` — all frozen dataclasses. Once created they cannot be mutated.

### 4. Thread safety

`Position` uses `threading.RLock` (re-entrant to allow event listeners to read state during a transition).  
`PositionRegistry` uses `threading.Lock`.  
`PositionHistory` uses `threading.Lock`.

### 5. No leaking internal state

`Position.to_dict()` and `Position.snapshot()` return new dicts, never references to internal structures.

---

## Adding a new field to Position

1. Add the parameter to `Position.__init__` and `__slots__`.
2. Add a read-only `@property`.
3. Update `to_dict()`.
4. Update `PositionFactory.create()` if it should be settable at construction.
5. Add a test in `TestPositionFields`.

---

## Adding a new state

1. Add the value to `PositionState` in `constants.py`.
2. Update `VALID_TRANSITIONS` with all inbound and outbound edges.
3. Update `ACTIVE_STATES`, `SUSPENDED_STATES`, `CLOSED_STATES`, `TERMINAL_STATES` as appropriate.
4. Add a factory function in `position_event.py` if a new event type is needed.
5. Add tests covering the new transitions.

---

## Event listeners

```python
def my_listener(event: PositionEvent) -> None:
    print(event.event_type, event.position_id)

position.add_event_listener(my_listener)
position.transition_to(PositionState.OPENING)  # listener fires
position.remove_event_listener(my_listener)
```

Listeners that raise exceptions are silently swallowed — the transition proceeds regardless.

---

## Registry statistics

Call `registry.notify_transition(to_state)` **after** a successful `position.transition_to()` to keep the registry statistics current. The registry does not hook into the position event system automatically (separation of concerns).

```python
transition = position.transition_to(PositionState.OPEN)
registry.notify_transition(PositionState.OPEN)
```

---

## Error codes

| Code | Exception | Meaning |
|------|-----------|---------|
| PL-000 | `PositionLifecycleError` | Base |
| PL-001 | `InvalidTransitionError` | Transition rejected by state machine |
| PL-002 | `PositionNotFoundError` | position_id not in registry |
| PL-003 | `DuplicatePositionError` | position_id already registered |
| PL-004 | `PositionValidationError` | Field/invariant violation |
| PL-005 | `PositionRegistryCapacityError` | Registry at max capacity |
| PL-006 | `PositionNotRunningError` | Registry not started |
| PL-007 | `PositionStateError` | Position in unexpected state |

---

## Future modules (do not implement here)

- **Position Engine** — drives the lifecycle from order fills
- **Position Book** — cross-position book keeping
- **Position Risk State** — per-position risk metrics
- **Position Snapshot** — point-in-time portfolio snapshot
- **Position Integration** — sole public entry point to all position subsystems
