# Compliance Guide

## Purpose

Compliance policies enforce regulatory and operational requirements such
as risk thresholds, jurisdiction rules, and data handling constraints.

---

## Compliance Context Fields

Compliance information is passed in `WorkflowPolicyContext.compliance_context`:

```python
compliance_context = {
    "risk_score":       0.75,           # 0.0 – 1.0
    "jurisdiction":     "EU",           # US, EU, APAC, …
    "data_class":       "PII",          # PII, PHI, FINANCIAL, PUBLIC
    "regulatory_flags": ["GDPR"],
    "approved_regions": ["EU", "UK"],
    "retention_days":   365,
}
```

---

## Common Compliance Policies

### 1. Block High Risk Score

```python
from iios.workflow.policies import (
    PolicyCondition, PolicyRule, WorkflowPolicyFactory,
    ConditionOperator, PolicyAction, PolicyPriorityLevel,
)

risk_cond = PolicyCondition.create(
    field    = "compliance_context.risk_score",
    operator = ConditionOperator.GREATER_THAN,
    value    = 0.8,
)
risk_rule = PolicyRule.create(
    name       = "block-high-risk",
    action     = PolicyAction.BLOCK,
    conditions = [risk_cond],
    priority   = PolicyPriorityLevel.CRITICAL,
)
policy = WorkflowPolicyFactory.create_compliance_policy(
    "Risk Threshold Gate",
    rules = [risk_rule],
)
```

### 2. EU Jurisdiction — Require GDPR Compliance

```python
eu_cond = PolicyCondition.create(
    field    = "compliance_context.jurisdiction",
    operator = ConditionOperator.EQUALS,
    value    = "EU",
)
gdpr_cond = PolicyCondition.create(
    field    = "compliance_context.regulatory_flags",
    operator = ConditionOperator.CONTAINS,
    value    = "GDPR",
)
# Both conditions must be true (AND logic)
eu_gdpr_rule = PolicyRule.create(
    name       = "eu-requires-gdpr",
    action     = PolicyAction.APPROVE,
    conditions = [eu_cond, gdpr_cond],
    priority   = PolicyPriorityLevel.HIGH,
)
```

### 3. PII Data — Manual Approval Required

```python
pii_cond = PolicyCondition.create(
    field    = "compliance_context.data_class",
    operator = ConditionOperator.EQUALS,
    value    = "PII",
)
pii_rule = PolicyRule.create(
    name       = "pii-manual-approval",
    action     = PolicyAction.REQUIRE_MANUAL_APPROVAL,
    conditions = [pii_cond],
    priority   = PolicyPriorityLevel.HIGH,
)
```

---

## SLA Compliance

```python
from iios.workflow.policies import PolicyType, PolicyDomain

sla_deadline_cond = PolicyCondition.create(
    field    = "metadata.sla_hours_remaining",
    operator = ConditionOperator.LESS_THAN_OR_EQUAL,
    value    = 2,
)
sla_rule = PolicyRule.create(
    name       = "sla-breach-escalate",
    action     = PolicyAction.ESCALATE,
    conditions = [sla_deadline_cond],
    priority   = PolicyPriorityLevel.HIGH,
)
sla_policy = WorkflowPolicy.create(
    name        = "SLA Monitor",
    policy_type = PolicyType.SLA,
    domain      = PolicyDomain.SLA_GOVERNANCE,
    rules       = [sla_rule],
)
```

---

## Audit Trail

Every compliance evaluation is automatically recorded in the audit log:

```python
audit = manager.history()
records = audit.recent_requests(20)
for req in records:
    print(req.request_id, req.workflow_id, req.created_at)

# Or retrieve by workflow
wf_history = manager.history().by_workflow("wf-order-42")
```
