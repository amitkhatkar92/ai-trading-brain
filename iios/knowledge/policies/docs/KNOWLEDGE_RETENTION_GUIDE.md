# Knowledge Retention Guide

## Retention Domain

Retention governance controls how long enterprise knowledge objects
are kept, when they are archived, and when they are purged.

Policy Type: `PolicyType.RETENTION`
Domain: `PolicyDomain.RETENTION`

## Retention Actions

| Action | Description |
|---|---|
| `APPROVE` | Retain — no action required |
| `ARCHIVE` | Move to archive tier |
| `REJECT` | Reject retention request |

## Recommended Retention Fields

```json
{
  "retention": {
    "age_days": 90,
    "data_class": "operational",
    "last_accessed_days": 30
  }
}
```

## Example Retention Policy

```python
from iios.knowledge.policies import (
    KnowledgePolicyFactory,
    PolicyType, PolicyDomain, PolicyAction, ConditionOperator,
)

factory = KnowledgePolicyFactory()

# Archive knowledge older than 365 days
cond = factory.create_condition(
    "Age check",
    "retention.age_days",
    ConditionOperator.GTE,
    365,
)
rule = factory.create_rule(
    "Archive old knowledge",
    PolicyAction.ARCHIVE,
    conditions=[cond],
)
policy = factory.create_policy(
    "Retention Governance",
    PolicyType.RETENTION,
    PolicyDomain.RETENTION,
    rules=[rule],
)
```

## Retention Tiers

```
Active      → available for retrieval (default)
Archived    → cold storage, audit retained
Purged      → deleted, audit entry retained
```
