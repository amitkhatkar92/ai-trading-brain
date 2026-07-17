# Capability Guide

## Supported capabilities

| Capability | Description |
|---|---|
| `CASH_TRADING` | Cash (equity) buy/sell |
| `MARGIN_TRADING` | Leveraged intraday positions |
| `MIS` | Margin Intraday Square-off product |
| `CNC` | Cash and Carry (delivery) product |
| `NRML` | Normal margin for F&O |
| `INTRADAY` | Any intraday product |
| `DELIVERY` | Delivery / long-term holding |
| `OPTIONS` | Equity or index options |
| `FUTURES` | Equity or index futures |
| `CURRENCY` | Currency derivatives |
| `COMMODITY` | Commodity futures / options |
| `GTT` | Good Till Triggered orders |
| `AMO` | After Market Orders |
| `BRACKET_ORDERS` | Bracket orders with target/stop |
| `COVER_ORDERS` | Cover orders with in-built stop |
| `PARTIAL_FILL` | Partial fill support |
| `ORDER_MODIFICATION` | Modify pending orders |
| `ORDER_CANCELLATION` | Cancel pending orders |
| `WEBSOCKET` | Real-time market data via WebSocket |
| `MARKET_DATA` | Market data (polling or streaming) |

## Declaring capabilities

```python
from iios.execution.gateway.brokers import make_capabilities, BrokerCapability

caps = make_capabilities(
    BrokerCapability.CASH_TRADING,
    BrokerCapability.MIS,
    BrokerCapability.CNC,
    BrokerCapability.ORDER_MODIFICATION,
    BrokerCapability.ORDER_CANCELLATION,
)
```

Or from any iterable:

```python
from iios.execution.gateway.brokers import make_capabilities_from_iterable

caps = make_capabilities_from_iterable(BrokerCapability)  # all capabilities
```

## Capability queries

```python
caps.has(BrokerCapability.OPTIONS)       # True/False
caps.supports_all(BrokerCapability.MIS, BrokerCapability.CNC)
caps.supports_any(BrokerCapability.GTT,  BrokerCapability.AMO)
caps.missing(BrokerCapability.OPTIONS, BrokerCapability.FUTURES)
```

## Capability-based broker discovery

```python
# From manager
options_brokers = manager.find_by_capability(BrokerCapability.OPTIONS)

# From a mapping
from iios.execution.gateway.brokers import find_brokers_by_capability
ids = find_brokers_by_capability(caps_map, BrokerCapability.OPTIONS)
```

## Consistency rules

The validator checks for internal consistency:
- `MARGIN_TRADING` → should include `MIS` or `NRML`
- `BRACKET_ORDERS` → should include `CASH_TRADING` or `MARGIN_TRADING`
- `COVER_ORDERS` → same as bracket orders
- `GTT` → should include `ORDER_MODIFICATION`
- Missing `ORDER_CANCELLATION` → warning

Consistency failures are **warnings** (not errors) and do not block
registration.
