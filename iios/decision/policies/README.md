# Decision Policy Framework

**C9 Decision Intelligence — Phase 1, Module 3**

Package: `iios.decision.policies`

---

## Purpose

The Decision Policy Framework evaluates every institutional decision
against configurable enterprise policies and determines whether the
decision is:

| Action | Meaning |
|--------|---------|
| `APPROVE` | Decision passes all policies |
| `APPROVE_WITH_CONDITIONS` | Approved subject to listed conditions |
| `REJECT` | Decision violates one or more policies |
| `BLOCK` | Hard stop — must not proceed |
| `ESCALATE` | Route to human review immediately |
| `DEFER` | Delay decision pending external information |
| `REQUIRE_MANUAL_REVIEW` | Manual approval required before proceeding |

**This framework performs NO optimisation, NO execution, and NO broker
communication.**

---

## Architecture

```
DecisionPolicyEngine          ← primary public interface (LifecycleAwareMixin)
  │
  ├── DecisionPolicyRegistry  ← thread-safe policy store (RLock)
  ├── DecisionPolicyManager   ← orchestration workflow
  │     ├── DecisionPolicyChain     ← sequential / parallel / weighted evaluation
  │     ├── DecisionPolicyEvaluator ← safe single-policy wrapper
  │     ├── DecisionPolicyValidator ← structural validation (6 checks)
  │     └── PolicyPriorityResolver  ← conflict resolution
  ├── DecisionPolicyStatistics ← 8 thread-safe counters
  ├── DecisionPolicyHistory    ← bounded event / response history
  └── DecisionPolicyFactory   ← stateless object factory

PolicyFrameworkAdapter        ← M2 PolicyFrameworkProtocol bridge
```

---

## Policy Types (15)

`RISK` · `COMPLIANCE` · `CAPITAL` · `EXPOSURE` · `POSITION` · `PORTFOLIO` ·
`MARKET` · `LIQUIDITY` · `VOLATILITY` · `TRADING_SESSION` · `INFRASTRUCTURE` ·
`OPERATIONAL` · `RECOVERY` · `MONITORING` · `ENTERPRISE_GOVERNANCE`

## Policy Priority (IntEnum)

| Value | Priority |
|-------|----------|
| 1 | CRITICAL |
| 2 | HIGH |
| 3 | MEDIUM |
| 4 | LOW |
| 5 | INFORMATIONAL |

Lower integer = higher urgency = evaluated first.

## Conflict Resolution Strategies

| Strategy | Behaviour |
|----------|-----------|
| `EXPLICIT_DENY_OVERRIDES` | BLOCK > REJECT > ESCALATE > APPROVE |
| `HIGHEST_PRIORITY_WINS`   | Winning policy = lowest priority integer |
| `ESCALATION_OVERRIDES`    | ESCALATE always wins non-deny outcomes |

## Chain Modes

| Mode | Behaviour |
|------|-----------|
| `SEQUENTIAL`  | Evaluate in priority order; stop on BLOCK |
| `PARALLEL`    | Evaluate all; collect all results |
| `WEIGHTED`    | Evaluate all; carry policy weights to resolver |
| `COMPOSITE`   | Reserved (alias for PARALLEL in M3) |
| `NESTED`      | Reserved (alias for PARALLEL in M3) |
| `CONDITIONAL` | Reserved (alias for PARALLEL in M3) |

---

## Quick Start

```python
from iios.decision.policies import (
    DecisionPolicyEngine, PolicyType, PolicyAction, PolicyPriority,
    PolicyConditionOperator, PolicyChainMode, ConflictResolutionStrategy,
)

# 1. Start engine
engine  = DecisionPolicyEngine()
engine.start()
factory = engine.factory()

# 2. Define a condition
cond = factory.create_condition(
    "high_risk",
    "inputs.risk_score",
    PolicyConditionOperator.GT,
    80,
)

# 3. Define a rule
rule = factory.create_rule("block_high_risk", [cond], PolicyAction.BLOCK)

# 4. Define a policy
policy = factory.create_policy(
    "RiskThreshold",
    PolicyType.RISK,
    PolicyPriority.CRITICAL,
    PolicyAction.APPROVE,      # default_action when no rule triggers
    rules=[rule],
)

# 5. Register
engine.register_policy(policy)

# 6. Evaluate a decision
ctx  = factory.create_context(
    request_id="req-001", decision_id="dec-001",
    inputs={"risk_score": 92},
)
req  = factory.create_request(
    ctx,
    chain_mode        = PolicyChainMode.SEQUENTIAL,
    conflict_strategy = ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES,
)
resp = engine.evaluate(req)

print(resp.action)          # PolicyAction.BLOCK
print(resp.is_blocked)      # True
print(resp.audit_report)    # full PolicyAuditReport

engine.stop()
```

