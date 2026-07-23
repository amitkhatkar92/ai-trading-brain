# iios.supervisor.engine — AI Supervisor Engine

**C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2**

## Overview

The `SupervisorEngine` is the Institutional AI Supervisor Engine — the primary
orchestration component for enterprise-wide supervision workflows in the IIOS
platform.

It coordinates an **8-phase pipeline** for every supervision request:

```
Initialize → Discover → Collect → Validate → Dispatch →
Supervise/Monitor → Publish → Complete
```

## Responsibilities

The engine DOES:
- Accept and process supervisor workflow requests
- Coordinate the 8-phase workflow pipeline
- Drive lifecycle sessions via M1 SupervisorLifecycle
- Route to M3 Governance Policy Framework and M4 Autonomous Governance Framework
  when registered
- Publish supervision snapshots
- Expose health, status, statistics, and query introspection

The engine does NOT:
- Evaluate governance policies (M3 responsibility)
- Perform AI reasoning or autonomous governance (M4 responsibility)
- Make trading decisions
- Execute trades
- Communicate with brokers

## Quickstart

```python
from iios.supervisor.engine import SupervisorEngine

engine = SupervisorEngine()
engine.start()

# Simple supervision
response = engine.supervise("supervision-run-001", "enterprise")
if response.is_success:
    print(f"Snapshot: {response.snapshot.snapshot_id}")

# With inputs
response = engine.supervise(
    "sup-002",
    "portfolio",
    inputs={"portfolio_snapshot": {...}, "risk_snapshot": {...}},
)

engine.stop()
```

## Components

| Class | Role |
|---|---|
| `SupervisorEngine` | PRIMARY PUBLIC INTERFACE |
| `SupervisorScheduler` | Priority-queue scheduler (heapq) |
| `SupervisorDispatcher` | Routes to M3 / M4 frameworks |
| `SupervisorSessionManager` | M1 SupervisorLifecycle wrapper |
| `SupervisorEngineRegistry` | Thread-safe pipeline / request / response store |
| `SupervisorEngineValidator` | 6-check structural validation |
| `SupervisorEngineHealth` | Component health aggregation |
| `SupervisorEngineStatus` | Immutable status snapshot |
| `SupervisorEngineStatistics` | Welford online statistics |
| `SupervisorEngineHistory` | Bounded audit history deques |
| `SupervisorEngineFactory` | Central value-object factory |
| `SupervisorWorkflowManager` | Internal 8-phase pipeline coordinator |

## Workflow Types

| Enum | Description |
|---|---|
| `ENTERPRISE_HEALTH_REVIEW` | Full enterprise health supervision |
| `SUBSYSTEM_SUPERVISION` | Deep supervision of a specific subsystem |
| `AUTONOMOUS_SESSION_MANAGEMENT` | Autonomous session lifecycle management |
| `PLATFORM_STATUS_REVIEW` | Platform-wide status review |
| `GOVERNANCE_PREPARATION` | Prepare governance artefacts |
| `SNAPSHOT_AGGREGATION` | Collect and aggregate subsystem snapshots |
| `OPERATIONAL_MONITORING` | Ongoing operational monitoring |
| `PERIODIC_SUPERVISION` | Scheduled periodic supervision |

## Governance Framework Hooks

M3 and M4 frameworks can be plugged in without restarting the engine:

```python
# Register M3 AI Governance Policy Framework
engine.register_governance_framework(my_governance_framework)

# Register M4 Autonomous Governance Framework
engine.register_autonomous_framework(my_autonomous_framework)
```

Framework callables receive `(pipeline: SupervisorPipeline, request: SupervisorRequest)`.
Exceptions from framework hooks are caught and logged — they never fail the pipeline.

## Event Listeners

```python
def on_event(event: SupervisorEngineEvent) -> None:
    print(f"{event.event_type.value} — {event.supervision_id}")

engine.add_listener(on_event)
# ...
engine.remove_listener(on_event)
```

## Health & Monitoring

```python
# Health report
health = engine.health()
# {"overall": "healthy", "components": {...}, "checked_at": 1234567890.0}

# Status snapshot
status = engine.status()
status.to_dict()

# Running statistics
stats = engine.statistics()
# {"total_requests": 42, "mean_elapsed_s": 0.012, ...}

# Query recent responses
responses = engine.query(supervision_id="sup-001", n=10)
```

## Error Hierarchy

```
SupervisorEngineError (SE-000)
├── SupervisorEngineNotRunningError (SE-001)
├── SupervisorSessionError (SE-002) — .session_id
├── SupervisorPipelineError (SE-003) — .pipeline_id
├── SupervisorDispatchError (SE-004) — .workflow_type
├── SupervisorCollectionError (SE-005) — .missing_inputs
├── SupervisorPublicationError (SE-006) — .supervision_id
├── SupervisorEngineValidationError (SE-007) — .failed_checks
├── SupervisorSchedulerError (SE-008)
└── SupervisorEngineCapacityError (SE-009) — .limit
```

## Thread Safety

All public methods on `SupervisorEngine` are thread-safe. Concurrent `supervise()`
calls are supported up to `max_sessions` (default: 200).

## Version

`VERSION = "1.0.0"` | `SCHEMA_VERSION = "1.0"`
