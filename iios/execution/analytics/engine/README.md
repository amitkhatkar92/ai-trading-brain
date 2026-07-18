# Execution Analytics Engine

**C8 Execution Analytics & Intelligence — Phase 1, Module 2**

---

## Overview

The Execution Analytics Engine (`ExecutionAnalyticsEngine`) coordinates all analytics activities across the Execution Intelligence subsystem. It orchestrates analytics workflows, analytics sessions, and analytics pipelines.

**Primary entry point:** `ExecutionAnalyticsEngine`

---

## What This Engine Does

| Responsibility | Detail |
|---|---|
| Accept analytics requests | Via `process()`, `submit()`, or `process_with_context()` |
| Validate requests | Request and context validation before any workflow |
| Manage analytics sessions | Delegates to M1 `AnalyticsLifecycle` via `AnalyticsSessionManager` |
| Dispatch pipelines | Via `AnalyticsDispatcher` → M3/M4 frameworks |
| Publish snapshots | `AnalyticsSnapshot` published after successful dispatch |
| Maintain statistics | `EngineAnalyticsStatistics` — counts, averages, rates |
| Maintain history | `EngineAnalyticsHistory` — bounded history of all workflow items |
| Emit domain events | 8 event types via registered listeners |
| Scheduler integration | Priority queue for periodic / event-driven / scheduled analytics |
| Health and status | `health()` and `status()` endpoints |

---

## What This Engine Does NOT Do

- **No performance calculations** — delegated to M3 Performance Analytics Framework
- **No predictive models** — delegated to M4 Predictive Intelligence Framework
- **No reporting or visualization**
- **No trade execution**

---

## Quick Start

```python
from iios.execution.analytics.engine import ExecutionAnalyticsEngine, make_analytics_request

engine = ExecutionAnalyticsEngine()
engine.start()

# Simple on-demand analytics
response = engine.submit("execution-session-id-001")
print(response.is_success, response.processing_ms)

# Full request
request = make_analytics_request(
    "execution-session-id-002",
    priority = 1,
    reason   = "post-trade analytics",
)
response = engine.process(request)
print(response.status, response.snapshot.engine_state)

engine.stop()
```

---

## Analytics Workflow

```
Receive Request
      │
      ▼
 [1] Validate Request
      │ REJECTED on failure
      ▼
 [2] Register Request
      │
      ▼
 [3] Build/Accept Context
      │
      ▼
 [4] Validate Context
      │ FAILED on failure
      ▼
 [5] Create Analytics Session (M1 AnalyticsLifecycle)
      │
      ▼
 [6] Advance Session States
      │  CREATED → INITIALIZING → COLLECTING → ANALYZING → READY → ACTIVE
      ▼
 [7] Create Analytics Pipeline
      │
      ▼
 [8] Dispatch Pipeline → M3 (Performance Analytics)
      │                 → M4 (Predictive Intelligence)
      ▼
 [9] Publish Analytics Snapshot
      │
      ▼
[10] Complete Session (ACTIVE → COMPLETED → ARCHIVED)
      │
      ▼
[11] Record Statistics + History
      │
      ▼
[12] Emit COMPLETED Event
      │
      ▼
Return AnalyticsResponse (SUCCESS)
```

---

## Engine States (per analytics cycle)

| State | Meaning |
|---|---|
| `IDLE` | Ready to accept a new request |
| `INITIALIZING` | Session initialization in progress |
| `COLLECTING` | Collecting execution data |
| `VALIDATING` | Validating collected data |
| `DISPATCHING` | Dispatching pipeline to frameworks |
| `ANALYZING` | Awaiting framework analysis |
| `PUBLISHING` | Publishing analytics snapshot |
| `COMPLETED` | Cycle completed successfully |
| `FAILED` | Cycle failed |
| `STOPPED` | Engine stopped (terminal) |

---

## Scheduler Guide

The engine includes a priority-based scheduler for periodic, event-driven, and scheduled analytics.

```python
# On-demand (immediate)
engine.schedule("exec-session-id", priority=5)

# Periodic
engine.schedule_periodic("exec-session-id", interval_s=300.0)

# Dequeue and process one
response = engine.dequeue_and_process()

# Dequeue and process all due
responses = engine.dequeue_and_process_all()
```

Priority rules:
- Lower number = higher priority (1 = highest, 10 = lowest)
- Equal priorities are processed in FIFO order

---

## Framework Registration (M3/M4)

When M3 and M4 are implemented, register them with the engine:

```python
engine.register_performance_framework(m3_performance_framework)
engine.register_predictive_framework(m4_predictive_framework)
```

The dispatcher will call:
- `m3.process(request_id)` for performance analytics
- `m4.predict(request_id)` for predictive intelligence

Until frameworks are registered, analytics cycles complete without framework delegation.

---

## API Reference

### `ExecutionAnalyticsEngine`

