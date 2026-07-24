# Knowledge Intelligence Guide

## Overview

`KnowledgeIntelligenceEngine` is the primary façade for the Knowledge Intelligence Framework.

## Lifecycle

```python
engine = KnowledgeIntelligenceEngine.create_default()
engine.start()   # LifecycleAwareMixin — state → "running"
# ... use engine ...
engine.stop()    # state → "stopped"
```

## Processing

```python
from iios.knowledge.intelligence import (
    KnowledgeIntelligenceEngine,
    KnowledgeIntelligenceRequest,
    IntelligenceWorkflowType,
)

request = KnowledgeIntelligenceRequest.create(
    knowledge_id  = "k-001",
    subsystem_id  = "market-intelligence",
    artifacts     = [{"artifact_id": "a1", "signal": "buy", "price": 100.0}],
    workflow_type = IntelligenceWorkflowType.FULL_INTELLIGENCE,
)

response = engine.process(request)
if response.succeeded:
    report = response.report
    print(f"Entities: {report.entities_extracted}")
    print(f"Embeddings: {report.embeddings_generated}")
    print(f"Vectors indexed: {report.vectors_indexed}")
```

## Retrieval

```python
from iios.knowledge.intelligence import RetrievalMode

# Semantic (vector similarity)
result = engine.retrieve("NIFTY buy signal", top_k=10)

# Hybrid (semantic + keyword combined)
result = engine.retrieve("NIFTY risk", mode=RetrievalMode.HYBRID)
```

## Introspection

```python
health    = engine.health()         # dict
status    = engine.status()         # dict with lifecycle + stats
stats     = engine.statistics()     # IntelligenceSnapshot
history   = engine.history(n=20)    # List[KnowledgeIntelligenceResponse]
```

## Event Listeners

```python
def on_event(event):
    print(f"Event: {event.event_type.value}")

engine.add_listener(on_event)
engine.remove_listener(on_event)
```

## M2 Integration (intelligence_delegate)

```python
delegate = engine.intelligence_delegate
result   = delegate("knowledge-id", {"artifacts": [...], "subsystem_id": "sub"})
```
