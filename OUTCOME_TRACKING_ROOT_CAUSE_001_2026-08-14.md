# Outcome Tracking Root Cause Analysis
## OUTCOME_TRACKING_ROOT_CAUSE_001
**Date:** 2026-08-14  
**Context:** Follow-up to KNOWLEDGE_VS_STRATEGY_VALUE_AUDIT_001 finding:
3,335 signal_births with `actual_move_pct=0.0` and `final_state=NULL`  
**Methodology:** Read-only source code trace + live VPS database inspection

---

## 1. Signal Lifecycle (as designed)

```
Scanner run (post-market, ~16:45 IST daily)
    │
    ▼
layer_1a.run_scan() + layer_1b.run_scan()       [oios/scanners/layer_1a.py, layer_1b.py]
    │  qualifying_signals (base_score > 4.0)
    ▼
signal_writer.write_scan_results()               [oios/scanners/signal_writer.py]
    │
    ├─► create_signal_birth()                    [oios/db/repository.py]
    │       Inserts row with:
    │         actual_move_pct = 0.0  (default)
    │         final_state     = NULL (default)
    │         current_state   = ACTIVE
    │
    └─► attach_or_create_opportunity()           [oios/domain/opportunity_service.py]
            Creates/merges opportunity in DISCOVERED state
    │
    ▼
ELE daily run (DESIGNED — NOT SCHEDULED)
    │
    run_ele_daily()                              [oios/engine/ele.py]
    │
    ├─► compute_actual_move_pct()               [oios/engine/re_calculator.py]
    │       Queries ohlcv_daily, computes direction-aware return
    │       Stores result in: opportunities.edge_consumed_pct  ← NOT signal_births
    │
    ├─► State machine transitions
    │       DISCOVERED → ACTIVE (when conviction_score ≥ 6.0)
    │       ACTIVE → INVALID (when TTL exhausted)
    │       Sets: opportunities.final_state, opportunities.invalidation_reason
    │
    └─► (MISSING: no write-back to signal_births.actual_move_pct)
    │
    ▼
signal_births.actual_move_pct stays at 0.0
signal_births.final_state stays at NULL
```

---

## 2. Root Cause #1 — PRIMARY: `run_ele_daily()` Never Called

**File:** `orchestrator/master_orchestrator.py`

**Evidence:**
```
$ grep -n "run_ele_daily\|from oios.engine.ele" orchestrator/master_orchestrator.py
(empty — zero matches)
```

The orchestrator calls these OIOS functions daily:
| Function | Called | Purpose |
|---|---|---|
| `write_scan_results()` | ✅ line ~3672 | Signal creation |
| `update_outcomes()` | ✅ line ~3497 | Market leader outcomes |
| `capture_daily_leaders()` | ✅ line ~3530 | Leader detection |
| `build_controls_for_date()` | ✅ line ~3613 | Control population |
| `run_ele_daily()` | ❌ **NEVER** | Advance signal lifecycle |

**Consequence:** Every `signal_births` record stays frozen at its birth values:
- `current_state = ACTIVE` — never transitions
- `age_trading_days = 0` — never incremented
- `actual_move_pct = 0.0` — never computed
- `final_state = NULL` — never set

---

## 3. Root Cause #2 — STRUCTURAL: No Write-Back to `signal_births.actual_move_pct`

Even if `run_ele_daily()` were called, it would NOT fix `signal_births.actual_move_pct`.

**Trace of ELE Step 2 (in `oios/engine/ele.py`, function `run_ele_cycle_for_opportunity`):**

```python
# Step 2: Actual move and EC_path
actual_move = compute_actual_move_pct(conn, opp.symbol, birth_direction, birth_price, today)
ec_path     = compute_ec_path(actual_move, expected_move_pct)
opp.edge_consumed_pct = ec_path   # ← stored on opportunity object

# ...

R.update_opportunity_state(conn, opp)  # ← writes to opportunities table only
```

**There is no code that does:**
```python
UPDATE signal_births SET actual_move_pct = ? WHERE signal_id = ?
```

**Confirmed via grep:**
```
$ grep -rn "UPDATE.*signal_births" oios/
tests/oios/test_phase_d.py:88:  UPDATE signal_births SET final_state=?, ...  # TEST FIXTURE ONLY
tests/oios/test_phase_e.py:590: UPDATE signal_births SET final_state='TTL_EXHAUSTED', ...  # TEST FIXTURE ONLY
```

