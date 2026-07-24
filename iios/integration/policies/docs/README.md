# Integration Governance Policy Framework

**Package:** `iios.integration.policies`
**Version:** 1.0.0
**Module:** C15 M3 — Enterprise Integration & Connectivity

---

## Overview

The Integration Governance Policy Framework (IGPF) governs every enterprise
integration **before** external communication is permitted.

It validates governance rules for connectors, adapters, protocols, authentication,
authorization, endpoint access, message routing, security, and compliance.

The framework **performs no** connector execution, protocol implementation,
API communication, or business processing.

---

## Package Contents

| File | Description |
|------|-------------|
| `constants.py` | Enums: PolicyType (20), PolicyAction (8), PolicyPriority (5), PolicyDomain (13), + operators, events, statuses |
| `exceptions.py` | IPG-000 through IPG-009 exception hierarchy |
| `integration_policy_condition.py` | `IntegrationPolicyCondition` — atomic evaluation condition |
| `integration_policy_rule.py` | `IntegrationPolicyRule` — conditions + action |
| `integration_policy.py` | `IntegrationPolicy` — versioned, immutable policy descriptor |
| `integration_policy_context.py` | `IntegrationPolicyContext` — evaluation attributes |
| `integration_policy_request.py` | `IntegrationPolicyRequest` — governance request |
| `integration_policy_result.py` | `IntegrationPolicyResult` + `GovernanceDecision` |
| `integration_policy_response.py` | `IntegrationPolicyResponse` — engine output |
| `integration_policy_priority.py` | `IntegrationPolicyPriority` — conflict resolution |
| `integration_policy_evaluator.py` | `IntegrationPolicyEvaluator` — core evaluation engine |
| `integration_policy_validator.py` | `IntegrationPolicyValidator` — 7 configuration checks |
| `integration_policy_chain.py` | `IntegrationPolicyChain` — 6-mode chain evaluation |
| `integration_policy_registry.py` | `IntegrationPolicyRegistry` — thread-safe policy store |
| `integration_policy_factory.py` | `IntegrationPolicyFactory` — object creation |
| `integration_policy_audit.py` | `IntegrationPolicyAudit` — bounded audit trail |
| `integration_policy_statistics.py` | `IntegrationPolicyStatistics` — 9 governance metrics |
| `integration_policy_history.py` | `IntegrationPolicyHistory` — request/response history |
| `integration_policy_events.py` | `IntegrationPolicyEventBus` — 9 event types |
| `integration_policy_engine.py` | `IntegrationPolicyEngine` — central coordinator |
| `integration_policy_manager.py` | `IntegrationPolicyManager` — top-level façade |

---

## Quick Start

```python
from iios.integration.policies import (
    IntegrationPolicyManager,
    IntegrationPolicyFactory,
    PolicyType, PolicyDomain, PolicyPriority, PolicyAction,
)

factory = IntegrationPolicyFactory()
manager = IntegrationPolicyManager()
manager.start()

# Register an allow-all policy
policy = factory.create_approve_all_policy()
manager.load_policy(policy)

# Create a governance context
context = factory.create_context(
    engine_request_id = "req-001",
    engine_session_id = "sess-001",
    connector_type    = "rest_api",
    adapter_type      = "rest",
    protocol_type     = "https",
    endpoint          = "https://api.example.com/v1/orders",
    environment       = "production",
)

# Evaluate governance
response = manager.evaluate_context(context)
print(response.is_approved)        # True
print(response.decision.to_dict()) # full decision record

manager.stop()
```

---

## Architecture Notes

- All policy, rule, condition, context, request, result, response objects are **immutable** (`frozen=True`)
- The engine maintains **no vendor-specific dependencies**
- Evaluation is **synchronous** and **thread-safe**
- Audit entries are created for **every** evaluation
- Events are emitted for **every** governance lifecycle transition
- History and audit are bounded ring-buffers (no unbounded growth)
