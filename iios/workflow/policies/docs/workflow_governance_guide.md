# Workflow Governance Guide

## Purpose

The governance framework evaluates every workflow against a set of registered
policies before execution is permitted.  This ensures enterprise compliance,
security enforcement, and operational risk control.

---

## Lifecycle

1. **Register policies** — at startup, load all governance policies into the `WorkflowPolicyManager`.
2. **Create a context** — per workflow, build a `WorkflowPolicyContext` with workflow metadata, security, compliance, and resource information.
3. **Create a request** — wrap the context in a `WorkflowPolicyRequest` (optionally filter by type / domain).
4. **Evaluate** — call `manager.evaluate(request)`.
5. **Act on the decision** — inspect `response.decision` and `response.can_proceed`.

---

## Full Example

```python
from iios.workflow.policies import (
    WorkflowPolicyManager,
    WorkflowPolicyFactory,
    WorkflowPolicyContext,
    PolicyCondition, PolicyRule, WorkflowPolicy,
    ConditionOperator, PolicyAction, PolicyPriorityLevel,
    PolicyType, PolicyDomain,
)

# 1. Start manager
manager = WorkflowPolicyManager()
manager.start()

# 2. Create a rule: reject if risk_score > 0.8
condition = PolicyCondition.create(
    field    = "compliance_context.risk_score",
    operator = ConditionOperator.GREATER_THAN,
    value    = 0.8,
    description = "High risk score detected",
)
rule = PolicyRule.create(
    name       = "block-high-risk",
    action     = PolicyAction.REJECT,
    conditions = [condition],
    priority   = PolicyPriorityLevel.CRITICAL,
)

# 3. Create and register the policy
policy = WorkflowPolicy.create(
    name        = "Enterprise Risk Gate",
    policy_type = PolicyType.RISK,
    domain      = PolicyDomain.RISK_GOVERNANCE,
    priority    = PolicyPriorityLevel.CRITICAL,
    rules       = [rule],
)
manager.register_policy(policy)

# 4. Build a context with a high risk score
context = WorkflowPolicyFactory.create_context(
    workflow_id        = "wf-order-42",
    compliance_context = {"risk_score": 0.95},
)

# 5. Evaluate
request  = WorkflowPolicyFactory.create_request("wf-order-42", context)
response = manager.evaluate(request)

print(response.decision)        # GovernanceDecision.REJECTED
print(response.can_proceed)     # False
print(response.reasoning)
# "Policy 'Enterprise Risk Gate' [risk_governance] applied action='reject': ..."
```

---

## Policy Evaluation Order

1. Policies are sorted by `priority` (CRITICAL → HIGH → MEDIUM → LOW → INFORMATIONAL).
2. Within each policy, rules are evaluated in priority order.
3. The **first rule whose conditions all pass** determines the policy action.
4. If **no rule matches**, the policy's `default_action` is used.
5. After all policies run, **conflict resolution** picks the highest-authority action.

---

## Conflict Resolution

| Precedence | Action |
|---|---|
| 0 (highest) | EMERGENCY_STOP |
| 1 | BLOCK |
| 2 | REJECT |
| 3 | REQUIRE_EXECUTIVE_APPROVAL |
| 4 | ESCALATE |
| 5 | REQUIRE_MANUAL_APPROVAL |
| 6 | APPROVE_WITH_CONDITIONS |
| 7 (lowest) | APPROVE |

---

## Thread Safety

All public API classes are thread-safe.  Multiple threads may call
`manager.evaluate()` concurrently without data races.

---

## Health & Statistics

```python
# Real-time health
print(manager.health())

# Aggregate evaluation statistics
stats = manager.statistics()
print(stats["policies_approved"])
print(stats["average_evaluation_time_ms"])

# Recent evaluations
history = manager.history()
for req in history.recent_requests(10):
    print(req.request_id, req.workflow_id)
```
