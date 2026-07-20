# iios.execution.analytics.integration — C8 M6

## Overview

The **Execution Analytics Integration** subsystem is the sixth and final module
of the C8 Execution Analytics layer.  It coordinates the five upstream analytics
components (M1-M5) as a single operational unit and delivers a clean, lifecycle-aware
interface to callers.

```
M1 AnalyticsLifecycle  →  session creation + state machine
M2 ExecutionAnalyticsEngine  →  analytics pipeline dispatch
M3 PerformanceAnalyticsEngine  →  KPI / scorecard reports
M4 PredictiveIntelligenceEngine  →  forecasts + risk assessment
M5 AnalyticsSnapshotFactory  →  snapshot build + publication
              ↓
ExecutionAnalyticsIntegration  ← ONLY public entry point
```

This module performs **no analytics calculations, no predictions, no reporting, and
no trade execution**.  It only orchestrates.

---

## Public API

```python
from iios.execution.analytics.integration import (
    ExecutionAnalyticsIntegration,
    AnalyticsIntegrationRequest,
)

integration = ExecutionAnalyticsIntegration()
integration.initialize()
integration.start()

request = AnalyticsIntegrationRequest(execution_session_id="exec-001")
response = integration.submit(request)

snapshot = response.snapshot   # ExecutionAnalyticsSnapshot (M5 object)

health    = integration.health()     # AnalyticsIntegrationHealth
status    = integration.status()     # AnalyticsIntegrationStatus
stats     = integration.statistics() # AnalyticsIntegrationStatistics
result    = integration.validate()   # IntegrationValidationResult
history   = integration.history()    # List[AnalyticsIntegrationResponse]

integration.restart()  # stop + start
integration.stop()
```

### Method reference

| Method | Description |
|--------|-------------|
| `initialize()` | Allocate and wire all sub-components (idempotent) |
| `start()` | Start all sub-components |
| `stop()` | Stop all sub-components |
| `restart()` | Stop then start |
| `submit(request)` | Run the full M1-M5 pipeline; returns `AnalyticsIntegrationResponse` |
| `query(...)` | Query previously published snapshots from M5 store |
| `snapshot()` | Latest published `ExecutionAnalyticsSnapshot` |
| `health()` | Per-component + overall `AnalyticsIntegrationHealth` |
| `status()` | `AnalyticsIntegrationStatus` snapshot |
| `statistics()` | `AnalyticsIntegrationStatistics` with 7 counters |
| `validate(...)` | 7-check `IntegrationValidationResult` |
| `history()` | Retained `AnalyticsIntegrationResponse` list |
| `events()` | Retained `AnalyticsIntegrationEvent` list |
| `snapshot_records()` | Retained `IntegrationSnapshotRecord` list |

---

## Workflow (`submit`)

```
1.  Validate request structure
2.  Register in AnalyticsIntegrationRegistry
3.  M1: Create analytics session (AnalyticsLifecycle.create)
4.  M1: Advance lifecycle → INITIALIZING → COLLECTING → ANALYZING → READY → ACTIVE
5.  M2: Invoke ExecutionAnalyticsEngine.process  (gracefully degraded)
6.  M3: Run PerformanceAnalyticsEngine.process   (gracefully degraded)
7.  M4: Run PredictiveIntelligenceEngine.submit  (gracefully degraded)
8.  M5: Build + publish ExecutionAnalyticsSnapshot
9.  M1: Complete analytics session
10. Build AnalyticsIntegrationResponse (SUCCESS / PARTIAL / FAILED / REJECTED)
11. Record statistics, events, history
```

Steps 5-8 are independently guarded by `try/except`.  Failure in any one
step degrades the result (PARTIAL) rather than raising.

---

## Graceful degradation

| Step | Required for SUCCESS? | On failure |
|------|-----------------------|------------|
| M1 session create | ✅ Yes | Returns FAILED immediately |
| M1 lifecycle advance | No | Stops advancing at error; continues |
| M2 engine invoke | No | Logged, continues |
| M3 performance | No | `performance_report=None` passed to M5 |
| M4 predictive | No | `prediction_report=None` passed to M5 |
| M5 snapshot build | No | `snapshot=None` → PARTIAL response |

---

## Statistics (7 counters)

