# Connector Governance Guide

**Module:** C15 M3 — Integration Governance Policy Framework

---

## Connector Governance Overview

The IGPF provides `CONNECTOR_GOVERNANCE` and `ADAPTER_GOVERNANCE` policy types
to control which connectors and adapters are permitted for enterprise integration.

The framework validates governance rules **before** the Integration Engine
dispatches to connectors.  It does not execute connectors.

---

## Connector Policy Types

| Policy Type | Domain | Purpose |
|-------------|--------|---------|
| `CONNECTOR_GOVERNANCE` | `CONNECTOR_GOVERNANCE` | Permit/deny connector types |
| `ADAPTER_GOVERNANCE` | `ADAPTER_GOVERNANCE` | Permit/deny adapter configurations |
| `ENDPOINT_GOVERNANCE` | `API_GOVERNANCE` | Control endpoint access |

---

## Example: Whitelist Connector Types

```python
from iios.integration.policies import (
    IntegrationPolicyFactory, PolicyType, PolicyDomain,
    PolicyAction, ConditionOperator, PolicyPriority,
)

factory = IntegrationPolicyFactory()

# Block all Kafka connectors in production
condition = factory.create_condition(
    "Kafka Connector Type",
    field_path     = "connector_type",
    operator       = ConditionOperator.EQUALS,
    expected_value = "kafka",
)
rule = factory.create_rule(
    "Block Kafka in Production",
    PolicyAction.BLOCK,
    [condition],
    description = "Kafka connectors require dedicated gateway",
)
policy = factory.create_policy(
    "Connector Governance — Kafka",
    PolicyType.CONNECTOR_GOVERNANCE,
    domain   = PolicyDomain.CONNECTOR_GOVERNANCE,
    priority = PolicyPriority.HIGH,
    rules    = [rule],
)
```

---

## Example: Environment-Based Connector Control

```python
from iios.integration.policies import PolicyEvaluationMode

# Require escalation for database connectors in production
cond_db = factory.create_condition(
    "Database Connector",
    "connector_type", ConditionOperator.EQUALS, "database"
)
cond_prod = factory.create_condition(
    "Production Environment",
    "environment", ConditionOperator.EQUALS, "production"
)
rule = factory.create_rule(
    "Escalate Production DB Access",
    PolicyAction.ESCALATE,
    [cond_db, cond_prod],
    evaluation_mode = PolicyEvaluationMode.ALL_MUST_PASS,
)
```

---

## Evaluation Context Fields for Connector Governance

Policy conditions may reference these fields in the evaluation context:

| Field | Type | Description |
|-------|------|-------------|
| `connector_type` | str | Connector type (e.g. `rest_api`, `kafka`) |
| `adapter_type` | str | Adapter type (e.g. `rest`, `kafka`) |
| `protocol_type` | str | Protocol type (e.g. `https`, `grpc`) |
| `endpoint` | str | Target endpoint URL or address |
| `environment` | str | Deployment environment |
| `connector_config.*` | dict | Connector configuration attributes |
| `adapter_config.*` | dict | Adapter configuration attributes |
| `endpoint_config.*` | dict | Endpoint configuration attributes |

---

## Priority Recommendation

| Scenario | Recommended Priority |
|----------|---------------------|
| Block unapproved connectors | `CRITICAL` |
| Escalate new connector types | `HIGH` |
| Audit connector usage | `MEDIUM` |
| Allow standard connectors | `LOW` |
