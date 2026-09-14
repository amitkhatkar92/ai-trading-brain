# Knowledge Pipeline Guide

## Overview

A `KnowledgePipeline` is created for every `KnowledgeRequest` submitted to the
`KnowledgeEngine`.  It tracks the lifecycle of that request through all 10
workflow phases.

## Pipeline States

| Status | Description |
|---|---|
| `PENDING` | Created, not yet running |
| `RUNNING` | Actively being processed |
| `COMPLETED` | Successfully finished |
| `FAILED` | Encountered an error |
| `CANCELLED` | Explicitly cancelled |

## Pipeline Stages

Each pipeline records a `PipelineStage` for each processing phase:

```
validate_context  → INITIALIZING
start_collection  → COLLECTING
validate_artifacts→ VALIDATING
classify          → CLASSIFYING
dispatch          → DISPATCHING
build_snapshot    → PROCESSING
publish           → PUBLISHING
```

## Accessing Pipeline Data

```python
response = engine.submit(request)
# Look up pipeline by knowledge_id
pipeline = engine.query(request.knowledge_id)
if pipeline:
    print(pipeline.status)      # PipelineStatus.COMPLETED
    print(pipeline.elapsed_ms)  # e.g. 12.5
    print(pipeline.stages)      # List[PipelineStage]
```

## History

```python
recent = engine.history(n=10)
for p in recent:
    print(p.knowledge_id, p.status.value, p.elapsed_ms)
```
