# Gateway Architecture Guide

## Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WorkflowGateway                          │  ← PUBLIC API
│         (initialize / start / stop / restart /              │
│          health / status / statistics / history /           │
│          validate / submit / query / cancel / retry)        │
├────────────────────┬───────────────────────────────────────┤
│ WorkflowGateway    │ WorkflowGatewayRouter                  │  ← ROUTING
│ Manager            ├───────────────────────────────────────┤
│ (lifecycle,        │ WorkflowGatewayDispatcher              │  ← DISPATCH
│  stats,            │ (coordinates M1-M5 subsystems)         │
│  history,          │                                        │
│  events)           │                                        │
├────────────────────┴───────────────────────────────────────┤
│                WorkflowComponentRegistry                    │  ← COMPONENT INDEX
├──────────────────────────────────────────────────────────  ┤
│  M1 Lifecycle  │  M2 Engine  │  M3 Policies  │  M4 Orch.  │  ← SUBSYSTEMS
│  M5 Snapshot Builder / Factory                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Classes

### WorkflowGateway
The ONLY class external code should use. Holds references to the manager,
validator, router, dispatcher, registry, and event bus.

### WorkflowGatewayManager
Owns all gateway-scoped state: component registry, statistics, history,
event bus, health monitor, and status tracker. Manages gateway lifecycle
transitions (initialize / start / stop / restart).

### WorkflowComponentRegistry
Thread-safe registry of M1–M5 component instances. Used by the dispatcher
to look up components by name. Named by constant strings from
`workflow_component_factory.py`.

### WorkflowComponentFactory
Creates and wires M1–M5 component instances. Registers them in the component
registry. Wires M3 as a governance hook in M2.

### WorkflowGatewayRouter
Stateless, maps `GatewayRequestType` → route string token (e.g. `"submit"`).

### WorkflowGatewayDispatcher
Dispatches requests to M2 engine and builds M5 snapshots.  Never raises
for workflow failures — always returns a `WorkflowGatewayResponse`.

### WorkflowGatewayValidation
Validates `WorkflowGatewayRequest` and `WorkflowGatewayResponse` against
invariants. Returns `GatewayValidationResult`.

---

## Component Name Registry

| Constant | Value | Component Type |
|---|---|---|
| `COMPONENT_LIFECYCLE` | `"lifecycle"` | `ComponentType.LIFECYCLE` |
| `COMPONENT_ENGINE` | `"engine"` | `ComponentType.ENGINE` |
| `COMPONENT_POLICY` | `"policy_engine"` | `ComponentType.POLICY_ENGINE` |
| `COMPONENT_ORCH` | `"orchestration_engine"` | `ComponentType.ORCHESTRATION_ENGINE` |
| `COMPONENT_SNAPSHOT_B` | `"snapshot_builder"` | `ComponentType.SNAPSHOT` |
| `COMPONENT_SNAPSHOT_F` | `"snapshot_factory"` | `ComponentType.SNAPSHOT` |

---

## Event Emission Map

| Gateway Action | Event Emitted |
|---|---|
| `initialize()` | `GATEWAY_INITIALIZED` |
| `start()` | `GATEWAY_STARTED` |
| `submit()` called | `WORKFLOW_SUBMITTED` |
| Response is success | `WORKFLOW_COMPLETED` |
| Response has snapshot | `SNAPSHOT_PUBLISHED` |
| `cancel()` success | `WORKFLOW_CANCELLED` |
| `retry()` success | `WORKFLOW_RETRIED` |
| `stop()` | `GATEWAY_STOPPED` |

---

## Thread Safety Contract

| Class | Thread-safe? | Notes |
|---|---|---|
| `WorkflowGateway` | ✅ | All methods lock internally |
| `WorkflowGatewayManager` | ✅ | `threading.Lock()` on state transitions |
| `WorkflowGatewayRegistry` | ✅ | Bounded list with lock |
| `WorkflowComponentRegistry` | ✅ | Lock on all mutations |
| `WorkflowGatewayHistory` | ✅ | Bounded deque with lock |
| `WorkflowGatewayStatistics` | ✅ | Lock on every counter update |
| `WorkflowGatewayEventBus` | ✅ | Per-event-type, lock on emit |
| `WorkflowGatewayRouter` | ✅ | Stateless |
| `WorkflowGatewayDispatcher` | ✅ | Stateless |
| `WorkflowGatewayValidation` | ✅ | Stateless |
| Domain objects (frozen dataclasses) | ✅ | Immutable |
