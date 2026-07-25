# Security Policy Guide

## Purpose

Security governance policies enforce authentication, authorization, and
threat-level controls before allowing workflow execution.

---

## Key Security Context Fields

Security information is passed through `WorkflowPolicyContext.security_context`:

```python
security_context = {
    "authenticated":   True,
    "user_role":       "operator",           # admin, operator, viewer
    "user_id":         "user-123",
    "auth_method":     "mfa",                # mfa, sso, api_key
    "threat_level":    "low",                # low, medium, high, critical
    "ip_address":      "10.0.0.1",
    "session_valid":   True,
}
```

---

## Common Security Policies

### 1. Require Authentication

```python
from iios.workflow.policies import (
    PolicyCondition, PolicyRule, WorkflowPolicyFactory,
    ConditionOperator, PolicyAction, PolicyPriorityLevel,
)

auth_cond = PolicyCondition.create(
    field    = "security_context.authenticated",
    operator = ConditionOperator.EQUALS,
    value    = True,
)
auth_rule = PolicyRule.create(
    name       = "require-authenticated",
    action     = PolicyAction.APPROVE,
    conditions = [auth_cond],
    priority   = PolicyPriorityLevel.CRITICAL,
)
policy = WorkflowPolicyFactory.create_security_policy(
    "Auth Gate",
    rules = [auth_rule],
)
```

### 2. Block on Critical Threat Level

```python
threat_cond = PolicyCondition.create(
    field    = "security_context.threat_level",
    operator = ConditionOperator.IN,
    value    = ["high", "critical"],
)
threat_rule = PolicyRule.create(
    name       = "block-high-threat",
    action     = PolicyAction.BLOCK,
    conditions = [threat_cond],
    priority   = PolicyPriorityLevel.CRITICAL,
)
```

### 3. Role-Based Access Control

```python
role_cond = PolicyCondition.create(
    field    = "security_context.user_role",
    operator = ConditionOperator.IN,
    value    = ["admin", "operator"],
)
role_rule = PolicyRule.create(
    name       = "role-based-approve",
    action     = PolicyAction.APPROVE,
    conditions = [role_cond],
    priority   = PolicyPriorityLevel.HIGH,
)
```

### 4. Require MFA for Admin Actions

```python
mfa_cond = PolicyCondition.create(
    field    = "security_context.auth_method",
    operator = ConditionOperator.EQUALS,
    value    = "mfa",
)
admin_cond = PolicyCondition.create(
    field    = "security_context.user_role",
    operator = ConditionOperator.EQUALS,
    value    = "admin",
)
mfa_rule = PolicyRule.create(
    name       = "admin-requires-mfa",
    action     = PolicyAction.APPROVE,
    conditions = [admin_cond, mfa_cond],   # AND logic — both must pass
    priority   = PolicyPriorityLevel.HIGH,
)
```

---

## Combining Security Policies

Register multiple security policies in the same manager.
Conflict resolution ensures that a BLOCK from one policy overrides an
APPROVE from another:

```python
manager.register_policy(auth_policy)       # APPROVE if authenticated
manager.register_policy(threat_policy)     # BLOCK if threat=high
manager.register_policy(role_policy)       # APPROVE if role=admin/operator

# Threat policy BLOCK will override auth APPROVE
response = manager.evaluate(request)
# response.decision → BLOCKED (if threat_level = "high")
```
