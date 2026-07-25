# Execution Engine Guide

## Execution Flow

```
execute(request)
  │
  ├─ get_definition(definition_id)   ← registry lookup
  ├─ validate(definition)            ← structural check
  ├─ resource_manager.acquire()      ← concurrency slot
  ├─ executor.execute(...)           ← WorkflowExecutor
  │    ├─ create runtime
  │    ├─ put in state_store
  │    ├─ emit WORKFLOW_EXECUTION_STARTED
  │    ├─ dependency_engine.get_execution_waves()
  │    └─ for each wave:
  │         ├─ filter conditions
  │         ├─ execute wave (parallel or sequential)
  │         ├─ emit STEP events
  │         ├─ checkpoint (if enabled)
  │         └─ break on failure
  ├─ compensate (on failure, if enabled)
  ├─ emit WORKFLOW_COMPLETED / WORKFLOW_EXECUTION_FAILED
  ├─ statistics.record_execution()
  └─ history.record(result)
```

---

## Wave-based execution

The `WorkflowDependencyEngine` uses Kahn's algorithm to compute
_execution waves_ — groups of steps whose dependencies are all satisfied.
Within each wave steps may be run in parallel.

### Wave routing

| WorkflowType | Execution mode |
|---|---|
| PARALLEL, SAGA, PIPELINE | Parallel (thread per step) |
| All others | Sequential (one at a time) |

---

## StepHandler signature

```python
def my_handler(
    step:    WorkflowStep,
    inputs:  Dict[str, Any],    # resolved from input_mapping
    context: Dict[str, Any],    # full workflow context (read-only)
) -> Dict[str, Any]:            # outputs (applied via output_mapping)
    ...
```

Handlers are registered by name on `WorkflowRegistry` or
`WorkflowOrchestrationEngine`.

---

## Timeout behaviour

`WorkflowTimeoutEngine` runs each step in a daemon thread and joins with
the step's `effective_timeout`.  If the thread is still alive, a
`StepResult.timed_out()` is returned immediately — the background thread
is abandoned (not killed; daemon threads terminate with the process).

---

## Retry backoff

`WorkflowRetryEngine` uses `RetryPolicy.backoff_for(attempt)`:

```
delay = min(base * multiplier^attempt, max_backoff)
```

Step status is set to `RETRYING` before sleeping.
