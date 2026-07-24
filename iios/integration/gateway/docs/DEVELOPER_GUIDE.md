# Enterprise Integration Gateway — Developer Guide

## Adding a New Operation Type

1. Add entry to `GatewayOperationType` in `constants.py`
2. Add entry to `OPERATION_REQUIRED_COMPONENTS` in `constants.py`
3. Update `IntegrationGatewayRouter.route()` if routing logic differs from defaults
4. Add a factory shortcut in `IntegrationGatewayFactory` if useful
5. Add tests in the M6 test file

## Adding a New Validation Check

1. Add entry to `GatewayValidationCheck` in `constants.py`
2. Add the check to `VALIDATION_CHECK_ORDER` in `constants.py`
3. Implement `_check_<name>()` in `IntegrationGatewayValidation`
4. Add it to the `check_methods` dict in `validate_request()`

## Adding a New Event Type

1. Add entry to `GatewayEventType` in `constants.py`
2. Emit via `self._event_bus.emit(GatewayEventType.<NEW>, ...)` at the appropriate point
3. Update tests and documentation

## Testing Patterns

### Unit test with stub components

```python
from iios.integration.gateway import (
    IntegrationGateway, IntegrationGatewayFactory,
    GatewayComponentType, IntegrationComponentRegistry,
)

class _StubLifecycle:
    def create_session(self, workflow_id):
        from types import SimpleNamespace
        return SimpleNamespace(session_id="sess-stub-001")
    def initialize(self, session_id, **kw): pass

class _StubEngine:
    def dispatch(self, req):
        from types import SimpleNamespace
        return SimpleNamespace(response_id="resp-001", status="success")

class _StubPolicyEngine:
    def evaluate(self, req):
        from types import SimpleNamespace
        return SimpleNamespace(overall_action=SimpleNamespace(value="allow"))

class _StubConnectorEngine:
    def execute(self, req):
        from types import SimpleNamespace
        return SimpleNamespace(status="success")

class _StubSnapshotRegistry:
    def register(self, snap): pass
    def list_ids(self): return ["snap-001"]
    def get(self, sid): return None

def make_test_gateway():
    components = {
        GatewayComponentType.LIFECYCLE: _StubLifecycle(),
        GatewayComponentType.ENGINE:    _StubEngine(),
        GatewayComponentType.POLICIES:  _StubPolicyEngine(),
        GatewayComponentType.SERVICES:  _StubConnectorEngine(),
        GatewayComponentType.SNAPSHOT:  _StubSnapshotRegistry(),
    }
    return IntegrationGatewayFactory.create_with_components(components)
```

### Concurrency test pattern

```python
import threading

def worker(gateway, results, lock):
    req = IntegrationGatewayRequest.create(...)
    resp = gateway.submit(req)
    with lock:
        results.append(resp.status)

threads = [threading.Thread(target=worker, args=(gw, results, lock))
           for _ in range(20)]
for t in threads: t.start()
for t in threads: t.join()
```

## Import Safety

The gateway package imports from the 5 subsystems ONLY from two locations:

1. `integration_component_factory.py` — lazy imports in `@staticmethod` methods
2. `integration_gateway_dispatcher.py` — lazy imports inside each `_step_*` method

This prevents circular imports and allows the gateway package to be imported without triggering all 5 subsystem imports.

## What the Gateway Does NOT Do

- No lifecycle state machine management (that's `integration_lifecycle`)
- No governance rule evaluation (that's `integration_policies`)
- No connector/adapter instantiation (that's `integration_services`)
- No protocol implementation (that's `integration_services`)
- No snapshot algorithm (that's `integration_snapshot`)
- No AI reasoning or business logic
- No vendor SDK calls

## File Conventions

- All source files: `from __future__ import annotations` at top
- Logging: `from iios.common.logging.logging_manager import get_logger`; use f-strings
- Errors: `from iios.common.errors.exceptions import IIOSError`
- No `requests`, `httpx`, `kafka`, `pika`, `redis`, `boto3`, `grpc`, `websockets`, `sqlalchemy`
- Frozen dataclasses for all immutable value objects
- `threading.Lock()` for all stateful mutable classes
