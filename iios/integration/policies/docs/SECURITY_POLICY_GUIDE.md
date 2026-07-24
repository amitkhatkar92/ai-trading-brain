# Security Policy Guide

**Module:** C15 M3 — Integration Governance Policy Framework

---

## Security Governance Overview

The IGPF supports 6 security-focused policy domains:

| Domain | Description |
|--------|-------------|
| `AUTHENTICATION` | Auth scheme governance |
| `AUTHORIZATION` | Access control governance |
| `SECURITY` | General security posture |
| `ENCRYPTION` | Transport and at-rest encryption |
| `NETWORK` | Network access and routing |
| `COMPLIANCE` | Regulatory compliance |

And 8 security-focused policy types:

| Policy Type | Governs |
|-------------|---------|
| `AUTHENTICATION` | Auth mechanisms |
| `AUTHORIZATION` | Permission grants |
| `CREDENTIAL_MANAGEMENT` | Credential lifecycle |
| `SECRET_MANAGEMENT` | Secret handling |
| `CERTIFICATE` | TLS certificates |
| `NETWORK_SECURITY` | Network access |
| `TRANSPORT_SECURITY` | TLS/DTLS settings |
| `ENCRYPTION` | Encryption standards |

---

## Security Approval Policy

```python
from iios.integration.policies import (
    IntegrationPolicyFactory, PolicyType, PolicyDomain, PolicyPriority,
    PolicyAction, ConditionOperator,
)

factory = IntegrationPolicyFactory()

# Require security approval for external endpoints
condition = factory.create_condition(
    "External Endpoint",
    field_path     = "endpoint_config.is_external",
    operator       = ConditionOperator.EQUALS,
    expected_value = True,
)
rule = factory.create_rule(
    "External Access Security Review",
    PolicyAction.REQUIRE_SECURITY_APPROVAL,
    [condition],
    description = "All external endpoints require security approval",
)
policy = factory.create_policy(
    "External Endpoint Security",
    PolicyType.NETWORK_SECURITY,
    domain   = PolicyDomain.SECURITY,
    priority = PolicyPriority.HIGH,
    rules    = [rule],
)
```

---

## Emergency Stop Policy

```python
# Trigger emergency stop for blocked environments
policy = factory.create_emergency_stop_policy(
    name          = "Production Emergency Stop",
    field_path    = "environment",
    trigger_value = "emergency",
)
```

---

## Encryption Enforcement Policy

```python
# Block integrations that do not use encrypted transport
condition = factory.create_condition(
    "Unencrypted Transport",
    field_path     = "security_config.tls_enabled",
    operator       = ConditionOperator.EQUALS,
    expected_value = False,
)
rule = factory.create_rule(
    "Block Unencrypted", PolicyAction.BLOCK, [condition]
)
policy = factory.create_policy(
    "Require TLS",
    PolicyType.ENCRYPTION,
    domain   = PolicyDomain.ENCRYPTION,
    priority = PolicyPriority.CRITICAL,
    rules    = [rule],
)
```

---

## Security Priority Hierarchy

All security policies should use `PolicyPriority.HIGH` or `PolicyPriority.CRITICAL`.

The conflict resolution strategy `MOST_RESTRICTIVE` (default) ensures that a
`CRITICAL` security block overrides any lower-priority approval.

---

## Security Events

Subscribe to these events for security monitoring:

```python
from iios.integration.policies import PolicyEventType

engine.event_bus.add_listener(
    lambda e: print(e.event_type, e.payload)
    if e.event_type in (
        PolicyEventType.SECURITY_APPROVAL_REQUESTED,
        PolicyEventType.EMERGENCY_STOP_TRIGGERED,
        PolicyEventType.INTEGRATION_BLOCKED,
    ) else None
)
```
