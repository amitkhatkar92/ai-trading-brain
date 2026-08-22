# EXECUTION FEEDBACK BRIDGE

**Purpose:** Connect execution outcomes back into OIOS without allowing OIOS to
influence execution decisions.

**Constraint:** Shadow Mode only. OIOS is a passive observer. No signal, threshold,
risk parameter, or position decision is affected by this bridge.

---

## Overview

The OIOS (Opportunity Intelligence & Observation System) tracks market
opportunities as they evolve through `DISCOVERED → ACTIVE → WATCHING → INVALID`.
Until this bridge, the OIOS `opportunities` table had `position_exists = 0` for
every row because the execution system never reported trade state back to OIOS.
That made OIOS position fields useless for learning.

This bridge closes the loop — in read-only shadow mode.

---

## Architecture Diagram

```
                                    ┌─────────────────────────────────────┐
   OrderManager                     │         EventBus (singleton)         │
  ──────────────────                │                                       │
  close_position()                  │  ORDER_PLACED ──────────────────────►│
      │                             │                                       │
      ├──► POSITION_CLOSED ────────►│  POSITION_CLOSED ───────────────────►│
      │    (new, fire-and-forget)   │                                       │
      │                             └──────────────┬──────────────────────┘
      │                                            │
      ▼                                            ▼
  paper_trades.csv              ExecutionFeedbackBridge  (oios/execution_bridge.py)
  (unchanged)                         │           │
                                      │           │
                               _on_trade_opened() │  _on_trade_closed()
                                      │           │
                                      ▼           ▼
                               ┌──────────────────────────────────┐
                               │  data/market_behavior.db          │
                               │  (OIOS DB)                        │
                               │                                   │
                               │  opportunities                    │
                               │    position_exists  ← updated     │
                               │    position_size_pct ← updated    │
                               │    position_open_date ← updated   │
                               │    trade_pnl_pct  ← updated       │
                               │                                   │
                               │  execution_trade_links  (NEW)     │
                               │    order_id → opportunity_id      │
                               └──────────────────────────────────┘
```

---

## Component Inventory

| File | Role | New / Modified |
|---|---|---|
| `communication/events.py` | Added `POSITION_CLOSED = "execution.position.closed"` | Modified |
| `execution_engine/order_manager.py` | `close_position()` now publishes `POSITION_CLOSED` to EventBus | Modified |
| `oios/execution_bridge.py` | `ExecutionFeedbackBridge` class + module singleton | **New** |
| `orchestrator/master_orchestrator.py` | `_setup_eda()` wires the bridge | Modified |

---

## Event Flow

### Trade Open (ORDER_PLACED)

```
Orchestrator._run_debate_and_decide()
    → OrderManager.place_order() returns order record
    → bus.publish(ORDER_PLACED, payload={order_id, symbol, direction, entry_price,
                                         quantity, strategy, stop_loss, target_price,
                                         confidence, rr})

ExecutionFeedbackBridge._on_trade_opened(event)
    1. Extract order_id, symbol, direction ("BUY"/"SELL"), entry_price, quantity
    2. Map direction to OIOS convention:  BUY→LONG,  SELL/SHORT→SHORT
    3. Query: find OIOS opportunity matching (symbol, direction) in state
              ACTIVE > WATCHING > DISCOVERED  (most mature wins)
    4. If found:
         UPDATE opportunities
            SET position_exists    = 1,
                position_size_pct  = (qty * entry) / total_capital * 100,
                position_open_date = today,
                last_updated_at    = now
    5. INSERT OR IGNORE execution_trade_links
         (order_id, opportunity_id, symbol, direction_exec, direction_oios,
          entry_price, linked_at)
    6. Cache: _order_opp_map[order_id] = opportunity_id
```

### Trade Close (POSITION_CLOSED)

```
OrderManager.close_position(order_id, exit_price, reason)
    → existing logic (journal, notifier) unchanged
    → bus.publish(POSITION_CLOSED, payload={order_id, symbol, direction,
                                             entry_price, exit_price, quantity,
                                             pnl, pnl_pct, strategy, close_reason})

ExecutionFeedbackBridge._on_trade_closed(event)
    1. Extract order_id, pnl, pnl_pct, close_reason
    2. Resolve opportunity_id:
         a. _order_opp_map (in-memory, fastest)
         b. execution_trade_links DB lookup (survives restart)
         c. Live find_opportunity(symbol, direction) (fallback for pre-bridge trades)
    3. If opportunity found:
         UPDATE opportunities
            SET position_exists = 0,
                trade_pnl_pct   = pnl_pct,
                last_updated_at = now
    4. UPDATE execution_trade_links SET close_reason, realized_pnl, pnl_pct
    5. Pop order_id from _order_opp_map
```

---

## close_reason Mapping

Execution system reasons are normalized before storage:

