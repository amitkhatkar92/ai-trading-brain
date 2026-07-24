# State Transition Guide — C16 M1 Workflow Lifecycle

## Complete Transition Table

| From State    | Permitted To States                                          |
|---------------|--------------------------------------------------------------|
| CREATED       | INITIALIZING, CANCELLED                                      |
| INITIALIZING  | VALIDATING, FAILED, CANCELLED                                |
| VALIDATING    | READY, FAILED, CANCELLED                                     |
| READY         | SCHEDULED, QUEUED, RUNNING, CANCELLED                        |
| SCHEDULED     | QUEUED, CANCELLED, FAILED                                    |
| QUEUED        | RUNNING, CANCELLED, FAILED                                   |
| RUNNING       | WAITING, PAUSED, COMPLETED, FAILED, CANCELLED                |
| WAITING       | RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED                |
| PAUSED        | RESUMING, CANCELLED, FAILED                                  |
| RESUMING      | RUNNING, FAILED, CANCELLED                                   |
| COMPLETED     | ARCHIVED                                                     |
| FAILED        | INITIALIZING, ARCHIVED                                       |
| CANCELLED     | ARCHIVED                                                     |
| ARCHIVED      | *(none — terminal)*                                          |

## WorkflowLifecycle Method → Transition Mapping

| Method                | To State     | Event Emitted          |
|-----------------------|--------------|------------------------|
| `create_session()`    | CREATED      | WORKFLOW_CREATED       |
| `initialize()`        | INITIALIZING | WORKFLOW_INITIALIZED   |
| `validate_workflow()` | VALIDATING   | WORKFLOW_VALIDATED     |
| `mark_ready()`        | READY        | WORKFLOW_VALIDATED     |
| `schedule()`          | SCHEDULED    | WORKFLOW_SCHEDULED     |
| `queue()`             | QUEUED       | WORKFLOW_SCHEDULED     |
| `start()`             | RUNNING      | WORKFLOW_STARTED       |
| `wait()`              | WAITING      | WORKFLOW_PAUSED        |
| `resume_from_wait()`  | RUNNING      | WORKFLOW_RESUMED       |
| `pause()`             | PAUSED       | WORKFLOW_PAUSED        |
| `resume()`            | RESUMING     | WORKFLOW_RESUMED       |
| `complete()`          | COMPLETED    | WORKFLOW_COMPLETED     |
| `fail()`              | FAILED       | WORKFLOW_FAILED        |
| `cancel()`            | CANCELLED    | WORKFLOW_CANCELLED     |
| `archive()`           | ARCHIVED     | WORKFLOW_ARCHIVED      |
| `retry()`             | INITIALIZING | WORKFLOW_INITIALIZED   |

## Error Conditions

| Exception                        | Trigger                                          |
|----------------------------------|--------------------------------------------------|
| `WorkflowSessionNotFoundError`   | `get_or_raise()` with unknown session_id         |
| `WorkflowInvalidTransitionError` | `transition_to()` with invalid target state      |
| `WorkflowSessionTerminatedError` | Any mutation on an ARCHIVED session              |
| `WorkflowCapacityError`          | Registry full (`DEFAULT_MAX_SESSIONS = 10_000`)  |