1. **Analytics Requests** — total requests received
2. **Analytics Sessions** — total M1 sessions created
3. **Analytics Snapshots Published** — total M5 snapshots published
4. **Performance Reports Generated** — total M3 reports produced
5. **Forecasts Generated** — total M4 prediction reports produced
6. **Subsystem Availability** — rolling availability ratio (0.0–1.0)
7. **Average Response Time (ms)** — EMA of processing latency

---

## Validation (7 checks)

| Code | Check |
|------|-------|
| `LIFECYCLE_CONSISTENCY` | M1 lifecycle component is running |
| `ENGINE_CONSISTENCY` | M2 analytics engine is running |
| `PERFORMANCE_CONSISTENCY` | M3 is running (when `include_performance=True`) |
| `PREDICTION_CONSISTENCY` | M4 is running (when `include_predictions=True`) |
| `SNAPSHOT_CONSISTENCY` | M5 factory/store is running |
| `INTEGRATION_CONSISTENCY` | Integration manager is in a running state |
| `SUBSYSTEM_READINESS` | Request fields are structurally valid |

---

## Events (8 types)

| Event | When |
|-------|------|
| `ANALYTICS_INITIALIZED` | `initialize()` completes |
| `ANALYTICS_STARTED` | `start()` completes |
| `ANALYTICS_COMPLETED` | A request finishes |
| `ANALYTICS_STOPPED` | `stop()` completes |
| `ANALYTICS_RESTARTED` | `restart()` completes |
| `ANALYTICS_VALIDATED` | `validate()` is called |
| `ANALYTICS_HEALTH_CHANGED` | Overall health level changes |
| `ANALYTICS_SNAPSHOT_PUBLISHED` | M5 snapshot is published |

---

## Health monitoring

The integration assesses health of all five components:

| Component | Blocking for operational? |
|-----------|--------------------------|
| M1 Lifecycle | ✅ Yes |
| M2 Engine | ✅ Yes |
| M3 Performance | No (degraded but operational) |
| M4 Predictive | No (degraded but operational) |
| M5 Snapshot | ✅ Yes |

Overall score is a weighted average (M1/M2/M5 weight=2, M3/M4 weight=1).
Thresholds: `≥0.8` → HEALTHY, `≥0.5` → DEGRADED, `<0.5` → CRITICAL.

---

## Package structure

```
iios/execution/analytics/integration/
├── __init__.py                              ← public exports
├── execution_analytics_integration_engine.py  ← PRIMARY PUBLIC INTERFACE
├── analytics_integration_manager.py           ← M1-M5 orchestration
├── analytics_integration_context.py           ← context value object
├── analytics_integration_request.py           ← request value object
├── analytics_integration_response.py          ← response value object
├── analytics_integration_snapshot.py          ← snapshot record wrapper
├── analytics_integration_registry.py          ← in-flight request registry
├── analytics_integration_validation.py        ← 7-check validator
├── analytics_integration_health.py            ← component + overall health
├── analytics_integration_status.py            ← status snapshot
├── analytics_integration_statistics.py        ← 7-counter statistics
├── analytics_integration_history.py           ← bounded history
├── analytics_integration_events.py            ← 8 event types + factories
├── analytics_component_registry.py            ← manages M1-M5 lifecycle
├── analytics_component_factory.py             ← creates M1-M5 instances
├── constants.py                               ← enums, IDs, defaults
└── exceptions.py                              ← EAI-000 through EAI-007
```

---

## Exceptions

| Code | Class | When |
|------|-------|------|
| EAI-000 | `IntegrationError` | Base class |
| EAI-001 | `IntegrationNotRunningError` | Operation on stopped subsystem |
| EAI-002 | `IntegrationNotReadyError` | `start()` without `initialize()` |
| EAI-003 | `IntegrationRequestError` | Malformed request |
| EAI-004 | `IntegrationValidationError` | Validation failure |
| EAI-005 | `IntegrationComponentError` | Component start/stop failure |
| EAI-006 | `IntegrationTimeoutError` | Operation timeout |
| EAI-007 | `IntegrationAlreadyRunningError` | `initialize()` while running |

---

## Tests

160 tests in `tests/unit/execution/analytics/integration/test_integration.py`.

Coverage areas: lifecycle, public API, workflow, graceful degradation,
validation, health, status, statistics, history, events, registry,
concurrency, regression.
