# Order Lifecycle Guide

Full reference for every state, transition rule, fill semantic, and recovery
pattern in the `iios.execution.lifecycle` package.

---

## 1. The 14 States

| State | Meaning | Active? | Terminal? |
|---|---|---|---|
| `CREATED` | Order object built; not yet validated | ✗ | ✗ |
| `VALIDATED` | Passed OrderValidator checks | ✗ | ✗ |
| `PENDING_SUBMISSION` | Queued for transmission to broker | ✓ | ✗ |
| `SUBMITTED` | Transmitted; waiting for broker ACK | ✓ | ✗ |
| `ACKNOWLEDGED` | Broker confirmed receipt; on exchange queue | ✓ | ✗ |
| `PARTIALLY_FILLED` | At least one fill; quantity remains | ✓ | ✗ |
| `FILLED` | Completely filled | ✗ | **✓** |
| `CANCEL_PENDING` | Cancel sent; waiting for exchange confirmation | ✓ | ✗ |
| `CANCELLED` | Exchange confirmed cancellation | ✗ | ✗ |
| `REJECTED` | Broker or exchange refused the order | ✗ | ✗ |
| `EXPIRED` | Time-in-force limit elapsed | ✗ | ✗ |
| `FAILED` | Unrecoverable runtime error | ✗ | ✗ |
| `RECOVERING` | Recovery protocol in progress | ✗ | ✗ |
| `RECOVERED` | Recovery succeeded; order may be resubmitted | ✗ | ✗ |

**Only `FILLED` is truly terminal.** `CANCELLED`, `REJECTED`, `EXPIRED`, and
`FAILED` all permit a `→ RECOVERING` transition, allowing automated retry logic.

---

## 2. Transition Table

```
CREATED             → VALIDATED | REJECTED | FAILED
VALIDATED           → PENDING_SUBMISSION | REJECTED | FAILED
PENDING_SUBMISSION  → SUBMITTED | CANCELLED | FAILED
SUBMITTED           → ACKNOWLEDGED | REJECTED | CANCEL_PENDING | EXPIRED | FAILED
ACKNOWLEDGED        → PARTIALLY_FILLED | FILLED | CANCEL_PENDING | REJECTED | EXPIRED | FAILED
PARTIALLY_FILLED    → PARTIALLY_FILLED | FILLED | CANCEL_PENDING | CANCELLED | EXPIRED | FAILED
CANCEL_PENDING      → CANCELLED | ACKNOWLEDGED | PARTIALLY_FILLED | FILLED | FAILED
FILLED              → (no transitions — terminal)
CANCELLED           → RECOVERING
REJECTED            → RECOVERING
EXPIRED             → RECOVERING
FAILED              → RECOVERING
RECOVERING          → RECOVERED | FAILED
RECOVERED           → PENDING_SUBMISSION | CANCELLED | FAILED
```

### Key rules

1. **`PARTIALLY_FILLED → PARTIALLY_FILLED`** is valid — each partial fill dispatches
   a new `ORDER_PARTIALLY_FILLED` event with updated fill data.

2. **`CANCEL_PENDING → ACKNOWLEDGED`** is valid — the exchange may reject the cancel
   request (e.g., the order was already matched). The order returns to active life.

3. **`CANCEL_PENDING → FILLED`** is valid — a race where the order is completely
   filled before the cancel reaches the exchange.

4. **`RECOVERED → PENDING_SUBMISSION`** — after recovery succeeds, the order is
   re-queued for submission (new broker call).

---

## 3. Fill Semantics

Fills are applied via `OrderRegistry.apply_fill(order_id, fill_qty, fill_price)`.

### Eligible states

An order must be in one of `FILL_STATES` to accept a fill:
`{ACKNOWLEDGED, PARTIALLY_FILLED, CANCEL_PENDING}`.

### Automatic state resolution

`apply_fill` determines the resulting state automatically:

| Before fill | After fill | Condition |
|---|---|---|
| ACKNOWLEDGED | PARTIALLY_FILLED | `filled_quantity < total_quantity` |
| ACKNOWLEDGED | FILLED | `filled_quantity == total_quantity` |
| PARTIALLY_FILLED | PARTIALLY_FILLED | `filled_quantity < total_quantity` |
| PARTIALLY_FILLED | FILLED | `filled_quantity == total_quantity` |
| CANCEL_PENDING | PARTIALLY_FILLED | `filled_quantity < total_quantity` |
| CANCEL_PENDING | FILLED | `filled_quantity == total_quantity` |

### Average price tracking

