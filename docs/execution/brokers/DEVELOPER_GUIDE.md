# Broker Abstraction Layer — Developer Guide

How to implement a broker adapter, extend the abstraction layer,
and integrate with the IIOS v1.0 framework.

---

## 1. IIOS v1.0 Conventions

### Logging

```python
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger

SYSTEM_ID = "iios:execution:brokers:dhan"

_log   = get_logger(__name__, engine_id=SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=SYSTEM_ID, component="DhanAdapter")

_log.info("Order submitted.", order_id=order_id)
_audit.log_workflow_event(
    SYSTEM_ID, "submit_order", "ORDER_SUBMITTED",
    actor="iios:system", order_id=order_id,
)
```

**Do NOT use `import logging` (stdlib).**

### Error handling

```python
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.errors.error_context import ErrorContext

ctx = ErrorContext(engine_id=SYSTEM_ID, operation="submit_order", stage="validation")
_get_err_mgr().report_failure(SYSTEM_ID, exc, ctx)
```

### Lifecycle services (`BrokerRegistry`, `BrokerManager`)

```python
registry = BrokerRegistry()
registry.start()
# ... use ...
registry.stop()
```

`lifecycle_state()` is a **method** → call as `self.lifecycle_state()`.

---

## 2. Implementing a Broker Adapter

Subclass `AbstractBroker` from `iios.execution.brokers.broker`:

```python
from iios.execution.brokers.broker import AbstractBroker
from iios.execution.brokers.broker_metadata import BrokerMetadata
from iios.execution.brokers.broker_request import (
    ConnectionRequest, OrderRequest, ModifyRequest,
    CancelRequest, PositionRequest, BalanceRequest, BrokerRequest,
)
from iios.execution.brokers.broker_response import (
    ConnectionResponse, OrderResponse, ModifyResponse,
    CancelResponse, PositionResponse, BalanceResponse, HealthResponse, BrokerResponse,
)
from iios.execution.brokers.constants import (
    BrokerConnectionState, BrokerHealthStatus, BrokerResponseStatus, BrokerRequestType,
)

class DhanAdapter(AbstractBroker):
    """Dhan broker adapter — IIOS v1.0."""

    def connect(self, request: ConnectionRequest) -> ConnectionResponse:
        # Do NOT put auth logic here — this is abstraction only.
        # In a real adapter, this is where the Dhan API session would be started.
        self._set_connection_state(BrokerConnectionState.CONNECTED)
        return ConnectionResponse(
            broker_id        = self.broker_id,
            request_id       = request.request_id,
            connection_state = BrokerConnectionState.CONNECTED,
        )

    def disconnect(self, request: ConnectionRequest) -> ConnectionResponse:
        self._set_connection_state(BrokerConnectionState.DISCONNECTED)
        return ConnectionResponse(
            broker_id        = self.broker_id,
            request_id       = request.request_id,
            connection_state = BrokerConnectionState.DISCONNECTED,
        )

    def health(self, request: BrokerRequest) -> HealthResponse:
        return HealthResponse(
            broker_id     = self.broker_id,
            request_id    = request.request_id,
            health_status = BrokerHealthStatus.HEALTHY,
            latency_ms    = 3.0,
        )

    def submit_order(self, request: OrderRequest) -> OrderResponse:
        self._require_connected()
        # Delegate to Dhan API client here (future adapter module).
        return OrderResponse(
            broker_id      = self.broker_id,
            request_id     = request.request_id,
            order_id       = request.order_id,
            acknowledged   = True,
        )

    def modify_order(self, request: ModifyRequest) -> ModifyResponse:
        self._require_connected()
        return ModifyResponse(
            broker_id = self.broker_id,
            request_id = request.request_id,
            order_id  = request.order_id,
            modified  = True,
        )

    def cancel_order(self, request: CancelRequest) -> CancelResponse:
        self._require_connected()
        return CancelResponse(
            broker_id = self.broker_id,
            request_id = request.request_id,
            order_id  = request.order_id,
            cancelled = True,
        )

    def order_status(self, request: OrderRequest) -> OrderResponse:
        self._require_connected()
        return OrderResponse(broker_id=self.broker_id, request_id=request.request_id)

    def positions(self, request: PositionRequest) -> PositionResponse:
        self._require_connected()
        return PositionResponse(broker_id=self.broker_id, request_id=request.request_id)

    def holdings(self, request: PositionRequest) -> PositionResponse:
        self._require_connected()
        return PositionResponse(broker_id=self.broker_id, request_id=request.request_id)

    def balances(self, request: BalanceRequest) -> BalanceResponse:
        self._require_connected()
        return BalanceResponse(broker_id=self.broker_id, request_id=request.request_id)

    def margin(self, request: BalanceRequest) -> BalanceResponse:
        self._require_connected()
        return BalanceResponse(broker_id=self.broker_id, request_id=request.request_id)
```

