# Workflow Definition Guide

## WorkflowDefinition

A `WorkflowDefinition` is a frozen, immutable description of a workflow.
It holds an ordered collection of `WorkflowStep` objects and declares
the execution shape (sequential, parallel, saga, …).

### Creating a definition

```python
from iios.workflow.orchestration import WorkflowFactory

step_a = WorkflowFactory.create_task_step("step-a", "handler_a")
step_b = WorkflowFactory.create_task_step(
    "step-b", "handler_b",
    dependencies=[step_a.step_id],
)
defn = WorkflowFactory.create_sequential_workflow(
    "my-workflow", [step_a, step_b],
    timeout_seconds=600.0,
    enable_checkpointing=True,
    enable_compensation=True,
)
```

---

## WorkflowStep

| Field | Type | Description |
|-------|------|-------------|
| `step_id` | str | Unique ID (prefix `step-`) |
| `name` | str | Human-readable name |
| `step_type` | StepType | TASK / APPROVAL / DELAY / … |
| `handler` | str | Registered handler name |
| `dependencies` | tuple[str] | step_ids that must complete first |
| `retry_policy` | RetryPolicy | Backoff configuration |
| `timeout_seconds` | float | 0 = no timeout |
| `compensation_step_id` | str\|None | Compensation step to run on failure |
| `condition` | str\|None | Registered condition handler name |
| `input_mapping` | dict | context_key → step_input_key |
| `output_mapping` | dict | step_output_key → context_key |

---

## RetryPolicy

```python
from iios.workflow.orchestration import RetryPolicy

policy = RetryPolicy(
    max_retries        = 3,
    backoff_seconds    = 1.0,
    backoff_multiplier = 2.0,
    max_backoff_seconds = 60.0,
)

# Backoff for attempt n:  min(base * multiplier^n, max)
delay = policy.backoff_for(attempt=2)   # → 4.0s
```

---

## WorkflowType selection guide

| Type | When to use |
|------|-------------|
| SEQUENTIAL | Steps must run one after another |
| PARALLEL | All steps are independent |
| CONDITIONAL | Some steps are skipped based on runtime state |
| SAGA | Compensatable business transaction |
| PIPELINE | Data transformation stages |
| APPROVAL | Human-in-the-loop gating |
| LOOP | Repeated execution (combine with scheduler) |
