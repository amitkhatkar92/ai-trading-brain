# Execution Risk Lifecycle

**IIOS C6 Execution Intelligence — Phase 4, Module 1**

---

## Overview

The Execution Risk Lifecycle module defines the **lifecycle** of a single execution risk evaluation within the IIOS platform.

This module is responsible for **one thing only**: tracking the states an execution risk evaluation passes through, from creation to archival.

---

## What It Is

- A strict institutional-grade state machine for execution risk evaluations
- An immutable transition and history ledger
- A thread-safe registry for managing active evaluations
- A factory for creating evaluations with validated inputs
- A validator for checking lifecycle invariants

## What It Is Not

- Not a risk scoring engine
- Not a risk rules engine
- Not a portfolio risk manager
- Not a broker interface
- Not an order executor

---

## Package Structure

```
iios/execution/risk/lifecycle/
├── constants.py                  — States, categories, events, transitions, IDs
├── exceptions.py                 — Error hierarchy (ERL-000 to ERL-007)
├── execution_risk.py             — Core domain object
├── execution_risk_state.py       — Immutable state occupancy record
├── execution_risk_transition.py  — Immutable transition record
├── execution_risk_event.py       — Immutable domain events + factories
├── execution_risk_history.py     — Bounded append-only history
├── execution_risk_statistics.py  — Mutable statistics accumulator
├── execution_risk_context.py     — Immutable request-scoped context
├── execution_risk_metadata.py    — Mutable annotation store
├── execution_risk_validation.py  — Stateless validator
├── execution_risk_factory.py     — Stateless factory
├── execution_risk_registry.py    — LifecycleAwareMixin registry
└── __init__.py                   — Public API
```

---

## Risk States

| State              | Meaning                                         |
|--------------------|-------------------------------------------------|
| CREATED            | Evaluation created, not yet queued              |
| PENDING_EVALUATION | Queued for evaluation                           |
| EVALUATING         | Evaluation in progress                          |
| PASSED             | Evaluation passed; execution may proceed        |
| WARNING            | Passed with warnings; proceed with caution      |
| BLOCKED            | Evaluation blocked execution                    |
| OVERRIDDEN         | Block or pass was manually overridden           |
| EXPIRED            | Evaluation expired before completion            |
| FAILED             | Evaluation encountered an error                 |
| ARCHIVED           | Terminal state; lifecycle complete              |

---

## Risk Categories

| Category      | Description                        |
|---------------|------------------------------------|
| EXPOSURE      | Position exposure limits           |
| MARGIN        | Margin availability                |
| LIQUIDITY     | Market liquidity adequacy          |
| CONCENTRATION | Portfolio concentration limits     |
| ORDER_SIZE    | Order quantity limits              |
| PRICE         | Price deviation checks             |
| EXECUTION     | Execution feasibility              |
| COMPLIANCE    | Regulatory compliance checks       |
| OPERATIONAL   | Operational risk controls          |

---

## Quick Start

```python
from iios.execution.risk.lifecycle import (
    RiskFactory,
    RiskRegistry,
    RiskState,
    RiskCategory,
)

# Create a risk evaluation
factory = RiskFactory()
risk = factory.create_exposure_risk(
    execution_id="exec-001",
    portfolio_id="portfolio-A",
    strategy_id="momentum-v2",
    order_id="ord-001",
)

# Drive through the lifecycle
risk.transition_to(RiskState.PENDING_EVALUATION)
risk.transition_to(RiskState.EVALUATING)
risk.transition_to(RiskState.PASSED, evaluation_time_ms=4.2)
risk.transition_to(RiskState.ARCHIVED)

# Register in a registry
registry = RiskRegistry()
registry.start()
registry = RiskFactory().create_exposure_risk(...)
registry.register(risk)
registry.notify_transition(risk, RiskState.PASSED)
stats = registry.statistics()
print(stats.evaluations_passed)  # 1
```

---

## Domain Events

| Event                    | Triggered on transition to |
|--------------------------|----------------------------|
| RISK_CREATED             | CREATED (factory event)    |
| RISK_EVALUATION_STARTED  | EVALUATING                 |
| RISK_PASSED              | PASSED                     |
| RISK_WARNING             | WARNING                    |
| RISK_BLOCKED             | BLOCKED                    |
| RISK_OVERRIDDEN          | OVERRIDDEN                 |
| RISK_EXPIRED             | EXPIRED                    |
| RISK_ARCHIVED            | ARCHIVED                   |

---

## Error Codes

| Code    | Exception                     | Trigger                        |
|---------|-------------------------------|--------------------------------|
| ERL-000 | ExecutionRiskLifecycleError   | Base exception                 |
| ERL-001 | InvalidRiskTransitionError    | Disallowed state transition    |
| ERL-002 | RiskNotFoundError             | risk_id not in registry        |
| ERL-003 | DuplicateRiskError            | risk_id already registered     |
| ERL-004 | RiskValidationError           | Validation invariant violated  |
| ERL-005 | RiskRegistryCapacityError     | Registry at max capacity       |
| ERL-006 | RiskRegistryNotRunningError   | Registry not started           |
| ERL-007 | RiskStateError                | Unexpected state encountered   |

---

## Future Modules

| Module | Responsibility                          |
|--------|-----------------------------------------|
| M2     | Risk Engine — evaluation orchestration  |
| M3     | Risk Rules — configurable rule sets     |
| M4     | Risk Controls — enforcement actions     |
| M5     | Risk Snapshot — point-in-time capture   |
| M6     | Risk Integration — public facade        |
