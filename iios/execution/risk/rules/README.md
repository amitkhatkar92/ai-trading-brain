# Execution Risk Rules Framework

**C6 Execution Intelligence — Phase 4, Module 3**

## Overview

The Execution Risk Rules Framework provides a pluggable, modular system for evaluating execution-time risk. Each rule is independently testable, configurable, and can be registered or removed without modifying the framework core.

## Package Structure

```
iios/execution/risk/rules/
├── __init__.py                  # Full public API
├── constants.py                 # Enumerations, defaults, system IDs
├── exceptions.py                # All framework exceptions
├── rule_category.py             # RuleCategory enum
├── rule_priority.py             # RulePriority enum
├── rule_result.py               # RuleResult + convenience constructors
├── rule_context.py              # RuleContext + factory functions
├── rule_events.py               # RuleEvent + factory functions
├── rule_history.py              # Bounded, thread-safe result history
├── rule_statistics.py           # Per-rule + aggregate statistics
├── rule_validation.py           # RuleFrameworkValidator
├── base_rule.py                 # BaseRule ABC + RuleEngineAdapter
├── rule_registry.py             # LifecycleAwareMixin rule store
├── rule_executor.py             # Sequential / priority / conditional execution
├── rule_factory.py              # Built-in rule factory
├── rule_manager.py              # LifecycleAwareMixin high-level coordinator
└── builtin/
    ├── __init__.py              # All 12 built-in rules + ALL_BUILTIN_RULES
    ├── emergency_stop_rule.py   # SAFETY / CRITICAL
    ├── compliance_rule.py       # COMPLIANCE / CRITICAL
    ├── exposure_rule.py         # EXPOSURE / HIGH
    ├── margin_rule.py           # MARGIN / HIGH
    ├── order_size_rule.py       # EXECUTION / HIGH
    ├── daily_loss_rule.py       # OPERATIONAL / HIGH
    ├── duplicate_order_rule.py  # EXECUTION / HIGH
    ├── session_rule.py          # COMPLIANCE / HIGH
    ├── liquidity_rule.py        # LIQUIDITY / NORMAL
    ├── price_deviation_rule.py  # MARKET / NORMAL
    ├── position_limit_rule.py   # POSITION / NORMAL
    └── operational_health_rule.py # OPERATIONAL / CRITICAL
```

## Quick Start

```python
from iios.execution.risk.rules import (
    RuleManager, RuleFactory, make_rule_context, ExecutionMode
)

# 1 — Start the manager
manager = RuleManager()
manager.start()

# 2 — Register built-in rules
manager.register_all_builtins()

# 3 — Build an evaluation context
ctx = make_rule_context(
    execution_snapshot={"quantity": 100, "notional_value": 50_000.0},
    position_snapshot={"portfolio_value": 500_000.0, "daily_pnl": -1_000.0},
    risk_limits={"max_exposure_pct": 0.20},
    system_info={"system_healthy": True, "broker_connection": True},
    session_info={"session_valid": True},
)

# 4 — Evaluate
results = manager.evaluate(ctx, mode=ExecutionMode.CONDITIONAL)

# 5 — Inspect
blocked = [r for r in results if r.blocked]
if blocked:
    print("EXECUTION BLOCKED:", blocked[0].message)

# 6 — Stop
manager.stop()
```

## Rule Outcomes

| Outcome | Meaning |
|---------|---------|
| `PASS` | Rule allows execution |
| `WARNING` | Rule raises concern, execution proceeds |
| `BLOCK` | Rule blocks execution |
| `OVERRIDE_REQUIRED` | Human override needed (treated as WARNING by M2) |
| `SKIPPED` | Rule not applicable or disabled |
| `FAILED` | Rule raised an exception during evaluation |

## Execution Modes

| Mode | Behaviour |
|------|-----------|
| `SEQUENTIAL` | Rules run in registration order, all results returned |
| `PRIORITY_ORDERED` | Highest priority first, all results returned |
| `CONDITIONAL` | Priority ordered, stops at first BLOCK |

## Adding a Custom Rule

```python
from iios.execution.risk.rules import BaseRule, RuleCategory, RuleContext, RuleResult
from iios.execution.risk.rules import make_pass_result, make_block_result

class MyCustomRule(BaseRule):
    @property
    def rule_id(self) -> str:
        return "custom:my_rule_v1"

    @property
    def rule_name(self) -> str:
        return "My Custom Rule"

    def category(self) -> RuleCategory:
        return RuleCategory.EXECUTION

    def _evaluate(self, context: RuleContext) -> RuleResult:
        import time
        t0 = time.time()
        # ... your logic ...
        return make_pass_result(
            self.rule_id, self.rule_name, self.category(),
            elapsed_ms=(time.time() - t0) * 1000,
        )

# Register it
manager.register(MyCustomRule())
```

## Bridging to M2 Risk Engine

```python
from iios.execution.risk.rules import RuleEngineAdapter, MyCustomRule

# Wrap for M2 protocol compatibility
adapter = RuleEngineAdapter(MyCustomRule())
engine.register_rule(adapter)
```
