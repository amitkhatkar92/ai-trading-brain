# Workflow Orchestration Framework — Module Overview

**Package:** `iios.workflow.orchestration`  
**Version:** C16 M4  
**Error prefix:** `WOF-000 … WOF-015`

---

## What is it?

The Workflow Orchestration Framework provides a pure-Python, thread-safe
engine for defining, executing, monitoring, and recovering multi-step
workflow processes.  It deliberately contains no AI reasoning,
no business-domain logic, and no vendor SDK imports.

---

## Architecture

```
WorkflowOrchestrationEngine  ← top coordinator
  ├─ WorkflowRegistry        ← definition + handler store
  ├─ WorkflowValidator       ← structural validation
  ├─ WorkflowResourceManager ← concurrency slots
  ├─ WorkflowExecutor        ← per-workflow coordinator
  │    ├─ WorkflowDependencyEngine   ← topological wave scheduling
  │    ├─ WorkflowSequentialEngine   ← sequential step execution
  │    ├─ WorkflowParallelEngine     ← parallel step execution
  │    ├─ WorkflowConditionalEngine  ← condition filtering
  │    ├─ WorkflowRetryEngine        ← exponential-backoff retry
  │    ├─ WorkflowTimeoutEngine      ← per-step deadline
  │    ├─ WorkflowCompensationEngine ← LIFO saga compensation
  │    ├─ WorkflowRecoveryEngine     ← checkpoint restoration
  │    └─ WorkflowCheckpointManager  ← per-wave state snapshots
  ├─ WorkflowStatistics      ← execution metrics
  ├─ WorkflowHistory         ← result history (bounded)
  ├─ WorkflowMonitor         ← real-time runtime visibility
  ├─ WorkflowOrchestrationEventBus ← typed event fan-out
  ├─ WorkflowQueueManager    ← priority async queue
  └─ WorkflowScheduler       ← one-shot + recurring timers
```

---

## Quick-start

```python
from iios.workflow.orchestration import (
    WorkflowOrchestrationEngine,
    WorkflowFactory,
)

# 1. Build engine
engine = WorkflowOrchestrationEngine()
engine.initialize()

# 2. Define steps
step1 = WorkflowFactory.create_task_step("fetch_data", handler="fetch")
step2 = WorkflowFactory.create_task_step("process", handler="process",
                                          dependencies=[step1.step_id])

# 3. Build definition
defn = WorkflowFactory.create_sequential_workflow("etl", [step1, step2])

# 4. Register
engine.register_definition(defn)
engine.register_handler("fetch",   lambda step, inputs, ctx: {"data": []})
engine.register_handler("process", lambda step, inputs, ctx: {"done": True})

# 5. Execute
request = WorkflowFactory.create_request("run-1", defn.definition_id)
result  = engine.execute(request)
print(result.status)   # WorkflowStatus.COMPLETED

engine.stop()
```

---

## Error Codes

| Code | Exception |
|------|-----------|
| WOF-000 | WorkflowOrchestrationError (base) |
| WOF-001 | WorkflowDefinitionError |
| WOF-002 | WorkflowValidationError |
| WOF-003 | WorkflowExecutionError |
| WOF-004 | WorkflowStepError |
| WOF-005 | WorkflowDependencyError |
| WOF-006 | WorkflowTimeoutError |
| WOF-007 | WorkflowRetryExhaustedError |
| WOF-008 | WorkflowCompensationError |
| WOF-009 | WorkflowCheckpointError |
| WOF-010 | WorkflowRecoveryError |
| WOF-011 | WorkflowRegistryError |
| WOF-012 | WorkflowResourceError |
| WOF-013 | WorkflowSchedulerError |
| WOF-014 | WorkflowPersistenceError |
| WOF-015 | WorkflowQueueError |
