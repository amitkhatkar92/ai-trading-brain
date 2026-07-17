# Execution Gateway Engine — C6 Phase 5, Module 2

## Overview

The **Execution Gateway Engine** (EGE) is the orchestration layer for gateway
operations in the IIOS execution pipeline.  It coordinates request lifecycle,
queuing, dispatch, sessions, and statistics — without owning any
broker-specific logic or routing algorithms.

```
ExecutionGatewayEngine          ← public API (thin wrapper)
    └── GatewayManager          ← 10-step workflow orchestrator
            ├── GatewayEngineRegistry      ← request state store
            ├── GatewayOperationQueue      ← FIFO / priority / retry / cancel
            ├── GatewayDispatcher          ← pluggable broker abstraction
            ├── GatewaySessionManager      ← session grouping
            ├── GatewayStateManager        ← engine operational state
            ├── GatewayEngineStatistics    ← counters & rates
            ├── GatewayEngineHistory       ← bounded operation log
            ├── EngineGatewayValidator     ← stateless validation
            ├── GatewayEngineFactory       ← object construction
            └── GatewayLifecycle (M1)      ← per-request lifecycle state machine
```

## Quick Start

```python
from iios.execution.gateway.engine import ExecutionGatewayEngine

engine = ExecutionGatewayEngine()
engine.start()

ctx = engine.make_context(
    execution_id="EX-001",
    order_id="ORD-001",
    portfolio_id="PORT-A",
    strategy_id="STRAT-MOMENTUM",
    symbol="NIFTY",
    side="BUY",
    quantity=50.0,
    price=22500.0,
)

response = engine.submit_request(ctx)
print(response.is_accepted)   # True (SimulatedDispatch default)

engine.stop()
```

## Module Map

| File | Role |
|---|---|
| `constants.py` | Enums, sentinels, defaults |
| `exceptions.py` | Typed exceptions (EGE-000 … EGE-010) |
| `gateway_context.py` | `EngineGatewayContext` — frozen, immutable input |
| `gateway_request.py` | `EngineGatewayRequest` — mutable, thread-safe runtime state |
| `gateway_response.py` | `GatewayResponse` — frozen outcome delivered to caller |
| `gateway_operation.py` | `GatewayOperation` — single audit log entry |
| `gateway_session.py` | `GatewaySession` + `GatewaySessionManager` |
| `gateway_statistics.py` | `GatewayEngineStatistics` |
| `gateway_history.py` | `GatewayEngineHistory` — bounded deque |
| `gateway_snapshot.py` | `GatewayEngineSnapshot` — point-in-time view |
| `gateway_operation_queue.py` | `GatewayOperationQueue` facade (FIFO / priority / retry / cancel) |
| `gateway_registry.py` | `GatewayEngineRegistry` — lifecycle-aware request store |
| `gateway_validation.py` | `EngineGatewayValidator` — stateless, returns `EngineValidationResult` |
| `gateway_state_manager.py` | `GatewayStateManager` — thread-safe engine state with history |
| `gateway_dispatcher.py` | `GatewayDispatcher` + `SimulatedDispatch` + broker/router protocols |
| `gateway_events.py` | `GatewayEngineEvent` + factory functions |
| `gateway_factory.py` | `GatewayEngineFactory` — static object construction helpers |
| `gateway_manager.py` | `GatewayManager` — 10-step workflow orchestrator |
| `execution_gateway_engine.py` | `ExecutionGatewayEngine` — public API |
| `__init__.py` | Public `__all__` |

## Architecture Constraints

- The EGE does **not** contain broker-specific logic.
- The EGE does **not** contain routing algorithms.
- The EGE does **not** execute trades directly.
- It **only** coordinates gateway operations.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\execution\gateway\engine\ -q
# 204 passed
```

## Docs

- [Gateway Engine Guide](docs/gateway_engine_guide.md)
- [Workflow Guide](docs/workflow_guide.md)
- [Queue Management Guide](docs/queue_management_guide.md)
- [Session Management Guide](docs/session_management_guide.md)
- [Developer Guide](docs/developer_guide.md)
