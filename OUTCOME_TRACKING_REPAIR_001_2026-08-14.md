# OUTCOME_TRACKING_REPAIR_001
## Signal Outcome Tracking Repair — Final Report
**Date:** 2026-08-14  
**Task:** OUTCOME_TRACKING_REPAIR_001  
**Verdict:** `OUTCOME_TRACKING_REPAIRED_BACKFILL_PENDING`

---

## 1. Problem Statement

All 3,335 signal records in `signal_births` had:
- `actual_move_pct = 0.0` (write-once at creation, never updated)
- `final_state = NULL` (no production code writes this field)

This made outcome tracking non-functional. Signal performance could not be measured and the Knowledge vs Strategy comparison (KNOWLEDGE_VS_STRATEGY_VALUE_AUDIT_001) could not be validated at signal level.

---

## 2. Root Cause Analysis

### Root Cause #1 — PRIMARY: `run_ele_daily()` Never Called

The Edge Lifecycle Engine (`oios/engine/ele.py`) was designed to advance signal lifecycle and compute outcomes. However, zero grep matches exist for `run_ele_daily` in `orchestrator/master_orchestrator.py`. The ELE is fully implemented but never invoked.

**Evidence:**
```
grep -r "run_ele_daily" orchestrator/ → 0 matches
```

Without ELE execution: all opportunities remain in `DISCOVERED` state, `age_trading_days = 0`, no state transitions occur.

### Root Cause #2 — STRUCTURAL: No Write-Back to `signal_births.actual_move_pct`

Even when ELE runs (in tests), it stores its computed `actual_move` in `opportunities.edge_consumed_pct`, not in `signal_births.actual_move_pct`. The `actual_move_pct` column in signal_births is effectively write-once (set to 0.0 at row creation via `create_signal_birth()`).

**Evidence:**
```sql
-- Only test fixtures ever write signal_births measurement columns:
-- test_phase_d.py line 88: UPDATE signal_births SET final_state=...
-- test_phase_e.py line 590: UPDATE signal_births SET actual_move_pct=...
-- Zero production code paths found
```

### Root Cause #3 — INFRASTRUCTURE: `trading_calendar` Has 0 Rows

The ELE conviction calculation queries `trading_calendar` to compute signal age in trading days. With 0 rows, all signals appear to be 0 trading days old, so TTL expiry never triggers.

**Evidence:**
```sql
SELECT COUNT(*) FROM trading_calendar → 0
```

### Root Cause #4 — CONSEQUENCE: `final_state` Stays NULL

No production code path writes to `signal_births.final_state`. The ELE's state machine writes `final_state` onto the in-memory `Opportunity` object which is then persisted to the `opportunities` table — not to `signal_births`.

---

## 3. Repair Design

### Approach

A standalone measurement module (`oios/engine/signal_outcome_tracker.py`) reconstructs outcomes directly from `ohlcv_daily` OHLC data, bypassing the broken ELE → opportunities pipeline entirely.

**Design constraints:**
- Read: `signal_births` + `ohlcv_daily` only
- Write: `signal_births` measurement columns only
- Never touches: `opportunities`, `decision_log`, `ct_decisions`, learning systems, CRE, OrderManager, Dhan API
- Idempotent: `WHERE final_state IS NULL` guard on all writes
- Future-safe: observation window is `(detected_at, min(detected_at + ttl, as_of_date)]`

### Direction-Aware Formulas

**LONG direction:**
| Metric | Formula |
|--------|---------|
| `actual_move_pct` | `(close_at_end - birth_price) / birth_price × 100` |
| `peak_move_pct` (MFE) | `max((high - birth_price) / birth_price × 100)` over window |
| `max_adverse_pct` (MAE) | `min((low - birth_price) / birth_price × 100)` — negative = adverse |

**SHORT direction:**
| Metric | Formula |
|--------|---------|
| `actual_move_pct` | `(birth_price - close_at_end) / birth_price × 100` |
| `peak_move_pct` (MFE) | `max((birth_price - low) / birth_price × 100)` over window |
| `max_adverse_pct` (MAE) | `min((birth_price - high) / birth_price × 100)` — negative = adverse |

