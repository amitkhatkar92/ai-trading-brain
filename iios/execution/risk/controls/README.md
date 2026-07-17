# Execution Risk Controls Framework

**C6 Execution Intelligence — Phase 4, Module 4**

## Overview

The Execution Risk Controls Framework translates pre-computed rule results
into enforceable operational actions. It **never** evaluates risk, **never**
executes orders, and **never** communicates with brokers. Its sole
responsibility is determining *what to do* after risk rules have been applied.

## Package Structure

```
iios/execution/risk/controls/
├── __init__.py                   # Full public API
├── constants.py                  # ControlAction, PolicyType, ACTION_PRIORITY
├── exceptions.py                 # Exception hierarchy (ERC-000 — ERC-008)
├── risk_control_action.py        # ControlActionMetadata + helpers
├── risk_control_context.py       # ControlContext + factory
├── risk_control_request.py       # ControlRequest + factory
├── risk_control_response.py      # ControlResponse + factories
├── risk_control_decision.py      # RiskControlDecision, OverrideInfo, EmergencyInfo
├── risk_control_policy.py        # All 6 built-in policy classes
├── risk_control_events.py        # ControlEvent + factory functions
├── risk_control_history.py       # Bounded, thread-safe decision history
├── risk_control_statistics.py    # ControlStatistics accumulator
├── risk_control_validation.py    # RiskControlValidator (stateless)
├── risk_control_registry.py      # ControlPolicyRegistry (lifecycle-aware)
├── risk_control_factory.py       # RiskControlFactory
├── risk_control_engine.py        # RiskControlEngine (lifecycle-aware)
└── risk_control_manager.py       # RiskControlManager (public facade)
```

## Quick Start

```python
from iios.execution.risk.controls import (
    RiskControlManager, PolicyType, ControlAction
)

# 1 — Start the manager (auto-registers all 5 built-in policies)
manager = RiskControlManager()
manager.start()

# 2 — Evaluate rule results (from M3)
decision = manager.evaluate_rule_results(
    rule_results=m3_rule_results,
    evaluation_id="eval-123",
    execution_id="exec-456",
)

# 3 — Act on the decision
if decision.is_emergency:
    # halt all trading
elif decision.blocked:
    # reject the order
elif decision.requires_override:
    # route to override workflow
elif decision.is_paused:
    # pause and retry later
elif decision.allowed:
    # forward to execution

# 4 — Apply authorized override
overridden = manager.apply_override(
    decision_id=decision.decision_id,
    approver="head_trader",
    reason="risk accepted at session level",
    affected_rules=["builtin:position:position_limit_v1"],
)

# 5 — Trigger emergency (bypass normal evaluation)
emergency = manager.trigger_emergency(
    "System anomaly detected",
    halt_level="FULL",
)

manager.stop()
```

## Control Actions (highest priority first)

| Action | Priority | Meaning |
|--------|----------|---------|
| `EMERGENCY_STOP` | 8 | Halt all execution immediately |
| `BLOCK` | 7 | Order rejected by risk rule |
| `CANCEL` | 6 | Order cancelled, no retry |
| `REQUIRE_OVERRIDE` | 5 | Needs authorized human approval |
| `PAUSE` | 4 | Paused pending review |
| `RETRY` | 3 | Transient condition — retry after delay |
| `ALLOW_WITH_WARNING` | 2 | Allowed, warnings recorded |
| `ALLOW` | 1 | All checks passed |

## Control Policies

| Policy | Type | Behaviour |
|--------|------|-----------|
| `SingleRulePolicy` | `SINGLE_RULE` | Any BLOCK → BLOCK. Strictest. |
| `MajorityPolicy` | `MAJORITY` | Pass fraction ≥ threshold → ALLOW |
| `HighestSeverityPolicy` | `HIGHEST_SEVERITY` | Highest-priority action wins (default) |
| `WeightedSeverityPolicy` | `WEIGHTED_SEVERITY` | Category-weighted sum of severity |
| `EmergencyPolicy` | `EMERGENCY` | Any BLOCK → EMERGENCY_STOP |
| `ConfigurablePolicy` | `CONFIGURABLE` | Wraps an arbitrary callable |

## Override Workflow

```python
# A blocked decision can be escalated for override
blocked = manager.evaluate(request)
# → decision.requires_override or decision.blocked

# Apply override (requires approver + reason)
approved = manager.apply_override(
    decision_id=blocked.decision_id,
    approver="risk_officer",
    reason="Market maker exception applied",
    new_action=ControlAction.ALLOW_WITH_WARNING,
)
```

Overrides cannot be applied to `EMERGENCY_STOP` decisions.

## Emergency Procedures

The framework supports two emergency paths:

1. **Rule-driven**: `EmergencyStopRule` in M3 produces a BLOCK outcome →
   `EmergencyPolicy` or `RiskControlEngine` converts to `EMERGENCY_STOP`
2. **Manual**: `manager.trigger_emergency(reason, halt_level=...)` bypasses
   all policy evaluation and records an immutable `EmergencyInfo`

Halt levels: `SUBSYSTEM`, `TRADING`, `FULL`.
