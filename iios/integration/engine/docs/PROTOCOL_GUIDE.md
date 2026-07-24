# Protocol Guide — C15 M2

## Overview

A **protocol** describes the communication standard for an integration.  Protocol
implementations live in M4.  The engine validates that the protocol for a request
is registered before dispatching.

## 13 Protocol Types

| Protocol | Description |
|---|---|
| HTTP | Plain HTTP |
| HTTPS | Secure HTTP |
| WEBSOCKET | WebSocket bidirectional |
| GRPC | gRPC binary protocol |
| AMQP | Advanced Message Queuing |
| KAFKA_PROTOCOL | Apache Kafka wire protocol |
| REDIS_PROTOCOL | Redis Serialization Protocol |
| JDBC | Java Database Connectivity |
| FILE_SYSTEM | Local/remote file system |
| CLOUD_API | Cloud provider REST APIs |
| BROKER_API | Trading broker proprietary |
| MARKET_DATA_API | Market data provider |
| INTERNAL | IIOS internal protocol |

## Registering a Protocol

```python
from iios.integration.engine import ProtocolDescriptor, ProtocolType, ConnectorType

descriptor = ProtocolDescriptor.create(
    protocol_type             = ProtocolType.HTTPS,
    name                      = "HTTPS Protocol",
    supported_connector_types = [ConnectorType.REST_API, ConnectorType.GRAPHQL],
)
manager.register_protocol(descriptor)
```

## ProtocolDescriptor Fields

| Field | Type | Description |
|---|---|---|
| protocol_id | str | Auto-generated unique ID |
| protocol_type | ProtocolType | Protocol category |
| name | str | Human-readable name |
| version | str | Semantic version |
| supported_connector_types | tuple[ConnectorType] | Compatible connectors (empty = all) |
| metadata | dict | Custom metadata |
| registered_at | str | ISO timestamp |

## Protocol–Connector Compatibility

When `supported_connector_types` is empty, the protocol is compatible with all connectors.
Otherwise, only the listed connector types are compatible.

```python
registry.supports_connector(ProtocolType.HTTPS, ConnectorType.REST_API)  # True
```