### Final State Taxonomy

| State | Condition |
|-------|-----------|
| `WIN` | `peak_move_pct >= expected_move_pct × 0.5` (half-target reached) |
| `LOSS` | TTL exhausted AND `actual_move_pct < 0` |
| `EXPIRED` | TTL exhausted AND `actual_move_pct >= 0` AND target not reached |
| `PENDING` | Signal still within TTL |
| `NO_DATA` | Required OHLCV data unavailable |

---

## 4. Backfill Preview Results (Dry-Run)

**Total signals:** 3,335  
**as_of_date:** 2026-08-13  
**Mode:** `dry_run=True` — no database records were modified  

| Outcome | Count | % |
|---------|-------|---|
| WIN | 1,046 | 31.4% |
| LOSS | 934 | 28.0% |
| EXPIRED | 268 | 8.0% |
| PENDING | 1,005 | 30.1% |
| NO_DATA | 82 | 2.5% |
| Errors | 0 | 0.0% |

**Win rate (closed signals only):** 46.5%  
**Reconstruction feasibility:** 3,253 / 3,335 signals (97.5%)

---

## 5. Questions Answered (Q1–Q10)

**Q1: Why is `actual_move_pct = 0.0` for all signals?**  
No `UPDATE signal_births SET actual_move_pct` path exists in any production code. `create_signal_birth()` inserts `0.0` as the initial value, and nothing ever updates it. The ELE computes `actual_move` but stores it in `opportunities.edge_consumed_pct`.

**Q2: Why is `final_state = NULL` for all signals?**  
`run_ele_daily()` is never called from the orchestrator (zero grep matches). Even if it were called, the ELE's state machine writes `final_state` to the `Opportunity` domain object → `opportunities` table, not to `signal_births`.

**Q3: Can historical outcomes be reconstructed?**  
**YES.** 100% OHLCV coverage for all 209 signal symbols. Signal data spans 2026-06-22 to 2026-08-14 and all required daily OHLC bars exist. 97.5% of signals fully resolvable.

**Q4: Can future outcomes be recorded going forward?**  
**YES.** `run_daily_outcome_resolution(conn)` can be called from the orchestrator after each OHLCV refresh. Idempotent — safe to call on every trading day.

**Q5: Are LONG and SHORT directions handled correctly?**  
**YES.** Direction-aware formulas implemented. LONG: profit = upward move. SHORT: profit = downward move. Validated by tests B (LONG) and C (SHORT).

**Q6: Can MFE and MAE be measured?**  
**YES.** MFE from daily `high` (LONG) or `low` (SHORT). MAE from daily `low` (LONG) or `high` (SHORT). Validated by tests D (MFE) and E (MAE).

**Q7: Is tracking idempotent?**  
**YES.** `_write_outcome()` uses `WHERE signal_id = ? AND final_state IS NULL` — already-resolved signals are never overwritten. Tested in G (duplicate signal), H (repeated EOD), and I (restart safety).

**Q8: Is there any future-data leakage?**  
**NO.** Observation window uses exclusive start: `trade_date > detected_at AND trade_date <= min(detected_at+ttl, as_of_date)`. Pre-signal prices cannot contaminate MFE/MAE calculations. Validated by test J.

**Q9: Does outcome tracking affect trading decisions?**  
**NO.** The measurement columns (`actual_move_pct`, `peak_move_pct`, `max_adverse_pct`, `final_state`) are not read by `re_calculator.compute_re()`, `DecisionEngine`, `strategy_lab`, `CapitalRiskEngine`, or `OrderManager`. The module has no imports from any of those subsystems. Verified by source inspection (tests N, O, P, Q, R).

**Q10: Can we now compare Knowledge vs Strategy signal performance?**  
**YES.** After backfill, `signal_births.final_state` can be joined with `archetype_id` and the knowledge feature columns to compute win rates broken down by:
- Knowledge combination (sector context, regime, volume)
- Archetype type (1A vs 1B vs 52W-HIGH)
- Signal direction (LONG vs SHORT)