Each fill updates the running weighted-average price:

```
avg_price = (prev_avg × prev_filled + fill_price × fill_qty) / new_filled
```

The `Order.average_price` property reflects the running average after each fill.

### Overfill protection

`OrderValidator.validate_fill` rejects any fill where
`fill_qty > order.remaining_quantity`.  The registry raises `InvalidFillError`.

---

## 4. Recovery Pattern

Any order in `{CANCELLED, REJECTED, EXPIRED, FAILED}` can be recovered:

```python
# 1. Initiate recovery
registry.apply_transition(order_id, OrderState.RECOVERING,
                          reason="network timeout — retry", actor=ACTOR_SYSTEM)

# 2a. Recovery succeeded → re-queue for submission
registry.apply_transition(order_id, OrderState.RECOVERED,
                          reason="broker reconnected", actor=ACTOR_SYSTEM)
registry.apply_transition(order_id, OrderState.PENDING_SUBMISSION,
                          reason="resubmit after recovery", actor=ACTOR_SYSTEM)

# 2b. Recovery failed → terminal for this attempt
registry.apply_transition(order_id, OrderState.FAILED,
                          reason="recovery exhausted max retries", actor=ACTOR_SYSTEM)
```

`OrderStatistics.retry_count` increments each time an order enters `RECOVERING`.

---

## 5. Event Dispatching

After every successful `apply_transition` or `apply_fill`, the registry dispatches
an `OrderEvent` to all registered listeners.

| State entered | Event type |
|---|---|
| CREATED | `ORDER_CREATED` |
| VALIDATED | `ORDER_VALIDATED` |
| PENDING_SUBMISSION | `ORDER_PENDING` |
| SUBMITTED | `ORDER_SUBMITTED` |
| ACKNOWLEDGED | `ORDER_ACKNOWLEDGED` |
| PARTIALLY_FILLED | `ORDER_PARTIALLY_FILLED` |
| FILLED | `ORDER_FILLED` |
| CANCEL_PENDING | `ORDER_CANCEL_PENDING` |
| CANCELLED | `ORDER_CANCELLED` |
| REJECTED | `ORDER_REJECTED` |
| EXPIRED | `ORDER_EXPIRED` |
| FAILED | `ORDER_FAILED` |
| RECOVERING | `ORDER_RECOVERY_STARTED` |
| RECOVERED | `ORDER_RECOVERED` |

Listeners are called **outside** the registry lock.  A listener that raises an
exception is logged as a warning and does not interrupt other listeners.

---

## 6. Cancellation Flow

```python
# User or risk system requests cancel
registry.apply_transition(order_id, OrderState.CANCEL_PENDING,
                          reason="user requested cancel", actor=ACTOR_USER)

# Broker adapter sends cancel to exchange, then:
# — Exchange confirms: CANCEL_PENDING → CANCELLED
registry.apply_transition(order_id, OrderState.CANCELLED,
                          reason="exchange confirmed cancel", actor=ACTOR_EXCHANGE)

# — Or exchange already filled it: CANCEL_PENDING → FILLED (via apply_fill)
registry.apply_fill(order_id, remaining, fill_price)
```

---

## 7. Time-In-Force and Expiry

When the exchange rejects an order due to TIF expiry:

```python
registry.apply_transition(order_id, OrderState.EXPIRED,
                          reason="DAY order expired at market close",
                          actor=ACTOR_EXCHANGE)
```

`TimeInForce` options: `DAY`, `GTC`, `IOC`, `FOK`, `GTD`, `ATO`, `ATC`.

---

## 8. Statistics Reference

`order.statistics` is an `OrderStatistics` instance updated on every transition
and fill.

| Attribute | Type | Description |
|---|---|---|
| `fill_pct` | float | `filled_quantity / total_quantity × 100` |
| `partial_fill_count` | int | Number of `PARTIALLY_FILLED` events |
| `submitted_at` | float? | `time.time()` of `SUBMITTED` transition |
| `acknowledged_at` | float? | `time.time()` of `ACKNOWLEDGED` transition |
| `first_fill_at` | float? | Timestamp of first fill |
| `filled_at` | float? | Timestamp of final fill |
| `execution_time_sec` | float? | `filled_at − submitted_at` |
| `retry_count` | int | Times entered `RECOVERING` |
| `cancellation_count` | int | Times entered `CANCEL_PENDING` |
| `failure_count` | int | Times entered `FAILED` |
| `rejection_count` | int | Times entered `REJECTED` |
| `state_durations` | dict[str, float] | Seconds spent in each completed state |
