# Developer Guide

## Exception hierarchy

```
IIOSError
└── BrokerAbstractionError              BAL-000
        ├── BrokerNotRegisteredError    BAL-001
        ├── BrokerAlreadyRegisteredError BAL-002
        ├── BrokerNotConnectedError     BAL-003
        ├── BrokerAuthenticationError   BAL-004
        ├── BrokerSessionExpiredError   BAL-005
        ├── BrokerCapabilityNotSupportedError BAL-006
        ├── BrokerValidationError       BAL-007
        ├── BrokerConfigurationError    BAL-008
        ├── BrokerConnectionError       BAL-009
        ├── BrokerRegistryCapacityError BAL-010
        ├── BrokerHealthError           BAL-011
        ├── BrokerRequestError          BAL-012
        ├── BrokerManagerNotRunningError BAL-013
        └── DuplicateBrokerError        BAL-014
```

## Thread safety

All public components are thread-safe:

| Component | Lock type |
|---|---|
| `BrokerRegistry` | `threading.Lock` |
| `BrokerConnection` | `threading.RLock` |
| `ConnectionPool` | `threading.Lock` |
| `BrokerSession` | `threading.RLock` |
| `BrokerSessionManager` | `threading.Lock` |
| `BrokerHealthMonitor` | `threading.Lock` |
| `BrokerStatisticsStore` | `threading.Lock` |
| `BrokerHistory` | `threading.Lock` |

## Events

Register a listener **before** `start()` to capture `BROKER_REGISTERED` events
fired during the first registration.

```python
manager = BrokerManager()
manager.add_event_listener(my_listener)
manager.start()
manager.register_broker(broker, config)
```

Event types and their triggers:

| Event | Trigger |
|---|---|
| `BROKER_REGISTERED` | `register_broker()` |
| `BROKER_CONNECTED` | `connect()` success |
| `BROKER_DISCONNECTED` | `disconnect()` |
| `AUTHENTICATION_SUCCEEDED` | `authenticate()` success |
| `AUTHENTICATION_FAILED` | `authenticate()` failure |
| `SESSION_EXPIRED` | `expire_stale_sessions()` |
| `RECONNECT_STARTED` | `signal_reconnect_started()` |
| `RECONNECT_SUCCEEDED` | `signal_reconnect_succeeded()` |
| `BROKER_HEALTH_CHANGED` | `check_health()` when health status changes |

## Validation

```python
from iios.execution.gateway.brokers import BrokerValidator

v = BrokerValidator()

# Validate before manual registration
result = v.validate_registration(broker, existing_ids, max_brokers)
v.raise_if_invalid(result, context="my_context")

# Validate a session
result = v.validate_session(session)

# Validate a connection
result = v.validate_connection(connection)
```

## Configuration defaults

```python
from iios.execution.gateway.brokers import (
    DEFAULT_MAX_BROKERS,              # 100
    DEFAULT_MAX_HISTORY,              # 5_000
    DEFAULT_HEARTBEAT_INTERVAL_SECS,  # 30.0
    DEFAULT_RECONNECT_DELAY_SECS,     # 5.0
    DEFAULT_MAX_RECONNECT_ATTEMPTS,   # 10
    DEFAULT_CONNECTION_TIMEOUT_SECS,  # 30.0
    DEFAULT_AUTH_TIMEOUT_SECS,        # 30.0
    DEFAULT_REQUEST_TIMEOUT_SECS,     # 10.0
    DEFAULT_SESSION_TIMEOUT_SECS,     # 3600.0
    DEFAULT_MAX_RETRIES,              # 3
)
```

Override at construction time:

```python
manager = BrokerManager(max_brokers=10, max_history=10_000)
```

## Testing your broker plugin

Use `_TestBroker` from the test suite as a reference implementation.
Ensure your plugin:

1. Subclasses `BrokerInterface`
2. Has non-empty `broker_id` and `broker_name`
3. Returns `BrokerResponse` from all operations
4. Returns `BrokerHealthRecord` from `health()`
5. Returns `BrokerCapabilities` from `capabilities()`
6. Returns `BrokerStatus` from `status()`
7. Returns `bool` from `ping()`

Run the interface compliance check:

```python
from iios.execution.gateway.brokers import BrokerValidator
v = BrokerValidator()
result = v.validate_interface_compliance(my_broker)
assert result.is_valid, result.errors
```