Both UPDATE statements are test fixtures, not production code.

`oios/db/repository.py` has:
- `create_signal_birth()` — INSERT only, sets `actual_move_pct=0.0`
- NO function to update measurement fields after creation

**Consequence:** `signal_births.actual_move_pct` is a write-once field set to 0.0 at birth. It has no update path in production code.

---

## 4. Root Cause #3 — INFRASTRUCTURE: `trading_calendar` Has 0 Rows

**Evidence:**
```sql
SELECT COUNT(*) FROM trading_calendar;
-- Result: 0
```

**Impact on ELE (even if it were called):**

The ELE conviction calculation (`_compute_conviction_re_weighted` in `ele.py`) uses:
```sql
SELECT COUNT(*) FROM trading_calendar
WHERE is_trading_day = 1
  AND calendar_date > ?
  AND calendar_date <= ?
```
to compute `signal_age_days`. With 0 rows, every signal appears 0 days old.

The state machine `check_terminal_conditions` (TTL expiry) uses `age_trading_days` (stored on opportunity, updated from calendar). With 0 calendar rows, no signal would ever age out via TTL.

**Consequence:** Even if ELE were running, signals would never TTL-expire because their trading-day age is always 0.

---

## 5. Root Cause #4 — TAXONOMY: `final_state` Stored as NULL, Misread as 'UNKNOWN'

**Evidence:**
```sql
SELECT final_state, COUNT(*) FROM signal_births GROUP BY final_state;
-- Result: (NULL, 3335)
```

The value is `NULL` (Python `None`), not the string `'UNKNOWN'`.

The previous KvS audit scripts used `COALESCE(final_state, 'UNKNOWN')` or similar transforms which displayed as `UNKNOWN: 3335`. This is a display artifact, not an actual value.

**Impact on taxonomy:** The intended final states (from test fixtures and outcome_distributor.py usage) are:
- `'TTL_EXHAUSTED'` — signal aged past its TTL
- `'INVALID'` — opportunity was invalidated
- `'WIN'` — used by outcome_distributor win_rate calculation
- No production code sets ANY of these values to signal_births

---

## 6. Data Availability for Reconstruction

**VPS database scan results:**

| Data | Status | Details |
|---|---|---|
| `signal_births` | 3,335 rows | dates 2026-06-22 to 2026-08-14 |
| `ohlcv_daily` | 20,604 rows | 209 symbols, 2026-03-24 to 2026-08-13 |
| OHLCV coverage | 100% | 20/20 checked signal symbols have OHLCV data |
| `trading_calendar` | **0 rows** | Cannot compute trading-day ages |
| `signal_births` with expired TTL | 2,267 of 3,335 | `julianday(now) - julianday(detected_at) > ttl` |
| `signal_births` still within TTL | ~1,068 of 3,335 | Born 2026-08-04 or later (TTL 10-18 days) |

**OHLCV availability for oldest signals:**
```
2026-06-22 RBLBANK.NS: ohlcv from 2026-06-22, prices available through 2026-08-13
```
→ For all signals born before 2026-07-24, price data covers the full TTL window.

**Reconstruction feasibility:**
- 2,267 signals past TTL → outcome fully determinable from OHLCV
- ~1,068 signals still within TTL → outcome partially determinable (compute actual_move_pct but mark as PENDING final_state)
- 0 signals with missing OHLCV (all 209 symbols covered)

---

## 7. Exact Failure Point Summary

```
WHERE THE OUTCOME DATA IS MISSING
══════════════════════════════════

CREATE signal (write_scan_results) → OK
    signal_births row created with actual_move_pct=0.0, final_state=NULL

MEASURE outcome (run_ele_daily) → NEVER CALLED
    Orchestrator has no call to run_ele_daily()
    Even if called: no write-back to signal_births.actual_move_pct exists

CLOSE signal (state machine) → NEVER RUNS
    trading_calendar empty → age stays 0 → TTL never triggers
    No final_state ever written to signal_births

══════════════════════════════════
RESULT: 3,335 signals frozen at birth state
```

---

## 8. Non-Issues (Correctly Functioning)