| Raw `close_reason` | Stored as |
|---|---|
| `SL_HIT` / `sl_hit` | `STOP_LOSS_HIT` |
| `TARGET_HIT` / `target_hit` | `TARGET_HIT` |
| `REPLACEMENT` | `TRADE_CLOSED` |
| `SYSTEM_CLEANUP` | `SYSTEM_CLEANUP` |
| `emergency_close` | `TRADE_CLOSED` |
| `manual` | `MANUAL_EXIT` |
| `CARRY_EXPIRED` | `TRADE_CLOSED` |
| *(anything else)* | `TRADE_CLOSED` |

---

## New DB Table: `execution_trade_links`

Created at bridge startup (`CREATE TABLE IF NOT EXISTS`) in
`data/market_behavior.db` (the OIOS database).

```sql
CREATE TABLE IF NOT EXISTS execution_trade_links (
    order_id        TEXT    PRIMARY KEY,
    opportunity_id  TEXT,                    -- NULL if no OIOS match
    symbol          TEXT    NOT NULL,
    direction_exec  TEXT    NOT NULL,        -- BUY / SELL
    direction_oios  TEXT    NOT NULL,        -- LONG / SHORT
    entry_price     REAL    NOT NULL,
    linked_at       TEXT    NOT NULL,        -- ISO-8601 timestamp
    close_reason    TEXT,                    -- populated on close
    realized_pnl    REAL,                    -- populated on close
    pnl_pct         REAL                     -- % of notional
);
```

Indexed on `symbol` and `opportunity_id` for efficient OIOS-side joins.

---

## Updated `opportunities` Fields

| Field | Updated by bridge? | Semantics |
|---|---|---|
| `position_exists` | ✅ Open → 1, Close → 0 | Whether a live trade is open |
| `position_size_pct` | ✅ On open | `(qty × entry) / total_capital × 100` |
| `position_open_date` | ✅ On open | ISO date the trade opened |
| `trade_pnl_pct` | ✅ On close | Realized P&L as % of notional |
| `last_updated_at` | ✅ Both | ISO-8601 timestamp of last bridge write |
| `final_state` | ❌ | Controlled by OIOS lifecycle engine only |
| `current_state` | ❌ | Never touched by execution bridge |

---

## Source of Truth Hierarchy

```
1. Execution System  (OrderManager)     ← authoritative for all trade decisions
2. OIOS DB           (market_behavior)  ← updated by bridge, read-only to execution
3. EventBus          (in-memory)        ← transport only, no persistence
```

OIOS writes from this bridge are **soft updates** — they enrich OIOS data quality
but OIOS logic never feeds back into execution.

---

## Failure Modes & Safety

| Failure | Consequence | Recovery |
|---|---|---|
| `market_behavior.db` does not exist | `get_connection()` auto-creates it | None needed |
| OIOS opportunity not found for a symbol | Link table still records the trade; `opportunity_id = NULL` | Manual reconciliation query |
| Bridge startup crash | `try/except` in `_setup_eda()` → bridge skipped, system runs normally | Fix bridge, restart |
| DB write error inside handler | Logged at DEBUG; execution continues | Next event retry |
| EventBus handler exception | EventBus isolates exceptions per subscriber | None; existing behaviour |
| System restart mid-session | `_order_opp_map` rebuilt lazily from `execution_trade_links` on close | Transparent |

---

## Verification Queries

Check that positions are being tracked:

```sql
-- Trades with matched OIOS opportunities
SELECT l.order_id, l.symbol, l.direction_exec, l.opportunity_id,
       o.current_state, o.position_exists, o.trade_pnl_pct
  FROM execution_trade_links l
  LEFT JOIN opportunities o ON o.opportunity_id = l.opportunity_id
 ORDER BY l.linked_at DESC
 LIMIT 20;

-- Match rate
SELECT
  COUNT(*) AS total_trades,
  SUM(CASE WHEN opportunity_id IS NOT NULL THEN 1 ELSE 0 END) AS matched,
  ROUND(100.0 * SUM(CASE WHEN opportunity_id IS NOT NULL THEN 1 ELSE 0 END)
        / COUNT(*), 1) AS match_pct
  FROM execution_trade_links;

-- Opportunities with position state
SELECT symbol, direction, current_state, position_exists,
       position_size_pct, trade_pnl_pct, position_open_date
  FROM opportunities
 WHERE position_exists = 1
 ORDER BY position_open_date DESC;
```

---

## Deployment

No migration needed. The bridge:
1. Creates `execution_trade_links` table automatically at startup.
2. Adds `POSITION_CLOSED` event type (backward-compatible — no existing subscriber breaks).
3. Uses lazy imports in `OrderManager.close_position()` (no circular import risk).
4. Is wired in `_setup_eda()` via try/except — if the OIOS package is absent the system starts normally.

The bridge becomes active from the next `main.py` restart.

---

*Generated: May 2025 | Session: OIOS Execution Feedback Integration (Shadow Safe)*
