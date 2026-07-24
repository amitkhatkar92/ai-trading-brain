# Integration Services Guide

## Engine Lifecycle

```python
engine = IntegrationServicesEngine()
engine.start()    # initialises sub-systems, emits CONNECTOR_LOADED event
# ... execute requests ...
engine.stop()
```

## Request Routing

The engine routes by `service_type`:

| service_type | Sub-engine |
|---|---|
| `REST_API`, `GRAPHQL`, `GRPC`, `WEBSOCKET`, `HTTP` | ApiGatewayEngine |
| `KAFKA`, `RABBITMQ`, `REDIS_STREAM`, `MESSAGE_QUEUE` | MessageBusEngine |
| `WEBHOOK` | WebhookEngine |
| `DATABASE` | DatabaseConnectorEngine |
| `FILE_TRANSFER` | FileTransferEngine |
| `EMAIL`, `SMS`, `PUSH_NOTIFICATION` | NotificationEngine |

## Request Execution Workflow

1. **Validate** — 6 structural checks (`IntegrationServicesValidator`)
2. **Authenticate** — if `auth_scheme != NONE`
3. **Rate limit** — token-bucket per service_type
4. **Execute with retry** — `RetryEngine` with configured strategy
5. **Record statistics** — 10 metrics
6. **Record history** — bounded deque
7. **Emit event** — `INTEGRATION_SERVICE_COMPLETED`

## Batch Execution

```python
requests = [req1, req2, req3]
responses = engine.execute_batch(requests)
```

## Statistics

```python
snap = engine.statistics.snapshot()
print(snap.requests_processed, snap.availability, snap.average_latency_ms)
```

## Event Subscription

```python
from iios.integration.services import ServiceEventType

def on_message(event):
    print(f"Message published: {event.payload}")

engine.event_bus.subscribe(ServiceEventType.MESSAGE_PUBLISHED, on_message)
```