---

## M2 Integration

```python
from iios.decision.policies import PolicyFrameworkAdapter

adapter = PolicyFrameworkAdapter(engine)
# Inject into M2 DecisionDispatcher:
dispatcher.register_framework("policy", adapter)
```

The adapter implements M2's `PolicyFrameworkProtocol`:

```python
def evaluate(self, context: DecisionEngineContext, inputs: Dict) -> Dict:
    ...
    return {
        "action":                   str,
        "is_approved":              bool,
        "is_rejected":              bool,
        "is_blocked":               bool,
        "evaluation_time_s":        float,
        "conditions":               list[str],
        "total_policies_evaluated": int,
        "error":                    str | None,
        "response_id":              str,
    }
```

---

## Runtime Statistics (8 counters)

```python
stats = engine.statistics().snapshot()
# {
#   "policies_evaluated":         int,
#   "policies_approved":          int,
#   "policies_rejected":          int,
#   "policies_blocked":           int,
#   "policies_escalated":         int,
#   "average_evaluation_time_s":  float,  # EMA α=0.1
#   "policy_coverage":            float,  # 0.0 – 1.0
#   "evaluation_throughput":      int,    # completions in last 60 s
# }
```

---

## Validation (6 checks)

| Code | Description |
|------|-------------|
| `POLICY_IDENTITY`    | `policy_id` and `name` are non-empty |
| `RULE_CONSISTENCY`   | Every rule has at least one condition |
| `CONDITION_VALIDITY` | Every condition has a non-empty `field_path` |
| `PRIORITY_INTEGRITY` | Priority is a recognised `PolicyPriority` value |
| `CONFLICT_INTEGRITY` | Policy has at least one rule or an explicit default |
| `AUDIT_COMPLETENESS` | `policy_type` and `default_action` are set |

Validation warnings are **logged but never fail** the evaluation.

---

## Events (8 types)

`POLICY_EVALUATION_STARTED` · `POLICY_LOADED` · `POLICY_VALIDATED` ·
`POLICY_APPROVED` · `POLICY_REJECTED` · `POLICY_BLOCKED` ·
`POLICY_ESCALATED` · `POLICY_EVALUATION_COMPLETED`

---

## Safety Guarantees

- **`evaluate()` never raises** on policy business-logic errors — errors
  are captured in the response's `error` field with `action=BLOCK`.
- **Thread-safe** for concurrent evaluations (Registry uses RLock,
  Statistics uses Lock, History uses Lock).
- **Zero-policy default**: when no policies are registered, the engine
  returns `APPROVE` with `total_evaluated=0`.
- **BLOCK stops sequential chains early** — ensures critical policies
  cannot be bypassed.

---

## Files

| File | Contents |
|------|---------|
| `constants.py` | All enums, constants, precedence maps |
| `exceptions.py` | DP-000 – DP-008 exception hierarchy |
| `decision_policy_condition.py` | `PolicyCondition` |
| `decision_policy_context.py` | `PolicyEvaluationContext` |
| `decision_policy_rule.py` | `PolicyRule` |
| `decision_policy_result.py` | `PolicyRuleResult`, `SinglePolicyResult`, `PolicyEvaluationSummary` |
| `decision_policy_priority.py` | `PolicyPriorityResolver` |
| `decision_policy_request.py` | `PolicyEvaluationRequest` |
| `decision_policy.py` | `DecisionPolicy` |
| `decision_policy_response.py` | `DecisionPolicyResponse` |
| `decision_policy_audit.py` | `PolicyAuditEntry`, `PolicyAuditReport`, `build_audit_report` |
| `decision_policy_events.py` | `DecisionPolicyEvent` + 8 factory functions |
| `decision_policy_statistics.py` | `DecisionPolicyStatistics` |
| `decision_policy_history.py` | `DecisionPolicyHistory` |
| `decision_policy_evaluator.py` | `DecisionPolicyEvaluator` |
| `decision_policy_validator.py` | `DecisionPolicyValidator` |
| `decision_policy_chain.py` | `DecisionPolicyChain` |
| `decision_policy_factory.py` | `DecisionPolicyFactory` |
| `decision_policy_registry.py` | `DecisionPolicyRegistry` |
| `decision_policy_manager.py` | `DecisionPolicyManager` |
| `decision_policy_engine.py` | `DecisionPolicyEngine` + `PolicyFrameworkAdapter` |
| `__init__.py` | Package exports |

---

*C9 M3 — Decision Policy Framework*
*22 source files · 167 tests · Version 1.0.0*
