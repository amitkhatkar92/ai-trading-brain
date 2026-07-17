# Queue Management Guide

## Queue types

`GatewayOperationQueue` is a facade over four specialised queues:

| Queue | Type | Usage |
|---|---|---|
| FIFO | `FifoQueue` | Normal-priority requests |
| Priority | `EnginePriorityQueue` | High-priority requests (`context.priority > 0`) |
| Retry | `RetryQueue` | Requests awaiting delay-based re-dispatch |
| Cancellation | `CancellationQueue` | Requests pending cancellation |

## Dispatch order

`dequeue_next()` checks priority queue first, then FIFO.  This means
high-priority requests always jump ahead of normal ones regardless of
arrival order.

## Size limits

`DEFAULT_MAX_QUEUE_SIZE = 5_000`.  When the total pending count exceeds
this, `validate_queue_capacity` will emit warnings.

## Priority routing

Set `context.priority > 0` when constructing the `EngineGatewayContext`:

```python
ctx = engine.make_context(
    ...,
    priority=10,   # any value > 0 → high priority
)
```

## Retry queue

Requests that fail dispatch are placed in the retry queue with a delay
(default `DEFAULT_RETRY_DELAY_SECS = 1.0`).  `dequeue_retry_ready()`
returns only items whose delay has elapsed.

## Cancellation queue

`enqueue_cancellation(request_id)` adds the request ID to a set.
`is_cancellation_pending(request_id)` is O(1).  The cancellation is
consumed by `dequeue_cancellation()` and the request is removed from
active queues.

## Statistics

```python
q_stats = engine.snapshot().queue_sizes
# Dict[str, int] — size per queue type
```
