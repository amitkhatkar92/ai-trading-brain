# Pipeline Guide

## Overview

`WorkflowPipeline` executes 8 ordered stages for every dispatched request.
Each stage is a callable registered by name.  Missing handlers are no-ops.

## 8 Pipeline Stages (in order)

| Stage                     | Description                                |
|---------------------------|--------------------------------------------|
| INITIALIZE_SESSION        | Session initialisation hook                |
| VALIDATE_REQUEST          | Request validation hook                    |
| APPLY_GOVERNANCE          | M3 governance policy (passthrough in M2)   |
| SCHEDULE_WORKFLOW         | Scheduling hook                            |
| DISPATCH_WORKFLOW         | Core dispatch logic                        |
| COORDINATE_ORCHESTRATION  | M4 orchestration (passthrough in M2)       |
| MONITOR_EXECUTION         | Execution monitoring hook                  |
| PUBLISH_SNAPSHOT          | Snapshot publication hook                  |

## Registering Stage Handlers

```python
pipeline = WorkflowPipeline()

def my_dispatch_handler(request, context, execution):
    # business logic here
    return {"result": "ok"}

pipeline.register_handler(
    WorkflowPipelineStage.DISPATCH_WORKFLOW,
    my_dispatch_handler,
)
```

Handler signature: `(request, context, execution) -> Optional[Any]`

The return value is stored in `execution.stage_results[stage.value]`.

## Execution Result

`WorkflowPipeline.execute()` returns a `PipelineExecution` object:

```python
execution = pipeline.execute(request, context)
execution.success           # True if all stages completed
execution.completed_stages  # list of stage names
execution.failed_stage      # None or failing stage name
execution.stage_results     # Dict[stage_name, result]
execution.error_message     # set if failed
```

## Stopping on Failure

If any stage raises an exception, the pipeline marks the `PipelineExecution`
as failed, records the `failed_stage`, and stops — remaining stages are skipped.
