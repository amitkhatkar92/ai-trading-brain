# MOVER_DISCOVERY_V3_SHADOW_AUDIT_001
**Status:** READ-ONLY — OBSERVATION ONLY  
**Date:** 2026-08-17  
**Audit ID:** MOVER_DISCOVERY_V3_SHADOW_AUDIT_001  
**Author:** Automated audit pipeline (no human edits)

---

## 1. Executive Summary

V3 shadow pipeline executed **2 successful runs** over the audit window (2026-08-13 → 2026-08-17).  
Technical health is **EXCELLENT** — zero crashes, zero leakage violations, zero production side-effects.  
Statistical verdict: **INSUFFICIENT_SAMPLE_CONTINUE** — 1 day of T+1 outcomes and 40 resolved data points cannot support any performance conclusion.  
Shadow observation must continue for a minimum of **20 more trading days** before any promotion decision.

---

## 2. Audit Window

| Parameter | Value |
|---|---|
| Audit start | 2026-08-13 (trading day) |
| Audit end | 2026-08-17 (report date) |
| Expected Phase D runs | 2 (2026-08-13, 2026-08-14) |
| Actual successful runs | 2 |
| NSE holidays in window | 1 (2026-08-15 Independence Day) |
| Weekend days in window | 1 (2026-08-16 Saturday) |
| Shadow JSONL size | 82 lines / 45,976 bytes |

---

## 3. Daily Run Health

| Date | Day | Expected? | Run? | Outcome |
|---|---|---|---|---|
| 2026-08-13 | Wednesday | YES | ✅ YES | PASS — 20 UP + 20 DOWN |
| 2026-08-14 | Thursday  | YES | ✅ YES | PASS — 20 UP + 20 DOWN |
| 2026-08-15 | Friday    | NO  | ✅ SKIPPED | NSE HOLIDAY — Phase D correctly skipped at 16:45 |
| 2026-08-16 | Saturday  | NO  | ✅ SKIPPED | WEEKEND — no Phase D slot |
| 2026-08-17 | Sunday    | NO  | ✅ SKIPPED | WEEKEND — report date |

**Schedule health: PERFECT — 0 unexpected skips, 0 unexpected runs.**

> **GAP_001 (Known, Accepted):** WeekendResearch calls `run_scan()` directly and bypasses `_run_post_market_scan()`. V3 shadow does NOT execute during Saturday intelligence cycles. This is correct behavior — the Saturday cycle does not constitute a valid Phase D run. No action required.

---

## 4. Pool Verification

| Metric | Run 1 (2026-08-13) | Run 2 (2026-08-14) | Required |
|---|---|---|---|
| UP pool size | 20 | 20 | 20 |
| DOWN pool size | 20 | 20 | 20 |
| Total candidates | 40 | 40 | 40 |
| Universe processed | 200 | 199 | ≥100 |
| Duplicate symbols in UP | 0 | 0 | 0 |
| Duplicate symbols in DOWN | 0 | 0 | 0 |
| UP/DOWN overlap | 0 | 0 | 0 |

**Pool health: ALL CLEAN.**

---

## 5. Ranking Verification

| Metric | Run 1 | Run 2 | Required |
|---|---|---|---|
| Ranks cover 1-20 exactly | YES | YES | YES |
| Scores strictly descending | YES | YES | YES |
| NaN or None scores | 0 | 0 | 0 |
| Rank-1 UP score | 0.8814 | N/A (Run2 T+1 not reached) | >0 |
| Rank-1 DOWN score | 0.7312 (adversely moved UP +6.5%) | N/A | >0 |

**Ranking health: CLEAN.**

---

## 6. Data Freshness

| Run | Execution Timestamp (UTC) | Trading Date Used | Lag |
|---|---|---|---|
| Run 1 | 2026-08-14T11:18:59Z | 2026-08-13 | 1 calendar day (expected) |
| Run 2 | 2026-08-17T02:34:24Z | 2026-08-14 | 3 calendar / 1 trading day (Aug15=holiday, Aug16=weekend) |

**Freshness: ACCEPTABLE.** Both lags reflect correct Phase D post-market behavior. No stale data beyond expected settlement lag.

---

## 7. Future-Data Leakage Check

