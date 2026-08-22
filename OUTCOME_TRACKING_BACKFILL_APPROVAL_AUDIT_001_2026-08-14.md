# OUTCOME_TRACKING_BACKFILL_APPROVAL_AUDIT_001
## Pre-Backfill Approval Audit — Final Report
**Date:** 2026-08-14  
**Audit ID:** OUTCOME_TRACKING_BACKFILL_APPROVAL_AUDIT_001  
**Baseline:** 3,335 signals — all `final_state IS NULL` — confirmed clean  
**Test Suite:** 43/43 PASS — 0 FAIL — 0 SKIP

---

## Verdict

**`BACKFILL_APPROVED_WITH_LIMITATIONS`**

Three limitations documented below. None affect trading decisions. None are blockers.

---

## 1. PENDING Audit

**Total PENDING signals: 1,005**

| Reason | Count | Explanation |
|--------|-------|-------------|
| `WITHIN_TTL_BY_CALENDAR` | 986 | Signal genuinely within its TTL as of today (2026-08-14) |
| `WITHIN_TTL_BY_ASOF` | 19 | as_of_date (2026-08-13) is one day behind today; these signals expired 2026-08-14 but not at as_of |

**TTL distribution:**

| TTL | Count |
|-----|-------|
| 10 days | 366 |
| 18 days | 639 |

**Date range of PENDING signals:** 2026-07-27 → 2026-08-12  
**Oldest PENDING:** detected 2026-07-27 (TTL=18 → expires 2026-08-14 = today)  
**Most recent PENDING:** detected 2026-08-12 (TTL=10 → expires 2026-08-22)

**Assessment:** All 1,005 PENDING signals are legitimately PENDING. There are no false positives. Signals will resolve naturally as `as_of_date` advances with each daily OHLCV refresh. The 19 "within TTL at as_of" signals will resolve in the next run tomorrow.

**Recommendation:** Do not force-resolve PENDING to WIN/LOSS/EXPIRED. Allow natural resolution.

---

## 2. NO_DATA Audit

**Total NO_DATA signals: 82**

| Category | Count |
|----------|-------|
| A. Missing OHLC in window | 0 |
| B. Symbol not in ohlcv_daily | 0 |
| C. Invalid timestamp | 0 |
| D. Outside available market history | **82** |
| E. Corrupted / incomplete record | 0 |
| F. Other | 0 |

**Cause:** All 82 signals were detected on `2026-08-13` = `MAX(trade_date)` in ohlcv_daily. The observation window starts exclusive of `detected_at`, so we need data for `trade_date > 2026-08-13`. No such data exists yet — the 2026-08-14 close has not been loaded.

**Example:**
```
symbol:       SBIN.NS
detected_at:  2026-08-13
ohlcv_max:    2026-08-13
window_end:   2026-08-23 (TTL=10)
OHLCV in window: 0 rows → NO_DATA (correct)
```

**Assessment:** All 82 NO_DATA signals are correctly classified. They are today's freshest signals awaiting tomorrow's price data. No data correction required.

**Recommendation:** NO_DATA remains NO_DATA. Will resolve automatically after the next OHLCV refresh loads 2026-08-14 data.

---

## 3. WIN/LOSS Sample Validation

**Samples:** 20 WIN + 20 LOSS + 10 EXPIRED = 50 total (RNG seed=42, reproducible)

**Result: 0 discrepancies in 50 samples**

Each sample was independently recomputed from raw `ohlcv_daily`:

| Check | Result |
|-------|--------|
| Signal direction matches DB | PASS × 50 |
| Entry == birth_price | PASS × 50 |
| Observation window = (detected_at, min(detected_at+ttl, as_of)] | PASS × 50 |
| actual_move_pct recomputed (< 0.01 pp tolerance) | PASS × 50 |
| MFE recomputed | PASS × 50 |
| MAE recomputed | PASS × 50 |
| final_state recomputed by taxonomy rules | PASS × 50 |

All 50 samples match independent recomputation exactly. Formulas are correct.

---

## 4. Backfill Mutation Safety

**Write-only columns (7 fields):**
```
actual_move_pct, peak_move_pct, max_adverse_pct,
days_to_peak, final_state, final_age_trading_days, last_updated_at
```

