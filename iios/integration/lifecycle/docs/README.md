# Integration Lifecycle — C15 M1

The `iios.integration.lifecycle` package implements the **Integration Lifecycle** — the
state machine that governs the operational lifecycle of enterprise integration sessions.

---

## Scope

This module manages **lifecycle state transitions only**.  
It does **not** orchestrate workflows, execute business logic, or call external systems.

---

## Package Contents

| File | Purpose |
|---|---|
| `constants.py` | 13 states, 11 events, enums, valid-transition table |
| `exceptions.py` | 7 typed exceptions (ILC-000 … ILC-006) |
| `integration_context.py` | Immutable per-session correlation context |
| `integration_metadata.py` | Immutable integration type/scope metadata |
| `integration_state.py` | Immutable point-in-time state record |
| `integration_transition.py` | Immutable audit record of a state change |
| `integration_session.py` | Mutable, thread-safe session entity |
| `integration_lifecycle.py` | State machine manager (coordinates all subsystems) |
| `integration_history.py` | Bounded, append-only transition history |
| `integration_statistics.py` | 6-counter rolling statistics |
| `integration_registry.py` | Thread-safe in-memory session registry |
| `integration_factory.py` | Session creation with defaults |
| `integration_validation.py` | 5-check session validator |
| `integration_events.py` | Event data objects and synchronous event bus |

---

## Quick Start

```python
from iios.integration.lifecycle import IntegrationLifecycle

lc = IntegrationLifecycle()
session = lc.create_session("my-workflow")

lc.initialize(session.session_id)
lc.discover(session.session_id)
lc.configure(session.session_id)
lc.validate_session(session.session_id)
lc.mark_ready(session.session_id)
lc.connect(session.session_id)
lc.activate(session.session_id)
lc.complete(session.session_id)
lc.archive(session.session_id)

print(lc.health())
```

---

## Architecture

See [INTEGRATION_LIFECYCLE_GUIDE.md](INTEGRATION_LIFECYCLE_GUIDE.md) for full design.  
See [STATE_DIAGRAM.md](STATE_DIAGRAM.md) for the state machine diagram.  
See [TRANSITION_GUIDE.md](TRANSITION_GUIDE.md) for per-transition rules.  
See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for extension patterns.
