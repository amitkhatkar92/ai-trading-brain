# Developer Guide — C15 M1 Integration Lifecycle

## Adding a New Integration Type

Add the new value to `IntegrationType` in `constants.py`:

```python
class IntegrationType(str, Enum):
    ...
    MY_CUSTOM = "my_custom"
```

No other files require changes — `IntegrationMetadata.integration_type` accepts any
`IntegrationType` member.

---

## Adding a Lifecycle Listener

```python
from iios.integration.lifecycle import IntegrationLifecycle, IntegrationLifecycleEvent

lc = IntegrationLifecycle()

def on_event(event: IntegrationLifecycleEvent) -> None:
    print(f"[{event.event_type.value}] session={event.session_id}")

lc.event_bus.add_listener(on_event)
```

Listeners are called synchronously in registration order.  Exceptions are logged and
suppressed so a bad listener cannot crash the lifecycle.

---

## Running Validation

```python
from iios.integration.lifecycle import IntegrationValidator

validator = IntegrationValidator()
report    = validator.validate(session)

if not report.passed:
    print(f"Failed checks: {report.failed_checks}")
```

---

## Custom Registry Capacity

```python
from iios.integration.lifecycle import IntegrationLifecycle, IntegrationRegistry

registry = IntegrationRegistry(max_sessions=500)
lc       = IntegrationLifecycle(registry=registry)
```

---

## Sharing a History Instance

If multiple `IntegrationLifecycle` instances should share a history (e.g. across
worker threads):

```python
from iios.integration.lifecycle import IntegrationHistory, IntegrationLifecycle

shared_history = IntegrationHistory(max_transitions=200_000)
lc1 = IntegrationLifecycle(history=shared_history)
lc2 = IntegrationLifecycle(history=shared_history)
```

---

## Thread Safety Rules

- `IntegrationSession.transition_to()` is protected by an internal `threading.Lock()`.
- `IntegrationRegistry` operations are protected by a lock.
- `IntegrationHistory` append operations are protected by a lock.
- `IntegrationLifecycleEventBus` listener iteration is protected by a lock.
- `IntegrationLifecycleStatistics` increments are protected by a lock.

---

## Testing Patterns

Always construct a fresh `IntegrationLifecycle()` per test to avoid state leakage.

```python
def test_full_lifecycle():
    lc      = IntegrationLifecycle()
    session = lc.create_session("wf-test")
    sid     = session.session_id

    lc.initialize(sid)
    lc.discover(sid)
    lc.configure(sid)
    lc.validate_session(sid)
    lc.mark_ready(sid)
    lc.connect(sid)
    lc.activate(sid)
    lc.complete(sid)
    lc.archive(sid)

    s = lc.get_session(sid)
    assert s.state.value == "archived"
```

---

## Extension Points

| Need | Extension |
|---|---|
| Persistent sessions | Subclass `IntegrationRegistry`; override `register` / `get` |
| Durable history | Subclass `IntegrationHistory`; append to a DB in `record_transition` |
| Async events | Wrap `IntegrationLifecycleEventBus.emit` to push to a queue |
| Custom validation | Add a 6th check in a subclass of `IntegrationValidator` |