**Immutable columns — verified NOT in write set:**
```
signal_id, symbol, archetype_id, archetype_version, signal_type,
detected_at, birth_price, base_score, regime_at_birth,
expected_ttl_days, expected_move_direction, expected_move_pct,
expected_move_pct_source, current_state, age_trading_days,
edge_consumed_pct, trade_executed
```

**Overlap:** zero

**UPDATE guard:** `WHERE signal_id = ? AND final_state IS NULL`

**Columns backfill CANNOT touch:**
- Original signal timestamp (`detected_at`)
- Symbol, direction (`expected_move_direction`), entry (`birth_price`)
- Strategy (`archetype_id`, `archetype_version`)
- Scanner score (`base_score`), knowledge score (`consensus_score_at_birth`)
- RE score (`re_score`), decision score
- Execution state (`trade_executed`), order IDs

**Assessment: MUTATION SAFE — CONFIRMED**

---

## 5. Original Signal Immutability

**Methodology:** SHA-256 hash over all 17 immutable columns for each of the 3,335 signals. Computed before and after dry-run.

**Result:** 0 hash changes after dry-run.  
**Immutability: CONFIRMED**

The exact UPDATE statement used in production:
```sql
UPDATE signal_births
SET actual_move_pct        = ?,
    peak_move_pct          = ?,
    max_adverse_pct        = ?,
    days_to_peak           = ?,
    final_state            = ?,
    final_age_trading_days = ?,
    last_updated_at        = ?
WHERE signal_id = ?
  AND final_state IS NULL
```

This statement cannot modify any of the 17 immutable columns. The `AND final_state IS NULL` guard additionally prevents overwriting previously resolved signals.

---

## 6. Feedback-Loop Isolation

### Consumers of measurement fields

**Fields investigated:** `actual_move_pct`, `peak_move_pct`, `max_adverse_pct`, `final_state`

| Consumer | Type | Reads | Writes to | Trading impact |
|----------|------|-------|-----------|----------------|
| `oios/engine/shadow_scorer.py` | Phase E1 analytics | `signal_births.final_state, peak_move_pct` | `shadow_cause_outcomes` only | **NONE** |
| `oios/engine/adaptive_intelligence.py` | Phase D analytics | `signal_births.final_state IS NOT NULL, peak_move_pct` | `pending_adjustments (PENDING, human-approved)` | **NONE** |
| `oios/engine/outcome_distributor.py` | Statistical analysis | All 3 fields | Analytics outputs | **NONE** |
| `oios/engine/counterfactual_engine.py` | Counterfactual analysis | `final_state, peak_move_pct` | Analysis results | **NONE** |
| `oios/reporting/weekly_report.py` | Reporting | `final_state` | Report strings | **NONE** |
| `oios/engine/re_calculator.py` | ELE (not called) | `actual_move_pct` as function parameter | EC path (not from DB) | **NONE** |

**Key verification:** `grep "shadow_scorer\|outcome_distributor\|adaptive_intelligence\|e_readiness" orchestrator/master_orchestrator.py` → **0 matches**

None of these consumers are in the trading decision path. The orchestrator does not call any of them.

### Shadow scorer detail

`shadow_scorer.py` reads `signal_births.final_state` to propagate outcomes to `shadow_cause_outcomes`. Its contract: *"OS_shadow is NEVER written to opportunities.conviction_score, NEVER passed to the state machine, NEVER visible to the execution engine."* Confirmed by code inspection.

### Adaptive intelligence detail

Outputs only to `pending_adjustments` with `status='PENDING'`, requiring explicit human `/approve` command before any parameter is changed. Cannot autonomously affect trading.

### Conclusion

**No feedback path to trading decisions exists. ISOLATED — CONFIRMED.**

### Taxonomy mismatch (pre-existing, not introduced by backfill)

Existing reporting modules (`weekly_report.py`, `phase_e_shadow.py`) query `signal_births.final_state = 'TTL_EXHAUSTED'` and `final_state = 'INVALID'` (ELE taxonomy). The new tracker writes `WIN`/`LOSS`/`EXPIRED`/`PENDING`/`NO_DATA`.

**Before backfill:** Reports return 0 (all NULL).  
**After backfill:** Reports return 0 (values are WIN/LOSS/etc., not TTL_EXHAUSTED/INVALID).  
**Net change to reports:** none. This is a pre-existing gap — the ELE was never called.

---

## 7. T3 Test

**Root cause:** Preview JSON was generated to `/tmp/OUTCOME_TRACKING_BACKFILL_PREVIEW_001.json` and not copied to the working directory `/root/ai-trading-brain/`.

