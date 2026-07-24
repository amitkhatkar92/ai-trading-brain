# Knowledge Governance Policy Framework

**Package:** `iios.knowledge.policies`
**Module:** C14 M3 — Enterprise Knowledge Intelligence, Phase 1

## Purpose

The Knowledge Governance Policy Framework governs all enterprise knowledge
before it is accepted into the institutional knowledge repository.

It validates governance rules for knowledge creation, classification,
retention, security, versioning, and publication.

## Responsibilities

- Load and manage versioned governance policies
- Evaluate knowledge artifacts against configurable policy rules
- Resolve conflicts across multiple policy decisions
- Generate explainable governance decisions
- Produce complete, auditable evaluation trails
- Emit structured events for every governance action

## What it does NOT do

- Knowledge reasoning (M4)
- Semantic search or embedding generation (M4)
- Vector indexing or retrieval (M4)
- LLM inference (M4)

## Primary Interface

```python
from iios.knowledge.policies import (
    KnowledgeGovernancePolicyEngine,
    KnowledgePolicyFactory,
    PolicyAction,
    PolicyType,
    PolicyDomain,
)

# Create the engine
engine = KnowledgeGovernancePolicyEngine()
engine.start()

# Register a policy
factory = KnowledgePolicyFactory()
policy  = factory.create_policy(
    "Classification Governance",
    PolicyType.CLASSIFICATION,
    PolicyDomain.CLASSIFICATION,
)
engine.register_policy(policy)

# Evaluate
request  = factory.create_request("run-001", "execution_intelligence")
response = engine.evaluate(request)

print(response.decision)   # GovernanceDecision.APPROVED
print(response.is_approved)  # True
```

## Integration with M2 Knowledge Engine

```python
from iios.knowledge.engine import KnowledgeEngine

governance = KnowledgeGovernancePolicyEngine()
governance.start()

knowledge_engine = KnowledgeEngine(
    governance_delegate=governance.governance_delegate,
)
knowledge_engine.start()
```

## File Map

| File | Purpose |
|---|---|
| `knowledge_policy_engine.py` | Primary façade |
| `knowledge_policy_manager.py` | 6-phase workflow (NEVER RAISES) |
| `knowledge_policy_registry.py` | Thread-safe policy store |
| `knowledge_policy.py` | Policy domain object |
| `knowledge_policy_rule.py` | Governance rule |
| `knowledge_policy_condition.py` | Atomic condition |
| `knowledge_policy_evaluator.py` | Per-policy evaluator |
| `knowledge_policy_priority.py` | Cross-policy conflict resolver |
| `knowledge_policy_chain.py` | Policy chain |
| `knowledge_policy_validator.py` | Structural validation |
| `knowledge_policy_context.py` | Evaluation context |
| `knowledge_policy_request.py` | Request value object |
| `knowledge_policy_response.py` | Response value object |
| `knowledge_policy_result.py` | Rule and policy results |
| `knowledge_policy_audit.py` | Audit trail |
| `knowledge_policy_statistics.py` | 8-counter statistics |
| `knowledge_policy_history.py` | Evaluation history |
| `knowledge_policy_events.py` | Events + bus |
| `knowledge_policy_factory.py` | Factory |
| `constants.py` | Enums and defaults |
| `exceptions.py` | KGP error hierarchy |
| `__init__.py` | Public API |
