# Interface Specification

## BrokerInterface contract

Every broker plugin must subclass `BrokerInterface` and implement all
abstract methods and properties listed below.

### Required properties

| Property | Type | Description |
|---|---|---|
| `broker_id` | `str` | Unique identifier (e.g. `"DHAN-001"`) |
| `broker_name` | `str` | Human-readable name (e.g. `"Dhan"`) |
| `is_connected` | `bool` | True when connection is in a ready state |
| `is_authenticated` | `bool` | True when a valid session exists |

### Required methods

| Method | Returns | Description |
|---|---|---|
| `connect()` | `BrokerResponse` | Establish connection |
| `disconnect()` | `BrokerResponse` | Graceful shutdown |
| `authenticate()` | `BrokerResponse` | Authenticate with credentials |
| `refresh_session()` | `BrokerResponse` | Extend or renew session |
| `health()` | `BrokerHealthRecord` | Lightweight health check |
| `status()` | `BrokerStatus` | Local state query (no network) |
| `capabilities()` | `BrokerCapabilities` | Declared capability set |
| `place_order(request)` | `BrokerResponse` | Submit new order |
| `modify_order(request)` | `BrokerResponse` | Modify pending order |
| `cancel_order(request)` | `BrokerResponse` | Cancel pending order |
| `get_order(order_id)` | `BrokerResponse` | Retrieve single order |
| `get_orders()` | `BrokerResponse` | Retrieve all orders |
| `get_positions()` | `BrokerResponse` | Retrieve open positions |
| `get_holdings()` | `BrokerResponse` | Retrieve long-term holdings |
| `get_funds()` | `BrokerResponse` | Retrieve available funds |
| `get_margin()` | `BrokerResponse` | Retrieve margin information |
| `ping()` | `bool` | Lightweight connectivity check |

### Minimal implementation skeleton

```python
from iios.execution.gateway.brokers import (
    BrokerInterface, BrokerCapabilities, BrokerConfiguration,
    BrokerStatus, BrokerResponse, BrokerHealthRecord,
    BrokerCapability, OrderRequest, ModifyOrderRequest,
    CancelOrderRequest,
    make_success_response, make_capabilities, make_health_record,
)

class MyBroker(BrokerInterface):
    def __init__(self) -> None:
        self._broker_id   = "MY-BROKER-001"
        self._broker_name = "My Broker"
        self._connected   = False
        self._authed      = False

    @property
    def broker_id(self) -> str:
        return self._broker_id

    @property
    def broker_name(self) -> str:
        return self._broker_name

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_authenticated(self) -> bool:
        return self._authed

    def connect(self) -> BrokerResponse:
        # ... real connection logic here ...
        self._connected = True
        return make_success_response("connect", self._broker_id)

    def disconnect(self) -> BrokerResponse:
        self._connected = False
        self._authed    = False
        return make_success_response("disconnect", self._broker_id)

    def authenticate(self) -> BrokerResponse:
        # ... real auth logic here ...
        self._authed = True
        return make_success_response("authenticate", self._broker_id)

    def refresh_session(self) -> BrokerResponse:
        return make_success_response("refresh", self._broker_id)

    def health(self) -> BrokerHealthRecord:
        return make_health_record(self._broker_id, is_healthy=self._connected)

    def status(self) -> BrokerStatus:
        if self._authed:
            return BrokerStatus.ACTIVE
        return BrokerStatus.DISCONNECTED

    def capabilities(self) -> BrokerCapabilities:
        return make_capabilities(
            BrokerCapability.CASH_TRADING,
            BrokerCapability.MIS,
            BrokerCapability.CNC,
            BrokerCapability.ORDER_MODIFICATION,
            BrokerCapability.ORDER_CANCELLATION,
        )

    def place_order(self, request: OrderRequest) -> BrokerResponse:
        # ... call broker API ...
        return make_success_response(request.request_id, self._broker_id)

    # ... implement remaining methods ...

    def ping(self) -> bool:
        return self._connected
```
