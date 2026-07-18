# Execution Analytics Lifecycle

**Package:** `iios/execution/analytics/lifecycle/`  
**Module:** C8 M1 — Execution Analytics Lifecycle  
**Version:** 1.0.0

---

## Overview

This module implements the **Execution Analytics Lifecycle** for the IIOS
Execution Analytics & Intelligence subsystem.

It manages the state machine for analytics sessions only.  It performs
**no analytics calculations**, no predictive intelligence, no reporting,
and no execution.

---

## State Diagram

```
                     ┌─────────┐
                     │ CREATED │
                     └────┬────┘
                          │ initialize()
                     ┌────▼──────────┐
                     │ INITIALIZING  │
                     └────┬──────────┘
                          │ collect()
                     ┌────▼──────────┐
            ┌────────│  COLLECTING   │◄─────────────────────┐
            │        └────┬──────────┘                      │
            │             │ analyze()                       │
            │        ┌────▼──────────┐                      │
            │        │  ANALYZING    │─────► collect()  ────┘
            │        └────┬──────────┘
            │             │ ready()
            │        ┌────▼──────────┐
            │        │    READY      │
            │        └────┬──────────┘
            │             │ activate()
            │        ┌────▼──────────┐
            │        │    ACTIVE     │─────► analyze() (re-analyze loop)
            │        └────┬──────────┘
            │             │ complete()
            │        ┌────▼──────────┐
            │        │  COMPLETED    │
            │        └────┬──────────┘
            │             │ archive()
  pause()   │        ┌────▼──────────┐
  (any      │        │   ARCHIVED    │ (terminal)
  active)   │        └───────────────┘
            │
            ▼
      ┌──────────┐    resume()   ┌──────────┐
      │  PAUSED  │──────────────►│ RESUMING │──► collect / analyze / ready / active
      └──────────┘               └──────────┘

  Any state (except ARCHIVED) ──► FAILED ──► ARCHIVED
```

---

## Valid Transitions

| From          | To                                        |
|---------------|-------------------------------------------|
| CREATED       | INITIALIZING, FAILED                      |
| INITIALIZING  | COLLECTING, FAILED                        |
| COLLECTING    | ANALYZING, PAUSED, FAILED                 |
| ANALYZING     | READY, COLLECTING, PAUSED, FAILED         |
| READY         | ACTIVE, PAUSED, FAILED                    |
| ACTIVE        | COMPLETED, PAUSED, ANALYZING, FAILED      |
| PAUSED        | RESUMING, FAILED                          |
| RESUMING      | COLLECTING, ANALYZING, READY, ACTIVE, FAILED |
| COMPLETED     | ARCHIVED                                  |
| FAILED        | ARCHIVED                                  |
| ARCHIVED      | *(terminal — no transitions)*             |

---

## Quick Start

```python
from iios.execution.analytics.lifecycle import (
    AnalyticsLifecycle,
    AnalyticsScope,
    AnalyticsMode,
    AnalyticsTrigger,
)

# 1. Create and start lifecycle
lc = AnalyticsLifecycle()
lc.start()

# 2. Create a session
session = lc.create(
    execution_session_id = "exec-2026-001",
    analytics_scope      = AnalyticsScope.EXECUTION,
    analytics_mode       = AnalyticsMode.REAL_TIME,
    analytics_trigger    = AnalyticsTrigger.AUTOMATIC,
)

# 3. Drive through states
lc.initialize(session.session_id)
lc.collect(session.session_id)
lc.analyze(session.session_id)
lc.ready(session.session_id)
lc.activate(session.session_id)
lc.complete(session.session_id)
lc.archive(session.session_id)

# 4. Check statistics
stats = lc.statistics()
print(stats.sessions_created)    # 1
print(stats.sessions_completed)  # 1
print(stats.sessions_archived)   # 1

lc.stop()
```

---

## Pause and Resume

```python
session = lc.create(execution_session_id="exec-002")
lc.initialize(session.session_id)
lc.collect(session.session_id)

# Pause mid-collection
lc.pause(session.session_id)

# Resume and continue
lc.resume(session.session_id)
lc.collect(session.session_id)   # re-enter COLLECTING from RESUMING
lc.analyze(session.session_id)
```

---

## Context-Based Creation

```python
from iios.execution.analytics.lifecycle import make_analytics_context

ctx = make_analytics_context(
    execution_session_id = "exec-003",
    analytics_scope      = AnalyticsScope.PORTFOLIO,
    analytics_mode       = AnalyticsMode.BATCH,
    portfolio_id         = "portfolio-alpha",
)
session = lc.create_from_context(ctx)
```

---

## Event Listeners

```python
def on_event(event):
    print(f"[{event.event_type.value}] session={event.session_id}")

lc.add_listener(on_event)
lc.create(execution_session_id="exec-004")
# prints: [analytics_created] session=<uuid>
```

---

## Module Structure

| File                        | Purpose                                      |
|-----------------------------|----------------------------------------------|
| `analytics_lifecycle.py`    | **Primary public API**                       |
| `analytics_session.py`      | Core mutable domain object                   |
| `analytics_state.py`        | Immutable state record + transition guard    |
| `analytics_transition.py`   | Immutable transition record                  |
| `analytics_context.py`      | Immutable session creation context           |
| `analytics_metadata.py`     | Immutable supplementary session metadata     |
| `analytics_history.py`      | Bounded history of sessions/events           |
| `analytics_statistics.py`   | Thread-safe runtime statistics               |
| `analytics_registry.py`     | Lifecycle-aware session store                |
| `analytics_factory.py`      | Session creation                             |
| `analytics_validation.py`   | Context and session validation               |
| `analytics_events.py`       | Immutable domain events                      |
| `constants.py`              | States, transitions, enums, limits           |
| `exceptions.py`             | Exception hierarchy (AL-000 … AL-007)        |
| `__init__.py`               | Public API surface                           |

---

## Exception Codes

| Code   | Exception                           | Meaning                              |
|--------|-------------------------------------|--------------------------------------|
| AL-000 | `AnalyticsError`                    | Base exception                       |
| AL-001 | `AnalyticsNotRunningError`          | Engine not started                   |
| AL-002 | `AnalyticsSessionNotFoundError`     | Session ID not in registry           |
| AL-003 | `AnalyticsInvalidTransitionError`   | Transition rejected by state machine |
| AL-004 | `AnalyticsValidationError`          | Context/session validation failure   |
| AL-005 | `AnalyticsSessionAlreadyExistsError`| Duplicate session ID                 |
| AL-006 | `AnalyticsSessionTerminalError`     | Session in ARCHIVED (immutable) state|
| AL-007 | `AnalyticsHistoryError`             | History operation failure            |

---

## Scope

This module is **lifecycle-only**.  Future C8 modules will add:

- Analytics Engine (M2)
- Performance Analytics Framework (M3)
- Predictive Intelligence Framework (M4)
- Analytics Snapshot (M5)
- Analytics Integration (M6)
