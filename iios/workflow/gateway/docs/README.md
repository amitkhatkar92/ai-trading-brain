# Enterprise Workflow Gateway — README

**Module:** `iios.workflow.gateway`
**Layer:** C16 M6 — Enterprise Workflow & Process Orchestration
**Build:** c16-m6

---

## Purpose

The Enterprise Workflow Gateway is the **ONLY public entry point** for
Enterprise Workflow & Process Orchestration.

External IIOS modules **MUST NOT** directly access:

- M1 — Workflow Lifecycle (`iios.workflow.lifecycle`)
- M2 — Workflow Engine (`iios.workflow.engine`)
- M3 — Workflow Governance Policy Framework (`iios.workflow.policies`)
- M4 — Workflow Orchestration Framework (`iios.workflow.orchestration`)
- M5 — Workflow Snapshot (`iios.workflow.snapshot`)

**All communication MUST occur through `WorkflowGateway`.**

---

## Quick Start

```python
from iios.workflow.gateway import WorkflowGateway, WorkflowGatewayFactory

# Create and start the gateway
gateway = WorkflowGateway()
gateway.initialize()
gateway.start()

# Submit a workflow
request  = WorkflowGatewayFactory.create_submit_request("wf-order-001", "Order Processing")
response = gateway.submit(request)

print(response.is_success)   # True
print(response.snapshot_id)  # wsnap-...

# Other operations
gateway.query("wf-order-001")
gateway.cancel("wf-order-001")
gateway.retry("wf-order-001")

# Observability
health = gateway.health()    # WorkflowHealthSummary
status = gateway.status()    # WorkflowStatus
stats  = gateway.statistics() # WorkflowStatistics
records = gateway.history()   # List[WorkflowGatewayHistoryRecord]

# Stop
gateway.stop()
```

---

## Components Integrated

| Module | Component |
|---|---|
| M1 | `WorkflowLifecycle` — session state transitions |
| M2 | `WorkflowEngine` — central execution coordinator |
| M3 | `WorkflowPolicyEngine` — governance evaluation |
| M4 | `WorkflowOrchestrationEngine` — step execution |
| M5 | `WorkflowSnapshotBuilder` / `WorkflowSnapshotFactory` — snapshot publication |

---

## Thread Safety

All services in `iios.workflow.gateway` are thread-safe.
The `WorkflowGateway` may be shared across threads without external locking.

---

## See Also

- [enterprise_workflow_gateway_guide.md](enterprise_workflow_gateway_guide.md)
- [public_api_guide.md](public_api_guide.md)
- [gateway_architecture_guide.md](gateway_architecture_guide.md)
- [integration_guide.md](integration_guide.md)
- [developer_guide.md](developer_guide.md)
