# Enterprise Integration Gateway — Architecture Guide

## Design Principles

1. **Gateway-only** — coordinates, never implements
2. **Single entry point** — all subsystem access flows through `IntegrationGateway`
3. **Provider independent** — no vendor SDK imports anywhere in the gateway package
4. **Thread-safe** — all stateful classes use `threading.Lock()`
5. **Backward compatible** — public method signatures never change
6. **Implementation agnostic** — doesn't know or care about connector/protocol details

## Component Architecture

```
External Caller
       │
       ▼
IntegrationGateway (13 public methods)
       │
       ├──► IntegrationGatewayValidation  (7 checks)
       │
       ├──► IntegrationGatewayRouter      (routing decision)
       │
       ├──► IntegrationGatewayDispatcher  (workflow coordinator)
       │         │
       │         ├── [1] IntegrationLifecycle    (lifecycle pkg)
       │         ├── [2] IntegrationEngine       (engine pkg)
       │         ├── [3] IntegrationPolicyEngine (policies pkg)
       │         ├── [4] ConnectorEngine         (services pkg)
       │         └── [5] IntegrationSnapshotRegistry (snapshot pkg)
       │
       ├──► IntegrationGatewayRegistry    (request tracking)
       ├──► IntegrationGatewayHealth      (health monitor)
       ├──► IntegrationGatewayStatusTracker (status)
       ├──► IntegrationGatewayStatistics  (metrics)
       ├──► IntegrationGatewayHistory     (audit trail)
       └──► IntegrationGatewayEventBus    (events)
```

## Workflow: submit()

```
1. Guard: gateway must be ACTIVE
2. Register request
3. Create IntegrationGatewayContext
4. Validate request (7 checks)
5. Route: determine required components
6. Dispatch:
   a. Lifecycle → create_session() + initialize()
   b. Engine    → dispatch(IntegrationRequest)
   c. Governance → evaluate(IntegrationPolicyRequest)
   d. Services  → execute(ConnectorRequest)
   e. Snapshot  → build + register
7. Build IntegrationGatewayResponse
8. Record history, update stats, emit event
9. Return response
```

## Component Registry

The `IntegrationComponentRegistry` stores live component instances keyed by `GatewayComponentType`:

| Key | Component |
|---|---|
| `LIFECYCLE` | `IntegrationLifecycle` |
| `ENGINE` | `IntegrationEngine` |
| `POLICIES` | `IntegrationPolicyEngine` |
| `SERVICES` | `ConnectorEngine` |
| `SNAPSHOT` | `IntegrationSnapshotRegistry` |

The `IntegrationComponentFactory` creates default instances. Inject custom instances for testing.

## Operation Routing

| Operation | Lifecycle | Engine | Governance | Services | Snapshot |
|---|---|---|---|---|---|
| SUBMIT | ✅ | ✅ | ✅ | ✅ | ✅ |
| CONNECT | ✅ | ✅ | ❌ | ✅ | ❌ |
| DISCONNECT | ✅ | ❌ | ❌ | ✅ | ❌ |
| VALIDATE | ❌ | ❌ | ❌ | ❌ | ❌ |
| QUERY | ❌ | ❌ | ❌ | ❌ | ❌ |
| HEALTH | ❌ | ❌ | ❌ | ❌ | ❌ |
| STATUS | ❌ | ❌ | ❌ | ❌ | ❌ |
| SNAPSHOT | ❌ | ❌ | ❌ | ❌ | ✅ |

## Thread Safety

All stateful gateway classes (`IntegrationGateway`, `IntegrationGatewayRegistry`, `IntegrationGatewayHistory`, `IntegrationGatewayStatistics`, `IntegrationGatewayStatusTracker`, `IntegrationGatewayEventBus`, `IntegrationComponentRegistry`) protect their internal state with `threading.Lock()`.

The `IntegrationGatewayContext` is not thread-safe by design — it is owned by a single request execution.

## Error Handling

`submit()` never raises — all failures are returned as `IntegrationGatewayResponse` with `status=FAILED`. The `error` and `error_code` fields carry the diagnostic.

Other public methods (`initialize`, `start`, `stop`, `restart`) raise `IntegrationGatewayError` subclasses on failure.

`GatewayNotReadyError` is raised by `submit()` if the gateway is not ACTIVE.

## Multi-Gateway with IntegrationGatewayManager

```python
from iios.integration.gateway import IntegrationGatewayManager

mgr = IntegrationGatewayManager(max_gateways=10)

# Create gateways for different environments
gw_prod    = mgr.create_gateway("gateway-production", auto_start=True)
gw_staging = mgr.create_gateway("gateway-staging", auto_start=True)

# Bulk operations
mgr.stop_all()
mgr.start_all()

# Health across all
health_map = mgr.health_all()   # Dict[str, IntegrationHealthSummary]

# Default gateway (lazily created)
gw = mgr.default_gateway()
```
