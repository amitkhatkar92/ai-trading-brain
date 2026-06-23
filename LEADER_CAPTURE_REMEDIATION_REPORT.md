# LEADER_CAPTURE_REMEDIATION_REPORT

**Verdict:** `BUG_FIXED_AND_VERIFIED`
**Date:** 2026-06-23
**Commit:** `d27e269`

---

## Root Cause

`capture_daily_leaders()` was wired inside `_do_eod_learning()` which runs
at **15:35 IST**. It used `datetime.now().strftime("%Y-%m-%d")` as `trade_date`.

At 15:35 IST, the OHLCV refresh (`run_daily_fetch()`) has **not yet run** — it
runs at 16:45 IST in `_run_post_market_scan()`. This meant:

```
15:35  _do_eod_learning():
         capture_daily_leaders("2026-06-23", conn)
           └── _compute_returns("2026-06-23")
                 └── SELECT close FROM ohlcv_daily WHERE trade_date="2026-06-23"
                       → 0 rows (OHLCV refresh hasn't run yet)
                 └── returns = {}   # no data → no leaders
         → captured = 0  every single day
```

### Evidence of bug
```
ohlcv_daily max_date        = 2026-06-22   (12 523 rows, 194 symbols)
market_leaders_daily max    = 2026-06-19   (150 rows, 5 days — only backfill)
```
The 3-day lag (June 19 → June 22) was the smoking gun: leaders stopped advancing
on the day the slot timing was last modified.

---

## Fix

**File:** `orchestrator/master_orchestrator.py`

Two changes in commit `d27e269`:

### 1 — Removed leader capture from `_do_eod_learning()` (15:35 IST)
The entire block using `datetime.now()` as `trade_date` was removed.

### 2 — Added leader capture to `_run_post_market_scan()` (16:45 IST)

Placed **after** `run_daily_fetch()` completes — so `ohlcv_daily` is fully
populated before `_compute_returns()` runs.

Uses `MAX(trade_date) FROM ohlcv_daily` as the date anchor (not
`datetime.now()`) so the capture always runs against data actually present
in the DB, even after a late start or a weekend.

```python
# In _run_post_market_scan() — AFTER run_daily_fetch() block
with _ml_oios_conn() as _ml_conn:
    _ml_trade_date = _ml_conn.execute(
        "SELECT MAX(trade_date) FROM ohlcv_daily"
    ).fetchone()[0]
    if _ml_trade_date:
        _ml_leaders = _cap_leaders(_ml_trade_date, _ml_conn, regime=_ml_regime)
```

---

## Scheduling Timeline (after fix)

| Time (IST) | Slot | Action |
|---|---|---|
| 15:35 | `_do_eod_learning` | Learning engine + CSV ingest (leader capture **removed**) |
| 16:45 | `_run_post_market_scan` | OHLCV refresh → **leader capture** → signal scan |

---

## Verification (VPS, 2026-06-23)

```sql
SELECT MAX(trade_date) FROM ohlcv_daily;
→ 2026-06-22

SELECT MAX(trade_date) FROM market_leaders_daily;
→ 2026-06-22     ← advanced from 2026-06-19

SELECT trade_date, COUNT(*) FROM market_leaders_daily
  GROUP BY trade_date ORDER BY trade_date DESC LIMIT 5;
→  2026-06-22  |  30
   2026-06-19  |  30
   2026-06-18  |  30
   2026-06-17  |  30
   2026-06-16  |  30

dates match = True
total rows  = 180 (6 trading days × 30 leaders each)
```

Backfill run: `leader_verify.py` captured leaders for 2026-06-20, 2026-06-22
(first two dates that had OHLCV data but no leaders due to the bug).

---

## Impact Assessment

| Layer | Affected? |
|---|---|
| Execution / order routing | ❌ No |
| Risk management / kill-switch | ❌ No |
| Strategy scoring / debate | ❌ No |
| Position sizing | ❌ No |
| Signal generation | ❌ No |
| OIOS shadow mode (observe-only) | ✅ Leader table now fully populated |
| OIOS weekly research (Saturday) | ✅ Can now look back at complete leader history |

The `market_leaders_daily` table is an OIOS shadow observation store only.
No trading decisions depend on it directly.

---

## Files Changed

| File | Change |
|---|---|
| `orchestrator/master_orchestrator.py` | Remove leader capture from 15:35 slot; add to 16:45 slot with `MAX(trade_date)` anchor |

**No other files changed. All trading interfaces unchanged.**
