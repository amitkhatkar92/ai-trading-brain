# OPEN_POSITION_FORENSIC.md
## Forensic Audit — Open and Stale Positions
**Date of Investigation:** June 16, 2026  
**Sources:** `data/paper_trades.csv`, `data/trading_brain.db` (trades table), `data/control_tower.db`  
**As-of date:** June 16, 2026

---

## 1. Executive Summary

There are **two separate journalling systems** that each hold unresolved positions:

| Store | Orchestrator | Open Positions | Real PnL Realised |
|---|---|---|---|
| `data/paper_trades.csv` | New orchestrator (post-March 2026) | 1 — ITC BUY | ₹0 |
| `data/trading_brain.db` (trades table) | Old orchestrator (pre-March 2026) | 3 — HDFCBANK, TCS, WIPRO | ₹0 |

The two stores are **completely isolated**. The new orchestrator's `_restore_from_journal()` reads only from `paper_trades.csv` and has no visibility into `trading_brain.db`. Old positions cannot be closed by the new system without direct DB intervention.

---

## 2. Position 1 — ITC BUY (Active, paper_trades.csv)

| Field | Value |
|---|---|
| Symbol | ITC |
| Direction | BUY |
| order_id | SIM_ITC_BUY_4861 |
| Opened | 2026-04-17 13:00:20 |
| Entry price | ₹308.55 |
| Quantity | 4,861 shares |
| Notional | ₹1,499,832 |
| Strategy | Mean_Reversion |
| Close event | **None** |
| Days held | ~43 calendar days / ~30 trading days |

### Why this position is still open

1. **System idle:** The last `ct_cycle` recorded in `control_tower.db` is 2026-04-02. The orchestrator has not run since. No monitor loop is executing SL checks or carry expiry.

2. **No monitoring heartbeat:** `TradeMonitor.check_and_expire_stale_limits()` is only called from within the orchestrator's `_do_monitor()` slot. With the scheduler stopped, this function has not been called since the last cycle.

3. **Stop-loss is registered but unmonitored:** An `SL_ORDER` was placed via `_place_stop_loss()` when the position was opened (SIM mode → `SIM_SL_ITC`). However, this SL only triggers if the monitor loop polls LTP and detects breach. No polling = no breach detection.

### Capital context at time of placement

The April 17 ITC trade passed the `MAX_CAPITAL_PER_TRADE_PCT = 15%` guard because:
- `TOTAL_CAPITAL` was raised to ₹10,000,000 (10 million) between April 2 and April 17.
- On April 2, `SmartExecutionEngine` reported `exposure_pct = 77.2%` for ₹617,400 exposure → implied `TOTAL_CAPITAL ≈ ₹800,000`.
- ITC notional = ₹1,499,832. This equals **15.0%** of ₹10,000,000 — exactly at the threshold.

This explains why March 18 trades were blocked (TOTAL_CAPITAL = ₹800,000 → 15% cap = ₹120,000) while April 17 trades passed (TOTAL_CAPITAL = ₹10,000,000 → 15% cap = ₹1,500,000).

---

## 3. Positions 2-4 — Old Orchestrator Remnants (trading_brain.db)

| id | Symbol | Direction | Opened | Entry | Quantity | Status | PnL |
|---|---|---|---|---|---|---|---|
| 25 | WIPRO | BUY | 2026-03-11 | (not available) | — | open | ₹0 |
| 26 | TCS | BUY | 2026-03-11 | (not available) | — | open | ₹0 |
| 28 | HDFCBANK | BUY | 2026-03-11 | (not available) | — | open | ₹0 |

- `exit_price = 0.0` for all three
- `status = 'open'` for all three
- These records were never updated because the old orchestrator was replaced before it could close them

### Why these are permanently stranded

The new `OrderManager` (`execution_engine/order_manager.py`) journals to `data/paper_trades.csv`. Its `_restore_from_journal()` method reads from the CSV:

```python
def _restore_from_journal(self) -> None:
    if not os.path.exists(PAPER_TRADES_CSV):
        return
    df = pd.read_csv(PAPER_TRADES_CSV)
    ...
```

No code path reads `trading_brain.db.trades`. The old HDFCBANK, TCS, WIPRO records:
- Cannot be closed by the new system
- Cannot be seen by `get_open_orders()` or `_symbol_has_open_position()`
- Do not occupy slots in `MAX_OPEN_POSITIONS = 15`
- Have no impact on current execution decisions

They are **orphaned data** — historically accurate but operationally inert.

---

## 4. Previously Closed Positions (March 16 Batch)

Six positions opened on March 16 were closed on April 15 via `SYSTEM_CLEANUP`:

