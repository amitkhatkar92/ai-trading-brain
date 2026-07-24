# Scheduler Guide — C15 M2

## Overview

The `IntegrationScheduler` manages a priority queue of integration requests
for deferred or recurring execution.

## Supported Modes

| Mode | Description |
|---|---|
| IMMEDIATE | Process as soon as polled |
| CONTINUOUS | Repeating integration (re-submitted after completion) |
| SCHEDULED | Time-based execution (ISO timestamp in `run_at`) |
| EVENT_DRIVEN | Triggered by an external event |
| PRIORITY | Prioritized above normal requests |
| BATCH | Grouped with other batch requests |
| RETRY | Re-queued after a failure |

## Priority

Priority is an integer 0–10.  Lower values = higher urgency.  Default = 5.

## Submitting a Scheduled Request

```python
job_id = engine.schedule(
    request  = my_request,
    mode     = "priority",
    priority = 1,           # high urgency
)
```

## Processing Scheduled Requests

The engine provides `process_scheduled()` which dequeues and dispatches
the highest-priority pending job:

```python
response = engine.process_scheduled()  # returns None if queue is empty
```

## Cancelling a Job

```python
engine.scheduler.cancel(job_id)  # job is skipped on next dequeue
```

## Queue Status

```python
n   = engine.scheduler.queue_size()    # pending count
top = engine.scheduler.peek()          # inspect highest priority without removing
```

## ScheduledJob Fields

| Field | Type | Description |
|---|---|---|
| job_id | str | Auto-generated job ID |
| request | IntegrationRequest | The request to dispatch |
| mode | SchedulerMode | Scheduling mode |
| priority | int | 0 (highest) – 10 (lowest) |
| scheduled_at | str | When the job was submitted |
| run_at | str or None | Target ISO timestamp (SCHEDULED mode) |
