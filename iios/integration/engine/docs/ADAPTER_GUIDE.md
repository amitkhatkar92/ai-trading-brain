# Adapter Guide — C15 M2

## Overview

An **adapter** bridges a connector to the engine's data model.  Adapters transform
requests and responses between the engine's protocol-agnostic format and the
connector's expected format.  Adapter implementations live in M4.

## 17 Adapter Types

| Type | Serves Connector |
|---|---|
| REST | REST_API |
| GRAPHQL | GRAPHQL |
| WEBSOCKET | WEBSOCKET |
| GRPC | GRPC |
| KAFKA | KAFKA |
| RABBITMQ | RABBITMQ |
| REDIS | REDIS_STREAM |
| DATABASE | DATABASE |
| FILE | FILE_TRANSFER |
| CLOUD | CLOUD_SERVICE |
| BROKER | BROKER_API |
| MARKET_DATA | MARKET_DATA |
| NOTIFICATION | NOTIFICATION |
| IDENTITY | IDENTITY_PROVIDER |
| ERP | ERP |
| CRM | CRM |
| GENERIC | ENTERPRISE + any |

## Registering an Adapter

```python
from iios.integration.engine import AdapterDescriptor, AdapterType, ConnectorType

descriptor = AdapterDescriptor.create(
    adapter_type   = AdapterType.REST,
    connector_type = ConnectorType.REST_API,
    name           = "REST Adapter v2",
    version        = "2.0.0",
    capabilities   = ["json", "xml"],
)
manager.register_adapter(descriptor)
```

## AdapterDescriptor Fields

| Field | Type | Description |
|---|---|---|
| adapter_id | str | Auto-generated unique ID |
| adapter_type | AdapterType | Adapter category |
| connector_type | ConnectorType | Which connector this adapter serves |
| name | str | Human-readable name |
| version | str | Semantic version |
| capabilities | tuple[str] | Supported formats/features |
| metadata | dict | Custom metadata |
| registered_at | str | ISO timestamp |

## Multi-Adapter Support

Multiple adapters can be registered for the same connector type.
The engine uses the first registered adapter for lookup.