| Method | Description |
|---|---|
| `start()` / `stop()` | Lifecycle |
| `initialize()` | Reset cycle state to IDLE |
| `process(request, context?)` | Full workflow for a request |
| `process_with_context(request, context)` | Process with explicit context |
| `submit(execution_session_id)` | Convenience: create + process |
| `collect(session_id, **snapshots)` | Build analytics context |
| `validate(request)` | Validate without processing |
| `schedule(session_id)` | Queue an on-demand request |
| `schedule_periodic(session_id, interval_s)` | Queue periodic analytics |
| `dequeue_and_process()` | Process next due request |
| `dequeue_and_process_all()` | Process all due requests |
| `publish(snapshot)` | Manual snapshot publish |
| `query(request_id)` | Find latest response for request |
| `statistics()` | Independent statistics copy |
| `history()` | Live history reference |
| `health()` | Engine health assessment |
| `status()` | Engine status snapshot |
| `add_listener(fn)` / `remove_listener(fn)` | Event listeners |
| `register_performance_framework(fw)` | Register M3 |
| `register_predictive_framework(fw)` | Register M4 |

---

## Events

| Event | Trigger |
|---|---|
| `ANALYTICS_INITIALIZED` | Session created |
| `ANALYTICS_STARTED` | Session moved to INITIALIZING |
| `ANALYTICS_COLLECTED` | Collection phase complete |
| `ANALYTICS_DISPATCHED` | Pipeline dispatched |
| `ANALYTICS_PUBLISHED` | Snapshot published |
| `ANALYTICS_COMPLETED` | Workflow completed |
| `ANALYTICS_FAILED` | Workflow failed |
| `ANALYTICS_STOPPED` | Engine stopped |

```python
def on_event(event: EngineAnalyticsEvent) -> None:
    print(event.event_type, event.request_id)

engine.add_listener(on_event)
```

---

## Module Structure

| File | Class / Function | Description |
|---|---|---|
| `execution_analytics_engine.py` | `ExecutionAnalyticsEngine` | **PRIMARY PUBLIC INTERFACE** |
| `analytics_manager.py` | `AnalyticsManager` | Workflow coordinator |
| `analytics_context.py` | `EngineAnalyticsContext` | Request context with input snapshots |
| `analytics_request.py` | `AnalyticsRequest` | Immutable analytics request |
| `analytics_response.py` | `AnalyticsResponse`, `AnalyticsSnapshot` | Engine outputs |
| `analytics_pipeline.py` | `AnalyticsPipeline` | Pipeline descriptor |
| `analytics_scheduler.py` | `AnalyticsScheduler` | Priority-based request queue |
| `analytics_dispatcher.py` | `AnalyticsDispatcher` | M3/M4 delegation |
| `analytics_session_manager.py` | `AnalyticsSessionManager` | M1 lifecycle bridge |
| `analytics_registry.py` | `EngineAnalyticsRegistry` | In-flight request store |
| `analytics_validation.py` | `EngineAnalyticsValidator` | Request/context/pipeline validation |
| `analytics_statistics.py` | `EngineAnalyticsStatistics` | Thread-safe counters + averages |
| `analytics_history.py` | `EngineAnalyticsHistory` | Bounded workflow history |
| `analytics_events.py` | `EngineAnalyticsEvent` | Immutable domain events |
| `analytics_factory.py` | `EngineAnalyticsFactory` | Object factory |
| `analytics_health.py` | `AnalyticsEngineHealth` | Health assessment |
| `analytics_status.py` | `AnalyticsEngineStatus` | Status snapshot |
| `constants.py` | — | Enums, system IDs, limits |
| `exceptions.py` | — | Exception hierarchy AE-000…AE-009 |
| `__init__.py` | — | Public API exports |

---

## Exception Codes

| Code | Exception | Cause |
|---|---|---|
| AE-000 | `AnalyticsEngineError` | Base exception |
| AE-001 | `AnalyticsEngineNotRunningError` | Engine not started |
| AE-002 | `AnalyticsEngineAlreadyRunningError` | Double start |
| AE-003 | `AnalyticsRequestNotFoundError` | Unknown request_id |
| AE-004 | `AnalyticsRequestValidationError` | Bad request fields |
| AE-005 | `AnalyticsPipelineError` | Pipeline coordination error |
| AE-006 | `AnalyticsSessionManagerError` | Session mapping error |
| AE-007 | `AnalyticsDispatchError` | Framework dispatch failure |
| AE-008 | `AnalyticsSchedulerError` | Scheduler queue full |
| AE-009 | `AnalyticsPublishError` | Snapshot publish error |

---

## Design Constraints

1. **Engine only coordinates** — all analytics calculations happen in M3/M4
2. **LifecycleAwareMixin** — start/stop lifecycle enforced throughout
3. **Thread-safe** — all mutable state protected by RLock/Lock
4. **High-throughput** — concurrent requests are fully supported
5. **No placeholders** — M3/M4 stubs deferred gracefully via dispatcher
