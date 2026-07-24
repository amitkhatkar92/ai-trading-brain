# Connector Guide — C15 M2

## Overview

A **connector** describes an integration endpoint type.  The engine uses
connector metadata to route requests.  Connector implementations live in M4.

## 18 Supported Connector Types

| Type | Description |
|---|---|
| REST_API | HTTP REST endpoints |
| GRAPHQL | GraphQL APIs |
| WEBSOCKET | WebSocket connections |
| GRPC | gRPC services |
| KAFKA | Apache Kafka topics |
| RABBITMQ | RabbitMQ queues |
| REDIS_STREAM | Redis Streams |
| MESSAGE_QUEUE | Generic message queues |
| DATABASE | Database connectors |
| FILE_TRANSFER | File transfer protocols |
| CLOUD_SERVICE | Cloud provider APIs |
| BROKER_API | Trading broker APIs |
| MARKET_DATA | Market data providers |
| NOTIFICATION | Notification services |
| IDENTITY_PROVIDER | Identity/auth providers |
| ERP | Enterprise Resource Planning |
| CRM | Customer Relationship Management |
| ENTERPRISE | Generic future enterprise |

## Registering a Connector

```python
from iios.integration.engine import ConnectorDescriptor, ConnectorType

descriptor = ConnectorDescriptor.create(
    connector_type = ConnectorType.REST_API,
    name           = "My REST Connector",
    version        = "2.0.0",
    capabilities   = ["GET", "POST", "PUT"],
    metadata       = {"base_url": "https://api.example.com"},
)
manager.register_connector(descriptor)
```

## Looking Up a Connector

```python
conn = engine.registry.get_connector(ConnectorType.REST_API)
# Returns ConnectorDescriptor or None
```

## ConnectorDescriptor Fields

| Field | Type | Description |
|---|---|---|
| connector_id | str | Auto-generated unique ID |
| connector_type | ConnectorType | Integration type |
| name | str | Human-readable name |
| version | str | Semantic version |
| capabilities | tuple[str] | Supported operations |
| metadata | dict | Custom metadata |
| registered_at | str | ISO timestamp |
