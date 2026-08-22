# POSITION_STATE_UNIFICATION.md
## Forensic Audit — Authoritative Position State
**Date of Investigation:** June 16, 2026  
**Scope:** All persistent stores that contain or imply position state  
**Verdict:** Three isolated stores, zero cross-sync, OIOS decoupled from execution.

---

## 1. Stores Examined

| Store | Path | Owner | Format |
|---|---|---|---|
| A | `data/paper_trades.csv` | New orchestrator (post-March 2026) | Append-only flat CSV |
| B | `data/trading_brain.db` (trades table) | Old orchestrator (March 11 2026) | SQLite |
| C | `data/replay.db` (opportunities table) | OIOS engine | SQLite, 12,040 rows |

No `data/oios.db` exists. OIOS uses `data/replay.db` as its primary store.

---

## 2. Store A — `data/paper_trades.csv` (Authoritative for Current System)

### Schema

```
timestamp, order_id, symbol, direction, quantity, entry_price,
stop_loss, target, strategy, confidence, rr, event
```

CLOSE rows append **extra anonymous columns** beyond the declared header:
```
..., event=CLOSE, [exit_price], [realized_pnl], [close_reason]
```
These overflow columns are stored under a `None` key when parsed by `csv.DictReader`. They are not part of the schema definition.

### Contents (as of June 16 2026)

| Event Type | Count |
|---|---|
| OPEN | 119 |
| CLOSE | 112 |
| REENTRY_OPEN | 2 |
| CANCELLED | 1 |
| **Total** | **234** |

### Open/Close balance

There are **7 unmatched OPEN records** (OPEN has no corresponding CLOSE with the same `order_id`):

| order_id | Symbol | Opened | Notional |
|---|---|---|---|
| SIM_ITC_BUY_4861 (entry 1) | ITC | 2026-04-17 10:30:23 | ₹1,499,862 |
| SIM_ITC_BUY_4861 (entry 2) | ITC | 2026-04-17 13:00:20 | ₹1,499,862 |
| SIM_RELIANCE_BUY_826 | RELIANCE | 2026-04-16 13:23:45 | ₹2,355,653 |
| 6 March 20 Hedging_Model opens | RELIANCE, HDFCBANK, ICICIBANK, INFY, LT, COALINDIA | 2026-03-20 07:35:xx | ₹93K–₹124K each |

Note: `SIM_ITC_BUY_4861` appears twice as OPEN with the same `order_id` (same symbol and quantity, same price, timestamps 10:30 and 13:00). This implies a re-entry created a second record without retiring the first, resulting in duplicate `order_id` keys pointing to two distinct OPEN rows — a CSV journal integrity defect.

### How `_restore_from_journal()` uses this store

`execution_engine/order_manager.py`, line 2808:

```python
def _restore_from_journal(self) -> None:
    if not os.path.exists(PAPER_TRADES_CSV):
        return
    df = pd.read_csv(PAPER_TRADES_CSV)
    # Reconstructs in-memory _orders and _portfolio from OPEN rows
    # only rows where event == 'OPEN' with no matching CLOSE are treated as live
```

This is the **only** mechanism by which `_symbol_has_open_position()` and `get_open_orders()` learn of prior positions after a restart. Only Store A is read here.

### Authoritative status

**Store A is the authoritative source of truth for the current orchestrator.** It is the only store read at startup, the only store that gates `DupGuard`, and the only store that affects `execute()` path decisions.

---

## 3. Store B — `data/trading_brain.db` (Orphaned Legacy Store)

### Contents

28 rows, all from `2026-03-11`, all with `mode='test'`.

| Pattern | Count |
|---|---|
| WIPRO BUY status=open entry=1501.5 qty=3 | 7 identical rows |
| TCS BUY status=open entry=4204.2 qty=1 | 7 identical rows |
| HDFCBANK BUY status=open entry=1701.7 qty=3 | 7 identical rows |
| INFY BUY status=closed entry=1801.8 exit=1868.13 qty=8 pnl=530.64 | 7 identical rows |

Each of the 7 "open" WIPRO rows is an exact duplicate (same entry_price, same quantity, different `ts_open` within the same day). This duplication pattern indicates the development/test harness for the old orchestrator ran the same portfolio setup 7 times without deduplication. The INFY closed trades show `ts_open` and `ts_close` within milliseconds of each other — confirming synthetic test execution, not real paper trading.

The 7 `pnl=530.64` INFY rows (`8 × (1868.13 − 1801.8) = 8 × 66.33 = ₹530.64`) are real arithmetic on plausible prices but are development test fixtures.

### Current impact on production

**Zero.** `order_manager._restore_from_journal()` does not read this database. None of the 21 open rows in this store occupy `MAX_OPEN_POSITIONS` slots. They do not influence `_symbol_has_open_position()`. They have no effect on any decision in the new orchestrator.

### Why they are permanently orphaned

The old orchestrator wrote to `trading_brain.db.trades`. The new orchestrator writes to `data/paper_trades.csv`. No migration or cleanup path was ever implemented. Both stores contain valid `status='open'` records for the same symbols (HDFCBANK appears in both), which means a combined query of both stores would overcount open positions.

---

## 4. Store C — `data/replay.db` opportunities table (OIOS Store)

### Contents

