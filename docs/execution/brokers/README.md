# Broker Abstraction Layer — Package README

**Package path:** `iios/execution/brokers/`
**Version:** 1.0.0
**IIOS Component:** C6 Execution Intelligence — Phase 1, Module 3

---

## Purpose

The Broker Abstraction Layer defines the **common broker contract** for the IIOS
institutional platform. It specifies what a broker must be able to do, the types
used to communicate with it, and how its metadata, capabilities, health, and
statistics are tracked.

**This layer does NOT:**
- Connect to any broker
- Implement API clients
- Perform HTTP, REST, WebSocket, or FIX communication
- Handle authentication or credentials
- Contain any exchange logic or vendor SDK

**This layer DOES:**
- Define `AbstractBrokerInterface` — the canonical contract every adapter must satisfy
- Provide `AbstractBroker` — a partial base with lifecycle boilerplate
- Define all request types: `ConnectionRequest`, `OrderRequest`, `ModifyRequest`,
  `CancelRequest`, `PositionRequest`, `BalanceRequest`, `HeartbeatRequest`
- Define all response types: `ConnectionResponse`, `OrderResponse`, etc.
- Track broker capabilities via `BrokerCapabilities`
- Maintain broker metadata via `BrokerMetadata`
- Store health records via `BrokerHealthMonitor`
- Accumulate statistics via `BrokerStatistics`
- Emit events via `BrokerEvent` and `BrokerEventType`
- Validate metadata and requests via `BrokerValidator`
- Orchestrate everything via `BrokerManager` (IIOS v1.0 lifecycle facade)

---

## Future Adapters (not in this module)

| Adapter | Module |
|---|---|
| Dhan | `iios/execution/brokers/adapters/dhan/` |
| Zerodha | `iios/execution/brokers/adapters/zerodha/` |
| Interactive Brokers | `iios/execution/brokers/adapters/ib/` |
| Binance | `iios/execution/brokers/adapters/binance/` |
| Paper Broker | `iios/execution/brokers/adapters/paper/` |
| Backtest Broker | `iios/execution/brokers/adapters/backtest/` |

---

## Package Structure

```
iios/execution/brokers/
├── __init__.py            # Full public API
├── constants.py           # System IDs, enums, bounds
├── exceptions.py          # Exception hierarchy (BR-000 … BR-013)
├── broker.py              # AbstractBroker — partial base class
├── broker_interface.py    # AbstractBrokerInterface — pure contract
├── broker_metadata.py     # BrokerMetadata, RateLimitSpec
├── broker_capabilities.py # BrokerCapabilities + helpers
├── broker_request.py      # All request dataclasses
├── broker_response.py     # All response dataclasses
├── broker_context.py      # BrokerOperationContext + make_context()
├── broker_validation.py   # BrokerValidator + BrokerValidationResult
├── broker_events.py       # BrokerEvent + BrokerEventType
├── broker_health.py       # BrokerHealthRecord + BrokerHealthMonitor
├── broker_statistics.py   # BrokerStatistics + RegistryStatistics
├── broker_registry.py     # BrokerRegistry (IIOS v1.0 LifecycleAwareMixin)
├── broker_factory.py      # BrokerFactory — creates BrokerMetadata objects
└── broker_manager.py      # BrokerManager — primary facade
```

---

## Quick Start

```python
from iios.execution.brokers import (
    BrokerManager,
    BrokerCapabilityCode,
    BrokerMode,
    Exchange,
    ProductType,
    TimeInForce,
)

# 1. Start the manager
manager = BrokerManager()
manager.start()

# 2. Register a broker by its metadata
record = manager.create_and_register(
    broker_id    = "dhan",
    broker_name  = "Dhan Broker",
    capabilities = frozenset({
        BrokerCapabilityCode.MARKET_ORDER,
        BrokerCapabilityCode.LIMIT_ORDER,
        BrokerCapabilityCode.AMO,
        BrokerCapabilityCode.GTT,
        BrokerCapabilityCode.PARTIAL_FILL,
    }),
    supported_modes     = frozenset({BrokerMode.LIVE, BrokerMode.PAPER}),
    supported_exchanges = frozenset({Exchange.NSE, Exchange.BSE, Exchange.NFO}),
    supported_products  = frozenset({ProductType.CNC, ProductType.MIS, ProductType.NRML}),
    supported_tif       = frozenset({TimeInForce.DAY, TimeInForce.IOC, TimeInForce.GTC}),
    description         = "Dhan institutional broker adapter",
)

# 3. Query capabilities
caps = manager.get_capabilities("dhan")
print(caps.has(BrokerCapabilityCode.AMO))   # True
print(caps.supports_exchange(Exchange.NSE)) # True

# 4. Track health (called by the future adapter)
manager.record_health_update("dhan", is_healthy=True, latency_ms=8.0)
hr = manager.get_health("dhan")
print(hr.is_healthy, hr.avg_latency_ms)     # True  8.0

# 5. Statistics
stats = manager.statistics()
print(stats.total_registered)   # 1

manager.stop()
```

---

## Error Codes

| Code | Exception | When raised |
|---|---|---|
| BR-000 | `BrokerAbstractionError` | Generic layer error |
| BR-001 | `BrokerRegistrationError` | Registration failure |
| BR-002 | `BrokerNotFoundError` | broker_id not in registry |
| BR-003 | `DuplicateBrokerError` | Duplicate broker_id |
| BR-004 | `BrokerCapacityError` | Registry full |
| BR-005 | `BrokerNotConnectedError` | Operation requires connection |
| BR-006 | `BrokerConnectionError` | Connect/disconnect failure |
| BR-007 | `BrokerValidationError` | Validation failure |
| BR-008 | `BrokerCapabilityError` | Capability not supported |
| BR-009 | `BrokerRequestError` | Malformed request |
| BR-010 | `BrokerResponseError` | Unexpected response |
| BR-011 | `BrokerHealthError` | Health check error |
| BR-012 | `BrokerNotRunningError` | Manager/registry not started |
| BR-013 | `BrokerFactoryError` | Factory cannot build broker |

---

## Tests

```
tests/unit/iios/execution/brokers/test_broker_abstraction_layer.py
```

16 test classes, 138 test cases.

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/iios/execution/brokers/test_broker_abstraction_layer.py -v
```

---

## Related Documentation

- [BROKER_INTERFACE_GUIDE.md](BROKER_INTERFACE_GUIDE.md) — Contract, operations, validation rules
- [CAPABILITY_MATRIX.md](CAPABILITY_MATRIX.md) — All capabilities, exchanges, products, TIF
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — IIOS conventions, how to implement an adapter
