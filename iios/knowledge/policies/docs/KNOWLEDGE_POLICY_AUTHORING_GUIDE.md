# Knowledge Policy Authoring Guide

## Anatomy of a Policy

```
KnowledgePolicy
    ├── policy_id         (auto-generated)
    ├── name
    ├── description
    ├── policy_type       (PolicyType enum)
    ├── domain            (PolicyDomain enum)
    ├── priority          (PolicyPriority enum — lower = higher priority)
    ├── version           (default "1.0")
    ├── status            (PENDING → ACTIVE → INACTIVE | DEPRECATED | ARCHIVED)
    └── rules: List[PolicyRule]
            ├── rule_id
            ├── name
            ├── action            (PolicyAction enum)
            ├── is_mandatory
            └── conditions: List[PolicyCondition]   (AND logic)
                    ├── condition_id
                    ├── field_path    (dot-separated, e.g. "metadata.source")
                    ├── operator      (ConditionOperator enum)
                    └── expected_value
```

## Example — Approve all Execution Intelligence knowledge

```python
from iios.knowledge.policies import (
    KnowledgePolicyFactory,
    PolicyType, PolicyDomain, PolicyAction,
    ConditionOperator,
)

factory = KnowledgePolicyFactory()

# Condition: artifacts must come from execution_intelligence
cond = factory.create_condition(
    "Source check",
    "metadata.source",
    ConditionOperator.EQ,
    "execution_intelligence",
)

# Rule: if condition met → APPROVE
rule = factory.create_rule(
    "Approve execution intelligence",
    PolicyAction.APPROVE,
    conditions=[cond],
)

# Policy
policy = factory.create_policy(
    "Execution Intelligence Governance",
    PolicyType.CLASSIFICATION,
    PolicyDomain.CLASSIFICATION,
    rules=[rule],
)
```

## Example — Block if quality score < threshold

```python
cond = factory.create_condition(
    "Quality gate",
    "quality.score",
    ConditionOperator.LT,
    0.6,
)
rule = factory.create_rule(
    "Block low quality",
    PolicyAction.BLOCK,
    conditions=[cond],
    is_mandatory=True,
)
policy = factory.create_policy(
    "Quality Governance",
    PolicyType.QUALITY,
    PolicyDomain.METADATA,
    rules=[rule],
)
```

## Condition Operators

| Operator | Description |
|---|---|
| `EQ` | Exact match |
| `NE` | Not equal |
| `GT` | Greater than |
| `LT` | Less than |
| `GTE` | Greater than or equal |
| `LTE` | Less than or equal |
| `CONTAINS` | Value in collection |
| `NOT_CONTAINS` | Value not in collection |
| `EXISTS` | Field is not None |
| `NOT_EXISTS` | Field is None |
| `IN_LIST` | Value in expected list |
| `NOT_IN_LIST` | Value not in expected list |

## Rule Evaluation (AND Logic)

All conditions in a rule must pass for the rule to trigger.
Rules with no conditions trigger unconditionally.
When multiple rules trigger, the highest-severity action is chosen.
