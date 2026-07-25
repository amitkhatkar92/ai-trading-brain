# Public API Guide

## Overview

All 14 public methods are on `WorkflowGateway`.

```python
from iios.workflow.gateway import WorkflowGateway

gateway = WorkflowGateway(gateway_id="my-gateway")
```

---

## Lifecycle API

### `initialize() → None`

Wires all M1–M5 components (Lifecycle, Engine, PolicyEngine,
OrchestrationEngine, SnapshotBuilder/Factory).

Must be called once before `start()`.

```python
gateway.initialize()
```

### `start() → None`

Transitions gateway to `RUNNING`. Raises `WorkflowGatewayNotInitializedError`
if `initialize()` has not been called.

### `stop() → None`

Gracefully stops the gateway. Emits `GATEWAY_STOPPED` event.

### `restart() → None`

Equivalent to `stop() + initialize() + start()`. All M1–M5 components
are re-created.

---

## Observability API

### `health() → WorkflowHealthSummary`

Returns a point-in-time health summary.

```python
h = gateway.health()
h.is_healthy         # bool
h.overall_status     # GatewayHealthStatus enum
h.gateway_state      # GatewayState enum
h.component_health   # Dict[str, str]
h.uptime_seconds     # float
h.to_dict()          # JSON-safe dict
```

### `status() → WorkflowStatus`

Returns current operational status.

```python
s = gateway.status()
s.is_operational     # bool
s.active_workflows   # int
s.total_processed    # int
s.to_dict()
```

### `statistics() → WorkflowStatistics`

Returns accumulated gateway metrics.

```python
st = gateway.statistics()
st.total_requests
st.successful_requests
st.failed_requests
st.rejected_requests
st.workflow_executions
st.snapshots_published
st.average_response_time_ms
st.average_processing_time_ms
st.gateway_availability       # 0.0–1.0
st.to_dict()
```

### `snapshot(workflow_id: str = "") → Optional[WorkflowSnapshot]`

Returns the latest M5 snapshot for a workflow, or `None`.

### `history(n: int = 20) → List[WorkflowGatewayHistoryRecord]`

Returns the N most recent gateway history records, newest first.

---

## Request API

### `validate(request: WorkflowGatewayRequest) → GatewayValidationResult`

Validates a request without submitting it.

```python
result = gateway.validate(request)
result.valid      # bool
result.issues     # Tuple[str, ...]
result.to_dict()
```

### `submit(request: WorkflowGatewayRequest) → WorkflowGatewayResponse`

The primary workflow submission method.

```python
from iios.workflow.gateway import WorkflowGatewayFactory

request  = WorkflowGatewayFactory.create_submit_request("wf-001", "My Workflow")
response = gateway.submit(request)
```

### `query(workflow_id: str, *, correlation_id: str = "") → WorkflowGatewayResponse`

Query the state of a workflow.

```python
response = gateway.query("wf-001")
```

### `cancel(workflow_id: str, *, correlation_id: str = "") → WorkflowGatewayResponse`

Cancel an active workflow.

```python
response = gateway.cancel("wf-001")
```

### `retry(workflow_id: str, *, correlation_id: str = "", payload: dict = None) → WorkflowGatewayResponse`

Retry a workflow.

```python
response = gateway.retry("wf-001")
```

---

## Error Handling

The gateway ALWAYS returns a `WorkflowGatewayResponse` — it never raises
exceptions for workflow-level errors. Error details are in:

```python
response.is_failure        # True
response.error_message     # "disk full" / "engine timeout" / ...
response.is_rejected       # True if validation or gateway-state failure
```

Infrastructure exceptions (`WorkflowGatewayNotInitializedError`,
`WorkflowGatewayNotRunningError`) are only raised from lifecycle methods,
never from request processing.