| Category | Count | Result |
|---|---|---|
| Forbidden keys scanned | 20 (see FORBIDDEN_FUTURE_KEYS set) | 0 violations |
| Candidates with any future-data key | 0 / 80 | CLEAN |
| Summary records with any future-data key | 0 / 2 | CLEAN |

**Leakage verdict: ZERO VIOLATIONS. No look-ahead contamination detected.**

All V3 features (`atr_pct`, `mom_5d`, `rs_pct_5d`, `vol_ratio`, `mom_accel`) computed exclusively from OHLCV rows with `trade_date <= trading_date`.

---

## 8. Shadow Isolation

| Safety Property | Evidence |
|---|---|
| `no_trades_generated=True` on all 82 records | CONFIRMED |
| `no_candidatestore_write=True` on all 2 summaries | CONFIRMED |
| Forbidden imports in runner (decision_engine, risk_control, etc.) | 0 found |
| CandidateStore.write() call in runner | NOT PRESENT |
| V3 exception caught by orchestrator try/except | CONFIRMED — "Phase D shadow failed — production unaffected" guard in place |

**Isolation: PERFECT. V3 shadow is fully read-only.**

---

## 9. Old Scanner Overlap

| Metric | Run 1 | Run 2 |
|---|---|---|
| Old scanner symbol count | 52 | 53 |
| V3 pool size | 40 | 40 |
| Overlap count | 0 | 0 |
| Overlap % | 0.0% | 0.0% |

**V3 selected a completely disjoint symbol set vs. the old scanner on both days.**  
This reflects the fundamental methodological difference: V3 uses continuous percentile ranking across ATR, momentum, and volume dimensions; the old scanner uses bucket classification with score floor ≥0.55.

---

## 10. T+1 Outcome Summary (Run 1 Only)

**Data date:** 2026-08-14 (T+1 for Run 1 trading_date 2026-08-13)  
**T+3 / T+5:** Not yet available at audit time.

### UP Pool Performance
| Metric | Value |
|---|---|
| Resolved T+1 outcomes | 20 / 20 |
| Average T+1 return | +0.381% |
| Positive T+1 returns | 6 / 20 (30%) |
| Returns ≥ +1% | 4 / 20 |
| Returns ≥ +2% | 2 / 20 |
| Best performer | GALAXYSURF.NS +20% (Rank 1 ✅) |

### DOWN Pool Performance
| Metric | Value |
|---|---|
| Resolved T+1 outcomes | 20 / 20 |
| Average T+1 return (favorable = negative) | +0.461% (adverse — DOWN candidates averaged positive returns) |
| Returns ≤ -1% | 7 / 20 |
| Returns ≤ -2% | 2 / 20 |
| Worst misclassification | RATEGAIN.NS placed DOWN, moved +6.5% UP |

**Note:** DOWN pool showed net adverse T+1 direction on Day 1. This is not diagnostic — single-day noise is the dominant effect.

---

## 11. Strong Mover Capture Rate (1 day)

**Strong UP movers** = stocks with T+1 return ≥ +2% on 2026-08-14 = **19 stocks** in universe.  
**Strong DN movers** = stocks with T+1 return ≤ -2% on 2026-08-14 = **21 stocks** in universe.

| Pool | V3 Captured | Total Strong Movers | Capture Rate | Random Expected |
|---|---|---|---|---|
| UP ≥ +2% | 2 | 19 | 10.5% | ~9.6% (20/209) |
| DOWN ≤ -2% | 2 | 21 | 9.5% | ~9.6% (20/209) |

**Verdict: INSUFFICIENT_SAMPLE.** With 1 day, V3 capture rate is statistically indistinguishable from random selection. 20+ days required.

---

## 12. Top-5 Mover Capture (1 day)

### Actual Top-5 UP on 2026-08-14
| Rank | Symbol | Return | In V3 UP? | V3 UP Rank |
|---|---|---|---|---|
| 1 | GALAXYSURF.NS | +20.0% | ✅ YES | 1 |
| 2 | RATEGAIN.NS   | +6.5%  | ❌ NO (in V3 DOWN) | — |
| 3 | SUDARSCHEM.NS | +6.2%  | ❌ NO (in V3 DOWN) | — |
| 4 | IDEAFORGE.NS  | +4.99% | ❌ NO (in V3 DOWN) | — |
| 5 | IDEA.NS       | +4.44% | ✅ YES | 5 |

**UP Top-5 capture: 2/5**

