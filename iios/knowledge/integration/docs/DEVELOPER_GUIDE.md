# Developer Guide — C14 M6

## Import conventions

Always import from `iios.knowledge.integration`:

```python
# ✅ Correct
from iios.knowledge.integration import (
    KnowledgeIntegrationEngine,
    KnowledgeIntegrationRequest,
    KnowledgeIntegrationResponse,
)

# ❌ Avoid importing sub-modules directly
from iios.knowledge.integration.knowledge_integration_engine import KnowledgeIntegrationEngine
```

## Engine state

`KnowledgeIntegrationEngine` must be in `RUNNING` state before calling
`submit()`, `query()`, `search()`, or `retrieve()`.

`initialize()` and `start()` are separate to allow pre-flight health checks:

```python
engine = KnowledgeIntegrationEngine()
engine.initialize()

health = engine.health()
if health.overall_healthy:
    engine.start()
else:
    print("Some components degraded — starting anyway")
    engine.start()
```

## Custom component injection

Inject pre-built components rather than relying on auto-discovery:

```python
from iios.knowledge.integration import (
    KnowledgeIntegrationEngine,
    KnowledgeComponentRegistry,
)
from iios.knowledge.intelligence import KnowledgeIntelligenceEngine
from iios.knowledge.snapshot import KnowledgeSnapshotFactory

registry = KnowledgeComponentRegistry()
registry.register_intelligence(my_intelligence_engine)
registry.register_snapshot(KnowledgeSnapshotFactory())

engine = KnowledgeIntegrationEngine(registry=registry)
engine.initialize()
engine.start()
```

## Testing patterns

```python
# Unit test: inject mock registry
from unittest.mock import MagicMock
from iios.knowledge.integration import (
    KnowledgeIntegrationEngine,
    KnowledgeComponentRegistry,
    KnowledgeSnapshotFactory,
)

registry = KnowledgeComponentRegistry()
registry.register_snapshot(KnowledgeSnapshotFactory())

engine = KnowledgeIntegrationEngine(registry=registry)
engine.initialize()
engine.start()

request = KnowledgeIntegrationRequest.create("s", "w", "e")
response = engine.submit(request)
assert response.succeeded
```

## Error handling

```python
from iios.knowledge.integration import (
    KnowledgeIntegrationError,
    IntegrationStateError,
    IntegrationValidationError,
)

try:
    response = engine.submit(request)
    if not response.succeeded:
        print(f"Integration failed: {response.error_message}")
except IntegrationStateError as exc:
    print(f"Engine not running: {exc.current_state}")
except KnowledgeIntegrationError as exc:
    print(f"Integration error [{exc.error_code}]: {exc}")
```

## Custom event listeners

```python
from iios.knowledge.integration import IntegrationEvent, IntegrationEventType

def on_snapshot_published(evt: IntegrationEvent) -> None:
    if evt.event_type == IntegrationEventType.SNAPSHOT_PUBLISHED:
        snapshot_id = evt.payload.get("snapshot_id", "")
        # Downstream consumers receive the snapshot ID here

engine.add_listener(on_snapshot_published)
```

## M6 constraints

M6 intentionally does NOT:
- Call M1 lifecycle state transitions (complete/fail/archive) — it only creates sessions
- Evaluate M3 governance policies with modification authority
- Perform M4 embedding generation outside the standard pipeline
- Manage M5 snapshot TTL or expiry

These are responsibilities of M1–M5 themselves.
M6 ONLY coordinates the sequence.
