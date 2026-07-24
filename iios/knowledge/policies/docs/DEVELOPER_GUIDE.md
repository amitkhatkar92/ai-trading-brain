# Knowledge Governance Policy Framework — Developer Guide

## Module Dependency Map

```
knowledge_policy_engine.py           ← primary façade (LifecycleAwareMixin)
    │
    ├── knowledge_policy_manager.py  ← 6-phase workflow (NEVER RAISES)
    │       ├── knowledge_policy_registry.py     ← active policy store
    │       ├── knowledge_policy_evaluator.py    ← per-policy evaluation
    │       ├── knowledge_policy_priority.py     ← cross-policy resolution
    │       ├── knowledge_policy_audit.py        ← audit trail
    │       ├── knowledge_policy_statistics.py   ← 8-counter metrics
    │       ├── knowledge_policy_history.py      ← evaluation history
    │       └── knowledge_policy_events.py       ← event bus
    │
    └── knowledge_policy_factory.py  ← value object factory
```

## Immutability Contract

| Object | Mutable? |
|---|---|
| `GovernancePolicyContext` | ❌ frozen dataclass |
| `KnowledgePolicyRequest` | ❌ frozen dataclass |
| `KnowledgePolicyResponse` | ❌ frozen dataclass |
| `GovernanceDecisionRecord` | ❌ frozen dataclass |
| `PolicyEvaluationResult` | ❌ frozen dataclass |
| `PolicyRuleResult` | ❌ frozen dataclass |
| `PolicyCondition` | ❌ frozen dataclass |
| `PolicyRule` | ❌ frozen dataclass |
| `ChainResult` | ❌ frozen dataclass |
| `GovernancePolicyEvent` | ❌ frozen dataclass |
| `PolicyAuditEntry` | ❌ frozen dataclass |
| `KnowledgePolicy` | ✅ mutable — status advances during lifecycle |

## Manager Never Raises

`KnowledgePolicyWorkflowManager.run_governance()` wraps the entire body
in `try/except Exception`.  All failures are captured as
`KnowledgePolicyResponse.failure(...)`.

## Error Code Table

| Code | Exception |
|---|---|
| `KGP-000` | `KnowledgeGovernanceError` (base) |
| `KGP-001` | `GovernanceNotRunningError` |
| `KGP-002` | `GovernanceValidationError` |
| `KGP-003` | `PolicyLoadError` |
| `KGP-004` | `PolicyEvaluationError` |
| `KGP-005` | `PolicyConflictError` |
| `KGP-006` | `PolicyNotFoundError` |
| `KGP-007` | `GovernanceCapacityError` |
| `KGP-008` | `AuditError` |
| `KGP-009` | `PolicyChainError` |

## Thread Safety

All stateful components use `threading.Lock()`:
- `KnowledgePolicyRegistry`
- `KnowledgePolicyAudit`
- `KnowledgeGovernanceStatistics`
- `KnowledgeGovernanceHistory`
- `GovernancePolicyEventBus`

## Logging Convention

```python
# CORRECT — f-strings only
_log.info(f"Policy registered: policy_id={policy_id!r}")

# WRONG — positional args not supported
_log.info("Policy: %s", policy_id)
```

## Adding a New Policy Type

1. Add to `PolicyType` in `constants.py`
2. Create policies of the new type using `KnowledgePolicyFactory.create_policy()`
3. Register with `engine.register_policy()`
4. No code changes required in the evaluator or manager

## Adding a New Governance Domain

1. Add to `PolicyDomain` in `constants.py`
2. Create policies with the new domain
3. The `PolicyPriorityResolver` resolves conflicts domain-agnostically