This enables the signal-level validation layer for KNOWLEDGE_VS_STRATEGY_VALUE_AUDIT_001.

---

## 6. Files Produced

| File | Status | Purpose |
|------|--------|---------|
| `OUTCOME_TRACKING_ROOT_CAUSE_001_2026-08-14.md` | ✅ Complete | Root cause analysis (Q1-Q10) |
| `oios/engine/signal_outcome_tracker.py` | ✅ Complete | Repair module (measurement only) |
| `OUTCOME_TRACKING_BACKFILL_PREVIEW_001.json` | ✅ Complete | Dry-run preview, 3,335 signals |
| `outcome_tracking_results.json` | ✅ Complete | Aggregate metrics and verdict |
| `test_outcome_tracking_001.py` | ✅ Complete | 43 tests (42 PASS, 1 SKIP) |
| `OUTCOME_TRACKING_REPAIR_001_2026-08-14.md` | ✅ This file | Final report |

---

## 7. Test Results

**Suite:** `test_outcome_tracking_001.py`  
**Environment:** VPS (Python 3.14, docker)  
**Result: 42/43 PASS, 0 FAIL, 1 SKIP**

| Test | Description | Result |
|------|-------------|--------|
| A | Signal birth captured | PASS |
| B1-B3 | LONG outcome (actual, MFE, MAE) | PASS |
| C1-C3 | SHORT outcome (actual, MFE, MAE) | PASS |
| D1-D2 | MFE correct + days_to_peak | PASS |
| E1 | MAE correct | PASS |
| F1-F4 | Missing OHLC handled safely | PASS |
| G1-G3 | Duplicate signal idempotency | PASS |
| H1-H2 | Repeated EOD idempotency | PASS |
| I1-I3 | Restart safety | PASS |
| J1-J2 | No future data leakage | PASS |
| K1 | Ambiguous/pending handled | PASS |
| L1-L6 | Taxonomy preserved | PASS |
| M1-M3 | Historical reconstruction | PASS |
| N1 | No DecisionEngine import | PASS |
| O1 | No StrategyLab import | PASS |
| P1 | No CRE import | PASS |
| Q1 | No OrderManager import | PASS |
| R1 | No Dhan API call | PASS |
| S1 | Live future signal path | PASS |
| T1-T2 | Backfill preview is read-only | PASS |
| T3 | Preview JSON content | SKIP (local file not on VPS) |

---

## 8. Next Steps (Require Explicit Approval)

### Step 1: Execute Historical Backfill (requires approval)
```python
# Run on VPS — writes actual outcomes to signal_births
from oios.engine.signal_outcome_tracker import run_daily_outcome_resolution
from oios.db.connection import get_connection

with get_connection() as conn:
    summary = run_daily_outcome_resolution(conn, as_of_date="2026-08-13")
    print(summary)
```
Expected: 3,253 signals resolved (0 errors)

### Step 2: Wire Daily Resolution to Orchestrator (requires approval)
Add one call to `master_orchestrator.py` after daily OHLCV refresh:
```python
# In _do_eod_learning() or equivalent, after OHLCV refresh:
from oios.engine.signal_outcome_tracker import run_daily_outcome_resolution
summary = run_daily_outcome_resolution(self._oios_conn)
self._log.info("[EOD] Outcome resolution: %s", summary)
```

### Step 3: Signal-Level KvS Analysis (after backfill)
Use `signal_births.final_state` + `archetype_id` to compute knowledge-segmented win rates for KNOWLEDGE_VS_STRATEGY_VALUE_AUDIT_001 validation.

---

## 9. Verdict

**`OUTCOME_TRACKING_REPAIRED_BACKFILL_PENDING`**

The repair module is complete, isolated, and validated. All 42 executable tests pass. The module can reconstruct 3,253 historical outcomes (97.5%) and record all future outcomes in daily operation. The historical backfill and orchestrator wiring are pending explicit approval to execute.
