# iios.decision.engine — Decision Engine

**C9 Decision Intelligence — Phase 1, Module 2**

The Decision Engine coordinates institutional decision workflows across the
IIOS platform. It orchestrates decision sessions, data collection, evaluation
pipelines and decision publication.

**What it does:**
- Accepts `DecisionRequest` objects via `submit()` (synchronous) or `schedule()` (async queue)
- Runs a deterministic 9-step pipeline per request
- Delegates evaluation to M3 Policy Framework and M4 Optimization Framework
- Produces `DecisionResponse` with a full `DecisionSnapshot`
- Maintains statistics, history, health status, and a priority scheduler

**What it does NOT do:**
- Evaluate decision policies (M3)
- Optimize decisions (M4)
- Execute trades
- Communicate with brokers
- Manage portfolios

---

## Quick Start

```python
from iios.decision.engine import DecisionEngine, DecisionRequest

# Create and start
engine = DecisionEngine()
engine.start()

# Submit a synchronous request
req = DecisionRequest.create(
    "decision-001",
    workflow_id  = "wf-rebalance",
    portfolio_id = "p-main",
    inputs       = {"price": 100.0, "signal": 0.8},
)
response = engine.submit(req)

assert response.is_success
print(response.snapshot.dispatch_results)

# Async scheduling
engine.schedule(req2)

# Introspection
print(engine.health())
print(engine.statistics())
print(engine.status())

engine.stop()
```

### Framework injection (M3 / M4)

```python
class MyPolicyFramework:
    def evaluate(self, context, inputs) -> dict:
        return {"approved": True, "confidence": 0.9}

class MyOptimizationFramework:
    def optimize(self, context, policy_result, inputs) -> dict:
        return {"position_size": 100}

engine.set_policy_framework(MyPolicyFramework())
engine.set_optimization_framework(MyOptimizationFramework())
```

---

## Engine States

The engine follows `LifecycleAwareMixin` states: `CREATED → STARTING → RUNNING → STOPPING → STOPPED`.

---

## Pipeline States (11)

| State | Meaning |
|---|---|
| `IDLE` | Created, not yet started |
| `INITIALIZING` | Starting up |
| `COLLECTING` | Gathering inputs |
| `VALIDATING` | Validating collected inputs |
| `DISPATCHING` | Dispatching to policy/optimization |
| `EVALUATING` | Policy/optimization running |
| `PUBLISHING` | Building and publishing snapshot |
| `COMPLETED` | Terminal success |
| `FAILED` | Terminal failure |
| `CANCELLED` | Terminal cancellation |
| `STOPPED` | Terminal engine-stop |

---

## 9-Step Workflow

```
1. Validate request       — 6-check validation gate
2. Create session         — M1 DecisionLifecycle session (CREATED)
3. Build context          — DecisionEngineContext from request + session IDs
4. Collect inputs         — from request.inputs (no external data fetch)
5. Validate collected     — re-validate with pipeline in VALIDATING state
6. Dispatch               — Policy Framework (M3) → Optimization Framework (M4)
7. Build snapshot         — DecisionSnapshot from pipeline results
8. Publish snapshot       — emit DECISION_PUBLISHED event
9. Complete session       — M1 lifecycle to COMPLETED, record response
```

---

## Scheduling Modes

`DecisionMode` controls how a request is classified (not how it is processed):

| Mode | Value | Description |
|---|---|---|
| `REAL_TIME` | `"real_time"` | Immediate execution required |
| `EVENT_DRIVEN` | `"event_driven"` | Triggered by market event |
| `SCHEDULED` | `"scheduled"` | Periodic/cron-like scheduling |
| `MANUAL` | `"manual"` | Operator-initiated |
| `PRIORITY` | `"priority"` | Elevated urgency |
| `BATCH` | `"batch"` | Bulk processing |

---

## Priority

`DecisionPriority` (IntEnum) controls dequeue order in the scheduler:

```python
CRITICAL = 1   # Dequeued first
HIGH     = 2
MEDIUM   = 3
LOW      = 4
BACKGROUND = 5  # Dequeued last
```

---

## Public API Reference

### `DecisionEngine`

