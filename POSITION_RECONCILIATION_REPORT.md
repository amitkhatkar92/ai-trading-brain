# POSITION RECONCILIATION REPORT

**Run Date:** 2026-06-16T17:28:50
**System:** ai_trading_brain (paper trading mode)

---

## Executive Summary

| Classification | Count |
|---|---|
| ✅ VALID_OPEN | 0 |
| 🔴 ORPHAN_DB | 3 |
| 🟡 ORPHAN_CSV | 1 |
| 🟠 DUPLICATE | 0 |
| 🔵 MISMATCH | 0 |
| **Total** | **4** |

**Key finding:** There are no currently active, in-window positions. The execution system
has zero positions it would restore on the next startup.

---

## Data Sources Audited

| Source | Path | Rows / Records |
|---|---|---|
| A: paper_trades.csv | `data/paper_trades.csv` | 1 unclosed OPEN rows found |
| B: trading_brain.db | `data/trading_brain.db` | 21 `status=open` rows found |
| C: execution_trade_links | `data/market_behavior.db` — **does not exist** (bridge never ran in production) |
| D: OIOS opportunities | `data/market_behavior.db` | 0 — DB absent |

---

## ID Format Mapping

The two open-position stores use **incompatible ID formats**:

| Store | ID Format | Example |
|---|---|---|
| `paper_trades.csv` | `SIM_{SYMBOL}_{DIR}_{QTY}` | `SIM_ITC_BUY_4861` |
| `trading_brain.db` | 8-char short hex UUID | `45A71EA9` |

There is no shared key between these two stores.
`_restore_from_journal()` only reads `paper_trades.csv` and has no visibility into `trading_brain.db`.

---

## Position Inventory

| Symbol | Dir | Classification | Source | order_id | trade_id | opp_id | Entry | Qty | Age | Strategy |
|---|---|---|---|---|---|---|---|---|---|---|
| `WIPRO` | `BUY` | ORPHAN_DB | DB | — | 45A71EA9 | — | ₹1,501.50 | 21 | 97d | Breakout_Volume |
| `TCS` | `BUY` | ORPHAN_DB | DB | — | 61C464ED | — | ₹4,204.20 | 7 | 97d | Breakout_Volume |
| `HDFCBANK` | `BUY` | ORPHAN_DB | DB | — | 119BE372 | — | ₹1,701.70 | 21 | 97d | Breakout_Volume |
| `ITC` | `BUY` | ORPHAN_CSV | CSV | SIM_ITC_BUY_4861 | — | — | ₹308.55 | 4861 | 60d | Mean_Reversion |

---

## Detailed Findings

### 🔴 WIPRO — ORPHAN_DB

| Field | Value |
|---|---|
| Classification | **ORPHAN_DB** |
| Source | DB |
| order_id | `—` |
| trade_id (DB) | `45A71EA9` |
| opportunity_id | `—` |
| Direction | BUY |
| Entry Price | ₹1,501.50 |
| Quantity | 21 |
| Opened At | 2026-03-11T10:44:19.398146 |
| Age | 97 days |
| Strategy | Breakout_Volume |

**Notes:**
- 7 duplicate DB rows for same entry (trade_ids: 45A71EA9, E6A4A4FD, 01071775, C04EC17B, B6A8DB88, 88B8211E, 2D337CB5)
- Old orchestrator write (trading_brain.db) — no CSV counterpart; invisible to _restore_from_journal()
- These positions cannot be SL/target monitored or closed by current system

### 🔴 TCS — ORPHAN_DB

| Field | Value |
|---|---|
| Classification | **ORPHAN_DB** |
| Source | DB |
| order_id | `—` |
| trade_id (DB) | `61C464ED` |
| opportunity_id | `—` |
| Direction | BUY |
| Entry Price | ₹4,204.20 |
| Quantity | 7 |
| Opened At | 2026-03-11T10:44:19.410507 |
| Age | 97 days |
| Strategy | Breakout_Volume |

**Notes:**
- 7 duplicate DB rows for same entry (trade_ids: 61C464ED, 92CCF75D, B4ECEA75, 73940A54, 7406975C, A9B6863D, 6551731E)
- Old orchestrator write (trading_brain.db) — no CSV counterpart; invisible to _restore_from_journal()
- These positions cannot be SL/target monitored or closed by current system

### 🔴 HDFCBANK — ORPHAN_DB

