# Protocol Guide

## Supported Protocols

| Protocol | TransportType | Used By |
|---|---|---|
| HTTP | `HTTP` | REST, HTTP |
| HTTPS | `HTTP` | REST, REST API |
| WebSocket | `WEBSOCKET` | WebSocket |
| gRPC | `GRPC` | gRPC |
| AMQP | `AMQP` | RabbitMQ |
| Kafka Protocol | `KAFKA_PROTOCOL` | Kafka |
| Redis Protocol | `REDIS_PROTOCOL` | Redis Streams |
| File System | `FILE_SYSTEM` | File Transfer |
| Database Wire | `DATABASE_WIRE` | Database |
| Internal | `INTERNAL` | Notifications, Event Bus |

## Protocol Registry

```python
from iios.integration.services import ProtocolRegistry, ProtocolDescriptor, TransportType

registry = ProtocolRegistry()
# Register custom protocol
desc = ProtocolDescriptor(
    protocol_id   = "my-protocol",
    transport     = TransportType.HTTP,
    name          = "My Protocol",
    version       = "1.0.0",
    metadata      = {},
)
registry.register(desc)
```

## Protocol Engine

The `ProtocolEngine` executes the transport layer for a connector context:

```python
from iios.integration.services import ProtocolEngine, ConnectorContext, ServiceType, TransportType, AuthScheme

engine = ProtocolEngine()
context = ConnectorContext.create(
    request_id     = "req-123",
    session_id     = "sess-456",
    service_type   = ServiceType.REST_API,
    transport_type = TransportType.HTTP,
    endpoint       = "https://api.example.com/data",
)
result = engine.execute(context, payload={"key": "val"})
```
