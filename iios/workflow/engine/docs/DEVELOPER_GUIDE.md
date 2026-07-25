# Developer Guide — Workflow Engine

## Extending the Engine

### Adding a Pipeline Stage Handler

```python
from iios.workflow.engine import WorkflowEngine, WorkflowPipelineStage

engine = WorkflowEngine()
engine.initialize()

# Register a custom dispatch handler
engine._dispatcher._pipeline.register_handler(
    WorkflowPipelineStage.DISPATCH_WORKFLOW,
    lambda req, ctx, exec: {"custom": True},
)
```

### Registering Governance / Orchestration Hooks

```python
def my_governance_check(request, context):
    # Validate against policy rules
    return {"approved": True}

engine.register_governance_hook(my_governance_check)
```

The hook is called after validation and before the pipeline.  Return value
is currently ignored (M3 delegation stub).

### Listening for Events

```python
bus = engine.event_bus()

def on_complete(event):
    print(f"Workflow {event.session_id} completed")

bus.add_listener(WorkflowEngineEventType.WORKFLOW_COMPLETED, on_complete)
```

### Custom Statistics Reset

```python
engine._stats.reset()   # reset all counters
```

### Injecting Dependencies (for testing)

```python
from iios.workflow.engine import (
    WorkflowEngine, WorkflowScheduler, WorkflowEngineEventBus
)

custom_bus = WorkflowEngineEventBus()
engine = WorkflowEngine(engine_id="test-engine", event_bus=custom_bus)
```

## Conventions

- All engine classes are **thread-safe** — every public method acquires `self._lock`.
- IDs are prefixed: `wenreq-`, `wenresp-`, `wenctx-`, `wevt-`, `wqi-`, `wsj-`, `wpipe-`.
- Frozen dataclasses for all immutable data objects.
- `execute()` **never raises** — failure is returned as a `WorkflowEngineResponse`.
- Statistics use `record_*()` methods — never access `_*` counters directly.

## Adding a New Validation Check

1. Add an entry to `WorkflowEngineValidationCheck` in `constants.py`.
2. Add a `_check_<name>()` method in `WorkflowEngineValidator`.
3. Call it inside `validate()`.
4. Add a test in `test_workflow_engine_m2.py`.

## Future Modules

| Hook                     | Module     | When                          |
|--------------------------|------------|-------------------------------|
| `_governance_hook`       | M3         | After validation, before queue |
| `_orchestration_hook`    | M4         | After queue, before pipeline  |

Both hooks are passthrough no-ops in M2.