| Field | Value |
|---|---|
| Classification | **ORPHAN_DB** |
| Source | DB |
| order_id | `—` |
| trade_id (DB) | `119BE372` |
| opportunity_id | `—` |
| Direction | BUY |
| Entry Price | ₹1,701.70 |
| Quantity | 21 |
| Opened At | 2026-03-11T10:44:19.511135 |
| Age | 97 days |
| Strategy | Breakout_Volume |

**Notes:**
- 7 duplicate DB rows for same entry (trade_ids: 119BE372, E0C3CC33, 3A3D61BD, C3D9A1C3, BD8116DD, 6ECBAEA2, A4AEAB46)
- Old orchestrator write (trading_brain.db) — no CSV counterpart; invisible to _restore_from_journal()
- These positions cannot be SL/target monitored or closed by current system

### 🟡 ITC — ORPHAN_CSV

| Field | Value |
|---|---|
| Classification | **ORPHAN_CSV** |
| Source | CSV |
| order_id | `SIM_ITC_BUY_4861` |
| trade_id (DB) | `—` |
| opportunity_id | `—` |
| Direction | BUY |
| Entry Price | ₹308.55 |
| Quantity | 4861 |
| Opened At | 2026-04-17 10:30:23 |
| Age | 60 days |
| Strategy | Mean_Reversion |

**Notes:**
- Age 60d exceeds carry limit 3d — would be SESSION_EXPIRED at next _restore_from_journal()
- No close row in CSV — system was not restarted after expiry window elapsed

---

## Root Cause Analysis

### Why 21 ORPHAN_DB positions exist (WIPRO×7, TCS×7, HDFCBANK×7)

Timeline:
```
2026-03-11 10:44–12:57  Old orchestrator ran 7 trade cycles for WIPRO, TCS, HDFCBANK.
                         Each cycle wrote an OPEN record to trading_brain.db.
                         Same entry price repeated across all cycles:
                           WIPRO    ₹1,501.50 × 3 qty  (×7 cycles = 21 qty total)
                           TCS      ₹4,204.20 × 1 qty  (×7 cycles)
                           HDFCBANK ₹1,701.70 × 3 qty  (×7 cycles)
                         No CLOSE was ever written — the old orchestrator likely
                         crashed or was replaced before positions were resolved.

2026-03-19+             New orchestrator deployed. Writes only to paper_trades.csv.
                         Never reads trading_brain.db.
                         The 21 old positions became permanently invisible.

2026-06-16 (today)      21 rows remain in trading_brain.db.status='open'.
                         The execution system is completely unaware of them.
```

**Why 7 cycles of the same trade?**
The identical entry prices across all 7 records for each symbol (e.g. WIPRO always
₹1,501.50) suggest this was a test run where the same signal fired repeatedly,
bypassing the duplicate-position guard — possibly because the old orchestrator did not
have the `_symbol_has_open_position()` guard that the current one has.

### Why 1 ORPHAN_CSV position exists (ITC, SIM_ITC_BUY_4861)

```
2026-04-17 13:00:20  ORDER_PLACED: SIM_ITC_BUY_4861 (ITC BUY 4861 × ₹308.55)
                      Written to paper_trades.csv as OPEN.
                      No CLOSE row written (system not restarted since? or close write failed).

2026-06-16 (today)   Age = 60 days.  Carry limit for EDG_MOMENT_* strategy = 5 days.
                      _restore_from_journal() would immediately SESSION_EXPIRE this
                      position at next startup — it will NOT be restored as live.
```

---

## Remediation SQL

