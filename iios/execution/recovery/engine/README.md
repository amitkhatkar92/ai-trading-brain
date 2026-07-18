# Execution Recovery Engine

**C7 Execution Recovery & Resilience — Phase 1, Module 2**

## Overview

The Execution Recovery Engine (`iios.execution.recovery.engine`) coordinates
all recovery activities across the execution subsystem.

It orchestrates recovery workflows, manages recovery sessions, and delegates
to the Recovery Policy Framework (M3) and the Failover Framework (M4).

**This module performs no recovery actions itself.** It is a pure coordinator.

---

## What it does

| Responsibility              | Component             |
|-----------------------------|-----------------------|
| Receive recovery requests   | `ExecutionRecoveryEngine` |
| Validate requests/context   | `RecoveryEngineValidator` |
| Manage recovery sessions    | `RecoverySessionManager` → M1 |
| Run 10-stage pipeline       | `RecoveryPipeline`    |
| Schedule requests           | `RecoveryScheduler`   |
| Dispatch to M3/M4 via ports | `RecoveryDispatcher`  |
| Publish snapshots           | `RecoveryFactory`     |
| Track statistics            | `RecoveryEngineStatistics` |
| Bounded history             | `RecoveryEngineHistory` |
| Emit domain events          | `RecoveryEngineEvent` |

## What it does NOT do

- No policy logic — delegated to **M3 RecoveryPolicyFramework** via `PolicyFrameworkPort`
- No failover logic — delegated to **M4 FailoverFramework** via `FailoverFrameworkPort`
- No broker communication
- No trade execution

---

## Quick Start

```python
from iios.execution.recovery.engine import (
    ExecutionRecoveryEngine,
    make_recovery_request,
    make_failure_context,
    RecoveryRequestPriority,
    RecoveryRequestType,
)

engine = ExecutionRecoveryEngine()
engine.start()

request = make_recovery_request(
    execution_session_id = "exec-001",
    subsystem_id         = "execution_gateway",
    failure_context      = make_failure_context(
        subsystem_id   = "execution_gateway",
        failure_type   = "GATEWAY_TIMEOUT",
        failure_reason = "Connection timed out after 30s",
        severity       = "HIGH",
    ),
    recovery_reason = "Automatic recovery triggered by health monitor",
    priority        = RecoveryRequestPriority.HIGH,
    request_type    = RecoveryRequestType.AUTOMATIC,
)

response = engine.start_recovery(request)

if response.is_success:
    print(f"Recovered in {response.duration_ms:.1f}ms")
else:
    print(f"Failed: {response.error_message}")

engine.stop()
```

---

## Recovery Pipeline (10 stages)

```
1. VALIDATE_CONTEXT      — validate request and build RecoveryContext
2. INITIALIZE_SESSION    — create M1 RecoverySession, CREATED → INITIALIZING
3. ASSESS_FAILURE        — INITIALIZING → DETECTING → ASSESSING
4. PLAN_RECOVERY         — ASSESSING → READY
5. DISPATCH_WORKFLOW     — READY → RECOVERING
6. COORDINATE_POLICIES   — invoke PolicyFrameworkPort (M3)
7. COORDINATE_FAILOVER   — invoke FailoverFrameworkPort (M4) if required
8. VERIFY_RESULT         — RECOVERING → VERIFYING → COMPLETED
9. PUBLISH_SNAPSHOT      — create and store RecoverySnapshot
10. FINALIZE             — archive session, build RecoveryResponse
```

---

## Wiring M3 and M4

```python
# Wire M3 Policy Framework
engine.set_policy_framework(my_policy_framework_port)

# Wire M4 Failover Framework
engine.set_failover_framework(my_failover_framework_port)
```

Both ports use the `NullPolicyFramework` / `NullFailoverFramework` by default
(always approve, never trigger failover) until M3 and M4 are implemented.

---

## Events

```python
from iios.execution.recovery.engine import RecoveryEngineEvent

def on_event(event: RecoveryEngineEvent) -> None:
    print(f"[{event.event_type.value}] req={event.request_id}")

engine.add_event_listener(on_event)
engine.remove_event_listener(on_event)
```

| Event Type             | When fired                          |
|------------------------|-------------------------------------|
| `recovery_initialized` | Session created and initialized     |
| `recovery_started`     | Recovery workflow begun (RECOVERING)|
| `failure_detected`     | Assessment complete                 |
| `recovery_dispatched`  | Policy/failover coordination done   |
| `recovery_verified`    | Verification passed                 |
| `recovery_completed`   | Full workflow complete               |
| `recovery_failed`      | Workflow failed at any stage        |
| `recovery_stopped`     | Operator abort                      |
| `engine_started`       | Engine lifecycle started            |
| `engine_stopped`       | Engine lifecycle stopped            |

---

## Package Structure

```
iios/execution/recovery/engine/
├── execution_recovery_engine.py  ← PRIMARY ENTRY POINT
├── recovery_manager.py           ← Internal workflow coordinator
├── recovery_session_manager.py   ← Bridges M2 requests with M1 sessions
├── recovery_dispatcher.py        ← Dispatches to PolicyPort + FailoverPort
├── recovery_scheduler.py         ← Priority queue of pending requests
├── recovery_pipeline.py          ← 10-stage pipeline state tracker
├── recovery_registry.py          ← Bounded request store
├── recovery_factory.py           ← Domain object factory
├── recovery_validation.py        ← Stateless validator
├── recovery_statistics.py        ← Thread-safe accumulator
├── recovery_history.py           ← Bounded deque history
├── recovery_context.py           ← Engine-level RecoveryContext + Snapshots
├── recovery_request.py           ← Immutable input DTO
├── recovery_response.py          ← Immutable output DTO
├── recovery_snapshot.py          ← Point-in-time workflow capture
├── recovery_events.py            ← Domain events + factory functions
├── constants.py                  ← Enums, limits, stage order
├── exceptions.py                 ← RE-000 … RE-010 hierarchy
└── __init__.py                   ← Full public surface
```

---

## Execution Snapshots (inputs from C6)

The engine accepts lightweight snapshot DTOs from C6:

```python
from iios.execution.recovery.engine import (
    ExecutionMonitoringSnapshot,
    ExecutionGatewaySnapshot,
    ExecutionRiskSnapshot,
)
```

These are decoupled from C6 internals — the engine works without them
(a warning is recorded in the validation result if none are provided).

---

## Statistics

```python
stats = engine.get_statistics()
print(stats.total_requests)
print(stats.sessions_completed)
print(stats.success_rate)
print(stats.average_recovery_time_ms)
print(stats.verification_success_rate)
print(stats.subsystem_availability)
```

---

## Future Modules

- **M3**: Recovery Policy Framework — policy-driven recovery decisions
- **M4**: Failover Framework — subsystem failover coordination
- **M5**: Recovery Snapshot Store — persistent snapshot archival
- **M6**: Recovery Integration — integrates all modules
