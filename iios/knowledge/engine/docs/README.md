# Knowledge Engine — C14 M2

The `iios.knowledge.engine` package coordinates enterprise knowledge workflows.

## Quick Start

```python
from iios.knowledge.engine import KnowledgeEngine, KnowledgeRequest, KnowledgeWorkflowType

engine = KnowledgeEngine()
engine.start()

request = KnowledgeRequest.create(
    knowledge_id = "run-001",
    subsystem_id = "execution_intelligence",
    workflow_type = KnowledgeWorkflowType.KNOWLEDGE_CAPTURE,
    inputs = {"execution_snapshot": {"status": "healthy"}},
)
response = engine.submit(request)
print(response.status)   # ResponseStatus.SUCCESS

engine.stop()
```

## Architecture

```
KnowledgeEngine  (LifecycleAwareMixin — primary public interface)
    │
    ├── KnowledgeWorkflowManager  — 10-phase pipeline orchestrator (internal)
    │       │
    │       ├── KnowledgeSessionManager  — wraps M1 KnowledgeLifecycle
    │       ├── KnowledgeEngineValidator — 6-check validation
    │       ├── KnowledgeDispatcher      — delegates to M3 (Governance) + M4 (Intelligence)
    │       ├── KnowledgeEngineFactory   — constructs value objects
    │       ├── KnowledgeEngineStatistics
    │       ├── KnowledgeEngineHistory
    │       └── KnowledgeEngineRegistry
    │
    ├── KnowledgeScheduler   — priority queue (5 modes)
    └── KnowledgeEngineEventBus — synchronous event dispatch
```

## Engine States

| State | Description |
|---|---|
| `IDLE` | Ready, no active cycle |
| `INITIALIZING` | Session initializing |
| `COLLECTING` | Collecting enterprise artifacts |
| `VALIDATING` | Validating artifacts |
| `CLASSIFYING` | Classifying knowledge type/scope |
| `DISPATCHING` | Dispatching to M3/M4 frameworks |
| `PROCESSING` | Processing dispatch results |
| `PUBLISHING` | Publishing knowledge snapshot |
| `COMPLETED` | Cycle complete |
| `FAILED` | Cycle failed |
| `STOPPED` | Engine stopped (terminal) |

## Package Contents

| Module | Responsibility |
|---|---|
| `constants.py` | Enums, state machine, defaults |
| `exceptions.py` | Typed error hierarchy (KNE prefix) |
| `knowledge_context.py` | Immutable engine context |
| `knowledge_request.py` | Immutable workflow request |
| `knowledge_response.py` | Response + snapshot value objects |
| `knowledge_pipeline.py` | Pipeline + stage tracking |
| `knowledge_scheduler.py` | Priority queue scheduler |
| `knowledge_dispatcher.py` | M3/M4 framework delegation |
| `knowledge_session_manager.py` | M1 lifecycle adapter |
| `knowledge_registry.py` | Pipeline registry |
| `knowledge_validation.py` | 6-check validator |
| `knowledge_health.py` | Health reporting |
| `knowledge_status.py` | Status reporting |
| `knowledge_statistics.py` | 7-counter statistics |
| `knowledge_history.py` | Bounded pipeline history |
| `knowledge_events.py` | 9 domain events + event bus |
| `knowledge_factory.py` | Value object factory |
| `knowledge_manager.py` | Workflow orchestrator (internal) |
| `knowledge_engine.py` | Primary public façade |
| `__init__.py` | Public API surface |

## Documentation

- [KNOWLEDGE_ENGINE_GUIDE.md](KNOWLEDGE_ENGINE_GUIDE.md)
- [KNOWLEDGE_PIPELINE_GUIDE.md](KNOWLEDGE_PIPELINE_GUIDE.md)
- [SCHEDULER_GUIDE.md](SCHEDULER_GUIDE.md)
- [PUBLIC_API_GUIDE.md](PUBLIC_API_GUIDE.md)
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
