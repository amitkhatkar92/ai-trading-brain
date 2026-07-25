# Integration Guide

## Integrating with the Enterprise Workflow Gateway

### Basic Integration Pattern

```python
from iios.workflow.gateway import WorkflowGateway, WorkflowGatewayFactory

class MyService:
    def __init__(self) -> None:
        self._gateway = WorkflowGateway()
        self._gateway.initialize()
        self._gateway.start()

    def process_order(self, order_id: str) -> None:
        request = WorkflowGatewayFactory.create_submit_request(
            workflow_id   = f"wf-order-{order_id}",
            workflow_name = "Order Processing Workflow",
            payload       = {"order_id": order_id},
            priority      = 2,
        )
        response = self._gateway.submit(request)
        if response.is_success:
            print(f"Order processed: snapshot={response.snapshot_id!r}")
        else:
            print(f"Order failed: {response.error_message}")

    def shutdown(self) -> None:
        self._gateway.stop()
```

---

## Event-Driven Integration

Subscribe to gateway events to react to workflow lifecycle changes.

```python
from iios.workflow.gateway import WorkflowGateway, GatewayEventType

gateway = WorkflowGateway()
gateway.initialize()
gateway.start()

# Subscribe to snapshot publication
def on_snapshot(event):
    print(f"Snapshot published for workflow={event.workflow_id!r}")

gateway._event_bus.add_listener(GatewayEventType.SNAPSHOT_PUBLISHED, on_snapshot)

# Subscribe to failures (not emitted on success-only path, check WORKFLOW_COMPLETED)
def on_completed(event):
    print(f"Workflow completed: {event.workflow_id!r}")

gateway._event_bus.add_listener(GatewayEventType.WORKFLOW_COMPLETED, on_completed)
```

---

## Health Check Integration

```python
def healthcheck(gateway: WorkflowGateway) -> dict:
    h = gateway.health()
    return {
        "healthy":          h.is_healthy,
        "state":            h.gateway_state.value,
        "component_health": h.component_health,
        "uptime_seconds":   h.uptime_seconds,
    }
```

---

## Custom Component Injection

For testing or specialized environments, inject pre-built component registries.

```python
from iios.workflow.gateway import (
    WorkflowGateway,
    WorkflowGatewayManager,
    WorkflowComponentRegistry,
    ComponentType,
    ComponentStatus,
)

registry = WorkflowComponentRegistry()
registry.register("engine", ComponentType.ENGINE, my_engine_instance)

manager = WorkflowGatewayManager(
    gateway_id         = "custom-gw",
    component_registry = registry,
)
gateway = WorkflowGateway(gateway_id="custom-gw", manager=manager)
```

---

## Bulk Operations

```python
requests = [
    WorkflowGatewayFactory.create_submit_request(f"wf-{i}", f"Workflow {i}")
    for i in range(100)
]

responses = [gateway.submit(req) for req in requests]
successes = sum(1 for r in responses if r.is_success)
print(f"{successes}/100 succeeded")
```

---

## Monitoring

```python
import time

def monitor_loop(gateway: WorkflowGateway, interval_s: float = 30.0) -> None:
    while True:
        h = gateway.health()
        s = gateway.statistics()
        print(
            f"health={h.overall_status.value!r} "
            f"total={s.total_requests} "
            f"success={s.successful_requests} "
            f"avail={s.gateway_availability:.2%}"
        )
        time.sleep(interval_s)
```
