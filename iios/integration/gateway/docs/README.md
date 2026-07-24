# Enterprise Integration Gateway

## Overview

The **Enterprise Integration Gateway** (`iios.integration.gateway`) is the **ONLY** public entry point for the entire Enterprise Integration & Connectivity subsystem (C15).

External components **MUST NOT** directly access:
- Integration Lifecycle (`iios.integration.lifecycle`)
- Integration Engine (`iios.integration.engine`)
- Integration Governance Policy Framework (`iios.integration.policies`)
- Integration Services Framework (`iios.integration.services`)
- Integration Snapshot (`iios.integration.snapshot`)

All communication **MUST** occur through the `IntegrationGateway`.

---

## Package Contents

| File | Purpose |
|---|---|
| `constants.py` | Enums and constants (GatewayState, GatewayEventType, etc.) |
| `exceptions.py` | Error hierarchy IGW-000 through IGW-010 |
| `integration_gateway.py` | `IntegrationGateway` — main class, 13 public API methods |
| `integration_gateway_manager.py` | `IntegrationGatewayManager` — multi-gateway management |
| `integration_gateway_context.py` | `IntegrationGatewayContext` — mutable workflow execution context |
| `integration_gateway_request.py` | `IntegrationGatewayRequest` — immutable input object |
| `integration_gateway_response.py` | `IntegrationGatewayResponse` — immutable output object |
| `integration_gateway_registry.py` | `IntegrationGatewayRegistry` — active request tracking |
| `integration_gateway_validation.py` | `IntegrationGatewayValidation` — 7-check validator |
| `integration_gateway_health.py` | `IntegrationGatewayHealth`, `IntegrationHealthSummary` |
| `integration_gateway_status.py` | `IntegrationGatewayStatusReport`, `IntegrationGatewayStatusTracker` |
| `integration_gateway_statistics.py` | `IntegrationGatewayStatistics`, `IntegrationStatistics` |
| `integration_gateway_history.py` | `IntegrationGatewayHistory`, `GatewayHistoryEntry` |
| `integration_gateway_events.py` | `IntegrationGatewayEventBus`, `GatewayEvent` |
| `integration_gateway_factory.py` | `IntegrationGatewayFactory` — convenience factory |
| `integration_gateway_router.py` | `IntegrationGatewayRouter`, `GatewayRouteDecision` |
| `integration_gateway_dispatcher.py` | `IntegrationGatewayDispatcher` — workflow executor |
| `integration_component_registry.py` | `IntegrationComponentRegistry`, `GatewayComponent` |
| `integration_component_factory.py` | `IntegrationComponentFactory` — default component creation |
| `__init__.py` | 70 public exports |

---

## Quick Start

```python
from iios.integration.gateway import (
    IntegrationGateway,
    IntegrationGatewayRequest,
    GatewayOperationType,
)

# Create and start the gateway
gateway = IntegrationGateway(gateway_id="my-gateway")
gateway.initialize()   # creates all 5 subsystem components
gateway.start()

# Submit a request
request = IntegrationGatewayRequest.create(
    operation     = GatewayOperationType.SUBMIT,
    workflow_id   = "wf-enterprise-001",
    enterprise_id = "ent-acme-corp",
    payload       = {"data": "value"},
    connector_config = {"type": "REST_API"},
)

response = gateway.submit(request)
print(response.status)         # GatewayResponseStatus.SUCCESS
print(response.snapshot_id)    # snap-...
print(response.lifecycle_session_id)
```

---

## Public API (13 methods)

| Method | Description |
|---|---|
| `initialize()` | Initialize gateway and all 5 subsystem components |
| `start()` | Start accepting requests (calls initialize if needed) |
| `stop()` | Graceful shutdown |
| `restart()` | Stop then re-initialize |
| `health()` | Returns `IntegrationHealthSummary` |
| `status()` | Returns `IntegrationGatewayStatusReport` |
| `statistics()` | Returns `IntegrationStatistics` |
| `snapshot()` | Returns latest `IntegrationSnapshot` |
| `history(n)` | Returns List[`GatewayHistoryEntry`] |
| `validate(request)` | Returns `GatewayValidationReport` without executing |
| `submit(request)` | Full workflow execution, returns `IntegrationGatewayResponse` |
| `query(request_id)` | Retrieve previous response by request_id |
| `connect(config)` | Establish integration connection, returns bool |
| `disconnect(session_id)` | Terminate integration session, returns bool |

---

## Error Codes

| Code | Exception | Description |
|---|---|---|
| IGW-000 | `IntegrationGatewayError` | Base exception |
| IGW-001 | `GatewayNotReadyError` | Gateway not ACTIVE |
| IGW-002 | `GatewayRequestValidationError` | Validation failed |
| IGW-003 | `GatewayWorkflowError` | Workflow execution failed |
| IGW-004 | `GatewayComponentError` | Required component unavailable |
| IGW-005 | `GatewayLifecycleError` | Lifecycle coordination failed |
| IGW-006 | `GatewayEngineError` | Engine coordination failed |
| IGW-007 | `GatewayGovernanceError` | Governance coordination failed |
| IGW-008 | `GatewayServicesError` | Services coordination failed |
| IGW-009 | `GatewaySnapshotError` | Snapshot coordination failed |
| IGW-010 | `GatewayCapacityError` | Gateway at capacity |