**Fix applied:**
```bash
cp /tmp/OUTCOME_TRACKING_BACKFILL_PREVIEW_001.json /root/ai-trading-brain/
```

No test logic was weakened. T3 now verifies the preview JSON contains actual signal data.

**Result:** 43/43 PASS — 0 FAIL — 0 SKIP

---

## 8. Backfill Idempotency

**Method:** DB copied to tempfile, resolver run 3 times.

| Run | total | resolved | no_data | notes |
|-----|-------|----------|---------|-------|
| 1 | 3,319 | 3,253 | 66 | All resolvable signals written |
| 2 | 66 | 0 | 66 | Zero additional writes |
| 3 | 66 | 0 | 66 | Zero additional writes |

**IDEMPOTENCY CONFIRMED:** `run2.resolved == 0`, `run3.resolved == 0`

**Note on 3,319 vs 3,335:** The idempotency copy was made during the audit run. The live scanner created 16 new signals after the copy was made; those signals appear in today's current total (3,335). All 3,335 currently have `final_state IS NULL` — confirmed. Full backfill will process all 3,335.

**Note on 66 remaining NULL:** These are NO_DATA signals (detected on 2026-08-13). The resolver correctly does not write to them — there is no outcome to record. They will resolve when tomorrow's OHLCV data arrives.

---

## 9. Daily Resolution Readiness

| Property | Status |
|----------|--------|
| Auto as_of_date detection | CONFIRMED — `MAX(trade_date) FROM ohlcv_daily` |
| Observation window | `(detected_at, min(detected_at+ttl, as_of_date)]` — future-safe |
| Idempotency | CONFIRMED — `WHERE final_state IS NULL` guard |
| Restart safety | CONFIRMED — test I: second run after restart = 0 writes |
| Missing OHLCV | Returns NO_DATA, no crash, no write (test F) |
| PENDING handling | Writes PENDING for within-TTL; idempotent (test G) |
| Exception handling | Per-signal try/except — single failure does not abort batch |
| Trading decision impact | NONE |

The function is ready for orchestrator integration. Not wired yet pending approval.

---

## Limitations

### L1: Taxonomy Mismatch (LOW severity, no trading impact)

The new tracker writes `WIN`/`LOSS`/`EXPIRED`/`PENDING`/`NO_DATA`. Existing reporting modules expect `TTL_EXHAUSTED`/`INVALID` (ELE's state machine taxonomy). After backfill, reports that query for ELE taxonomy values will return 0 — the same as today. This is a pre-existing design gap. No new risk introduced.

### L2: NO_DATA Signals Stay NULL (by design)

82 signals detected on 2026-08-13 will remain `final_state IS NULL` after backfill. They cannot be resolved until the next OHLCV refresh provides 2026-08-14 data. This is correct behaviour. The post-backfill state will be: 3,253 resolved + 82 awaiting next price bar.

### L3: PENDING Signals Written as PENDING

1,005 within-TTL signals will have `final_state = 'PENDING'` after backfill. This is correct. They will advance to WIN/LOSS/EXPIRED as `as_of_date` advances in daily resolution runs. The idempotency guard prevents double-writes.

---

## Blockers

**None.**

---

## Pending Actions (require explicit approval)

1. **Execute historical backfill** — run `resolve_signal_outcomes(conn, '2026-08-13', dry_run=False)` on VPS production DB. Expected: 3,253 signals resolved.
2. **Wire daily resolver to orchestrator** — add one call to `run_daily_outcome_resolution(conn)` in `_do_eod_learning()`. Expected: PENDING signals advance naturally; new signals tracked from next day.

---

## Verdict

**`BACKFILL_APPROVED_WITH_LIMITATIONS`**

All critical checks pass:
- PENDING: all legitimate ✓
- NO_DATA: all explainable (brand-new signals) ✓  
- Validation: 0/50 discrepancies ✓
- Mutation safety: zero immutable columns in write set ✓
- Immutability: 3,335 signal hashes unchanged ✓
- Feedback loop: no trading decision path affected ✓
- Idempotency: run 2 and 3 both produce 0 additional writes ✓
- Daily readiness: confirmed ✓
- Test suite: **43/43 PASS** ✓

Limitations L1–L3 are documented, non-blocking, and non-trading.

The historical backfill and daily resolution wiring are ready for execution upon explicit approval.
