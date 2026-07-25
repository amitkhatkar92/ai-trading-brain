# Scheduler Guide

## Overview

`WorkflowScheduler` wraps `WorkflowQueue` with schedule-aware semantics.
It creates `ScheduledWorkflowJob` records, assigns a `run_at` timestamp,
and provides a FIFO-by-priority dequeue interface.

## Job Creation

```python
scheduler = WorkflowScheduler()
job = scheduler.schedule(request)         # IMMEDIATE mode — run_at = now
print(job.job_id, job.run_at)
```

Dispatch modes:
- `IMMEDIATE` — `run_at = now`
- `SCHEDULED` — same (future: engine should pass an explicit `run_at`)
- Others — enqueued at normal priority

## Dequeue

```python
job = scheduler.next()    # Returns Optional[ScheduledWorkflowJob]
```

Returns the highest-priority, next-due job or `None` if empty.

## Cancel

```python
cancelled = scheduler.cancel_job(job.job_id)   # True if cancelled
```

## Introspection

```python
scheduler.queue_size()     # current queue depth
scheduler.job_count()      # alias for queue_size
scheduler.is_empty()       # True if nothing queued
scheduler.list_jobs()      # List[ScheduledWorkflowJob] snapshot
```

## Priority

Jobs inherit the priority from their `WorkflowEngineRequest`.  Lower
numeric value = higher priority:

| Value | Label    |
|-------|----------|
| 0     | CRITICAL |
| 1     | HIGH     |
| 2     | NORMAL   |
| 3     | LOW      |
