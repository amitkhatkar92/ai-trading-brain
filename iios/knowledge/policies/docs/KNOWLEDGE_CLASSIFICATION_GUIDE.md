# Knowledge Classification Guide

## Classification Domain

Classification governance controls how enterprise knowledge objects
are assigned to categories, types, and subsystem ownership.

Policy Type: `PolicyType.CLASSIFICATION`
Domain: `PolicyDomain.CLASSIFICATION`

## Supported Subsystem Sources

| Source | Knowledge Type |
|---|---|
| `execution_intelligence` | Execution snapshots, order history |
| `execution_recovery` | Recovery records, resilience events |
| `execution_analytics` | Analytics reports, performance data |
| `decision_intelligence` | Decision snapshots, scenario analysis |
| `portfolio_intelligence` | Portfolio snapshots, allocation reports |
| `risk_intelligence` | Risk snapshots, VaR reports |
| `market_intelligence` | Market regime, sector analysis |
| `ai_supervisor` | Governance decisions, audit trails |
| `infrastructure` | System health, telemetry |
| `enterprise` | Cross-system enterprise events |

## Classification Fields

Recommended artifact structure for classification:

```json
{
  "metadata": {
    "source": "execution_intelligence",
    "subsystem_id": "execution_intelligence",
    "classification": "operational",
    "data_class": "time_series",
    "sensitivity": "internal"
  }
}
```

## Example Classification Policy

```python
from iios.knowledge.policies import (
    KnowledgePolicyFactory,
    PolicyType, PolicyDomain, PolicyAction, ConditionOperator,
)

factory = KnowledgePolicyFactory()

# Only accept classified artifacts
cond = factory.create_condition(
    "Classification present",
    "metadata.classification",
    ConditionOperator.EXISTS,
)
rule = factory.create_rule(
    "Require classification",
    PolicyAction.APPROVE,
    conditions=[cond],
)
policy = factory.create_policy(
    "Classification Governance",
    PolicyType.CLASSIFICATION,
    PolicyDomain.CLASSIFICATION,
    rules=[rule],
)
```

## Classification Hierarchy

```
unclassified    → pending governance review
public          → freely shareable
internal        → internal enterprise use
confidential    → restricted access
restricted      → senior governance approval required
```