### Actual Top-5 DOWN on 2026-08-14
| Rank | Symbol | Return | In V3 DOWN? | V3 DN Rank |
|---|---|---|---|---|
| 1 | CENTUM.NS    | -6.66% | ❌ NO | — |
| 2 | MIDHANI.NS   | -6.33% | ❌ NO | — |
| 3 | NATIONALUM.NS| -6.12% | ❌ NO | — |
| 4 | OLECTRA.NS   | -5.5%  | ❌ NO | — |
| 5 | NATCOPHARM.NS| -5.1%  | ❌ NO (in V3 UP Rank 20) | — |

**DOWN Top-5 capture: 0/5**

---

## 13. Score vs Future Magnitude Correlation

| Metric | Value |
|---|---|
| Run 1 UP — Spearman rank correlation (score vs T+1 return) | CANNOT ASSESS (1 day) |
| Run 1 DOWN — Spearman rank correlation | CANNOT ASSESS (1 day) |

20+ days required for stable Spearman estimate.

---

## 14. UP vs DOWN Directional Asymmetry

Not assessable from 1 day.

---

## 15. Regime Breakdown

Not assessable — regime context not captured in shadow records.

---

## 16. V3 vs Old Scanner Comparative Performance

**CANNOT ASSESS.** The old scanner's symbol list on 2026-08-13 was not retained in a queryable form. T+1 outcomes for old-scanner-only candidates cannot be computed.

> **GAP_002 (Design gap):** Old scanner does not persist its final candidate list to a durable JSONL. Until GAP_002 is addressed, side-by-side outcome comparison is not possible.

---

## 17. V3-Only Opportunities (Run 1)

Since overlap = 0, all 40 V3 candidates were V3-exclusive.

**V3-only UP candidates that became ≥ +1% movers:** 4  
(GALAXYSURF +20%, IDEA +4.44%, BDL +1.64%, AJANTPHARM +1.61%)

**V3-only DOWN candidates that moved ≤ -1%:** 5  
(HINDZINC -2.84%, CRAFTSMAN -1.8%, ASHOKLEY -1.3%, WHIRLPOOL -1.1%, BAJFINANCE -1.05%)

**V3 directional misclassifications (DOWN→actual UP ≥ +2%):** 3  
(RATEGAIN +6.5%, SUDARSCHEM +6.2%, IDEAFORGE +4.99%)

These were V3's most costly wrong-direction calls on Day 1. Single-day noise — do not tune.

---

## 18. Old-Scanner-Only Opportunities

**CANNOT ASSESS.** See GAP_002.

---

## 19. Stability

| Metric | Value |
|---|---|
| Pipeline crashes | 0 |
| Empty pools | 0 |
| Identical pools across runs | 0 (Run1 ≠ Run2) |
| Duration Run 1 | 789.2 ms |
| Duration Run 2 | 268.3 ms |
| Duration variance | 3x (likely cache warm on Run 2) |
| Memory leaks observed | None |
| Log corruption | None |

**Stability verdict: EXCELLENT.**

---

## 20. Outcome Tracking Pipeline

| Outcome Horizon | Available for Run 1? | Available for Run 2? |
|---|---|---|
| T+1 | ✅ YES (40 / 40 resolved) | ❌ NOT YET |
| T+3 | ❌ NOT YET (2026-08-18/19) | ❌ NOT YET |
| T+5 | ❌ NOT YET (2026-08-20/21) | ❌ NOT YET |

The outcome join script is functional. T+3/T+5 windows will populate as OHLCV data arrives.

---

## 21. Capital Feasibility

OBSERVATIONAL — no capital committed. Shadow generates candidate lists only.

---

## 22. Sample Size Assessment

| Requirement | Current | Gap |
|---|---|---|
| Minimum days for stable hit rate | 20 | -18 days |
| Minimum days for Spearman correlation | 30 | -28 days |
| Minimum days for UP/DOWN asymmetry | 20 | -18 days |
| Minimum days for regime breakdown | 40 | -38 days |
| Current resolved data points | 40 (T+1 only) | — |

**Verdict: INSUFFICIENT_SAMPLE. Continue shadow observation.**

---

## 23. Production Impact

Zero. Shadow runs are fully isolated:
- No CandidateStore writes
- No DecisionEngine calls
- No broker interactions
- Orchestrator wraps shadow in try/except — pipeline failure does not affect Phase D production