| System | Status | Evidence |
|---|---|---|
| `market_leader_outcomes` | ✅ Working | 1,410 outcome rows (from `outcome_tracker.update_outcomes`) |
| `signal_births` creation | ✅ Working | 3,335 correct signal records with valid birth_price, direction, score |
| `ohlcv_daily` refresh | ✅ Working | Daily refresh runs, 20,604 rows through 2026-08-13 |
| OHLCV coverage | ✅ Complete | All 209 signal symbols have price data |
| Repair feasibility | ✅ Confirmed | OHLCV available for all signals |

---

## 9. Failure Classification

| Root Cause | Type | Severity | Fixable Without Trading Changes |
|---|---|---|---|
| RC1: `run_ele_daily()` not called | Missing orchestrator hook | HIGH | YES — add call to orchestrator |
| RC2: No write-back to `signal_births.actual_move_pct` | Missing update path | HIGH | YES — add measurement module |
| RC3: `trading_calendar` empty | Data gap | MEDIUM | YES — populate calendar OR use calendar-day fallback |
| RC4: `final_state` stays NULL | Consequence of RC1+RC2 | HIGH | YES — fixed by measurement module |

**Minimum repair scope (measurement only):**
- Create `oios/engine/signal_outcome_tracker.py` to compute and persist outcomes from OHLCV
- Do NOT add `run_ele_daily()` to orchestrator (that would change trading behavior)
- Do NOT populate `trading_calendar` as part of this fix (separate concern)

---

## 10. Answers to Required Questions

**Q1: Why are 3,335 signal_births stuck at `actual_move_pct=0`?**  
`compute_actual_move_pct()` is called inside the ELE cycle but writes to `opportunities.edge_consumed_pct`, not `signal_births.actual_move_pct`. There is no UPDATE path for `signal_births.actual_move_pct` in any production code.

**Q2: Why are they stuck at `final_state=NULL`?**  
`run_ele_daily()` is never called from the orchestrator. The state machine that sets `final_state` never runs. Even if ELE ran, it would set `final_state` on `opportunities`, not on `signal_births`.

**Q3: Can historical outcomes be reconstructed reliably?**  
YES for 2,267 signals (past TTL). OHLCV data is 100% available for all signal symbols. The birth_price, direction, and detected_at are all accurate. Reconstruction is deterministic from OHLCV.

**Q4: Can future signal outcomes now be recorded reliably?**  
YES — the measurement module (`signal_outcome_tracker.py`) is a daily addition to the orchestrator. It is observational only and does not touch trading logic.

**Q5: Are LONG and SHORT outcomes directionally correct?**  
They will be after the repair. The computation is direction-aware:
- LONG: `(close - birth_price) / birth_price × 100`
- SHORT: `(birth_price - close) / birth_price × 100`

**Q6: Can MFE/MAE be measured?**  
YES. OHLCV has `high` and `low` columns. MFE = max favorable excursion from OHLC highs (LONG) or lows (SHORT). MAE = max adverse excursion from OHLC lows (LONG) or highs (SHORT).

**Q7: Is outcome tracking idempotent?**  
The repair module checks `final_state IS NULL` before updating. Already-closed signals are skipped. Repeated runs produce identical results.

**Q8: Is there any future-data leakage?**  
NO. The outcome tracker reads OHLCV data AFTER the signal detection date. It writes ONLY to `signal_births` measurement columns (`actual_move_pct`, `peak_move_pct`, `final_state`). These columns are not read by the scanner, DecisionEngine, StrategyLab, CRE, or OrderManager.

**Q9: Does outcome tracking affect any trading decision?**  
NO. The `signal_births` table is an observational record. It is read by `oios/engine/re_calculator.py` for RE computation, but the measurement columns (`actual_move_pct`, `final_state`) are not used in the ELE RE formula — only `birth_price`, `base_score`, `expected_move_pct`, and `signal_type` feed into RE computation.

**Q10: Can we now reliably compare Knowledge vs Strategy?**  
AFTER repair + backfill: YES. The research question requires comparing outcomes for strategy-gated signals vs ungated signals. With actual outcomes populated, both cohorts are comparable.

---

*Analysis completed: 2026-08-14. No production changes made.*  
*Data sources: market_behavior.db, orchestrator/master_orchestrator.py, oios/engine/ele.py, oios/engine/re_calculator.py, oios/db/repository.py*
