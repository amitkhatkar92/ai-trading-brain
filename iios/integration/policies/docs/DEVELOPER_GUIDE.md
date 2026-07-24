# Developer Guide

**Module:** C15 M3 — Integration Governance Policy Framework

---

## Architecture

```
IntegrationPolicyManager          ← top-level façade
    │
    └─► IntegrationPolicyEngine   ← central coordinator
             │
             ├─► IntegrationPolicyRegistry     ← thread-safe policy store
             ├─► IntegrationPolicyEvaluator    ← core rule evaluation
             ├─► IntegrationPolicyPriority     ← conflict resolution
             ├─► IntegrationPolicyValidator    ← 7 configuration checks
             ├─► IntegrationPolicyChain        ← 6-mode chain evaluation
             ├─► IntegrationPolicyAudit        ← bounded audit trail
             ├─► IntegrationPolicyStatistics   ← 9 governance metrics
             ├─► IntegrationPolicyHistory      ← request/response history
             └─► IntegrationPolicyEventBus     ← 9 event types
```

---

## Threading

All subsystems are thread-safe.  The engine uses a lock only for lifecycle
transitions (`start()` / `stop()`).  Evaluation calls are lock-free — each
call operates on immutable data objects.

---

## Extending the Framework

### Adding a Custom Policy

```python
from iios.integration.policies import (
    IntegrationPolicyFactory, IntegrationPolicyEngine,
    PolicyType, PolicyDomain, PolicyPriority,
    PolicyAction, ConditionOperator,
)

factory = IntegrationPolicyFactory()
engine  = IntegrationPolicyEngine()
engine.start()

# Create a rate-limiting governance policy
condition = factory.create_condition(
    "High Priority Request",
    field_path     = "priority",
    operator       = ConditionOperator.LESS_THAN,
    expected_value = 3,
)
rule   = factory.create_rule("Rate Limit Critical", PolicyAction.ESCALATE, [condition])
policy = factory.create_policy(
    "Rate Limiting Policy",
    PolicyType.RATE_LIMITING,
    domain   = PolicyDomain.ENTERPRISE,
    priority = PolicyPriority.MEDIUM,
    rules    = [rule],
)
engine.load_policy(policy)
```

### Using Policy Chains

```python
from iios.integration.policies import (
    IntegrationPolicyFactory, IntegrationPolicyEngine, PolicyChainMode,
)

factory = IntegrationPolicyFactory()
engine  = IntegrationPolicyEngine()
engine.start()

p1 = factory.create_approve_all_policy()
p2 = factory.create_security_approval_policy()

chain = factory.create_chain(
    name     = "Security Chain",
    mode     = PolicyChainMode.PRIORITY,
    policies = [p1, p2],
)

context  = factory.create_context("req-001", "sess-001", "rest_api")
decision = engine.evaluate_chain(chain, context)
print(decision.final_action)
```

### Subscribing to Events

```python
from iios.integration.policies import PolicyEventType

def on_blocked(event):
    if event.event_type in (
        PolicyEventType.INTEGRATION_BLOCKED,
        PolicyEventType.EMERGENCY_STOP_TRIGGERED,
    ):
        print(f"GOVERNANCE ALERT: {event.event_type} — {event.request_id}")

engine.event_bus.add_listener(on_blocked)
```

---

## Connecting to M2 (Integration Engine)

The M2 engine has a governance hook `_coordinate_governance()`.
When M3 is available, M2 calls it before dispatch:

```python
# In integration_engine.py (M2 hook — not yet wired)
def _coordinate_governance(self, request, context):
    if self._policy_engine:
        policy_ctx = IntegrationPolicyContext.create(
            engine_request_id = request.request_id,
            engine_session_id = context.session_id,
            connector_type    = request.connector_type.value,
            adapter_type      = request.adapter_type.value,
            protocol_type     = request.protocol_type.value,
            endpoint          = request.endpoint,
        )
        policy_req = IntegrationPolicyRequest.create(policy_ctx)
        response   = self._policy_engine.evaluate(policy_req)
        if not response.is_approved:
            raise IntegrationDispatchError(
                f"Governance rejected: {response.decision.final_action}",
                request_id=request.request_id,
            )
```

---

## Testing Patterns

```python
from iios.integration.policies import (
    IntegrationPolicyFactory, IntegrationPolicyEngine,
)

def make_engine():
    factory = IntegrationPolicyFactory()
    engine  = IntegrationPolicyEngine()
    engine.start()
    engine.load_policy(factory.create_approve_all_policy())
    return engine, factory

def make_context(factory, **kwargs):
    return factory.create_context(
        "req-test", "sess-test", "rest_api", **kwargs
    )
```

---

## Do Not

- Open any network connection from within the policy framework
- Instantiate broker/connector clients
- Call `requests`, `httpx`, `aiohttp`, `kafka-python`, `pika`, or similar
- Import from `iios.integration.engine` (avoid circular dependency)
- Perform any I/O operation inside a policy rule condition
