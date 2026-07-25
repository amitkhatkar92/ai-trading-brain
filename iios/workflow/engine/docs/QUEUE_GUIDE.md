# Queue Guide

## Overview

`WorkflowQueue` is a thread-safe, bounded, priority-ordered queue backed
by a min-heap of `PriorityWorkflowItem` objects.

## Usage

```python
queue = WorkflowQueue(max_size=10_000)
queue.enqueue(item)          # raises WorkflowQueueCapacityError if full
item = queue.dequeue()       # returns Optional[PriorityWorkflowItem]
queue.cancel(item_id)        # soft-cancel; dequeue skips cancelled items
```

## Priority Ordering

Lower numeric priority value = dequeued first:

| Priority | Constant         |
|----------|-----------------|
| 0        | CRITICAL        |
| 1        | HIGH            |
| 2        | NORMAL (default)|
| 3        | LOW             |

Equal-priority items are served FIFO by insertion sequence.

## Capacity

```python
queue = WorkflowQueue(max_size=500)
queue.is_full()     # True when size == max_size
queue.size()        # current item count
queue.max_size      # configured limit
```

When `max_size` is reached, `enqueue()` raises `WorkflowQueueCapacityError`.

## Peek

```python
next_item = queue.peek()  # returns top item without removing it
```

## Clear

```python
queue.clear()  # removes all items, resets heap
```
