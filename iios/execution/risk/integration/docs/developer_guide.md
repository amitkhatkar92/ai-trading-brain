# Developer Guide — Execution Risk Integration

## Adding a new risk rule (M3)

1. Subclass `iios.execution.risk.rules.BaseRule`
2. Implement `evaluate(request, context) → RuleResult`
3. Register after manager start:

```python
from iios.execution.risk.rules import BaseRule, RuleResult, RuleOutcome

class MyRule(BaseRule):
    rule_name = "my_custom_rule"

    def evaluate(self, request, context) -> RuleResult:
        if some_condition(request):
            return RuleResult(
                rule_name=self.rule_name,
                rule_category="execution",
                outcome=RuleOutcome.BLOCKED,
                message="Custom block condition met",
                elapsed_ms=0.5,
            )
        return RuleResult(
            rule_name=self.rule_name,
            rule_category="execution",
            outcome=RuleOutcome.PASSED,
            message="OK",
            elapsed_ms=0.5,
        )

manager.register_rule(MyRule())
```

## Extending ExecutionContext

`ExecutionContext` is a frozen dataclass.  Add new fields via the `metadata`
dict rather than modifying the dataclass — the dataclass signature is a
public interface and cannot be changed without a version bump.

```python
ctx = IntegrationRequestFactory.create_context(
    "EX-1", "ORD-1",
    metadata={"exchange": "NSE", "segment": "EQ"},
)
```

## Changing default policy (M4)

`RiskControlManager` is instantiated by the engine with the default policy
`HIGHEST_SEVERITY`.  To use a different policy, override
`_build_controls_manager()` in a subclass of `ExecutionRiskIntegrationEngine`:

```python
from iios.execution.risk.controls import PolicyType

class StrictEngine(ExecutionRiskIntegrationEngine):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._controls_manager = RiskControlManager(
            default_policy_type=PolicyType.MAJORITY
        )
        self._component_registry.register(ComponentType.CONTROLS, self._controls_manager)
```

## Adding a new event type

1. Add value to `IntegrationEventType` in `constants.py`
2. Add factory function in `execution_risk_events.py`
3. Call `self._emit(make_new_event(...))` at the integration engine
4. Add a test case in `TestIntegrationEvents`

## Customising evaluation modes

`EvaluationMode` is passed through in `ExecutionRiskRequest.evaluation_mode`.
The current integration engine does not change behaviour based on mode — this is
intentional.  Future M7 (Execution Gateway) may forward mode to M2/M4.

To act on mode now, inspect `request.evaluation_mode` inside a custom rule:

```python
def evaluate(self, request, context):
    if context.get("evaluation_mode") == "strict":
        ...
```

## Thread safety

`ExecutionRiskIntegrationEngine` is thread-safe.  Statistics and history
updates are guarded by `threading.RLock`.  M2, M4, M5 are independently
thread-safe.

## Testing conventions

- Use `_manager()` / `_engine()` helpers to create started instances
- Always call `.stop()` after each test (or use `try/finally`)
- Do NOT mock M2/M4/M5 for happy-path tests — use real components
- Use `SnapshotFactory.create_block_snapshot()` for direct `ExecutionRiskResponse` construction in test helpers

## Version bump procedure

1. Update `VERSION` in `constants.py`
2. Update `SYSTEM_ID` audit log messages if needed
3. Update this guide + README
4. Add changelog entry to `ARCHITECTURE.md`
