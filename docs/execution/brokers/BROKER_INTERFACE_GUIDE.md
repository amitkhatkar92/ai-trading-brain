# Broker Interface Guide

Full reference for `AbstractBrokerInterface`, all 11 abstract operations,
request/response types, validation rules, and the event model.

---

## 1. The Broker Contract (`AbstractBrokerInterface`)

Every broker adapter MUST subclass `AbstractBroker` (which implements
`AbstractBrokerInterface`) and override all abstract methods.

### Abstract operations

| Category | Method | Request type | Response type |
|---|---|---|---|
| **Connection** | `connect()` | `ConnectionRequest` | `ConnectionResponse` |
| **Connection** | `disconnect()` | `ConnectionRequest` | `ConnectionResponse` |
| **Health** | `health()` | `BrokerRequest` | `HealthResponse` |
| **Health** | `heartbeat()` | `HeartbeatRequest` | `BrokerResponse` |
| **Orders** | `submit_order()` | `OrderRequest` | `OrderResponse` |
| **Orders** | `modify_order()` | `ModifyRequest` | `ModifyResponse` |
| **Orders** | `cancel_order()` | `CancelRequest` | `CancelResponse` |
| **Orders** | `order_status()` | `OrderRequest` | `OrderResponse` |
| **Account** | `positions()` | `PositionRequest` | `PositionResponse` |
| **Account** | `holdings()` | `PositionRequest` | `PositionResponse` |
| **Account** | `balances()` | `BalanceRequest` | `BalanceResponse` |
| **Account** | `margin()` | `BalanceRequest` | `BalanceResponse` |

### Properties

| Property | Type | Description |
|---|---|---|
| `broker_id` | `str` | Unique, immutable identifier |
| `metadata` | `BrokerMetadata` | Static broker description |
| `capabilities` | `BrokerCapabilities` | Capability set |
| `connection_state` | `BrokerConnectionState` | Current connectivity |
| `is_connected` | `bool` | Shortcut for `CONNECTED` state |

### Inherited from `AbstractBroker`

`AbstractBroker` provides:
- `_set_connection_state(state)` — thread-safe state mutation
- `_require_connected()` — guard that raises `BrokerNotConnectedError` if disconnected
- `heartbeat()` default — delegates to `health()` with timing wrapper
- `to_dict()` / `__repr__()` — serialisation and display

---

## 2. Request Types

All requests share these base fields:

| Field | Type | Description |
|---|---|---|
| `request_id` | `str` | Auto-generated UUID |
| `broker_id` | `str` | Target broker identifier |
| `request_type` | `BrokerRequestType` | Enum (ORDER, MODIFY, etc.) |
| `broker_mode` | `BrokerMode` | PAPER / LIVE / SIMULATION |
| `requested_at` | `float` | Unix timestamp |
| `correlation_id` | `str` | Cross-service trace ID |

### `OrderRequest` additional fields

| Field | Type | Description |
|---|---|---|
| `order_id` | `str` | Internal order ID |
| `instrument` | `str` | e.g. "RELIANCE" |
| `exchange` | `Exchange` | e.g. Exchange.NSE |
| `product` | `ProductType` | e.g. ProductType.CNC |
| `side` | `str` | "BUY" or "SELL" |
| `quantity` | `Decimal` | Number of units |
| `order_type` | `str` | "MARKET", "LIMIT", "STOP" |
| `price` | `Decimal \| None` | Limit price |
| `trigger_price` | `Decimal \| None` | Stop trigger |
| `tif` | `TimeInForce` | e.g. TimeInForce.DAY |
| `capability` | `BrokerCapabilityCode` | Which capability covers this |

---

## 3. Response Types

All responses share these base fields:

| Field | Type | Description |
|---|---|---|
| `response_id` | `str` | Auto-generated UUID |
| `request_id` | `str` | Echoes the originating request |
| `broker_id` | `str` | Originating broker |
| `status` | `BrokerResponseStatus` | SUCCESS / FAILURE / REJECTED / TIMEOUT |
| `succeeded` | `bool` | `status == SUCCESS` |
| `failed` | `bool` | `status` in `{FAILURE, REJECTED, TIMEOUT}` |
| `has_error` | `bool` | `failed` OR `error_message` non-empty |
| `duration_ms` | `float` | Adapter processing time |
| `error_message` | `str` | Human-readable error |
| `error_code` | `str` | Machine-readable code |

