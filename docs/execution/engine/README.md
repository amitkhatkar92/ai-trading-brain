# Execution Engine — Package README

**Package path:** `iios/execution/engine/`
**Version:** 1.0.0
**IIOS Component:** C6 Execution Intelligence — Phase 1, Module 2

---

## Purpose

The Execution Engine coordinates the **execution workflow** for a single
`ExecutionRequest`. It drives each request through a well-defined state machine
(IDLE → VALIDATING → PREPARING → READY → EXECUTING → COMPLETED) and produces an
`ExecutionResult` and `ExecutionSnapshot` for downstream consumption.

**This engine does NOT:**
- Communicate with brokers or exchanges
- Place, route, or modify real orders
- Implement execution algorithms (TWAP, VWAP, etc.)
- Access market data

**This engine DOES:**
- Validate the execution request and resolved context
- Advance the associated M1 `Order` to `PENDING_SUBMISSION`
- Build the `ExecutionContext` (resolution of order, portfolio, decision, strategy)
- Publish `ExecutionSnapshot` events at each phase
- Return a deterministic `ExecutionResult`

---

## Package Structure

```
iios/execution/engine/
├── __init__.py              # Public API — all exports
├── constants.py             # System IDs, enums, bounds
├── exceptions.py            # Exception hierarchy (EX-000 … EX-010)
├── execution_state.py       # EngineExecutionState + VALID_ENGINE_TRANSITIONS
├── execution_request.py     # ExecutionRequest — input contract
├── execution_context.py     # ExecutionContext — resolved, immutable context
├── execution_result.py      # ExecutionResult — final outcome record
├── execution_snapshot.py    # ExecutionSnapshot — point-in-time state capture
├── execution_events.py      # ExecutionEvent + ExecutionEventType
├── execution_history.py     # ExecutionHistory — per-execution transition log
├── execution_statistics.py  # ExecutionStatistics + EngineStatistics
├── execution_validation.py  # ExecutionValidator — stateless validation
├── execution_factory.py     # ExecutionFactory — creates requests and contexts
├── execution_registry.py    # ExecutionRegistry — thread-safe record store
├── execution_engine.py      # ExecutionEngine — main entry point
└── execution_manager.py     # ExecutionManager — facade over engine + registry
```

---

## Quick Start

```python
from iios.execution.engine import (
    ExecutionManager, ExecutionMode,
)
from iios.execution.lifecycle import OrderRegistry, OrderFactory, OrderContext, OrderSide
from decimal import Decimal

# ── Set up M1 Order Lifecycle ─────────────────────────────────────
order_registry = OrderRegistry()
order_registry.start()

factory   = OrderFactory()
order_ctx = OrderContext(strategy_id="STRAT-001", portfolio_id="PORT-001",
                         decision_id="DEC-001", workflow_id="WF-001")
order = factory.create_market_order(
    context=order_ctx, instrument="RELIANCE", exchange="NSE",
    side=OrderSide.BUY, quantity=Decimal("100"),
)
order_registry.register(order)

# Advance to VALIDATED (normally done by validator component)
from iios.execution.lifecycle import OrderState
order_registry.apply_transition(order.order_id, OrderState.VALIDATED,
                                 reason="validated", actor="validator")

# ── Submit to Execution Engine ────────────────────────────────────
manager = ExecutionManager()
manager.start()

request = manager.create_request(
    order_id     = order.order_id,
    decision_id  = "DEC-001",
    portfolio_id = "PORT-001",
    strategy_id  = "STRAT-001",
)

result = manager.submit(request, order_registry=order_registry)

print(f"Succeeded:   {result.succeeded}")          # True
print(f"Final state: {result.final_state.value}")  # COMPLETED
print(f"Duration:    {result.duration_ms:.1f} ms")
print(f"Order state: {order.state.value}")          # PENDING_SUBMISSION

manager.stop()
order_registry.stop()
```

---

## Key Concepts

| Concept | Class | Notes |
|---|---|---|
| Engine state machine | `EngineExecutionState`, `VALID_ENGINE_TRANSITIONS` | 9 states; COMPLETED/FAILED/CANCELLED are terminal |
| Input | `ExecutionRequest` | Identifiers, mode, priority, expiry |
| Resolved context | `ExecutionContext` | Order + intelligence snapshots (immutable) |
| Final outcome | `ExecutionResult` | succeeded / failed / cancelled |
| Point-in-time capture | `ExecutionSnapshot` | Published at READY and terminal states |
| Event | `ExecutionEvent` | Dispatched at every significant state change |
| Transition log | `ExecutionHistory` | Append-only, thread-safe |
| Per-execution metrics | `ExecutionStatistics` | Phase durations, outcome |
| Engine-wide metrics | `EngineStatistics` | Success rate, avg times |
| Validation | `ExecutionValidator` | Stateless; request, context, and transition |
| Factory | `ExecutionFactory` | Creates requests and contexts |
| Registry | `ExecutionRegistry` | Thread-safe store of `ExecutionRecord` objects |
| Main engine | `ExecutionEngine` | Drives the state machine |
| Facade | `ExecutionManager` | Owns engine lifetime; preferred entry point |

---

## Error Codes

| Code | Exception | When raised |
|---|---|---|
| EX-000 | `ExecutionEngineError` | Generic engine error |
| EX-001 | `ExecutionRequestError` | Malformed request |
| EX-002 | `ExecutionValidationError` | Validation failure |
| EX-003 | `ExecutionPreparationError` | Context assembly failure |
| EX-004 | `ExecutionRegistryError` | Registry operation failure |
| EX-005 | `ExecutionNotFoundError` | Unknown execution_id |
| EX-006 | `DuplicateExecutionError` | Duplicate execution_id |
| EX-007 | `ExecutionCapacityError` | max_executions reached |
| EX-008 | `ExecutionEngineNotRunningError` | Engine not started |
| EX-009 | `ExecutionStateError` | Invalid state transition |
| EX-010 | `ExecutionCancelledError` | Execution was cancelled |

---

## Thread Safety

`ExecutionRegistry` and `ExecutionEngine` are fully thread-safe:

- All mutations hold `threading.RLock`.
- Event listeners are dispatched **outside** the registry lock.
- `ExecutionHistory` and `ExecutionStatistics` carry their own `threading.Lock`.

---

## Tests

```
tests/unit/iios/execution/engine/test_execution_engine.py
```

15 test classes, 121 test cases.

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/iios/execution/engine/ -v --tb=short
```

---

## Related Documentation

- [EXECUTION_GUIDE.md](EXECUTION_GUIDE.md) — All 9 states, transition rules, validation, statistics
- [STATE_DIAGRAM.md](STATE_DIAGRAM.md) — Mermaid state diagram
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — IIOS conventions, how to extend, C6 lock manifest

---

## Integration Map

```
Decision Layer
    ↓
ExecutionRequest  ──→  ExecutionEngine  ──→  ExecutionResult
                           │
                    ┌──────┴──────┐
               OrderRegistry   PortfolioIntelligenceSnapshot
               (M1 Lifecycle)  DecisionSnapshot
                           │   StrategySnapshot
                    ┌──────┴──────┐
               ExecutionContext
                    │
               ExecutionSnapshot ──→ Listeners (Monitoring, Broker Adapter)
```
