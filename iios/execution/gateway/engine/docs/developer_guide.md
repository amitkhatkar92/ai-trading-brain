# Developer Guide

## Adding a real broker

Implement `BrokerAbstractionProtocol`:

```python
from iios.execution.gateway.engine.gateway_dispatcher import (
    BrokerAbstractionProtocol,
    DispatchResult,
    DispatchOutcome,
)
import time

class DhanBroker:
    @property
    def is_available(self) -> bool:
        return True   # add real health check

    def dispatch(self, request) -> DispatchResult:
        # call Dhan API here
        return DispatchResult(
            accepted=True,
            outcome=DispatchOutcome.ACCEPTED,
            external_id="DHAN-ORD-001",
            result_metadata={},
            error_code=None,
            error_message=None,
            dispatched_at=time.time(),
        )

    def cancel(self, request_id: str, reason: str) -> bool:
        # call Dhan cancel API
        return True

engine.register_broker(DhanBroker())
```

## Adding a routing framework

Implement `RoutingFrameworkProtocol`:

```python
from iios.execution.gateway.engine.gateway_dispatcher import (
    RoutingFrameworkProtocol,
    RouteDecision,
)

class SmartRouter:
    @property
    def is_available(self) -> bool:
        return True

    def route(self, request) -> RouteDecision:
        return RouteDecision(
            routed=True,
            route_id="DHAN-EQUITY",
            route_metadata={"reason": "default"},
        )

engine.register_router(SmartRouter())
```

## Listening to events

```python
from iios.execution.gateway.engine import EngineEventType

def on_event(event):
    if event.event_type == EngineEventType.DISPATCH_COMPLETED:
        print(f"Dispatched: {event.request_id}")

# Register BEFORE start() to capture GATEWAY_STARTED
engine = ExecutionGatewayEngine()
engine.add_event_listener(on_event)
engine.start()
```

## Exception hierarchy

```
IIOSError
└── ExecutionGatewayEngineError            EGE-000
        ├── GatewayEngineNotRunningError   EGE-001
        ├── GatewayRequestSubmissionError  EGE-002
        ├── GatewayDispatchError           EGE-003
        ├── GatewayQueueFullError          EGE-004
        ├── GatewaySessionNotFoundError    EGE-005
        ├── GatewaySessionExpiredError     EGE-006
        ├── GatewayValidationFailedError   EGE-007
        ├── GatewayEngineRequestNotFoundError EGE-008
        ├── DuplicateEngineRequestError    EGE-009
        └── GatewayRegistryCapacityError   EGE-010
```

## Thread safety

All public methods on `ExecutionGatewayEngine` and `GatewayManager` are
thread-safe.  Internal objects (`GatewayEngineRegistry`, `GatewaySession`,
`GatewayEngineRequest`, queues) each carry their own lock.

## Extending defaults

All capacity and timing defaults are defined in `constants.py`:

```python
DEFAULT_MAX_REQUESTS       = 10_000
DEFAULT_MAX_QUEUE_SIZE     = 5_000
DEFAULT_MAX_SESSIONS       = 1_000
DEFAULT_SESSION_TIMEOUT    = 3_600.0
DEFAULT_MAX_RETRIES        = 3
DEFAULT_RETRY_DELAY_SECS   = 1.0
DEFAULT_MAX_HISTORY        = 5_000
```

Override at construction time:

```python
engine = ExecutionGatewayEngine(
    max_requests=50_000,
    max_queue_size=20_000,
    max_sessions=5_000,
    max_history=10_000,
    session_timeout=7_200.0,
    retry_delay=0.5,
)
```

## Testing

Use the default `ExecutionGatewayEngine()` — it ships with `SimulatedDispatch`
which always returns `DispatchOutcome.ACCEPTED`.

```python
engine = ExecutionGatewayEngine()
engine.start()
ctx = engine.make_context("EX", "ORD", "PORT", "STRAT")
resp = engine.submit_request(ctx)
assert resp.is_accepted
engine.stop()
```

See `tests/unit/execution/gateway/engine/test_execution_gateway_engine.py`
for the full test suite (204 tests).
