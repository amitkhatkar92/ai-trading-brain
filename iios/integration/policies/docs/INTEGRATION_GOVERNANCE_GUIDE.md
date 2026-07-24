# Integration Governance Guide

**Module:** C15 M3 — Integration Governance Policy Framework

---

## Governance Model

Every enterprise integration passes through the IGPF before execution.
The engine evaluates governance policies against the integration context
and produces a `GovernanceDecision` that permits or blocks the integration.

### Governance Pipeline

```
IntegrationPolicyRequest
        │
        ▼
 ┌─────────────────────────┐
 │  load_policies          │  Load all registered policies
 │  validate_configuration │  Validate policy config (7 checks)
 │  evaluate_rules         │  Run all rule conditions against context
 │  resolve_conflicts      │  Apply conflict resolution strategy
 │  apply_priorities       │  Order by policy priority
 │  generate_decision      │  Produce GovernanceDecision
 │  generate_audit         │  Record IntegrationAuditEntry
 └─────────────────────────┘
        │
        ▼
 IntegrationPolicyResponse
```

---

## Engine States

| State | Description |
|-------|-------------|
| Not started | `is_ready = False`. `evaluate()` raises `PolicyEngineNotReadyError` |
| Ready | `is_ready = True`. Accepts evaluation requests |
| Stopped | `is_ready = False` again. Cannot evaluate |

---

## Policy Actions (8)

| Action | Effect |
|--------|--------|
| `APPROVE` | Integration is permitted |
| `APPROVE_WITH_CONDITIONS` | Integration permitted with attached conditions |
| `REJECT` | Integration is denied |
| `BLOCK` | Integration is hard-blocked |
| `ESCALATE` | Route to human review |
| `REQUIRE_MANUAL_REVIEW` | Pause for manual assessment |
| `REQUIRE_SECURITY_APPROVAL` | Requires security team sign-off |
| `EMERGENCY_STOP` | Immediate halt; no override |

---

## Conflict Resolution Rules

When multiple policies produce conflicting actions, the framework resolves
the conflict using the **MOST_RESTRICTIVE** strategy by default:

```
EMERGENCY_STOP  > BLOCK  > REJECT  > REQUIRE_SECURITY_APPROVAL
    > REQUIRE_MANUAL_REVIEW  > ESCALATE  > APPROVE_WITH_CONDITIONS
    > APPROVE
```

Alternative strategies: `MOST_PERMISSIVE`, `CRITICAL_OVERRIDES_ALL`,
`EMERGENCY_STOP_OVERRIDES_ALL`, `PRIORITY_WINS`.

---

## Governance Decision

```python
decision = response.decision
print(decision.final_action)   # PolicyAction.APPROVE
print(decision.approved)       # True
print(decision.conditions)     # additional conditions if APPROVE_WITH_CONDITIONS
print(decision.reasons)        # reasons from blocking policies
print(decision.policy_results) # per-policy IntegrationPolicyResult objects
```

---

## Error Codes

| Code | Exception | Description |
|------|-----------|-------------|
| IPG-000 | `IntegrationPolicyError` | Base exception |
| IPG-001 | `PolicyEngineNotReadyError` | Engine not started |
| IPG-002 | `PolicyNotFoundError` | Policy ID not in registry |
| IPG-003 | `PolicyRuleError` | Invalid or inconsistent rule |
| IPG-004 | `PolicyConditionError` | Invalid condition |
| IPG-005 | `PolicyValidationError` | Policy failed validation |
| IPG-006 | `PolicyConflictError` | Unresolvable policy conflict |
| IPG-007 | `PolicyEvaluationError` | Evaluation pipeline failure |
| IPG-008 | `PolicyRegistrationError` | Registry at capacity |
| IPG-009 | `PolicyChainError` | Chain construction/execution error |

---

## Governance Event Flow

```
GOVERNANCE_STARTED
       │
       ├─ POLICY_LOADED (per policy)
       │
       ├─ POLICY_VALIDATED (per policy)
       │
       └─ (one of)
             INTEGRATION_APPROVED
             INTEGRATION_REJECTED
             INTEGRATION_BLOCKED
             SECURITY_APPROVAL_REQUESTED
             EMERGENCY_STOP_TRIGGERED
                   │
                   ▼
          GOVERNANCE_COMPLETED
```
