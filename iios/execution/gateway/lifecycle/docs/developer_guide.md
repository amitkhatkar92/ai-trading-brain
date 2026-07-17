# Developer Guide — Execution Gateway Lifecycle

## Adding a new lifecycle state

1. Add the value to `GatewayState` in `constants.py`
2. Update `VALID_TRANSITIONS` in `constants.py`
3. Update sentinel sets (`ACTIVE_STATES`, `OUTCOME_STATES`, etc.) as appropriate
4. Add a factory function in `gateway_events.py`
5. Add the state → event mapping in `gateway_request.py` (`_STATE_EVENT_FACTORY`)
6. Add a transition method in `GatewayLifecycle` (`gateway_lifecycle.py`)
7. Update `state_diagram.md`
8. Add test cases in `TestStateMachine` and `TestGatewayLifecycle`

## Adding a new transition method

Methods in `GatewayLifecycle` follow this template:

```python
def my_transition(
    self,
    gateway_id: str,
    *,
    actor:  str = ACTOR_LIFECYCLE,
    reason: str = "Default reason",
) -> GatewayRequest:
    self._assert_running()
    request = self._get_request(gateway_id)
    request.transition_to(GatewayState.MY_TARGET, actor=actor, reason=reason)
    with self._lock:
        # Update statistics as needed
        self._stats.record_transition()
    _log.debug("My transition.", gateway_id=gateway_id)
    return request
```

## Adding metadata to requests

`GatewayMetadata` is the mutable store:

```python
request.metadata.set_tag("broker", "dhan")
request.metadata.set_priority(10)
request.metadata.set_notes("High priority — pre-market")
```

## Extending GatewayContext

`GatewayContext` is a frozen dataclass.  Add new fields via the
`execution_payload` dict rather than modifying the dataclass:

```python
ctx = make_gateway_context("EX-1", "ORD-1", "PORT-1", "STRAT-1",
          execution_payload={"lot_size": 50, "tick_size": 0.05})
```

## Thread safety

- `GatewayRequest` uses an internal `threading.RLock` for all state mutations.
- `GatewayRegistry` uses `threading.Lock` for the store.
- `GatewayLifecycle` uses `threading.RLock` for statistics and event listener mutations.
- Multiple threads may call `evaluate()`, `transition_to()`, and `create()` concurrently.

## Exception handling

| Code   | Exception                         | When                                     |
|--------|-----------------------------------|------------------------------------------|
| EGL-001 | `InvalidGatewayTransitionError`  | `transition_to()` rejects target state   |
| EGL-002 | `GatewayRequestNotFoundError`    | `get()` / any method with unknown ID     |
| EGL-003 | `DuplicateGatewayRequestError`   | `register()` called with existing ID    |
| EGL-004 | `GatewayValidationError`         | `raise_if_invalid()` on failed result   |
| EGL-005 | `GatewayRegistryCapacityError`   | Registry at max capacity                 |
| EGL-006 | `GatewayLifecycleNotRunningError` | Any write before `start()`             |
| EGL-007 | `GatewayStateError`              | Unexpected state for operation           |

## Testing conventions

- Use the `_lifecycle()` helper to get a started `GatewayLifecycle`.
- Use the `_full_workflow()` helper to drive through the happy path.
- Call `lc.stop()` after every test that starts a lifecycle.
- Test invalid transitions explicitly (`pytest.raises(InvalidGatewayTransitionError)`).
- Patch `_state` directly only in `TestStateMachine.test_all_valid_transitions_accepted`
  — never in other tests.

## Version bump

1. Update `VERSION` in `constants.py`
2. Add entry to project `ARCHITECTURE.md`