---

## 24. Q&A — 20 Programmatic Questions

| # | Question | Answer |
|---|---|---|
| Q1 | Expected runs in audit window? | **2** |
| Q2 | Successfully completed? | **2 / 2** |
| Q3 | Every valid run produced 20 UP + 20 DOWN? | **YES** |
| Q4 | Trading date lag correct? | **YES** (1-day lag expected post-market behavior) |
| Q5 | Future-data leakage? | **NONE — 0 violations across 80 candidates** |
| Q6 | Shadow isolated from trading? | **YES** |
| Q7 | Overlap with old scanner? | **0% (0/52 Run1, 0/53 Run2)** |
| Q8 | V3-only candidates that became meaningful movers? | **4 UP (≥1%), 5 DOWN (≤-1%) — 1 day only** |
| Q9 | Old-scanner-only meaningful movers? | **CANNOT ASSESS — GAP_002** |
| Q10 | V3 ≥2% strong-mover capture? | **UP: 10.5% (2/19), DN: 9.5% (2/21) — 1 day, INSUFFICIENT** |
| Q11 | Top-5 capture? | **UP: 2/5, DN: 0/5 — 1 day, INSUFFICIENT** |
| Q12 | V3 score vs future magnitude correlation? | **CANNOT ASSESS — 1 day** |
| Q13 | UP vs DOWN asymmetry? | **CANNOT ASSESS — 1 day** |
| Q14 | Regime breakdown? | **CANNOT ASSESS** |
| Q15 | V3 improves discovery vs old scanner? | **CANNOT ASSESS — GAP_002** |
| Q16 | Statistically sufficient sample? | **NO — 40 data points vs 400+ needed** |
| Q17 | Outcome-tracking pipeline healthy? | **PARTIAL — T+1 available Run1, T+3/T+5 pending** |
| Q18 | Biggest uncertainty? | **Sample size (2 days vs 20+ needed)** |
| Q19 | Continue shadow observation? | **YES** |
| Q20 | Production change justified? | **NO** |

---

## 25. Secondary Findings

| Finding | ID | Severity |
|---|---|---|
| Technical pipeline fully healthy | SF_001 | INFO |
| V3 zero overlap with production scanner | SF_002 | INFO |
| GALAXYSURF.NS UP Rank 1 matched actual top UP mover (+20%) | SF_003 | POSITIVE |
| DOWN pool directional accuracy needs monitoring | SF_004 | WATCH |
| GAP_001: WeekendResearch bypasses V3 hook | GAP_001 | LOW (known, accepted) |
| GAP_002: Old scanner list not retained — V1/V3 comparison blocked | GAP_002 | MEDIUM (future design item) |

---

## 26. Primary Verdict

```
E. INSUFFICIENT_SAMPLE_CONTINUE
```

> V3 shadow pipeline is technically healthy, produces clean isolated outputs, and has zero safety violations. However, 2 trading days and 40 resolved data points provide no statistical basis for any performance conclusion.  
> **Continue shadow observation. Do not promote. Do not tune. Do not compare.**  
> Revisit at 20 trading days minimum.

---

## 27. Artefact Manifest

| File | Description |
|---|---|
| [mover_discovery_v3_shadow_results.json](mover_discovery_v3_shadow_results.json) | Full audit JSON with all per-run metrics |
| [mover_discovery_v3_daily_performance.csv](mover_discovery_v3_daily_performance.csv) | Per-run tabular performance (2 rows) |
| [mover_discovery_v3_top_movers.csv](mover_discovery_v3_top_movers.csv) | Actual top-10 UP and DN movers on 2026-08-14 with V3 capture status |
| [mover_discovery_v3_v1_comparison.csv](mover_discovery_v3_v1_comparison.csv) | V3 vs old scanner side-by-side (partial — GAP_002) |
| [mover_discovery_v3_missed_and_recovered.json](mover_discovery_v3_missed_and_recovered.json) | V3-only candidates with T+1 outcomes |
| [../../tests/test_mover_discovery_v3_shadow_001.py](../../tests/test_mover_discovery_v3_shadow_001.py) | 20-test audit verification suite — 20/20 PASS |

---

*End of MOVER_DISCOVERY_V3_SHADOW_AUDIT_001 — 2026-08-17*
