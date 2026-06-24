# OIOS Control Pipeline Certification

**Date:** 2026-06-24  
**Scope:** `build_controls_for_date()` + `compute_differentials()` daily wiring  
**Commit:** `f20483f`  
**VERDICT: `BUG_FIXED_AND_VERIFIED`**

---

## Audit Findings

### Caller Inventory

| Function | File | Callers |
|---|---|---|
| `build_controls_for_date(date, conn)` | `oios/phase_f/control_population.py:55` | `_run_post_market_scan()` (now wired), `_run_oios_weekly_research()` |
| `compute_differentials(date, conn)` | `oios/phase_f/differential_engine.py:56` | `_run_post_market_scan()` (now wired), `_run_oios_weekly_research()` |

### Root Cause

Both functions were written into `orchestrator/master_orchestrator.py` during the prior `OIOS_CONTROL_PIPELINE_AUDIT` session, but the response was **interrupted before `git commit` / `git push` / VPS deploy**. The local file had the 44-line addition (`git diff HEAD` confirmed); the remote (`origin/main`) and the VPS container did not.

The VPS ran the 2026-06-23 16:45 post-market scan with the old orchestrator binary, which executed:
- ✅ OHLCV refresh
- ✅ `update_outcomes()`
- ✅ `capture_daily_leaders()`
- ✅ `extract_features_batch()`
- ❌ `build_controls_for_date()` — **missing from VPS**
- ❌ `compute_differentials()` — **missing from VPS**

Result: `market_research_controls` and `feature_differentials` remained at `2026-06-22`.

---

## Fix Applied

**Commit `f20483f`** — `orchestrator/master_orchestrator.py` +44 lines

### Block 1 — `build_controls_for_date()` in `_run_post_market_scan()` (16:45 IST)

Inserted after `extract_features_batch()`, before `compute_differentials()`:

```python
try:
    from oios.db.connection import get_connection as _cp_daily_conn
    from oios.phase_f.control_population import build_controls_for_date as _cp_daily_build
    with _cp_daily_conn() as _cp_conn:
        _cp_trade_date = _cp_conn.execute(
            "SELECT MAX(trade_date) FROM ohlcv_daily"
        ).fetchone()[0]
        if _cp_trade_date:
            _cp_n = _cp_daily_build(_cp_trade_date, _cp_conn)
            log.info("[OIOS] control_population: date=%s controls=%d", _cp_trade_date, _cp_n)
except Exception as _cp_daily_exc:
    log.warning("[OIOS] control_population failed (non-critical): %s", _cp_daily_exc)
```

### Block 2 — `compute_differentials()` in `_run_post_market_scan()` (16:45 IST)

Inserted after `build_controls_for_date()`:

```python
try:
    from oios.db.connection import get_connection as _de_daily_conn
    from oios.phase_f.differential_engine import compute_differentials as _de_daily_diff
    with _de_daily_conn() as _de_conn:
        _de_trade_date = _de_conn.execute(
            "SELECT MAX(trade_date) FROM ohlcv_daily"
        ).fetchone()[0]
        if _de_trade_date:
            _de_n = _de_daily_diff(_de_trade_date, _de_conn)
            log.info("[OIOS] differential_engine: date=%s differentials=%d", _de_trade_date, _de_n)
except Exception as _de_daily_exc:
    log.warning("[OIOS] differential_engine failed (non-critical): %s", _de_daily_exc)
```

---

## Complete Daily 16:45 Execution Order (as of this fix)

```
_run_post_market_scan()  [16:45 IST]
  1. Phase D run_scan()
  2. UniverseGenerationAudit
  3. OHLCV refresh          (run_daily_fetch + run_daily_bhav_fetch)
  4. update_outcomes()       [commit 5d35a19]
  5. capture_daily_leaders() [commit d27e269]
  6. extract_features_batch()[commit dd26395]
  7. build_controls_for_date()[commit f20483f]  ← this fix
  8. compute_differentials() [commit f20483f]  ← this fix
  9. Layer 1A signal scan
 10. Layer 1B opportunity scan
```

---

## Verification

### Required SQL (from task)

```sql
SELECT MAX(trade_date) FROM market_research_controls;  → 2026-06-23
SELECT MAX(trade_date) FROM feature_differentials;     → 2026-06-23
```

### Row Counts (after backfill)

| Table | Before | After | Added |
|---|---|---|---|
| `market_research_controls` | 1500 (max 2026-06-22) | 1650 (max 2026-06-23) | +150 |
| `feature_differentials` | 1499 (max 2026-06-22) | 1647 (max 2026-06-23) | +148 |

---

## Backfill

Script `control_pipeline_backfill.py` run inside VPS container:
- Identified `2026-06-23` as the single missing date
- `build_controls_for_date('2026-06-23', conn)` → 150 control rows (INSERT OR IGNORE)
- `compute_differentials('2026-06-23', conn)` → 148 differential rows (INSERT OR REPLACE)

---

## Forward Automation

No further intervention required. The complete 8-step Phase F pipeline now runs daily at 16:45 IST. Each new trading day will:
1. Capture leaders for the latest OHLCV date
2. Extract 12 features per leader
3. Build control cohort (3–10 similar non-leaders per winner)
4. Compute winner-vs-control feature differentials with outcome gaps

**VERDICT: `BUG_FIXED_AND_VERIFIED`**