| State | Count |
|---|---|
| INVALID | 11,948 |
| ACTIVE | 55 |
| DISCOVERED | 30 |
| WATCHING | 7 |
| **Total** | **12,040** |

### The `position_exists` field

The `opportunities` schema includes:

```sql
position_exists         INTEGER DEFAULT 0,  -- SQLite boolean: 0/1
position_size_pct       REAL    DEFAULT 0.0,
position_open_date      TEXT,
```

**Current value across all 12,040 rows:**

```
position_exists = 0  for ALL rows
position_open_date = NULL  for ALL rows
```

This confirms that OIOS has never been told that any opportunity resulted in an execution. The `position_exists` field exists by design to allow OIOS to track whether the execution system acted on an opportunity — but no write path currently populates it.

### OIOS link to execution system

A search across all 170+ `.py` files in the `oios/` package found **zero references** to:
- `paper_trades.csv`
- `OrderManager`
- `order_manager`
- `execute(signal`
- `trading_brain.db`

OIOS operates entirely on its own `data/replay.db` domain. It emits intelligence (via `ShadowScorer`, `VelocityEngine`, `PropagationEngine`) but has no read or write path to the execution journal.

---

## 5. Inconsistency Map

| Position | Store A | Store B | Store C |
|---|---|---|---|
| ITC BUY open | ✅ OPEN (×2) | ❌ absent | ❌ absent (`position_exists=0`) |
| HDFCBANK (Mar 11) | ❌ absent | ✅ open (×7 dups) | ❌ absent |
| WIPRO (Mar 11) | ❌ absent | ✅ open (×7 dups) | ❌ absent |
| TCS (Mar 11) | ❌ absent | ✅ open (×7 dups) | ❌ absent |
| RELIANCE BUY (Apr 16) | ✅ OPEN (unmatched) | ❌ absent | ❌ absent |
| March 20 Hedging_Model | ✅ OPEN (6 symbols) | ❌ absent | ❌ absent |

A combined query across all three stores would find HDFCBANK simultaneously open in Store B (×7) and absent from Store A and C — and Store A is the only one that counts for execution decisions.

---

## 6. How Positions Become Orphaned

### Pathway 1: Orchestrator replacement (Store B)
The old orchestrator wrote to `trading_brain.db`. When the new orchestrator was deployed, it wrote to `paper_trades.csv`. No close events were written to `trading_brain.db` for existing open positions. All 21 open rows remain permanently orphaned.

### Pathway 2: Restart without close (Store A)
If the orchestrator stops between an OPEN event and its corresponding CLOSE (SL hit, target, carry expiry), the position remains as an unmatched OPEN row in the CSV. The next orchestrator startup will call `_restore_from_journal()` and reconstruct the position — preventing DupGuard bypass. This pathway is correctly handled.

### Pathway 3: Duplicate order_id on re-entry (Store A)
`SIM_ITC_BUY_4861` was written twice as OPEN with the same `order_id`. If `_restore_from_journal()` groups by `order_id`, it may reconstruct only one position when there should be two (or zero net, depending on close matching logic). The exact behaviour depends on the pandas groupby logic in `_restore_from_journal()`.

### Pathway 4: OIOS-execution decoupling (Store C)
OIOS identifies an ACTIVE opportunity, OIOS `conviction_score` rises, OIOS would flag the symbol for action — but the execution system makes an independent decision, and the result is never written back to `position_exists`. OIOS can simultaneously flag RELIANCE as ACTIVE while RELIANCE's position in Store A is unmonitored and expired. The two systems are operating on divergent state.

---

## 7. Authoritative Source: Conclusion

| Question | Answer |
|---|---|
| Which store is authoritative? | **`data/paper_trades.csv`** — the only store read by `_restore_from_journal()` |
| Which stores cause inconsistency? | **`trading_brain.db`** (21 phantom open positions); **`replay.db` `position_exists`** (never populated) |
| Does OIOS know about any execution? | **No.** Zero positions reflected in `position_exists` across 12,040 rows |
| Are there any orphaned positions in the active store? | **Yes.** ITC BUY has two OPEN rows with the same `order_id`; 6 March-20 Hedging_Model positions have no CLOSE; RELIANCE BUY (Apr 16) has no CLOSE |

---

## 8. Recommended Remediation Path

*Documentation only — no changes implemented.*

1. **Retire `trading_brain.db.trades`** — write all 28 rows as `status='closed'` with `ts_close=NOW(), exit_price=0, pnl=0, notes='orphaned_legacy'`. This prevents any future tooling from misreading open count.

2. **Deduplicate `paper_trades.csv` order_id collisions** — either enforce unique `order_id` per position or differentiate re-entry positions by appending a timestamp suffix. Current `SIM_{SYMBOL}_{DIR}_{QTY}` format does not distinguish re-entries.

3. **Populate `opportunities.position_exists`** — define a scheduled or event-driven sync: when `OrderManager` places a trade, write `position_exists=1` to the matching OIOS opportunity (join on symbol + direction). Reverse on close. Until this path exists, OIOS intelligence cannot account for execution state.

4. **Audit March-20 Hedging_Model positions** — 6 open positions (RELIANCE, HDFCBANK, ICICIBANK, INFY, LT, COALINDIA) opened 2026-03-20 07:35 have no CLOSE in the CSV. Determine if they were still held at system shutdown or closed externally.

---

*End of POSITION_STATE_UNIFICATION.md — observation only, no changes applied*
