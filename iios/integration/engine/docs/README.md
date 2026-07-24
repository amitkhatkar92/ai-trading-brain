# Integration Engine — C15 M2

The `iios.integration.engine` package implements the **Integration Engine** — the central
coordinator for all enterprise integration workflows across the IIOS platform.

---

## Scope

The Integration Engine:
- Initializes integration sessions
- Manages lifecycle
- Coordinates enterprise integrations
- Registers connectors, adapters, protocols
- Dispatches integration workflows
- Delegates governance to M3 (Integration Governance Policy Framework)
- Delegates execution to M4 (Integration Services Framework)
- Publishes integration snapshots
- Maintains history and statistics

The Integration Engine does **not**:
- Implement governance policy evaluation
- Implement protocol-specific business logic
- Implement connector execution
- Implement business processing
- Implement AI reasoning

---

## Quick Start

```python
from iios.integration.engine import (
    IntegrationManager,
    ConnectorDescriptor, AdapterDescriptor, ProtocolDescriptor,
    ConnectorType, AdapterType, ProtocolType,
)

mgr = IntegrationManager()
mgr.start()

# Register a connector
mgr.register_connector(
    ConnectorDescriptor.create(ConnectorType.REST_API, "REST Connector")
)
mgr.register_adapter(
    AdapterDescriptor.create(AdapterType.REST, ConnectorType.REST_API, "REST Adapter")
)
mgr.register_protocol(
    ProtocolDescriptor.create(ProtocolType.HTTPS, "HTTPS Protocol")
)

# Submit a request
from iios.integration.engine import IntegrationRequest
request  = IntegrationRequest.create(ConnectorType.REST_API,
                                     protocol_type=ProtocolType.HTTPS,
                                     endpoint="https://api.example.com/data")
response = mgr.submit_request(request)

print(response.is_success)     # True
print(mgr.get_health().status) # "healthy"
mgr.stop()
```

---

## Package Contents

| File | Purpose |
|---|---|
| `constants.py` | Enums, states, pipeline stages, system identifiers |
| `exceptions.py` | 10 typed exceptions (IEN-000 … IEN-009) |
| `integration_request.py` | Immutable integration request |
| `integration_response.py` | Immutable integration response |
| `integration_context.py` | Per-request engine context |
| `connector_manager.py` | ConnectorDescriptor + ConnectorManager |
| `adapter_manager.py` | AdapterDescriptor + AdapterManager |
| `protocol_registry.py` | ProtocolDescriptor + ProtocolRegistry |
| `integration_registry.py` | Unified facade over the three registries |
| `integration_session_manager.py` | M1 lifecycle session bridge |
| `integration_pipeline.py` | Ordered stage coordinator |
| `integration_dispatcher.py` | Dispatches requests through pipeline |
| `integration_scheduler.py` | Priority queue for scheduled requests |
| `integration_validation.py` | 7-check request validator |
| `integration_health.py` | Engine health reporting |
| `integration_status.py` | Engine status snapshot |
| `integration_statistics.py` | 9-counter statistics |
| `integration_history.py` | Bounded request/response history |
| `integration_events.py` | 9-event engine event bus |
| `integration_factory.py` | Data object factory |
| `integration_engine.py` | Central coordinator |
| `integration_manager.py` | Top-level public API |

---

## Documentation

- [INTEGRATION_ENGINE_GUIDE.md](INTEGRATION_ENGINE_GUIDE.md) — architecture and design
- [CONNECTOR_GUIDE.md](CONNECTOR_GUIDE.md) — connector registration and management
- [ADAPTER_GUIDE.md](ADAPTER_GUIDE.md) — adapter registration and management
- [PROTOCOL_GUIDE.md](PROTOCOL_GUIDE.md) — protocol registry
- [SCHEDULER_GUIDE.md](SCHEDULER_GUIDE.md) — scheduling modes
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — extension patterns
