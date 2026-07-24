# Developer Guide — C15 M2 Integration Engine

## Connecting M3 Governance

When M3 (Integration Governance Policy Framework) is implemented, inject it into
the engine via subclass override or constructor injection:

```python
class GovernedIntegrationEngine(IntegrationEngine):
    def __init__(self, governance_framework, **kwargs):
        super().__init__(**kwargs)
        self._governance = governance_framework

    def _coordinate_governance(self, request, context):
        self._governance.evaluate(request, context)
```

## Connecting M4 Services

When M4 (Integration Services Framework) is implemented:

```python
class ServicedIntegrationEngine(IntegrationEngine):
    def __init__(self, services_framework, **kwargs):
        super().__init__(**kwargs)
        self._services = services_framework

    def _coordinate_services(self, request, context):
        self._services.execute(request, context)
```

## Adding a Custom Connector Type

Add to `ConnectorType` in `constants.py`:

```python
class ConnectorType(str, Enum):
    ...
    MY_CONNECTOR = "my_connector"
```

Register a descriptor:

```python
engine.register_connector(
    ConnectorDescriptor.create(ConnectorType.MY_CONNECTOR, "My Connector")
)
```

## Listening to Engine Events

```python
from iios.integration.engine import IntegrationEngineEvent

def on_event(event: IntegrationEngineEvent):
    print(f"[{event.event_type.value}] req={event.request_id}")

engine.event_bus.add_listener(on_event)
```

## Querying History

```python
# Most recent responses
responses = engine.history.recent_responses(n=10)

# All responses for a specific session
session_responses = engine.history.by_session(session_id)

# Response for a specific request
resp = engine.history.response_for_request(request_id)
```

## Custom Statistics Tracking

```python
stats = engine.stats
stats.record_message_routed()
stats.record_availability_tick(available=True)

report = stats.report()
print(f"Sessions: {report.integration_sessions}")
print(f"Availability: {report.integration_availability:.2%}")
```

## Testing Patterns

Always construct a fresh engine per test and register required connectors/adapters/protocols:

```python
def make_engine():
    engine = IntegrationEngine()
    engine.initialize()
    engine.register_connector(
        ConnectorDescriptor.create(ConnectorType.REST_API, "REST")
    )
    engine.register_adapter(
        AdapterDescriptor.create(AdapterType.REST, ConnectorType.REST_API, "REST Adapter")
    )
    engine.register_protocol(
        ProtocolDescriptor.create(ProtocolType.HTTPS, "HTTPS")
    )
    return engine
```

## Thread Safety

- `IntegrationEngine.dispatch()` is thread-safe — concurrent dispatches are tracked by `_active_count`
- `IntegrationEngineRegistry`, `ConnectorManager`, `AdapterManager`, `ProtocolRegistry` are all lock-protected
- `IntegrationEngineHistory` appends are lock-protected
- `IntegrationEngineStatistics` increments are lock-protected
- `IntegrationEngineEventBus` listener iteration is lock-protected
