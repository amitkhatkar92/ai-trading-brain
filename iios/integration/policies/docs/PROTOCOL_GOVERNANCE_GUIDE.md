# Protocol Governance Guide

**Module:** C15 M3 — Integration Governance Policy Framework

---

## Protocol Governance Overview

The IGPF controls which protocols are permitted for enterprise integration
through `PROTOCOL_GOVERNANCE` and related policy types.

---

## Protocol Policy Types

| Policy Type | Governs |
|-------------|---------|
| `PROTOCOL_GOVERNANCE` | Protocol selection and version |
| `TRANSPORT_SECURITY` | TLS requirements, cipher suites |
| `NETWORK_SECURITY` | Network-level protocol controls |
| `MESSAGE_ROUTING` | Routing protocol governance |

---

## Example: Enforce HTTPS Only

```python
from iios.integration.policies import (
    IntegrationPolicyFactory, PolicyType, PolicyDomain,
    PolicyAction, ConditionOperator, PolicyPriority,
)

factory = IntegrationPolicyFactory()

# Block any non-HTTPS protocol in production
condition = factory.create_condition(
    "Non-HTTPS Protocol",
    field_path     = "protocol_type",
    operator       = ConditionOperator.NOT_IN,
    expected_value = ["https", "grpc", "internal"],
)
rule = factory.create_rule(
    "Block Insecure Protocols",
    PolicyAction.BLOCK,
    [condition],
)
policy = factory.create_policy(
    "Protocol Security — HTTPS Only",
    PolicyType.PROTOCOL_GOVERNANCE,
    domain   = PolicyDomain.PROTOCOL_GOVERNANCE,
    priority = PolicyPriority.CRITICAL,
    rules    = [rule],
)
```

---

## Example: Require TLS Configuration

```python
# Escalate when TLS is not explicitly configured
cond_no_tls = factory.create_condition(
    "TLS Not Configured",
    field_path = "protocol_config.tls_version",
    operator   = ConditionOperator.NOT_EXISTS,
)
rule = factory.create_rule(
    "Escalate Missing TLS Config",
    PolicyAction.ESCALATE,
    [cond_no_tls],
)
```

---

## Evaluation Context Fields for Protocol Governance

| Field | Description |
|-------|-------------|
| `protocol_type` | Protocol type string (e.g. `https`, `grpc`, `amqp`) |
| `protocol_config.*` | Protocol configuration attributes |
| `security_config.tls_enabled` | TLS enablement flag |
| `security_config.tls_version` | TLS version string |
| `security_config.cipher_suites` | Permitted cipher suites |

---

## Protocol Priority Table

| Protocol | Risk Level | Recommended Policy Priority |
|----------|------------|----------------------------|
| `http` (unencrypted) | HIGH | `CRITICAL` block |
| `https` | LOW | `LOW` approve |
| `grpc` | LOW | `LOW` approve |
| `amqp` | MEDIUM | `HIGH` review |
| `kafka_protocol` | MEDIUM | `HIGH` review |
| `internal` | NONE | `INFORMATIONAL` |
