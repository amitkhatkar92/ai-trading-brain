# Approval Policy Guide

## Overview

Approval policies allow the governance framework to route workflows
through human or executive review before proceeding.

---

## Approval Decision Types

| Decision | When to Use |
|---|---|
| REQUIRES_MANUAL_APPROVAL | Standard human review |
| REQUIRES_EXECUTIVE_APPROVAL | High-value or high-risk decisions |
| ESCALATED | Unable to decide automatically — route upward |

---

## Creating an Approval Policy

```python
from iios.workflow.policies import (
    WorkflowPolicy, PolicyRule, PolicyCondition,
    PolicyType, PolicyDomain, PolicyPriorityLevel,
    PolicyAction, ConditionOperator,
)

# Require manual approval for workflows with value > 100,000
high_value_cond = PolicyCondition.create(
    field    = "metadata.order_value",
    operator = ConditionOperator.GREATER_THAN,
    value    = 100_000,
    description = "Order value exceeds $100K",
)

high_value_rule = PolicyRule.create(
    name       = "high-value-manual-approval",
    action     = PolicyAction.REQUIRE_MANUAL_APPROVAL,
    conditions = [high_value_cond],
    priority   = PolicyPriorityLevel.HIGH,
)

approval_policy = WorkflowPolicy.create(
    name        = "High-Value Approval Gate",
    policy_type = PolicyType.HUMAN_APPROVAL,
    domain      = PolicyDomain.APPROVAL_GOVERNANCE,
    priority    = PolicyPriorityLevel.HIGH,
    rules       = [high_value_rule],
    default_action = PolicyAction.APPROVE,
)
```

---

## Executive Approval

```python
exec_cond = PolicyCondition.create(
    field    = "metadata.order_value",
    operator = ConditionOperator.GREATER_THAN,
    value    = 1_000_000,
    description = "Order value exceeds $1M — executive approval required",
)

exec_rule = PolicyRule.create(
    name       = "exec-approval-1m",
    action     = PolicyAction.REQUIRE_EXECUTIVE_APPROVAL,
    conditions = [exec_cond],
    priority   = PolicyPriorityLevel.CRITICAL,
)
```

---

## Checking for Approval Requirements

```python
response = manager.evaluate(request)

if response.requires_approval:
    if response.decision.value == "requires_executive_approval":
        notify_executive(response)
    else:
        notify_approver(response)
elif response.is_escalated:
    route_to_escalation_team(response)
elif response.can_proceed:
    execute_workflow()
```

---

## Emergency Stop

For immediate halts (not just approval requests):

```python
emergency_cond = PolicyCondition.create(
    field    = "security_context.threat_level",
    operator = ConditionOperator.EQUALS,
    value    = "critical",
)

emergency_rule = PolicyRule.create(
    name       = "emergency-stop-on-threat",
    action     = PolicyAction.EMERGENCY_STOP,
    conditions = [emergency_cond],
    priority   = PolicyPriorityLevel.CRITICAL,
)
```

Emergency stop has the highest precedence and overrides all other decisions.