```python
class DecisionEngine(LifecycleAwareMixin):
    def __init__(
        self,
        max_active:             int   = 1_000,
        max_completed:          int   = 5_000,
        max_history:            int   = 2_000,
        max_queue:              int   = 10_000,
        worker_threads:         int   = 4,
        policy_framework:       Optional[PolicyFrameworkProtocol]       = None,
        optimization_framework: Optional[OptimizationFrameworkProtocol] = None,
    ): ...

    def submit(self, request: DecisionRequest) -> DecisionResponse: ...
    def schedule(self, request: DecisionRequest) -> None: ...
    def cancel(self, request_id: str) -> bool: ...
    def query(self, session_id: str) -> Optional[DecisionResponse]: ...

    def history(self) -> DecisionEngineHistory: ...
    def statistics(self) -> DecisionEngineStatistics: ...
    def validate(self, request: DecisionRequest) -> EngineValidationResult: ...
    def health(self) -> DecisionEngineHealth: ...
    def status(self) -> DecisionEngineStatus: ...

    def set_policy_framework(self, framework: PolicyFrameworkProtocol) -> None: ...
    def set_optimization_framework(self, framework: OptimizationFrameworkProtocol) -> None: ...

    def add_listener(self, listener: Callable[[DecisionEngineEvent], None]) -> None: ...
    def remove_listener(self, listener: Callable[[DecisionEngineEvent], None]) -> None: ...
```

### `DecisionRequest.create()`

```python
DecisionRequest.create(
    decision_id:    str,
    *,
    request_id:     Optional[str] = None,          # auto-generated UUID if None
    workflow_id:    str = "",
    portfolio_id:   str = "",
    strategy_id:    str = "",
    decision_mode:  DecisionMode = DecisionMode.REAL_TIME,
    decision_reason: str = "",
    priority:       DecisionPriority = DecisionPriority.MEDIUM,
    deadline_s:     float = 30.0,
    inputs:         Dict[str, Any] = {},
    metadata:       Dict[str, Any] = {},
) -> DecisionRequest
```

---

## Event Reference (8 types)

| Event | Emitted when |
|---|---|
| `DECISION_INITIALIZED` | Session created, pipeline starts |
| `DECISION_STARTED` | Context built, collecting begins |
| `DECISION_COLLECTED` | Inputs gathered from request |
| `DECISION_DISPATCHED` | Policy + optimization complete |
| `DECISION_PUBLISHED` | Snapshot built and stored |
| `DECISION_COMPLETED` | Full pipeline success |
| `DECISION_FAILED` | Pipeline or session failure |
| `DECISION_STOPPED` | Engine-stop during active pipeline |

---

## Validation Checks (6)

| Code | What it checks |
|---|---|
| `SESSION_VALIDITY` | `request_id` is non-empty |
| `PIPELINE_CONSISTENCY` | Pipeline not in terminal state |
| `LIFECYCLE_CONSISTENCY` | `decision_id` is non-empty |
| `SNAPSHOT_CONSISTENCY` | `inputs` is not None |
| `SUBSYSTEM_HEALTH` | Engine is running |
| `INPUT_COMPLETENESS` | `decision_id` non-empty (duplicate guard) |

---

## Statistics (8 counters)

| Counter | Description |
|---|---|
| `decision_sessions` | Total sessions created |
| `decision_requests` | Total requests submitted |
| `decision_pipelines` | Total pipelines executed |
| `average_decision_time_s` | EMA (α=0.1) of total pipeline time |
| `average_collection_time_s` | EMA (α=0.1) of collection phase time |
| `average_dispatch_time_s` | EMA (α=0.1) of dispatch phase time |
| `subsystem_availability` | Fraction of health checks that passed |
| `decision_throughput` | Completions per 60-second sliding window |

---

## Framework Integration

The engine is designed as a pure coordinator. Policy and optimization logic is
always injected from outside:

```python
# M3 Policy Framework protocol
class PolicyFrameworkProtocol(Protocol):
    def evaluate(self, context: DecisionEngineContext, inputs: Dict) -> Dict: ...

# M4 Optimization Framework protocol
class OptimizationFrameworkProtocol(Protocol):
    def optimize(self, context: DecisionEngineContext, policy_result: Dict, inputs: Dict) -> Dict: ...
```

When no framework is injected, the dispatcher uses an empty-dict pass-through.
`dispatch_results` will contain `{"policy": {}, "optimization": {}}`.

---

## Developer Guide

### Thread safety

All public methods are thread-safe. Multiple threads may call `submit()`
concurrently. The scheduler uses an RLock; the registry and statistics use
separate locks.

### Error handling

`submit()` never raises for pipeline/business failures — all errors are
captured in the returned `DecisionResponse` with `status=FAILED` and
`response.error` containing the reason. Only `DecisionEngineNotRunningError`
is raised (before the pipeline starts) if the engine is not running.

### Testing

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/decision/engine/ -v
```

158 tests; 7–8 seconds including concurrency and stress tests.

### Key constants

```python
from iios.decision.engine.constants import (
    ENGINE_SYSTEM_ID,     # "iios:decision:engine"
    VERSION,              # "1.0.0"
    SCHEMA_VERSION,       # "1.0"
    DEFAULT_MAX_ACTIVE,   # 1_000
    DEFAULT_MAX_QUEUE,    # 10_000
    DEFAULT_WORKER_THREADS, # 4
    EMA_ALPHA,            # 0.1
)
```
