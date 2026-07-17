# Gateway Engine Guide

## Purpose

`ExecutionGatewayEngine` is the single public entry point for submitting
gateway requests.  It wraps `GatewayManager` and exposes a stable interface
that the rest of the execution pipeline depends on.

## Lifecycle

```
engine.start()        → starts GatewayManager and M1 GatewayLifecycle
engine.submit_request(ctx) → returns GatewayResponse
engine.stop()         → graceful shutdown
```

The engine implements `LifecycleAwareMixin`.  Calling `start()` twice raises
`EngineAlreadyRunningError`.  Calling `stop()` twice raises
`EngineNotRunningError`.

## State machine

```
IDLE → INITIALIZING → VALIDATING → QUEUING → DISPATCHING → COMPLETING
                                                          → FAILED
     → STOPPED
```

## Key properties

| Property | Type | Description |
|---|---|---|
| `engine_state` | `EngineState` | Current operational state |
| `request_count` | `int` | Total requests registered |
| `has_live_broker` | `bool` | True if a real broker is attached |
| `has_router` | `bool` | True if a routing framework is attached |

## Observability

```python
snap = engine.snapshot()         # GatewayEngineSnapshot — point-in-time
stats = engine.statistics()      # GatewayEngineStatistics — counters

# or from the snapshot
print(snap.statistics.completion_rate)
print(snap.active_session_count)
```

## Broker integration

```python
from iios.execution.gateway.engine import ExecutionGatewayEngine

class MyBroker:
    @property
    def is_available(self) -> bool: ...
    def dispatch(self, request) -> DispatchResult: ...
    def cancel(self, request_id: str, reason: str) -> bool: ...

engine = ExecutionGatewayEngine()
engine.register_broker(MyBroker())
engine.start()
```

Without a registered broker the engine uses `SimulatedDispatch`, which
always returns `DispatchOutcome.ACCEPTED`.  This is the default for paper
trading.
