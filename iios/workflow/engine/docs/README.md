# Workflow Engine — C16 M2

## Overview

The Workflow Engine (`iios.workflow.engine`) is the central coordinator for enterprise workflow execution. It receives workflow requests, validates them, creates M1 lifecycle sessions, schedules and dispatches them through a configurable pipeline, then publishes results.

## Architecture

```
WorkflowManager (public API)
    └── WorkflowEngine (coordinator)
            ├── WorkflowEngineValidator     — 6-check validation
            ├── WorkflowScheduler           — schedule + queue
            │       └── WorkflowQueue       — bounded priority queue
            ├── WorkflowDispatcher          — run pipeline
            │       └── WorkflowPipeline    — 8-stage pipeline
            ├── WorkflowSessionManager      — M1 lifecycle bridge
            ├── WorkflowEngineEventBus      — event notifications
            ├── WorkflowEngineStatistics    — 8 runtime metrics
            ├── WorkflowEngineHistory       — bounded request/response log
            ├── WorkflowEngineRegistry      — active request index
            └── WorkflowMonitor             — stall detection
```

## Quick Start

```python
from iios.workflow.engine import WorkflowManager, WorkflowEngineFactory
from iios.workflow.lifecycle import WorkflowType
from iios.workflow.engine import WorkflowDispatchMode

factory = WorkflowEngineFactory()
manager = WorkflowManager()
manager.start()

request = factory.create_request(
    workflow_id   = "wf-onboarding-001",
    workflow_type = WorkflowType.SEQUENTIAL,
    dispatch_mode = WorkflowDispatchMode.IMMEDIATE,
)

response = manager.execute(request)
print(response.status, response.is_success)

manager.stop()
```

## Error Codes

| Code    | Class                         | Meaning                            |
|---------|-------------------------------|-------------------------------------|
| WEN-000 | WorkflowEngineError           | Base engine error                   |
| WEN-001 | WorkflowEngineNotReadyError   | Engine stopped or not started       |
| WEN-002 | WorkflowRequestValidationError| Request failed validation checks    |
| WEN-003 | WorkflowSessionError          | M1 lifecycle session failure        |
| WEN-004 | WorkflowQueueCapacityError    | Queue is at max capacity            |
| WEN-005 | WorkflowDispatchError         | Pipeline dispatch failure           |
| WEN-006 | WorkflowSchedulerError        | Scheduler failure                   |
| WEN-007 | WorkflowPipelineError         | Pipeline stage execution error      |
| WEN-008 | WorkflowMonitorError          | Monitor failure                     |
| WEN-009 | WorkflowGovernanceError       | M3 governance delegation failure    |
| WEN-010 | WorkflowOrchestrationError    | M4 orchestration delegation failure |

## Module Files

| File                        | Class(es)                                     |
|-----------------------------|-----------------------------------------------|
| `constants.py`              | Enums, actor names, default values            |
| `exceptions.py`             | WEN-000 through WEN-010                       |
| `workflow_request.py`       | `WorkflowEngineRequest`                       |
| `workflow_response.py`      | `WorkflowEngineResponse`                      |
| `workflow_context.py`       | `WorkflowEngineContext`                       |
| `workflow_events.py`        | `WorkflowEngineEvent`, `WorkflowEngineEventBus` |
| `workflow_priority.py`      | `PriorityWorkflowItem`, `priority_label`      |
| `workflow_queue.py`         | `WorkflowQueue`                               |
| `workflow_scheduler.py`     | `WorkflowScheduler`, `ScheduledWorkflowJob`   |
| `workflow_pipeline.py`      | `WorkflowPipeline`, `PipelineExecution`       |
| `workflow_dispatcher.py`    | `WorkflowDispatcher`                          |
| `workflow_session_manager.py` | `WorkflowSessionManager`                   |
| `workflow_registry.py`      | `WorkflowEngineRegistry`                      |
| `workflow_validation.py`    | `WorkflowEngineValidator`                     |
| `workflow_health.py`        | `WorkflowEngineHealth`, `WorkflowEngineHealthReport` |
| `workflow_status.py`        | `WorkflowEngineStatusTracker`, `WorkflowEngineStatus` |
| `workflow_statistics.py`    | `WorkflowEngineStatistics`, `WorkflowEngineStatisticsReport` |
| `workflow_history.py`       | `WorkflowEngineHistory`                       |
| `workflow_monitor.py`       | `WorkflowMonitor`, `ActiveWorkflowRecord`     |
| `workflow_factory.py`       | `WorkflowEngineFactory`                       |
| `workflow_engine.py`        | `WorkflowEngine`                              |
| `workflow_manager.py`       | `WorkflowManager`                             |

## See Also

- [WORKFLOW_ENGINE_GUIDE.md](WORKFLOW_ENGINE_GUIDE.md) — engine internals
- [SCHEDULER_GUIDE.md](SCHEDULER_GUIDE.md) — scheduling
- [QUEUE_GUIDE.md](QUEUE_GUIDE.md) — priority queue
- [PIPELINE_GUIDE.md](PIPELINE_GUIDE.md) — pipeline stages
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — extending the engine
