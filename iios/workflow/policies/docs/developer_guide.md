# Developer Guide — Workflow Governance Policy Framework (C16 M3)

## Adding a New Policy Type

1. Add the new value to `PolicyType` in `constants.py`
2. Add a corresponding `PolicyDomain` if needed
3. Register a factory method in `WorkflowPolicyFactory`
4. Add the new type to the `__init__.py` exports

## Extending Condition Operators

1. Add the new operator to `ConditionOperator` in `constants.py`
2. Implement the operator in `PolicyCondition._apply_operator()` in
   `workflow_policy_condition.py`
3. Add a test case in `tests/unit/workflow/test_workflow_policies_m3.py`

---

## ID Prefixes Reference

| Class | Prefix |
|---|---|
| PolicyCondition | `pcond-` |
| PolicyRule | `prule-` |
| WorkflowPolicyContext | `pctx-` |
| WorkflowPolicy | `pol-` |
| WorkflowPolicyRequest | `preq-` |
| WorkflowPolicyResponse | `presp-` |
| WorkflowPolicyResult | `pres-` |
| WorkflowPolicyAuditRecord | `wpa-` |
| WorkflowPolicyEvent | `wpevt-` |
| PolicyPriorityItem | `ppi-` |
| WorkflowPolicyEngine | `wpe-` |

---

## Error Codes Reference

| Code | Exception | When Raised |
|---|---|---|
| WGP-000 | WorkflowPolicyError | Base; never raised directly |
| WGP-001 | WorkflowPolicyNotFoundError | `registry.get(id)` — id not found |
| WGP-002 | WorkflowPolicyValidationError | `validator.validate_or_raise()` failed |
| WGP-003 | WorkflowPolicyEvaluationError | Internal evaluator exception |
| WGP-004 | WorkflowPolicyConflictError | Conflicting policy registration |
| WGP-005 | WorkflowGovernanceDecisionError | Decision processing failure |
| WGP-006 | WorkflowPolicyChainError | Chain evaluation failure |
| WGP-007 | WorkflowPolicyRegistryError | Registry capacity or lookup error |
| WGP-008 | WorkflowPolicyAuditError | Audit record not found |
| WGP-009 | WorkflowPolicyEngineError | Engine internal error |
| WGP-010 | WorkflowEmergencyStopError | Emergency stop triggered |

---

## Event Types Reference

| PolicyEventType | When Emitted |
|---|---|
| WORKFLOW_POLICY_LOADED | After successful policy registration |
| WORKFLOW_POLICY_VALIDATED | Before evaluation starts |
| WORKFLOW_GOVERNANCE_STARTED | At evaluation start |
| WORKFLOW_APPROVED | Decision = APPROVED or APPROVED_WITH_CONDITIONS |
| WORKFLOW_REJECTED | Decision = REJECTED |
| WORKFLOW_BLOCKED | Decision = BLOCKED |
| APPROVAL_REQUESTED | Decision = REQUIRES_MANUAL/EXEC_APPROVAL or ESCALATED |
| EMERGENCY_STOP_TRIGGERED | Decision = EMERGENCY_STOPPED |
| WORKFLOW_GOVERNANCE_COMPLETED | After full evaluation cycle |

---

## Testing Patterns

```python
from iios.workflow.policies import (
    WorkflowPolicyManager,
    WorkflowPolicyFactory,
    GovernanceDecision,
)

def test_approve_all():
    mgr = WorkflowPolicyManager()
    mgr.start()
    policy = WorkflowPolicyFactory.create_approve_all_policy("test-approve")
    mgr.register_policy(policy)
    req = WorkflowPolicyFactory.create_request("wf-test")
    resp = mgr.evaluate(req)
    assert resp.is_approved
    assert resp.decision == GovernanceDecision.APPROVED
    mgr.stop()

def test_reject_all():
    mgr = WorkflowPolicyManager()
    mgr.start()
    policy = WorkflowPolicyFactory.create_reject_all_policy("test-reject")
    mgr.register_policy(policy)
    req = WorkflowPolicyFactory.create_request("wf-test")
    resp = mgr.evaluate(req)
    assert resp.is_rejected
    assert not resp.can_proceed
    mgr.stop()
```

---

## Thread Safety Contracts

| Component | Lock Type | Notes |
|---|---|---|
| WorkflowPolicyRegistry | `threading.Lock()` | All reads and writes |
| WorkflowPolicyChain | `threading.Lock()` | State guard |
| WorkflowPolicyAudit | `threading.Lock()` | Deque + index updates |
| WorkflowPolicyHistory | `threading.Lock()` | Deque + index updates |
| WorkflowPolicyStatistics | `threading.Lock()` | All counter updates |
| WorkflowPolicyEventBus | `threading.Lock()` | Listener list per event type |
| WorkflowPolicyEngine | `threading.Lock()` | State transitions only |
| WorkflowPolicyManager | `threading.Lock()` | State transitions only |

All domain objects (`PolicyCondition`, `PolicyRule`, `WorkflowPolicy`, …) are
frozen dataclasses and inherently thread-safe.

---

## Performance Notes

- Evaluation is synchronous and in-process — typical latency < 1 ms for
  ≤20 policies with simple conditions.
- The audit, history, and statistics components are O(1) amortised for
  writes — bounded deques handle capacity automatically.
- Event bus listeners are called synchronously within `emit()`.  Keep
  listeners short; offload heavy work to a queue.

---

## Deployment

The package has no external dependencies beyond `iios.common`.
It is included in the main Docker image and auto-imported via the
`iios.workflow` namespace.

No database migrations are required — all state is in-memory and
reset on restart.