### Registering the adapter

```python
from iios.execution.brokers import BrokerManager, BrokerMode, Exchange, ProductType, TimeInForce
from iios.execution.brokers import BrokerCapabilityCode
from iios.execution.brokers.broker_metadata import BrokerMetadata

manager = BrokerManager()
manager.start()

metadata = BrokerMetadata(
    broker_id    = "dhan",
    broker_name  = "Dhan Broker",
    capabilities = frozenset({
        BrokerCapabilityCode.MARKET_ORDER,
        BrokerCapabilityCode.LIMIT_ORDER,
        BrokerCapabilityCode.AMO,
        BrokerCapabilityCode.PARTIAL_FILL,
    }),
    supported_modes     = frozenset({BrokerMode.LIVE, BrokerMode.PAPER}),
    supported_exchanges = frozenset({Exchange.NSE, Exchange.BSE, Exchange.NFO}),
    supported_products  = frozenset({ProductType.CNC, ProductType.MIS, ProductType.NRML}),
    supported_tif       = frozenset({TimeInForce.DAY, TimeInForce.IOC}),
)

record   = manager.register(metadata)
adapter  = DhanAdapter(metadata)
```

---

## 3. Adding a New Capability

1. Add a new member to `BrokerCapabilityCode` in `constants.py`.
2. Document it in `docs/execution/brokers/CAPABILITY_MATRIX.md`.
3. Export it from `__init__.py`.
4. Add test coverage in `test_broker_abstraction_layer.py`.

---

## 4. Adding a New Request / Response Type

Requests:
1. Create a new `@dataclass` subclassing `BrokerRequest` in `broker_request.py`.
2. Add a `BrokerRequestType` enum member in `constants.py`.
3. Export from `__init__.py`.

Responses:
1. Create a new `@dataclass(frozen=True)` subclassing `BrokerResponse` in `broker_response.py`.
2. Export from `__init__.py`.
3. Add the corresponding abstract method to `AbstractBrokerInterface`.
4. Add a default (or abstract) implementation to `AbstractBroker`.

---

## 5. C6 Lock Manifest

The following elements are locked at version 1.0.0.
Changes require explicit architectural review.

| Element | What is locked |
|---|---|
| `AbstractBrokerInterface` abstract methods | Signatures of all 12 operations |
| `BrokerCapabilityCode` existing values | Renaming or removing any value |
| `Exchange` existing values | Renaming or removing any value |
| `ProductType` existing values | Renaming or removing any value |
| `TimeInForce` existing values | Renaming or removing any value |
| `BrokerRequest` base fields | `request_id`, `broker_id`, `request_type`, `requested_at` |
| `BrokerResponse` base fields | `response_id`, `request_id`, `broker_id`, `status`, `succeeded`, `failed`, `has_error` |
| Error codes BR-000 through BR-013 | Semantics of each exception |
| `BrokerManager` public methods | `register()`, `unregister()`, `create_and_register()`, `get_record()`, `get_capabilities()`, `statistics()` |
| `BrokerRegistry` public methods | Same as manager + `all_records()`, `count()` |
| `BrokerFactory` public methods | `create_metadata()`, `gen_broker_id()` |

**Additive changes** (new capabilities, new exchanges, new optional fields, new
helper methods) are permitted without review, provided no locked element is altered.

---

## 6. Testing Conventions

```
tests/unit/iios/execution/brokers/test_broker_abstraction_layer.py
```

- 16 test classes, 138 test cases.
- Use `BrokerRegistry` and `BrokerManager` fixtures (start/stop included).
- Implement a minimal concrete `ConcreteBroker` inline for interface tests.
- Use `frozenset` for all capability, exchange, product, and TIF sets.

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/iios/execution/brokers/ -v
```

---

## 7. Deployment

```powershell
git add iios/execution/brokers/ tests/unit/iios/execution/brokers/ docs/execution/brokers/
git commit -m "feat(c6): Broker Abstraction Layer Module 3 — contracts, metadata, health, statistics"
git push origin main
ssh -i ~/.ssh/trading_vps root@178.18.252.24 `
    "cd /root/ai-trading-brain && git pull origin main && docker compose build --no-cache && docker compose down && docker compose up -d && sleep 8 && docker compose ps"
```

Both containers must show `Up … (healthy)` before the deploy is considered complete.
