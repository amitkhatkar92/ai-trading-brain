# Developer Guide

## Package Structure

```
iios/workflow/gateway/
├── __init__.py                         ← public API exports
├── constants.py                        ← enums, prefixes, defaults
├── exceptions.py                       ← WGW-000…WGW-011 error hierarchy
├── workflow_gateway_request.py         ← WorkflowGatewayRequest (frozen)
├── workflow_gateway_response.py        ← WorkflowGatewayResponse (frozen)
├── workflow_gateway_context.py         ← WorkflowGatewayContext (frozen)
├── workflow_gateway_validation.py      ← WorkflowGatewayValidation
├── workflow_gateway_health.py          ← WorkflowGatewayHealth + WorkflowHealthSummary
├── workflow_gateway_status.py          ← WorkflowGatewayStatus + WorkflowStatus
├── workflow_gateway_statistics.py      ← WorkflowGatewayStatistics + WorkflowStatistics
├── workflow_gateway_history.py         ← WorkflowGatewayHistory + HistoryRecord
├── workflow_gateway_events.py          ← WorkflowGatewayEvent + EventBus
├── workflow_gateway_registry.py        ← WorkflowGatewayRegistry
├── workflow_gateway_router.py          ← WorkflowGatewayRouter
├── workflow_gateway_dispatcher.py      ← WorkflowGatewayDispatcher
├── workflow_gateway_factory.py         ← WorkflowGatewayFactory
├── workflow_gateway_manager.py         ← WorkflowGatewayManager
├── workflow_component_registry.py      ← WorkflowComponentRegistry + ComponentRecord
├── workflow_component_factory.py       ← WorkflowComponentFactory
├── workflow_gateway.py                 ← WorkflowGateway (main public class)
└── docs/
    ├── README.md
    ├── enterprise_workflow_gateway_guide.md
    ├── public_api_guide.md
    ├── gateway_architecture_guide.md
    ├── integration_guide.md
    └── developer_guide.md              ← this file
```

---

## Design Rules

### 1. Gateway Only

`WorkflowGateway` performs NO execution, governance evaluation, lifecycle
management, orchestration, or business processing.  It coordinates.

### 2. Frozen Domain Objects

`WorkflowGatewayRequest`, `WorkflowGatewayResponse`, `WorkflowGatewayContext`,
`WorkflowGatewayEvent`, `WorkflowGatewayHistoryRecord`, `WorkflowStatistics`,
`WorkflowStatus`, `WorkflowHealthSummary`, `GatewayValidationResult`,
`ComponentRecord` — ALL are `@dataclass(frozen=True)`.

### 3. Never Raise for Workflow Errors

The gateway's request processing methods (`submit`, `query`, `cancel`,
`retry`) ALWAYS return a `WorkflowGatewayResponse`. They never raise
exceptions for workflow-level failures.

Only lifecycle methods (`initialize`, `start`, `stop`, `restart`) may raise.

### 4. Lazy Component Imports

`WorkflowComponentFactory` uses lazy imports (inside methods) to avoid circular
imports between M1–M5 and M6.  Do not move imports to module level.

### 5. Error Hierarchy

```
IIOSError
└── WorkflowGatewayError                WGW-000  — base
    ├── WorkflowGatewayNotInitializedError  WGW-001
    ├── WorkflowGatewayNotRunningError       WGW-002
    ├── WorkflowGatewayValidationError       WGW-003
    ├── WorkflowGatewayRequestError          WGW-004
    ├── WorkflowGatewayResponseError         WGW-005
    ├── WorkflowGatewayRoutingError          WGW-006
    ├── WorkflowGatewayDispatchError         WGW-007
    ├── WorkflowGatewayComponentError        WGW-008
    ├── WorkflowGatewayHistoryError          WGW-009
    ├── WorkflowGatewayStatisticsError       WGW-010
    └── WorkflowGatewayTimeoutError          WGW-011
```

---

## Adding a New Public API Method

1. Add the method to `WorkflowGateway` in `workflow_gateway.py`.
2. If it processes a request, route through `_process()`.
3. Add a convenience factory method in `WorkflowGatewayFactory`.
4. Add the method to the `GatewayRequestType` enum if it maps to a new type.
5. Add a router mapping in `workflow_gateway_router.py`.
6. Add a handler in `WorkflowGatewayDispatcher`.
7. Export from `__init__.py`.
8. Add tests in `test_workflow_gateway_m6.py`.
9. Update `public_api_guide.md`.

---

## Running Tests

```bash
# M6 tests only
python -m pytest tests/unit/workflow/test_workflow_gateway_m6.py -v

# Full C16 regression (M1–M6)
python -m pytest tests/unit/workflow/ -v

# With coverage
python -m pytest tests/unit/workflow/test_workflow_gateway_m6.py \
  --cov=iios/workflow/gateway --cov-report=term-missing
```

Expected baseline: **807+ tests passing** across M1–M5 (previous), plus M6 tests.

---

## Version Identifiers

| Constant | Value |
|---|---|
| `VERSION` | `"1.0.0"` |
| `BUILD_VERSION` | `"c16-m6"` |
| `GATEWAY_VERSION` | `"1.0"` |
| `FRAMEWORK_VERSION` | `"c16-1.0"` |

---

## ID Prefix Registry

| Object | Prefix | Example |
|---|---|---|
| Gateway | `wgw-` | `wgw-enterprise-workflow` |
| Request | `wgwreq-` | `wgwreq-a3f9c12e8b4d` |
| Response | `wgwres-` | `wgwres-c84f1a9d3e2b` |
| Event | `wgwevt-` | `wgwevt-7d4e2a1c` |
| Context | `wgwctx-` | `wgwctx-1b9e7c3d5f2a` |
| Record | `wgwrec-` | `wgwrec-f3a2b1c4d5e6` |