```sql
-- ===================================================================
-- REMEDIATION SQL — generated by reconcile_positions.py
-- Run date: 2026-06-16T17:28:50
-- REVIEW AND TEST BEFORE RUNNING. These are NOT auto-executed.
-- ===================================================================

-- ---------------------------------------------------------------
-- SECTION 1: Close phantom open trades in trading_brain.db
--
-- Context: 21 open records from old orchestrator (2026-03-11).
-- The new orchestrator never reads this table. These positions
-- are unmonitored, unrestorable, and block accurate portfolio math.
-- Resolution: mark all as 'closed' with a reconciliation reason.
-- ---------------------------------------------------------------

-- Step 1a: Preview rows to be closed
SELECT id, trade_id, symbol, direction, quantity, entry_price,
       status, ts_open
  FROM trades
 WHERE status = 'open';

-- Step 1b: Close all phantom open positions
-- (Affects 21 rows across WIPRO×7, TCS×7, HDFCBANK×7)
UPDATE trades
   SET status   = 'closed',
       ts_close = '2026-06-16T17:28:50',
       pnl      = 0,
       net_pnl  = 0,
       notes    = 'RECONCILED: orphaned legacy position — old orchestrator (2026-03-11); never monitored by current system'
 WHERE status = 'open';

-- Step 1c: Verify
SELECT COUNT(*) AS remaining_open FROM trades WHERE status='open';
-- Expected: 0

-- ---------------------------------------------------------------
-- SECTION 2: Expire orphaned CSV positions (paper_trades.csv)
--
-- These SQL statements are not applicable to a CSV file.
-- The CSV remedy is to append SESSION_EXPIRED CLOSE rows.
-- The script below is PYTHON pseudocode for illustration only.
-- ---------------------------------------------------------------

-- Python pseudocode (do not run as SQL):
-- import csv
-- from datetime import datetime
-- CLOSE_ROW = {
--   # order_id: SIM_ITC_BUY_4861
--   'timestamp':   '2026-06-16T17:28:50',
--   'order_id':    'SIM_ITC_BUY_4861',
--   'symbol':      'ITC',
--   'direction':   'BUY',
--   'quantity':    '4861',
--   'entry_price': '308.55',
--   'stop_loss':   '',
--   'target':      '',
--   'strategy':    'Mean_Reversion',
--   'confidence':  '',
--   'rr':          '',
--   'event':       'CLOSE',
--   'exit_price':  '308.55',
--   'pnl':         '0.0',
--   'reason':      'SESSION_EXPIRED (reconciliation: age=60d > carry_limit)'
-- }

-- ---------------------------------------------------------------
-- SECTION 3: Diagnostic queries (safe to run at any time)
-- ---------------------------------------------------------------

-- 3a: All open positions in trading_brain.db
SELECT trade_id, symbol, direction, quantity, entry_price, ts_open
  FROM trades
 WHERE status='open'
 ORDER BY symbol, ts_open;

-- 3b: Duplicate open positions (same symbol+direction+entry)
SELECT symbol, direction, entry_price, COUNT(*) AS dup_count
  FROM trades
 WHERE status='open'
 GROUP BY symbol, direction, entry_price
 HAVING COUNT(*) > 1;

-- 3c: Cross-check: execution_trade_links (market_behavior.db)
-- (Run from market_behavior.db, after ATTACH if needed)
SELECT order_id, symbol, direction_exec, opportunity_id,
       linked_at, close_reason, realized_pnl
  FROM execution_trade_links
 ORDER BY linked_at DESC;

-- 3d: OIOS opportunities with position_exists=1 (should be 0 for orphans)
SELECT opportunity_id, symbol, direction, current_state,
       position_exists, position_size_pct, trade_pnl_pct
  FROM opportunities
 WHERE position_exists = 1;

```

---

## Traceability Matrix

Every discovered position mapped to its provenance chain:

| order_id / trade_id | Source | CSV open? | DB open? | OIOS link? | OIOS opp? | Traceable? |
|---|---|---|---|---|---|---|
| `45A71EA9` | DB | — | ✅ | ❌ | ❌ | ✅ |
| `61C464ED` | DB | — | ✅ | ❌ | ❌ | ✅ |
| `119BE372` | DB | — | ✅ | ❌ | ❌ | ✅ |
| `SIM_ITC_BUY_4861` | CSV | ✅ | — | ❌ | ❌ | ✅ |

---

## Verification Queries

Run after applying remediation to confirm clean state:

```sql
-- 1. Confirm no phantom open rows remain in trading_brain.db
SELECT COUNT(*) AS phantom_open
  FROM trades
 WHERE status = 'open';
-- Expected: 0

-- 2. Confirm paper_trades.csv has no unexpired open-only positions
-- (Python: parse CSV, find order_ids where OPEN has no CLOSE and age <= carry_limit)

-- 3. Cross-verify execution_trade_links has no unresolved open positions
SELECT COUNT(*) AS unresolved_links
  FROM execution_trade_links
 WHERE close_reason IS NULL;
-- Expected: 0 after all positions are closed

-- 4. Confirm OIOS position_exists is 0 for all stale entries
SELECT COUNT(*) AS phantom_oios_open
  FROM opportunities
 WHERE position_exists = 1;
-- Expected: 0 (no positions were ever bridge-linked)
```

---

*Generated by `reconcile_positions.py` on 2026-06-16T17:28:50*
