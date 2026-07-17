# Connection Lifecycle

## Broker status state machine

```
DISCONNECTED
    │
    ▼  connect()
CONNECTING
    │
    ▼  set_connected()
CONNECTED ──────────────────────────► DEGRADED
    │                                    │
    ▼  authenticate()                    │
AUTHENTICATING                           │
    │                                    │
    ▼  mark_authenticated()              │
ACTIVE ◄─────────────────────────────────┘
    │
    │  failure
    ▼
RECONNECTING ──► CONNECTED
    │
    │  max attempts exceeded
    ▼
FAILED ──► (re-register required)

─── stop() ──► STOPPED (from any state)
```

## BrokerConnection state transitions

| Method | Transitions to |
|---|---|
| `set_connecting()` | CONNECTING |
| `set_authenticating()` | AUTHENTICATING |
| `set_connected()` | CONNECTED; records `connected_at` |
| `set_active()` | ACTIVE |
| `set_degraded()` | DEGRADED |
| `set_reconnecting()` | RECONNECTING; increments `reconnect_count` |
| `set_disconnected()` | DISCONNECTED; records `disconnected_at` |
| `set_failed()` | FAILED (terminal) |
| `set_stopped()` | STOPPED (terminal) |
| `record_heartbeat()` | Updates `last_heartbeat_at` |

## Ready states

`is_ready` is True for: **CONNECTED, ACTIVE, DEGRADED**.

Only ready connections should receive order operations.

## ConnectionPool

A broker may have multiple named connections:

```python
pool = manager._get_pool("DHAN-001")
pool.add("orders")
pool.add("data")

conn_orders = pool.get("orders")
conn_data   = pool.get("data")

pool.is_any_ready()      # True if any connection is ready
pool.disconnect_all()    # Set all connections to DISCONNECTED
pool.stop_all()          # Set all connections to STOPPED
```

## Manager-driven connection flow

```python
# 1. Register broker plugin
manager.register_broker(broker, config)

# 2. Establish network connection
resp = manager.connect("DHAN-001")         # calls broker.connect()

# 3. Authenticate
resp = manager.authenticate("DHAN-001")    # calls broker.authenticate()

# 4. Submit orders
resp = manager.place_order("DHAN-001", req)

# 5. Refresh before session expires
resp = manager.refresh_session("DHAN-001")

# 6. Handle reconnect
manager.signal_reconnect_started("DHAN-001")
manager.signal_reconnect_succeeded("DHAN-001")

# 7. Disconnect
resp = manager.disconnect("DHAN-001")
```

## Auto-reconnect

The manager's `signal_reconnect_started()` and `signal_reconnect_succeeded()`
methods update connection state and fire the appropriate events.
The actual reconnection logic lives in the broker plugin or a separate
reconnect scheduler that calls `manager.connect()` + `manager.authenticate()`.
