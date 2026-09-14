# Subsystem Workflow Guide

## Full Evaluation Workflow

```
ExecutionRiskIntegrationManager.evaluate(request)
          │
          ▼
ExecutionRiskIntegrationEngine.evaluate(request)
          │
          ├─ 1. IntegrationValidator.validate_request()
          │         └─ failure → blocked ExecutionRiskResponse (validation_passed=False)
          │
          ├─ 2. emit EVALUATION_REQUESTED event
          │
          ├─ 3. _build_m2_request()
          │         └─ maps ExecutionRiskRequest → EvaluationRequest
          │
          ├─ 4. M2 RiskEngine.evaluate(m2_request)
          │         └─ failure (succeeded=False) → fallback blocked response
          │
          ├─ 5. map M2 RuleOutcome → risk_state
          │         PASSED  → "PASSED"
          │         WARNING → "WARNING"
          │         BLOCKED → "BLOCKED"
          │         ERROR   → "BLOCKED"
          │         SKIPPED → "PASSED"
          │
          ├─ 6. M4 RiskControlManager.evaluate_rule_results()
          │         └─ returns RiskControlDecision (action, policy_used, reason)
          │
          ├─ 7. _build_lifecycle_proxy()
          │         └─ SimpleNamespace satisfying M5 SnapshotBuilder.with_lifecycle()
          │
          ├─ 8. M5 SnapshotBuilder.build()
          │         └─ immutable ExecutionRiskSnapshot
          │
          ├─ 9. M5 SnapshotRegistry.register() + .publish()
          │         └─ snapshot status → PUBLISHED
          │
          ├─ 10. build ExecutionRiskResponse
          │          approved = action in {"ALLOW", "ALLOW_WITH_WARNING"}
          │
          ├─ 11. update IntegrationStatistics
          │
          ├─ 12. append to IntegrationHistory
          │
          └─ 13. emit EVALUATION_COMPLETED + SNAPSHOT_PUBLISHED events

```

## Component Ownership

```
ExecutionRiskIntegrationEngine
    owns M2 RiskEngine              (rule evaluation)
    owns M4 RiskControlManager      (control decisions)
    owns M5 SnapshotRegistry        (snapshot storage & publication)
    owns ComponentRegistry          (health introspection)
    owns IntegrationHistory         (response log)
    owns IntegrationStatistics      (counters)

    does NOT own M1 ExecutionRisk lifecycle  ← managed by M2 internally
    does NOT own M3 BaseRule instances       ← registered externally
```

## Lifecycle proxy pattern

M5 SnapshotBuilder requires a lifecycle object with a `.state.value` attribute.
The integration engine creates a `SimpleNamespace` proxy:

```python
SimpleNamespace(
    risk_id=...,
    state=SimpleNamespace(value=risk_state),   # e.g. "PASSED"
    risk_category=SimpleNamespace(value="EXECUTION"),
    execution_id=..., order_id=..., ...
)
```

This avoids a hard dependency on M1 at the integration layer.

## M2 → M4 data flow

M2 returns `EvaluationResult.rule_results: Tuple[RuleResult, ...]`.
These are passed directly to M4 `evaluate_rule_results()`.
M4 applies the configured policy (default: `HIGHEST_SEVERITY`) and returns a
`RiskControlDecision` with an `action` and `reason`.

## Decision mapping

| M4 ControlAction | `approved` | Notes |
|---|---|---|
| ALLOW | True | — |
| ALLOW_WITH_WARNING | True | `has_warnings=True` on response |
| RETRY | False | upstream should retry |
| PAUSE | False | circuit breaker triggered |
| REQUIRE_OVERRIDE | False | `was_overridden` checked on override info |
| CANCEL | False | order cancelled |
| BLOCK | False | hard block |
| EMERGENCY_STOP | False | `is_emergency=True`; risk_state forced to BLOCKED |