Responses are **frozen** (`@dataclass(frozen=True)`) — never mutated after creation.

---

## 4. Validation Rules

### Metadata validation (`BrokerValidator.validate_metadata`)

| Rule | Error code |
|---|---|
| `broker_id` non-empty | `MISSING_BROKER_ID` |
| `broker_name` non-empty | `MISSING_BROKER_NAME` |

### Request validation (`BrokerValidator.validate_request`)

| Rule | Error code |
|---|---|
| `request_id` non-empty | `MISSING_REQUEST_ID` |
| `broker_id` non-empty | `MISSING_BROKER_ID` |
| Non-health request requires `CONNECTED` state | `BROKER_NOT_CONNECTED` |
| `OrderRequest.capability` supported by broker | `UNSUPPORTED_CAPABILITY` |
| `OrderRequest.exchange` supported by broker | `UNSUPPORTED_EXCHANGE` |
| `OrderRequest.product` supported by broker | `UNSUPPORTED_PRODUCT` |

### Response validation (`BrokerValidator.validate_response`)

| Rule | Error code |
|---|---|
| `response_id` non-empty | `MISSING_RESPONSE_ID` |
| `broker_id` non-empty | `MISSING_BROKER_ID` |

---

## 5. Events

Events are emitted by `BrokerRegistry` when the following occur:

| Event type | When emitted |
|---|---|
| `BROKER_REGISTERED` | Broker metadata registered |
| `BROKER_UNREGISTERED` | Broker removed from registry |
| `BROKER_CONNECTED` | Connection state set to `CONNECTED` |
| `BROKER_DISCONNECTED` | Connection state set to anything other than `CONNECTED` |
| `BROKER_HEALTHY` | Health record updated as healthy |
| `BROKER_UNHEALTHY` | Health record updated as unhealthy |
| `REQUEST_VALIDATED` | Request passed validation (dispatched by adapters) |
| `RESPONSE_RECEIVED` | Response received from adapter |
| `HEARTBEAT_SENT` | Heartbeat dispatched |

### Listening for events

```python
from iios.execution.brokers import BrokerManager, BrokerEvent, BrokerEventType

manager = BrokerManager()
manager.start()

def on_event(event: BrokerEvent) -> None:
    if event.event_type == BrokerEventType.BROKER_HEALTHY:
        print(f"Broker {event.broker_id} is healthy")

manager.add_listener(on_event)
```

Listeners are called **outside** the registry lock. A faulty listener logs a warning
and does not interrupt other listeners.

---

## 6. Health Tracking

`BrokerHealthMonitor` maintains one `BrokerHealthRecord` per broker.

Each record tracks:
- `status` (HEALTHY / DEGRADED / UNHEALTHY / UNKNOWN)
- `connection_state` (CONNECTED / DISCONNECTED / …)
- `check_count`, `healthy_count`, `unhealthy_count`
- `consecutive_failures` (reset to 0 on each healthy update)
- `last_latency_ms`, `avg_latency_ms`
- `health_rate` = `healthy_count / check_count`

Updates via `BrokerManager.record_health_update(broker_id, is_healthy, latency_ms)`.

---

## 7. Statistics

### Per-broker (`BrokerStatistics`)

Tracks requests by type, success/failure counts, and average response time.

```python
stats = manager.get_statistics("dhan")
print(stats.success_rate)      # 0.98
print(stats.avg_response_ms)   # 7.3
print(stats.order_requests)    # 142
```

### Registry-level (`RegistryStatistics`)

```python
rs = manager.statistics()
print(rs.total_registered)    # 3
print(rs.total_requests)      # 5_412
print(rs.success_rate)        # 0.997
```

---

## 8. BrokerOperationContext

`BrokerOperationContext` is an immutable snapshot of the state at the moment a
broker operation is dispatched. It carries:

- `broker_id`, `operation`, `request_type`
- `broker_mode`, `connection_state`, `health_status`
- `request_id`, `correlation_id`
- `is_connected`, `is_healthy` (computed)
- `age_ms` (time since creation)

Create via:

```python
from iios.execution.brokers import make_context

ctx = make_context(
    broker_id        = "dhan",
    operation        = "submit_order",
    request          = order_request,
    connection_state = BrokerConnectionState.CONNECTED,
    health_status    = BrokerHealthStatus.HEALTHY,
)
```
