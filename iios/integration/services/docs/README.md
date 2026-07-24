# Integration Services Framework — Module 4

## Overview

The Integration Services Framework (ISF) is **C15 Phase 1, Module 4** of the
IIOS Enterprise Integration platform. It provides provider-independent connector
abstractions, messaging adapters, resilience primitives, and security components
for enterprise integration workflows.

## Package

```
iios/integration/services/
```

## Architecture

```
IntegrationServicesEngine          ← Central coordinator
│
├── Validation       IntegrationServicesValidator  (6 checks)
├── Authentication   AuthenticationEngine          (8 schemes)
├── Rate Limiting    RateLimitEngine               (token bucket)
├── Retry            RetryEngine                   (5 strategies)
│
├── Routing
│   ├── ApiGatewayEngine     → REST / GraphQL / gRPC / WS / HTTP
│   ├── MessageBusEngine     → Kafka / RabbitMQ / Redis Streams
│   ├── WebhookEngine        → HTTP webhook dispatch
│   ├── DatabaseConnectorEngine → DB query/execute
│   ├── FileTransferEngine   → upload/download
│   └── NotificationEngine   → email / SMS / push
│
├── Observability
│   ├── IntegrationServicesStatistics  (10 metrics)
│   ├── IntegrationServicesHistory     (bounded log)
│   └── IntegrationServicesEventBus    (10 event types)
│
└── Security
    ├── CredentialProvider
    ├── SecretManager
    └── CertificateManager
```

## Quick Start

```python
from iios.integration.services import (
    IntegrationServicesEngine,
    IntegrationServicesFactory,
)

engine = IntegrationServicesEngine()
engine.start()

# REST call
req = IntegrationServicesFactory.create_rest_request(
    endpoint="https://api.example.com/orders",
    payload={"order_id": "12345"},
)
response = engine.execute(req)
assert response.status.value == "success"

# Kafka publish
kafka_req = IntegrationServicesFactory.create_kafka_request(
    topic="trade-signals",
    payload={"symbol": "NIFTY", "signal": "BUY"},
)
response = engine.execute(kafka_req)

engine.stop()
```

## Files (48 source files)

| Group | Files |
|-------|-------|
| Core | `constants.py`, `exceptions.py` |
| Data | `connector_request.py`, `connector_response.py`, `connector_context.py` |
| Registry | `connector_registry.py`, `adapter_registry.py`, `protocol_registry.py` |
| Management | `connector_manager.py`, `connector_factory.py`, `adapter_factory.py` |
| Engines | `connector_engine.py`, `adapter_engine.py`, `protocol_engine.py`, `transport_engine.py` |
| Clients | `http_client.py`, `rest_client.py`, `graphql_client.py`, `grpc_client.py`, `websocket_client.py` |
| Gateway | `api_gateway_engine.py` |
| Messaging | `kafka_adapter.py`, `rabbitmq_adapter.py`, `redis_stream_adapter.py`, `message_bus_engine.py` |
| Streaming | `event_bus_engine.py`, `stream_engine.py`, `queue_engine.py` |
| Specialized | `webhook_engine.py`, `database_connector_engine.py`, `file_transfer_engine.py`, `notification_engine.py` |
| Security | `authentication_engine.py`, `authorization_engine.py`, `credential_provider.py`, `secret_manager.py`, `certificate_manager.py` |
| Resilience | `retry_engine.py`, `failover_engine.py`, `rate_limit_engine.py`, `timeout_engine.py`, `connection_pool.py` |
| Observability | `integration_services_validator.py`, `integration_services_statistics.py`, `integration_services_history.py`, `integration_services_events.py` |
| Factory / Engine | `integration_services_factory.py`, `integration_services_engine.py`, `__init__.py` |

## Key Principles

1. **Provider-independent**: All vendor SDKs (requests, kafka-python, pika, redis, etc.) are excluded from the framework. Adapters define contracts; real implementations are injected at deployment.
2. **Thread-safe**: All engines use `threading.Lock()` on mutable state.
3. **Immutable data**: `ConnectorRequest`, `ConnectorResponse`, `ConnectorContext` are all `@dataclass(frozen=True)`.
4. **No circular imports**: `iios.integration.services` does NOT import from `iios.integration.policies` or `iios.integration.engine`.
