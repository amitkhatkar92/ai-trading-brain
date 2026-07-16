# Position Lifecycle — README

**C6 Execution Intelligence · Phase 3 · Module 1**

Package: `iios/execution/positions/lifecycle/`

---

## What this module does

The Position Lifecycle defines every valid state of a trading position from creation until archival.

It **only** manages position lifecycle state. It does not:

- Execute orders or communicate with brokers
- Calculate portfolio allocations or optimise positions
- Evaluate risk or apply risk limits
- Persist positions to any storage layer

---

## Quick start

```python
from decimal import Decimal
from iios.execution.positions.lifecycle import (
    PositionFactory,
    PositionRegistry,
    PositionState,
    PositionDirection,
    PositionProduct,
)

# 1 — Create a position
factory = PositionFactory()
position = factory.create_long(
    instrument="NIFTY50",
    exchange="NSE",
    product=PositionProduct.FUTURES,
    quantity=Decimal("100"),
    portfolio_id="port-001",
    strategy_id="momentum-v2",
)

# 2 — Drive the state machine
position.transition_to(PositionState.OPENING)
position.transition_to(PositionState.OPEN)
position.update_quantities(open_quantity=Decimal("100"), closed_quantity=Decimal("0"))
position.update_prices(avg_entry=Decimal("22500.50"))

# 3 — Register in a lifecycle registry
registry = PositionRegistry()
registry.start()
registry.register(position)

# 4 — Query
active = registry.active()          # all OPENING/OPEN/PARTIALLY_CLOSED/CLOSING
by_strat = registry.by_strategy("momentum-v2")

# 5 — Close out
position.transition_to(PositionState.CLOSING)
position.transition_to(PositionState.CLOSED)
position.update_pnl(realized=Decimal("1250.00"))
position.transition_to(PositionState.ARCHIVED)

registry.stop()
```

---

## Files

| File | Purpose |
|------|---------|
| `constants.py` | Enumerations, system IDs, state machine graph (`VALID_TRANSITIONS`) |
| `exceptions.py` | Exception hierarchy (PL-000 – PL-007) |
| `position_state.py` | `PositionStateRecord` — immutable per-state occupancy record |
| `position_transition.py` | `PositionTransition` — immutable per-transition record |
| `position_event.py` | `PositionEvent` + 7 factory functions |
| `position_history.py` | Thread-safe bounded append-only transition + state history |
| `position_statistics.py` | Mutable statistics accumulator |
| `position_context.py` | Immutable request-scoped context |
| `position_metadata.py` | Mutable key-value annotation store |
| `position_validation.py` | `PositionValidator` + `ValidationResult` |
| `position.py` | `Position` — core domain object |
| `position_factory.py` | `PositionFactory` — validated construction |
| `position_registry.py` | `PositionRegistry` — `LifecycleAwareMixin` store |
| `__init__.py` | Full public API |

---

## Tests

`tests/unit/execution/positions/test_position_lifecycle.py`

171 tests, 0 failures.
