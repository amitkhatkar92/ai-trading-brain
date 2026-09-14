# Scheduler Guide

## Overview

The `KnowledgeScheduler` supports five collection modes:

| Mode | Description |
|---|---|
| `CONTINUOUS` | Requests submitted and processed immediately |
| `SCHEDULED` | Time-based batches at configured intervals |
| `EVENT_DRIVEN` | Triggered by enterprise events |
| `PRIORITY` | Priority-ordered dequeue |
| `BATCH` | Multiple requests enqueued and processed together |

## Priority Levels

| Priority | Value | Usage |
|---|---|---|
| `CRITICAL` | 0 | Urgent operational events |
| `HIGH` | 1 | Time-sensitive collection |
| `NORMAL` | 2 | Standard knowledge capture |
| `LOW` | 3 | Background collection |
| `BATCH` | 4 | Bulk / offline aggregation |

## Direct Submit (Synchronous)

```python
response = engine.submit(request)   # immediate execution
```

## Scheduled Submit (Queued)

```python
accepted = engine.schedule(request)   # enqueue for later processing
count    = engine.schedule_batch(requests)

# Process next queued request
response = engine.process_next()   # returns None if queue empty
```

## Scheduler Statistics

```python
status = engine.status()
print(status["scheduler_depth"])   # current queue depth
```
