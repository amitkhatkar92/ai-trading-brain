# Messaging Guide

## Kafka

```python
from iios.integration.services import IntegrationServicesFactory

req = IntegrationServicesFactory.create_kafka_request(
    topic     = "trade-signals",
    payload   = {"symbol": "NIFTY", "signal": "BUY", "confidence": 0.87},
    operation = "produce",
)
response = engine.execute(req)
```

## RabbitMQ

```python
req = IntegrationServicesFactory.create_rabbitmq_request(
    exchange    = "iios.signals",
    routing_key = "trade.buy",
    payload     = {"symbol": "BANKNIFTY", "side": "BUY"},
)
response = engine.execute(req)
```

## Redis Streams

```python
from iios.integration.services import ConnectorRequest, ServiceType, TransportType

req = ConnectorRequest.create(
    approved_request_id = "redis-req-001",
    service_type        = ServiceType.REDIS_STREAM,
    transport_type      = TransportType.REDIS_PROTOCOL,
    endpoint            = "redis://localhost:6379",
    payload             = {"event": "trade", "symbol": "NIFTY"},
    connector_config    = {
        "redis_operation":  "xadd",
        "redis_stream_key": "iios:trades",
    },
)
response = engine.execute(req)
```

## Message Delivery Modes

| Mode | Description |
|---|---|
| `AT_MOST_ONCE` | Fire-and-forget (may be lost) |
| `AT_LEAST_ONCE` | Retries until ack'd (may duplicate) |
| `EXACTLY_ONCE` | Idempotent delivery (broker-level support) |

## In-Process Queue

```python
from iios.integration.services import QueueEngine, MessageDeliveryMode

queue = QueueEngine()
queue.create_queue("signals")
msg = queue.enqueue("signals", {"symbol": "NIFTY"})
msgs = queue.dequeue("signals", max_count=10)
```

## Event Bus

```python
from iios.integration.services import EventBusEngine

bus = EventBusEngine()
bus.subscribe("market.signal", lambda e: print(e.payload))
bus.publish_to("market.signal", source="strategy-lab", payload={"symbol": "NIFTY"})
```
