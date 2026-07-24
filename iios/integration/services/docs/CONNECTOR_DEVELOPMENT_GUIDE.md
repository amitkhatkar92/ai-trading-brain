# Connector Development Guide

## Creating a Custom Connector

Register a `ConnectorDescriptor` in the `ConnectorRegistry`:

```python
from iios.integration.services import (
    ConnectorDescriptor, ConnectorRegistry, ServiceType, TransportType
)

registry = ConnectorRegistry()
descriptor = ConnectorDescriptor(
    connector_id   = "my-rest-connector",
    service_type   = ServiceType.REST_API,
    transport_type = TransportType.HTTP,
    name           = "My REST Connector",
    version        = "1.0.0",
    metadata       = {},
)
registry.register(descriptor)
```

## Injecting into the Engine

```python
from iios.integration.services import (
    ConnectorEngine, ConnectorManager, IntegrationServicesEngine
)

manager = ConnectorManager(registry=registry)
connector_engine = ConnectorEngine(connector_manager=manager)
engine = IntegrationServicesEngine(connector_engine=connector_engine)
```

## ConnectorRequest Fields

| Field | Type | Description |
|---|---|---|
| `request_id` | str | Auto-generated unique ID |
| `approved_request_id` | str | Parent governance request ID |
| `service_type` | ServiceType | Target service type |
| `transport_type` | TransportType | Transport protocol |
| `auth_scheme` | AuthScheme | Authentication method |
| `endpoint` | str | Target URL/address |
| `payload` | Dict | Request body |
| `timeout_ms` | int | Execution timeout |
| `retry_max_attempts` | int | Retry count |