| Symbol | Opened | Closed | Exit Price | Reason | PnL |
|---|---|---|---|---|---|
| COALINDIA | 2026-03-16 | 2026-04-15 | = entry_price | SYSTEM_CLEANUP | ₹0 |
| HDFCBANK | 2026-03-16 | 2026-04-15 | = entry_price | SYSTEM_CLEANUP | ₹0 |
| ICICIBANK | 2026-03-16 | 2026-04-15 | = entry_price | SYSTEM_CLEANUP | ₹0 |
| INFY | 2026-03-16 | 2026-04-15 | = entry_price | SYSTEM_CLEANUP | ₹0 |
| LT | 2026-03-16 | 2026-04-15 | = entry_price | SYSTEM_CLEANUP | ₹0 |
| RELIANCE | 2026-03-16 | 2026-04-15 | = entry_price | SYSTEM_CLEANUP | ₹0 |

`SYSTEM_CLEANUP` is the close reason written by `close_position()` when positions are force-closed by a batch shutdown path (not a real SL hit or target hit). `exit_price = entry_price` confirms no P&L was captured before close.

These 6 positions — having been open from March 16 to April 15 (21 trading days) without any SL or target trigger — confirm the **monitor loop was not running** for their entire holding period.

---

## 5. The March 13 Batch (90 Positions — All Closed)

On March 13, 2026, the old orchestrator placed 90 positions in a single session (13:36–14:00 IST). All were closed the same session via `REPLACEMENT` or `SYSTEM_CLEANUP` at `exit_price = entry_price`. PnL = ₹0 for all.

This mass-position event triggered the addition of `FIX 3A` (capital per trade guard) and `FIX 3B` (total exposure guard) to `OrderManager`. These guards subsequently blocked all March 18 execution (see `EXECUTION_PATH_REPORT.md`).

---

## 6. Realized PnL Across All Paper Trading Activity

```sql
SELECT close_reason, COUNT(*) AS trades, SUM(pnl) AS total_pnl
FROM paper_trades
WHERE action = 'CLOSE'
GROUP BY close_reason;
```

| Close Reason | Count | Total PnL |
|---|---|---|
| REPLACEMENT | 87 | ₹0.00 |
| SYSTEM_CLEANUP | 15+ | ₹0.00 |
| SL_HIT | 0 | — |
| TARGET_HIT | 0 | — |
| CARRY_EXPIRED | 0 | — |

**All PnL is zero.** No trade has ever completed a natural SL-hit or target-hit lifecycle. Every close was triggered by system housekeeping, not price movement.

---

## 7. System Activity Timeline

```
2026-03-11  Old orchestrator: HDFCBANK, TCS, WIPRO opened → still open in trading_brain.db
2026-03-13  90 orders placed/closed in bulk via old orchestrator (position explosion)
2026-03-16  New orchestrator: 6 positions opened (COALINDIA, HDFCBANK, ICICIBANK, INFY, LT, RELIANCE)
2026-03-18  New orchestrator: 3 cycles, 18 APPROVED decisions → 0 executed (capital guard)
2026-03-19  Some paper_trades activity (see CSV)
2026-04-02  New orchestrator: 2 cycles → 0 executed (DecisionEngine rejection)
2026-04-15  March 16 positions closed via SYSTEM_CLEANUP, exit_price = entry_price
2026-04-16  2 new opens: ICICIBANK, RELIANCE
2026-04-17  ITC BUY opened @ ₹308.55, qty=4861  ← LAST ACTIVITY
2026-04-17  ICICIBANK, RELIANCE closed via SYSTEM_CLEANUP
2026-06-16  Today — system completely idle since April 17
            ITC position: 43 calendar days / ~30 trading days without SL monitoring
```

---

## 8. Risk Assessment of Current Open Position

**ITC BUY @ ₹308.55 — unmonitored for ~30 trading days**

| Risk Factor | Status |
|---|---|
| Stop-loss filed? | Yes (SIM_SL_ITC, simulated) |
| Stop-loss monitored? | **No** — monitor loop not running |
| Carry limit (3 trading days)? | **Violated** — held 30+ trading days |
| Unrealized PnL captured? | **No** — no LTP polling since April 17 |
| Position in new orchestrator's `_orders`? | **No** — not restored unless orchestrator restarts |

The position will remain invisible to `get_open_orders()` until `_restore_from_journal()` runs on the next orchestrator startup. When it does, `check_and_expire_stale_limits()` should detect it as carry-expired and close it at the restored LTP (or entry price if LTP unavailable).

---

*End of OPEN_POSITION_FORENSIC.md — observation only, no fixes applied*
