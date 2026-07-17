# Workflow Guide — 10-Step Request Processing

`GatewayManager.process_request(context)` implements a deterministic
10-step workflow for every request.

## Steps

```
Step 1  — Record received           stats.record_received()
Step 2  — Validate context          EngineGatewayValidator.validate_context()
Step 3  — Validate capacity         EngineGatewayValidator.validate_queue_capacity()
Step 4  — Register request          create session + EngineGatewayRequest
                                    register in GatewayEngineRegistry
                                    drive M1 lifecycle: create → receive
                                      → start_validation → mark_ready
Step 5  — Queue                     enqueue_fifo() or enqueue_priority()
                                    M1: lc.queue()
                                    fire REQUEST_QUEUED event
Step 6  — Set dispatching state     mark_dispatched()
                                    M1: lc.start_routing()
                                    fire REQUEST_DISPATCHED event
Step 7  — Dispatch                  GatewayDispatcher.dispatch(request)
Step 8a — Success path              set_dispatch_result(ACCEPTED)
                                    mark_completed()
                                    M1: lc.dispatch() → lc.complete() → lc.archive()
                                    stats.record_completed()
                                    fire DISPATCH_COMPLETED event
Step 8b — Failure path              set_error(code, message)
                                    M1: lc.dispatch() → lc.fail() → lc.archive()
                                    stats.record_failed()
                                    fire DISPATCH_FAILED event
Step 9  — Append history            append_operation + append_response
Step 10 — Return GatewayResponse
```

## M1 Lifecycle transitions (per request)

The EGE drives the M1 `GatewayLifecycle` for every request:

```
create → receive → start_validation → mark_ready → queue
       → start_routing → dispatch → complete → archive
                                   → fail    → archive
```

## GatewayResponse fields

| Field | Description |
|---|---|
| `response_id` | Unique response UUID |
| `request_id` | Matches the submitted context |
| `lifecycle_request_id` | M1 gateway_id for cross-layer tracing |
| `session_id` | Session that owned this request |
| `status` | `RequestStatus` string |
| `outcome` | `DispatchOutcome` string or None |
| `is_accepted` | True when outcome == ACCEPTED |
| `is_failed` | True when status == FAILED |
| `elapsed_ms` | Wall time from received to response |

## Cancel

```python
ok = engine.cancel_request("REQ-001", reason="user cancelled")
# Returns False if request is already terminal
```

## Retry

```python
# request must be in FAILED state and can_retry == True
resp = engine.retry_request("REQ-001")
```

Retry re-submits via `process_request` after incrementing `retry_count`.
`max_retries` defaults to `DEFAULT_MAX_RETRIES = 3`.
