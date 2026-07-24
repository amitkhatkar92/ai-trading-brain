# Enterprise Integration Gateway — Public API Guide

## IntegrationGatewayRequest

The primary input object for all gateway operations.

```python
from iios.integration.gateway import (
    IntegrationGatewayRequest, GatewayOperationType
)

# SUBMIT — full integration workflow
req = IntegrationGatewayRequest.create(
    operation     = GatewayOperationType.SUBMIT,
    workflow_id   = "wf-001",
    enterprise_id = "ent-001",
    payload          = {"key": "value"},
    connector_config = {"type": "REST_API", "service_type": "api"},
    protocol_config  = {"type": "http"},
    auth_config      = {"scheme": "bearer", "token": "..."},
    endpoint_config  = {"url": "https://api.example.com/v1/data"},
    platform_context = {"region": "ap-south-1"},
    metadata         = {"correlation": "req-001"},
)

# CONNECT
req = IntegrationGatewayRequest.create(
    operation        = GatewayOperationType.CONNECT,
    workflow_id      = "wf-connect",
    enterprise_id    = "ent-001",
    connector_config = {"type": "REST_API"},
)

# DISCONNECT
req = IntegrationGatewayRequest.create(
    operation     = GatewayOperationType.DISCONNECT,
    workflow_id   = "wf-disconnect",
    enterprise_id = "ent-001",
    session_id    = "sess-abc123",
)

# VALIDATE (dry-run)
req = IntegrationGatewayRequest.create(
    operation     = GatewayOperationType.VALIDATE,
    workflow_id   = "wf-001",
    enterprise_id = "ent-001",
)
```

### IntegrationGatewayFactory shortcuts

```python
from iios.integration.gateway import IntegrationGatewayFactory, GatewayOperationType

req = IntegrationGatewayFactory.create_submit_request(
    workflow_id      = "wf-001",
    enterprise_id    = "ent-001",
    payload          = {"key": "value"},
    connector_config = {"type": "REST_API"},
)

req = IntegrationGatewayFactory.create_connect_request(
    workflow_id      = "wf-001",
    enterprise_id    = "ent-001",
    connector_config = {"type": "REST_API"},
)

req = IntegrationGatewayFactory.create_disconnect_request(
    workflow_id   = "wf-001",
    enterprise_id = "ent-001",
    session_id    = "sess-001",
)
```

---

## IntegrationGatewayResponse

```python
response = gateway.submit(request)

# Status check
response.is_successful           # True / False
response.is_failed               # True / False
response.status                  # GatewayResponseStatus.SUCCESS

# Correlation IDs
response.lifecycle_session_id    # "sess-..."  (lifecycle session)
response.engine_request_id       # engine-level request ID
response.governance_decision     # "allow" / "deny" / ...
response.snapshot_id             # "snap-..."  (integration snapshot)

# Timing
response.processing_time_ms      # float
response.completed_at            # ISO timestamp

# Error detail (on failure)
response.error                   # human-readable message
response.error_code              # "IGW-005" etc.

# Serialization
d = response.to_dict()           # Dict[str, Any]
```

---

## Validation

```python
from iios.integration.gateway import IntegrationGatewayValidation

validator = IntegrationGatewayValidation()
report = validator.validate_request(
    request,
    gateway_state        = gateway.state,
    available_components = gateway.component_registry.available_types(),
)

print(report.passed)       # True / False
print(report.error_count)  # int
for issue in report.errors:
    print(issue.check, issue.message)
```

### 7 validation checks

| Check | Description |
|---|---|
| `GATEWAY_CONSISTENCY` | Gateway must be in ACTIVE state |
| `WORKFLOW_CONSISTENCY` | workflow_id and enterprise_id must be non-empty |
| `COMPONENT_AVAILABILITY` | Required components must be registered |
| `LIFECYCLE_INTEGRITY` | Lifecycle component available for lifecycle ops |
| `GOVERNANCE_INTEGRITY` | Policies component available for governance ops |
| `SNAPSHOT_INTEGRITY` | Snapshot component available for snapshot ops |
| `RESPONSE_COMPLETENESS` | Request has submitted_at timestamp |

---

## Health

```python
health = gateway.health()

health.is_healthy           # True / False
health.overall_health       # "healthy" / "degraded" / "unavailable"
health.gateway_state        # GatewayState.ACTIVE
health.active_requests      # int
health.uptime_seconds       # float

for comp_key, comp_health in health.components.items():
    print(comp_key, comp_health.status)  # "healthy" / "degraded" / "unavailable"
```

---

## Statistics

```python
from iios.integration.gateway import IntegrationStatistics

stats: IntegrationStatistics = gateway.statistics()

stats.gateway_requests           # total requests received
stats.successful_requests        # count
stats.failed_requests            # count
stats.rejected_requests          # count (failed validation)
stats.snapshot_publications      # count
stats.average_processing_time_ms # float
stats.average_response_time_ms   # float
stats.gateway_availability       # float 0.0–1.0

d = stats.as_dict()              # Dict[str, Any]
```

---

## History

```python
entries = gateway.history(n=50)   # most recent 50

for entry in entries:
    print(entry.request_id, entry.status, entry.processing_time_ms)

# Full report
from iios.integration.gateway import IntegrationGatewayHistory
hist = IntegrationGatewayHistory()
report = hist.report()
print(report.total_entries, report.successful, report.failed)
```

---

## Events

```python
from iios.integration.gateway import GatewayEventType

def on_completed(event):
    print(f"Completed: {event.request_id} snapshot={event.payload.get('snapshot_id')}")

gateway.event_bus.subscribe(GatewayEventType.GATEWAY_COMPLETED, on_completed)

# All 8 event types:
# GATEWAY_INITIALIZED, GATEWAY_STARTED, GATEWAY_VALIDATED, GATEWAY_EXECUTED,
# SNAPSHOT_PUBLISHED, GATEWAY_COMPLETED, GATEWAY_FAILED, GATEWAY_STOPPED
```
