# Broker Abstraction Guide

## What is the BAL?

The Broker Abstraction Layer isolates every IIOS module from broker-specific
APIs.  When the execution pipeline needs to place an order, it calls
`BrokerManager.place_order()`.  The manager delegates to the registered
broker plugin.  The caller never knows whether the broker is Dhan, Zerodha,
Angel One, or a paper-trading simulator.

## Design principles

1. **Single interface.** All brokers implement `BrokerInterface`.
2. **Uniform responses.** All operations return `BrokerResponse`.
3. **No credentials.** The BAL never stores API keys, tokens, or secrets.
4. **Pure abstraction.** No SDK code lives in this package.

## BrokerManager responsibility

The manager:
- Drives the connection lifecycle (connect → authenticate → refresh)
- Routes requests to the right broker plugin
- Fires domain events (BROKER_CONNECTED, AUTHENTICATION_SUCCEEDED, …)
- Tracks per-broker statistics and history
- Monitors health
- Manages sessions and connection state

The manager does NOT:
- Contain broker-specific logic
- Store credentials
- Implement routing algorithms

## Multiple brokers

```python
manager.register_broker(dhan_broker,    dhan_config)
manager.register_broker(zerodha_broker, zerodha_config)

# Set the default
manager.set_default_broker("DHAN-001")

# Or select explicitly
resp = manager.place_order("ZERODHA-001", order_req)
```

## Capability-based routing

```python
# Find all brokers that support OPTIONS
options_brokers = manager.find_by_capability(BrokerCapability.OPTIONS)
```
