# Workflow Policy Guide

## Policy Structure

A `WorkflowPolicy` is composed of:

| Component | Description |
|---|---|
| `policy_id` | Unique identifier (auto-generated, prefix `pol-`) |
| `name` | Human-readable name |
| `policy_type` | `PolicyType` enum (14 types) |
| `domain` | `PolicyDomain` enum (12 domains) |
| `priority` | `PolicyPriorityLevel` — controls evaluation order |
| `rules` | Ordered list of `PolicyRule` objects |
| `default_action` | Action to use when no rules fire |
| `enabled` | Boolean — disabled policies are never evaluated |
| `version` | Version string |

---

## Policy Types

| PolicyType | Purpose |
|---|---|
| WORKFLOW_GOVERNANCE | General workflow governance |
| EXECUTION_APPROVAL | Execution gate |
| SCHEDULING | Schedule-based governance |
| RESOURCE_ALLOCATION | Resource limits |
| PRIORITY | Priority-based governance |
| DEPENDENCY | Dependency checks |
| SECURITY | Security enforcement |
| COMPLIANCE | Regulatory compliance |
| RISK | Risk assessment |
| HUMAN_APPROVAL | Human-in-the-loop |
| SLA | Service Level Agreement |
| AUDIT | Audit requirements |
| RETENTION | Data retention |
| ENTERPRISE_WORKFLOW | Enterprise-wide governance |

---

## Policy Domains

| PolicyDomain | Governance Area |
|---|---|
| WORKFLOW_GOVERNANCE | General workflow |
| SCHEDULING_GOVERNANCE | Scheduling |
| EXECUTION_GOVERNANCE | Execution |
| SECURITY_GOVERNANCE | Security |
| COMPLIANCE_GOVERNANCE | Compliance |
| RISK_GOVERNANCE | Risk |
| RESOURCE_GOVERNANCE | Resources |
| APPROVAL_GOVERNANCE | Approvals |
| DEPENDENCY_GOVERNANCE | Dependencies |
| SLA_GOVERNANCE | SLA |
| AUDIT_GOVERNANCE | Auditing |
| ENTERPRISE_GOVERNANCE | Enterprise-wide |

---

## Creating Policies

```python
from iios.workflow.policies import (
    WorkflowPolicy, PolicyType, PolicyDomain,
    PolicyPriorityLevel, PolicyAction,
)

# Minimal policy — approves everything
policy = WorkflowPolicy.create(
    name        = "Default Approve",
    policy_type = PolicyType.WORKFLOW_GOVERNANCE,
)

# Policy with explicit settings
policy = WorkflowPolicy.create(
    name           = "Production Gate",
    policy_type    = PolicyType.EXECUTION_APPROVAL,
    domain         = PolicyDomain.EXECUTION_GOVERNANCE,
    priority       = PolicyPriorityLevel.CRITICAL,
    default_action = PolicyAction.REJECT,          # fail-safe default
    rules          = [my_approve_rule],
    description    = "Must pass all execution checks",
    version        = "2.1.0",
)
```

---

## Factory Shortcuts

```python
from iios.workflow.policies import WorkflowPolicyFactory

# Always approve
policy = WorkflowPolicyFactory.create_approve_all_policy("default-approve")

# Always reject (lock-down)
policy = WorkflowPolicyFactory.create_reject_all_policy("lock-down")

# Security policy
policy = WorkflowPolicyFactory.create_security_policy(
    "auth-check",
    rules = [auth_rule],
)

# Risk policy
policy = WorkflowPolicyFactory.create_risk_policy(
    "risk-gate",
    rules = [high_risk_rule],
)
```

---

## Policy Rules

Each `PolicyRule` maps a set of `PolicyCondition`s to a `PolicyAction`:

```python
from iios.workflow.policies import (
    PolicyCondition, PolicyRule,
    ConditionOperator, PolicyAction, PolicyPriorityLevel,
)

cond = PolicyCondition.create(
    field    = "security_context.authenticated",
    operator = ConditionOperator.EQUALS,
    value    = True,
    description = "User must be authenticated",
)

rule = PolicyRule.create(
    name       = "require-auth",
    action     = PolicyAction.APPROVE,
    conditions = [cond],
    priority   = PolicyPriorityLevel.HIGH,
    description = "Allow only authenticated requests",
)
```

---

## Condition Operators (15 supported)

| Operator | Description |
|---|---|
| EQUALS / NOT_EQUALS | Equality check |
| GREATER_THAN / LESS_THAN | Numeric comparison |
| GREATER_THAN_OR_EQUAL / LESS_THAN_OR_EQUAL | Numeric boundary |
| IN / NOT_IN | Membership test |
| CONTAINS / NOT_CONTAINS | String/list containment |
| IS_NULL / IS_NOT_NULL | Null check |
| STARTS_WITH / ENDS_WITH | String prefix/suffix |
| MATCHES | Regex match |

---

## Context Fields (dot-notation)

The context is flattened using dot-notation.  Example paths:

| Path | Source |
|---|---|
| `workflow_id` | Context top-level |
| `workflow_type` | Context top-level |
| `environment` | Context top-level |
| `security_context.user_role` | Nested dict |
| `compliance_context.risk_score` | Nested dict |
| `resource_context.cpu_limit` | Nested dict |
| `metadata.priority` | Nested dict |
