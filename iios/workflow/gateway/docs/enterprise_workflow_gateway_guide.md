# Enterprise Workflow Gateway Guide

## What is the Enterprise Workflow Gateway?

The Enterprise Workflow Gateway is the **single, stable, versioned API** that
coordinates M1–M5 subsystems into a unified enterprise workflow service.

It is a **coordinator** — not an executor. It:
- Validates requests
- Routes them to the right subsystem sequence
- Dispatches to M2 (engine), which in turn coordinates M1, M3, M4
- Generates M5 snapshots from results
- Returns structured responses
- Maintains history, statistics, and health

It does NOT:
- Execute workflow business logic
- Evaluate governance policies (delegates to M3)
- Manage lifecycle state directly (delegates to M2→M1)
- Execute orchestration steps (delegates to M2→M4)

---

## Gateway Processing Pipeline

```
External Caller
      │
      ▼ WorkflowGatewayRequest
WorkflowGateway.submit()
      │
      ├── 1. Guard (gateway RUNNING?)
      ├── 2. Validate request (WorkflowGatewayValidation)
      ├── 3. Create context (WorkflowGatewayContext)
      ├── 4. Route (WorkflowGatewayRouter)
      ├── 5. Dispatch (WorkflowGatewayDispatcher)
      │         │
      │         ├── M2 WorkflowEngine.execute()
      │         │      ├── M1 WorkflowLifecycle (session)
      │         │      ├── M3 WorkflowPolicyEngine (governance hook)
      │         │      └── M4 WorkflowOrchestrationEngine (orchestration hook)
      │         │
      │         └── M5 WorkflowSnapshotFactory (publish snapshot)
      │
      ├── 6. Record (history + statistics + events)
      ├── 7. Register (WorkflowGatewayRegistry)
      └── 8. Return WorkflowGatewayResponse
```

---

## Gateway States

| State | Description |
|---|---|
| `UNINITIALIZED` | Fresh instance — no components wired |
| `INITIALIZED` | Components created and registered |
| `RUNNING` | Accepting and processing requests |
| `STOPPING` | Draining in-flight requests |
| `STOPPED` | All processing stopped |
| `FAILED` | Unrecoverable error |

---

## Gateway Lifecycle

```python
gateway = WorkflowGateway()

gateway.initialize()   # Wire M1–M5 components
gateway.start()        # Begin accepting requests

# ... process requests ...

gateway.stop()         # Graceful shutdown
gateway.restart()      # stop + re-initialize + start
```

---

## Request Types

| Type | Method | Description |
|---|---|---|
| SUBMIT | `gateway.submit(request)` | Submit workflow for execution |
| QUERY | `gateway.query(workflow_id)` | Query current workflow state |
| CANCEL | `gateway.cancel(workflow_id)` | Cancel an active workflow |
| RETRY | `gateway.retry(workflow_id)` | Retry a previous submission |
| VALIDATE | `gateway.validate(request)` | Validate without submitting |

---

## Response Structure

```python
response = gateway.submit(request)

response.is_success      # True / False
response.is_failure      # True / False
response.is_pending      # True / False
response.is_rejected     # True / False

response.response_id     # "wgwres-..."
response.request_id      # mirrors request
response.workflow_id     # mirrors request
response.session_id      # M1 session ID (if created)
response.snapshot_id     # M5 snapshot ID (if published)
response.error_message   # populated on failure
response.gateway_latency_ms
response.processing_time_ms
```
