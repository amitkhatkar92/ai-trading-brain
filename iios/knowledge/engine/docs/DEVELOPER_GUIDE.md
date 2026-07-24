# Knowledge Engine — Developer Guide

## Module Dependency Map

```
knowledge_engine.py            ← primary façade
    │
    ├── knowledge_manager.py   ← workflow orchestrator (NEVER RAISES)
    │       ├── knowledge_session_manager.py ← M1 adapter
    │       ├── knowledge_dispatcher.py      ← M3/M4 delegation
    │       ├── knowledge_validation.py      ← 6-check validator
    │       ├── knowledge_factory.py         ← value object factory
    │       ├── knowledge_statistics.py
    │       ├── knowledge_history.py
    │       └── knowledge_registry.py
    │
    ├── knowledge_scheduler.py  ← priority queue
    └── knowledge_events.py     ← event bus
```

## Immutability Contract

| Object | Mutable? |
|---|---|
| `KnowledgeEngineContext` | ❌ frozen dataclass |
| `KnowledgeRequest` | ❌ frozen dataclass |
| `KnowledgeResponse` | ❌ frozen dataclass |
| `KnowledgeSnapshot` | ❌ frozen dataclass |
| `PipelineStage` | ❌ frozen dataclass |
| `KnowledgeEngineEvent` | ❌ frozen dataclass |
| `KnowledgePipeline` | ✅ mutable — state advances during workflow |

## Manager Never Raises

`KnowledgeWorkflowManager.run_workflow()` wraps its entire body in a
`try/except Exception`.  All failures are captured as `KnowledgeResponse.failure(...)`.

## Adding a New Workflow Type

1. Add to `KnowledgeWorkflowType` in `constants.py`
2. If a new collect/classify step is needed, update `_collect_artifacts` and `_classify` in `knowledge_manager.py`
3. Add tests for the new workflow type
4. Update documentation

## Logging Convention

```python
# CORRECT — f-strings only
_log.info(f"Knowledge session created: knowledge_id={knowledge_id!r}")

# WRONG — positional args not supported
_log.info("Session: %s", knowledge_id)
```

## Injecting M3 / M4 Delegates

```python
def my_governance(knowledge_id: str, context: dict) -> dict:
    # call M3 Knowledge Governance Policy Framework
    return {"status": "approved", "knowledge_id": knowledge_id}

def my_intelligence(knowledge_id: str, context: dict) -> dict:
    # call M4 Knowledge Intelligence Framework
    return {"status": "processed", "knowledge_id": knowledge_id}

engine = KnowledgeEngine(
    governance_delegate   = my_governance,
    intelligence_delegate = my_intelligence,
)
engine.start()
```

Delegates can also be registered after start:

```python
engine.set_governance_delegate(my_governance)
engine.set_intelligence_delegate(my_intelligence)
```
