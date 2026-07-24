# Knowledge Compliance Guide

## Compliance Domain

Compliance governance ensures that enterprise knowledge objects meet
regulatory, legal, and enterprise policy requirements before publication.

Policy Type: `PolicyType.COMPLIANCE`
Domain: `PolicyDomain.COMPLIANCE`

## Compliance Fields

```json
{
  "compliance": {
    "region": "IN",
    "regulatory_framework": "SEBI",
    "pii_present": false,
    "consent_obtained": true,
    "classification": "non-public"
  }
}
```

## Example — Block Non-Compliant Knowledge

```python
from iios.knowledge.policies import (
    KnowledgePolicyFactory,
    PolicyType, PolicyDomain, PolicyAction, ConditionOperator,
)

factory = KnowledgePolicyFactory()

# Block if PII present without consent
pii_cond = factory.create_condition(
    "PII present",
    "compliance.pii_present",
    ConditionOperator.EQ,
    True,
)
consent_cond = factory.create_condition(
    "No consent",
    "compliance.consent_obtained",
    ConditionOperator.EQ,
    False,
)
rule = factory.create_rule(
    "Block PII without consent",
    PolicyAction.BLOCK,
    conditions=[pii_cond, consent_cond],   # AND logic — both must match
    is_mandatory=True,
)
policy = factory.create_policy(
    "Privacy Compliance",
    PolicyType.COMPLIANCE,
    PolicyDomain.COMPLIANCE,
    rules=[rule],
)
```

## Escalation for Manual Review

```python
# Escalate if regulatory framework is unknown
cond = factory.create_condition(
    "Unknown framework",
    "compliance.regulatory_framework",
    ConditionOperator.NOT_IN_LIST,
    ["SEBI", "RBI", "IRDAI", "PFRDA"],
)
rule = factory.create_rule(
    "Escalate unknown framework",
    PolicyAction.ESCALATE,
    conditions=[cond],
)
```
