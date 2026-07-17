# Broker Abstraction Layer — C6 Phase 5, Module 3

## Purpose

The **Broker Abstraction Layer** (BAL) isolates the entire IIOS platform
from broker-specific APIs.  Every broker must implement the same interface.
No IIOS module may directly communicate with broker SDKs or REST APIs.

```
BrokerManager               ← public orchestrator
    └── BrokerRegistry      ← broker storage and lookup
    └── ConnectionPool      ← connection state per broker
    └── BrokerSessionManager ← auth session tracking
    └── BrokerHealthMonitor ← health record storage
    └── BrokerStatisticsStore ← per-broker counters
    └── BrokerHistory       ← bounded event + response log
    └── BrokerValidator     ← stateless validation
    └── BrokerFactory       ← object construction helpers
```

## Quick Start

```python
from iios.execution.gateway.brokers import BrokerManager, BrokerConfiguration
from iios.execution.gateway.brokers import make_order_request, OrderSide, OrderType, ProductType

manager = BrokerManager()
manager.start()

# Register your broker plugin (implements BrokerInterface)
manager.register_broker(my_broker, BrokerConfiguration(
    broker_id="DHAN-001",
    broker_name="Dhan",
))

# Connect and authenticate
manager.connect("DHAN-001")
manager.authenticate("DHAN-001")

# Place an order
req  = make_order_request(
    "DHAN-001", "NIFTY", "NSE",
    OrderSide.BUY, OrderType.MARKET, ProductType.MIS,
    quantity=50.0, price=0.0,
)
resp = manager.place_order("DHAN-001", req)
print(resp.is_success)

manager.stop()
```

## Module Map

| File | Role |
|---|---|
| `constants.py` | Enums, sentinels, defaults |
| `exceptions.py` | Typed exceptions (BAL-000 … BAL-014) |
| `broker_interface.py` | `BrokerInterface` ABC — every plugin must satisfy this |
| `broker_capabilities.py` | `BrokerCapabilities` — immutable frozenset of capabilities |
| `broker_configuration.py` | `BrokerConfiguration` — frozen configuration record |
| `broker_request.py` | Standardized request models (OrderRequest, etc.) |
| `broker_response.py` | `BrokerResponse` — uniform outcome model |
| `broker_connection.py` | `BrokerConnection` + `ConnectionPool` — connection state |
| `broker_session.py` | `BrokerSession` + `BrokerSessionManager` — auth session state |
| `broker_health.py` | `BrokerHealthRecord` + `BrokerHealthMonitor` |
| `broker_statistics.py` | `BrokerStatistics` + `BrokerStatisticsStore` |
| `broker_history.py` | `BrokerHistory` — bounded event + response log |
| `broker_events.py` | `BrokerEvent` + 9 factory functions |
| `broker_validation.py` | `BrokerValidator` + `BrokerValidationResult` |
| `broker_factory.py` | `BrokerFactory` — static construction helpers |
| `broker_registry.py` | `BrokerRegistry` (LifecycleAwareMixin) |
| `broker_manager.py` | `BrokerManager` (LifecycleAwareMixin) — orchestrator |
| `__init__.py` | Public `__all__` |

## Architecture Constraints

- The BAL does **not** implement Dhan, Zerodha, or any other broker.
- The BAL does **not** contain REST clients or WebSocket clients.
- The BAL does **not** store credentials or tokens.
- It **only** defines the abstraction contract and coordinates operations.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\execution\gateway\brokers\ -q
# 277 passed
```

## Docs

- [Broker Abstraction Guide](docs/broker_abstraction_guide.md)
- [Interface Specification](docs/interface_specification.md)
- [Capability Guide](docs/capability_guide.md)
- [Connection Lifecycle](docs/connection_lifecycle.md)
- [Developer Guide](docs/developer_guide.md)
