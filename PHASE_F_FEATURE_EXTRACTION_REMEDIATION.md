# PHASE_F_FEATURE_EXTRACTION_REMEDIATION

**Verdict:** `FIXED_AND_VERIFIED`
**Date:** 2026-06-23
**Commit:** `dd26395`

---

## Evidence (Pre-Fix)

```
market_leaders_daily     = 300  ✅
market_leader_outcomes   = 300  ✅
market_leader_features   =   0  ❌  — the bug
feature_differentials    =   0  ❌  — blocked by above
```

---

## Root Cause

`extract_features_batch()` (Phase F1.3) was wired **only** inside
`_run_oios_weekly_research()`, which runs at **17:30 IST on Saturdays**.

The 16:45 IST daily post-market slot:
```
capture_daily_leaders()  → market_leaders_daily   ✅ working
                             ↓
extract_features_batch() → market_leader_features  ❌ NOT CALLED
```

Without features in `market_leader_features`:

| Downstream step | Impact |
|---|---|
| `control_population.build_controls_for_date()` | `_compute_fingerprint()` reads `market_leader_features` → returns empty dict → fingerprint hash = hash("") → all candidates match with same score → controls built but not meaningful |
| `differential_engine.compute_differentials()` | `_load_all_winner_features()` returns `{}` → diff matrix is empty → 0 rows inserted |

Both were stuck at 0 forever as long as features never existed.

### Why it wasn't caught earlier

Saturday's `_run_oios_weekly_research()` calls `extract_features_batch()`
but the system had never reached a Saturday since leaders were first
backfilled. Even on the first Saturday after wiring, the code would
have worked — but only once a week, leaving 5 days of leaders with no
features.

---

## Fix

**File:** `orchestrator/master_orchestrator.py`

Added feature extraction immediately after leader capture in
`_run_post_market_scan()` (16:45 IST):

```python
# ── OIOS Phase F1.3 — feature extraction for today's leaders ─────────
# Runs immediately after leader capture so features are always available
# before control-population (Saturday) needs them for fingerprinting.
try:
    from oios.phase_f import feature_extractor as _fe_mod
    with _fe_oios_conn() as _fe_conn:
        _fe_trade_date = _fe_conn.execute(
            "SELECT MAX(trade_date) FROM ohlcv_daily"
        ).fetchone()[0]
        if _fe_trade_date:
            _fe_leaders = [...]  # SELECT from market_leaders_daily WHERE trade_date=?
            _fe_mod.extract_features_batch(_fe_leaders, _fe_conn)
```

Uses `INSERT OR REPLACE` → idempotent. Saturday weekly research continues
to re-run `extract_features_batch()` — safe because existing rows are
replaced (not duplicated).

---

## Scheduling Timeline (after fix)

| Time (IST) | Slot | Phase F action |
|---|---|---|
| 16:45 daily | `_run_post_market_scan` | OHLCV → leaders → **features** → signal scan |
| 17:30 Saturday | `_run_oios_weekly_research` | features → controls → **differentials** |

---

## Backfill

`phase_f_backfill.py` was run inside the container to populate all
10 historical trading dates:

| Step | Action | Result |
|---|---|---|
| Feature extraction | `extract_features_batch()` × 10 dates | 3600 rows (30 leaders × 12 features × 10 dates) |
| Control population | `build_controls_for_date()` × 10 dates | 1500 rows (150 controls/date) |
| Differentials | `compute_differentials()` × 10 dates | 1499 rows (one date had 1 skipped due to `MIN_SIMILARITY_FOR_DIFF=0.50`) |

---

## VPS Verification (2026-06-23, post-fix)

```sql
SELECT COUNT(*) FROM market_leaders_daily;
→ 300

SELECT COUNT(*) FROM market_leader_features;
→ 3600   (was 0)

SELECT COUNT(*) FROM market_research_controls;
→ 1500   (was 0)

SELECT COUNT(*) FROM feature_differentials;
→ 1499   (was 0)

SELECT COUNT(*) FROM market_leader_outcomes;
→ 300    (unchanged)
```

By trading date (all 10 dates):
```
2026-06-22  leaders=30  features=30  controls=150  diffs=150
2026-06-19  leaders=30  features=30  controls=150  diffs=150
2026-06-18  leaders=30  features=30  controls=150  diffs=150
2026-06-17  leaders=30  features=30  controls=150  diffs=150
2026-06-16  leaders=30  features=30  controls=150  diffs=150
2026-06-15  leaders=30  features=30  controls=150  diffs=150
2026-06-12  leaders=30  features=30  controls=150  diffs=150
2026-06-11  leaders=30  features=30  controls=150  diffs=150
2026-06-10  leaders=30  features=30  controls=150  diffs=149
2026-06-09  leaders=30  features=30  controls=150  diffs=150
```

---

## Impact Assessment

| Layer | Affected? |
|---|---|
| Execution / order routing | ❌ No |
| Risk management / kill-switch | ❌ No |
| Strategy scoring / debate | ❌ No |
| Position sizing | ❌ No |
| Signal generation | ❌ No |
| OIOS shadow mode (observe-only) | ✅ Phase F research pipeline now fully operational |
| Weekly differential research | ✅ Saturday run will now find all features pre-populated |

All Phase F tables are shadow-only (observe/record). No trading decisions
depend on them.

---

## Files Changed

| File | Change |
|---|---|
| `orchestrator/master_orchestrator.py` | Added `extract_features_batch()` wiring in `_run_post_market_scan()` after leader capture |
| `phase_f_backfill.py` | One-time backfill script (features → controls → differentials for 10 dates) |

**No other files changed. All trading interfaces unchanged.**

---

## Success Criteria — Met

| Criterion | Result |
|---|---|
| `market_leader_features > 0` | ✅ 3600 rows |
| `feature_differentials > 0` | ✅ 1499 rows |
| All prerequisites (features → controls → diffs) | ✅ Full pipeline verified |
