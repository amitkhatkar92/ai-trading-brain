# Workflow Governance Policy Framework — Module 3 (C16 M3)

## Overview

The **Workflow Governance Policy Framework** (`iios.workflow.policies`) provides
enterprise-grade governance evaluation for workflow execution.  It determines
whether a workflow is *approved*, *rejected*, *blocked*, *escalated*, or
subject to *emergency stop* based on a composable set of rules and policies.

---

## Architecture

```
WorkflowPolicyManager        ← top-level public API
  └── WorkflowPolicyEngine   ← central coordinator
        ├── WorkflowPolicyRegistry    — registered policies (by type / domain)
        ├── WorkflowPolicyValidator   — configuration validation
        ├── WorkflowPolicyChain       — multi-policy evaluation pipeline
        │     └── WorkflowPolicyEvaluator  — single-policy evaluation
        ├── WorkflowPolicyAudit       — immutable audit trail
        ├── WorkflowPolicyStatistics  — evaluation metrics
        ├── WorkflowPolicyHistory     — bounded request/response history
        └── WorkflowPolicyEventBus   — per-event-type event bus
```

---

## Package Layout

```
iios/workflow/policies/
├── __init__.py
├── constants.py                        — enums, precedence tables
├── exceptions.py                       — WGP-000 … WGP-010
├── workflow_policy_condition.py        — PolicyCondition  (frozen dataclass)
├── workflow_policy_rule.py             — PolicyRule       (frozen dataclass)
├── workflow_policy_context.py          — WorkflowPolicyContext
├── workflow_policy.py                  — WorkflowPolicy
├── workflow_policy_request.py          — WorkflowPolicyRequest
├── workflow_policy_response.py         — WorkflowPolicyResponse
├── workflow_policy_result.py           — WorkflowPolicyResult
├── workflow_policy_priority.py         — PolicyPriorityItem
├── workflow_policy_evaluator.py        — WorkflowPolicyEvaluator
├── workflow_policy_validator.py        — WorkflowPolicyValidator
├── workflow_policy_registry.py         — WorkflowPolicyRegistry
├── workflow_policy_chain.py            — WorkflowPolicyChain
├── workflow_policy_audit.py            — WorkflowPolicyAudit / AuditRecord
├── workflow_policy_statistics.py       — WorkflowPolicyStatistics / Report
├── workflow_policy_history.py          — WorkflowPolicyHistory
├── workflow_policy_events.py           — WorkflowPolicyEvent / EventBus
├── workflow_policy_factory.py          — WorkflowPolicyFactory
├── workflow_policy_engine.py           — WorkflowPolicyEngine
└── workflow_policy_manager.py          — WorkflowPolicyManager
```

---

## Quick Start

```python
from iios.workflow.policies import (
    WorkflowPolicyManager,
    WorkflowPolicyFactory,
)

manager = WorkflowPolicyManager()
manager.start()

# Register an approve-all policy
policy = WorkflowPolicyFactory.create_approve_all_policy("default-approve")
manager.register_policy(policy)

# Evaluate governance
request = WorkflowPolicyFactory.create_request("wf-123")
response = manager.evaluate(request)

print(response.decision)           # GovernanceDecision.APPROVED
print(response.is_approved)        # True
print(response.can_proceed)        # True

manager.stop()
```

---

## Governance Decision Hierarchy

| Decision | Meaning |
|---|---|
| APPROVED | Workflow may proceed |
| APPROVED_WITH_CONDITIONS | Workflow may proceed with constraints |
| REQUIRES_MANUAL_APPROVAL | Human review required |
| REQUIRES_EXECUTIVE_APPROVAL | Executive sign-off required |
| ESCALATED | Issue escalated to higher authority |
| REJECTED | Workflow rejected |
| BLOCKED | Workflow blocked — stronger than reject |
| EMERGENCY_STOPPED | Immediate halt — overrides all |

---

## Key Design Principles

1. **Fail-open safety net** — engine errors return APPROVED and log the issue, preventing the governance system from becoming a blocking point
2. **Conflict resolution** — when multiple policies apply, the highest-authority action wins (EMERGENCY_STOP > BLOCK > REJECT > … > APPROVE)
3. **Immutability** — all domain objects (`PolicyCondition`, `PolicyRule`, `WorkflowPolicy`, …) are frozen dataclasses
4. **Thread safety** — all mutable components (`Registry`, `Audit`, `Chain`, …) use `threading.Lock()`
5. **No vendor SDK** — pure Python; no external library dependencies beyond `iios.common`

---

## Module Reference

| Module | Key Class | Responsibility |
|---|---|---|
| `constants` | enums, dicts | All enum types and precedence tables |
| `exceptions` | `WorkflowPolicyError` + 10 subtypes | Error hierarchy (WGP-000–010) |
| `workflow_policy_condition` | `PolicyCondition` | 15-operator field evaluation |
| `workflow_policy_rule` | `PolicyRule` | Condition-to-action mapping |
| `workflow_policy_context` | `WorkflowPolicyContext` | Workflow evaluation context |
| `workflow_policy` | `WorkflowPolicy` | Versioned named policy |
| `workflow_policy_request` | `WorkflowPolicyRequest` | Governance evaluation input |
| `workflow_policy_response` | `WorkflowPolicyResponse` | Governance evaluation output |
| `workflow_policy_result` | `WorkflowPolicyResult` | Per-policy result |
| `workflow_policy_priority` | `PolicyPriorityItem` | Priority-ordered policy wrapper |
| `workflow_policy_evaluator` | `WorkflowPolicyEvaluator` | Single-policy evaluator |
| `workflow_policy_validator` | `WorkflowPolicyValidator` | Policy configuration validator |
| `workflow_policy_registry` | `WorkflowPolicyRegistry` | Thread-safe policy store |
| `workflow_policy_chain` | `WorkflowPolicyChain` | Multi-policy chain evaluator |
| `workflow_policy_audit` | `WorkflowPolicyAudit` | Bounded audit log |
| `workflow_policy_statistics` | `WorkflowPolicyStatistics` | Evaluation metrics |
| `workflow_policy_history` | `WorkflowPolicyHistory` | Request/response history |
| `workflow_policy_events` | `WorkflowPolicyEventBus` | Per-event-type event bus |
| `workflow_policy_factory` | `WorkflowPolicyFactory` | Standard object factory |
| `workflow_policy_engine` | `WorkflowPolicyEngine` | Central coordinator |
| `workflow_policy_manager` | `WorkflowPolicyManager` | Public API |
