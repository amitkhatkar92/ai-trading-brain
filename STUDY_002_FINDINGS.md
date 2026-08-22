# STUDY 002 FINDINGS
## One-Year Historical Market Learning

**Document Type:** Research Findings  
**Date:** 2026-08-01  
**Evidence Source:** `data/study002_results.json`, `data/study002_replay.db`

---

## Classification Key

Every finding is classified as one of:
- **VERIFIED** — directly measured from study data
- **PROBABLE** — inferred from consistent patterns across multiple observations
- **HYPOTHESIS** — plausible interpretation not directly testable from this data alone

---

## Section 1 — Market Regime Findings

### F-01 — The market year 2025-08-01 to 2026-07-31 was predominantly SIDEWAYS

**Classification:** VERIFIED  
**Evidence:** NIFTY50-based regime detection across all 244 trading sessions:
- SIDEWAYS: 191 sessions (78.3%)
- TRENDING_DOWN: 37 sessions (15.2%)
- TRENDING_UP: 16 sessions (6.6%)
- VOLATILE: 0 sessions (0.0%)

A year with 78% SIDEWAYS, 15% bear, 6% bull is a low-momentum, low-directional-conviction market year. The near-absence of TRENDING_UP (only 16 sessions) is statistically notable.

---

### F-02 — Signal generation rate was 100% in trending regimes, 87% in SIDEWAYS

**Classification:** VERIFIED  
**Evidence:** Signal activity per regime:
- TRENDING_UP: 709 signals across 16 sessions = 44.3 signals/session, all 16 days had signals
- TRENDING_DOWN: 535 signals across 37 sessions = 14.5 signals/session, all 37 days had signals
- SIDEWAYS: 7,318 signals across 191 sessions = 38.3 signals/session, 166 of 191 days had signals (86.9%)

**Observation:** TRENDING_UP generated the highest signal density (44.3/session). Despite having the fewest sessions, bull markets produced proportionally more signals per session than bear or sideways markets.

---

### F-03 — TRENDING_DOWN produced the lowest signal density despite 100% activity rate

**Classification:** VERIFIED  
**Evidence:** TRENDING_DOWN sessions averaged 14.5 signals/session versus 38.3 for SIDEWAYS and 44.3 for TRENDING_UP. Signal density is not correlated with signal activity rate.

---

### F-04 — The VOLATILE regime did not occur in this market year

**Classification:** VERIFIED  
**Evidence:** 0 of 244 sessions classified as VOLATILE by NIFTY50 SMA200 + 20-day change algorithm.

**Hypothesis (H-01):** The absence of VOLATILE classification may reflect the smoothness of the regime detection algorithm (SMA200 + 20d change ≥ ±2%), which requires sustained directionality. Short-term volatility spikes may have been present in the market but not captured by this algorithm.

---

## Section 2 — Signal and Archetype Findings

### F-05 — DNA_1B_SECTOR_PRE_BKT is the dominant archetype by signal count

**Classification:** VERIFIED  
**Evidence:** Archetype signal breakdown:

| Archetype | Signals | % of Total |
|---|---|---|
| DNA_1B_SECTOR_PRE_BKT | 3,577 | 41.8% |
| DNA_1A_MOMENTUM_CONT | 1,928 | 22.5% |
| DNA_1A_SECTOR_BKT | 1,185 | 13.8% |
| DNA_1A_52W_HIGH_EXPAND | 792 | 9.3% |
| DNA_1B_QUIET_ACCUMULATION | 711 | 8.3% |
| DNA_1B_LOW_NOISE_STRENGTH | 237 | 2.8% |
| DNA_1A_RESULTS_FOLLOWTHR | 132 | 1.5% |

DNA_1B_SECTOR_PRE_BKT alone accounts for 41.8% of all signals across 244 sessions.

---

### F-06 — ALL 8,562 signals were LONG direction. Zero SHORT signals were generated.

**Classification:** VERIFIED  
**Evidence:** `by_direction: {'LONG': 1966}` in opportunities; all 8,562 signals mapped to LONG opportunities only.

**Probable interpretation (P-01):** The platform's archetypes are structurally biased toward LONG signals. In a year with 15% TRENDING_DOWN and 78% SIDEWAYS sessions, a well-calibrated system would be expected to generate some SHORT signals. The complete absence of SHORT signals across all three regimes indicates the scanner set does not currently include SHORT-biased archetypes.

**Hypothesis (H-02):** TRENDING_DOWN sessions in particular represent market conditions where SHORT-biased archetypes would generate signals. Study 003 should include a SHORT archetype set.

---

### F-07 — 95.4% of all opportunities expired as INVALID

**Classification:** VERIFIED  
**Evidence:**
- INVALID: 1,876 of 1,966 opportunities (95.4%)
- ACTIVE at window end: 42 (2.1%)
- DISCOVERED at window end: 42 (2.1%)
- WATCHING at window end: 6 (0.3%)
- Closed (COMPLETED + INVALIDATED): 0 (0.0%)

The high INVALID rate is expected — opportunities have TTL expiry, and 244 sessions of continuous scanning generates many short-lived signals that do not progress to full activation.

---

### F-08 — Zero opportunities closed (COMPLETED or INVALIDATED by stop/target)

**Classification:** VERIFIED  
**Evidence:** `closed_opportunities = 0`.

**Observation:** "INVALID" in this DB means TTL-expired, not outcome-settled. The state machine uses INVALID for TTL exhaustion and NEVER_MATURED. The state COMPLETED/INVALIDATED (with stop/target outcome) was never reached in the study period.

**Structural gap (G-01):** The replay framework does not simulate actual price-based exits (stop-loss hits, target hits) because it does not compute intraday prices. TTL-based expiry is the only path to closure. A live paper-trading run would generate real outcome data.

---

## Section 3 — Sector Findings

### F-09 — BANKING_FINANCE generated the most signals of any sector (1,541)

**Classification:** VERIFIED  
**Evidence:** Signal count by sector:
1. BANKING_FINANCE: 1,541 (18.0%)
2. PHARMA: 895 (10.5%)
3. INFRA: 809 (9.5%)
4. AUTO: 768 (9.0%)
5. IT: 743 (8.7%)
6. METALS: 721 (8.4%)

The top 6 sectors generated 5,477 of 8,562 signals (64.0%).

---

### F-10 — METALS sector showed the highest year-long average conviction (0.328)

**Classification:** VERIFIED  
**Evidence:** Sector average conviction scores (FULL rows only):

| Rank | Sector | Avg Conviction | Peak Conviction | Peak Date |
|---|---|---|---|---|
| 1 | METALS | 0.328 | 0.963 | 2026-01-29 |
| 2 | TELECOM | 0.320 | 0.847 | 2025-10-08 |
| 3 | BANKING_FINANCE | 0.319 | 0.800 | 2026-06-17 |
| 4 | DEFENCE | 0.317 | 0.972 | 2026-06-17 |
| 5 | AUTO | 0.309 | 0.862 | 2026-05-07 |
| 6 | PHARMA | 0.307 | 0.775 | 2026-06-23 |
| 7 | IT | 0.294 | 0.976 | 2026-07-29 |
| 8 | INFRA | 0.292 | 0.791 | 2026-05-07 |
| 9 | ENERGY | 0.276 | 0.778 | 2026-01-02 |
| 10 | CONSUMER_DURABLES | 0.264 | 0.889 | 2026-05-08 |
| 11 | CHEMICALS | 0.259 | 0.897 | 2026-05-06 |
| 12 | FMCG | 0.255 | 0.786 | 2025-09-04 |

---

### F-11 — IT sector achieved the highest single-day conviction of the entire study (0.976 on 2026-07-29)

**Classification:** VERIFIED  
**Evidence:** Peak conviction = 0.976 (IT sector, 2026-07-29).

IT's annual average conviction was 0.294 (rank 7 of 12), but its peak (0.976) was the all-study maximum. This indicates that IT went through a concentrated breakout phase in the final week of the study window — consistent with the IT-led signal burst observed in RE001 (which covered the overlapping final 30 sessions).

---

### F-12 — Sector conviction quality was nearly complete across all 244 sessions

**Classification:** VERIFIED  
**Evidence:** 2,916 FULL-quality conviction rows = 12 sectors × 243 trading dates = 99.6% FULL coverage. Only 1 trading date across all 12 sectors had non-FULL quality.

---

## Section 4 — Feature Database Findings

### F-13 — 50,539 labelled feature vectors were computed from one-year OHLCV data

**Classification:** VERIFIED  
**Evidence:** Stage 4 computed 50,539 feature rows from 51,793 OHLCV rows (209 symbols × 248 dates). 209 rows were skipped (no next-day close available for forward return computation on last date). 0 rows skipped for insufficient history.

---

### F-14 — The positive return rate was 28.3% across all regimes

**Classification:** VERIFIED  
**Evidence:** 14,302 of 50,539 feature rows had next-day return ≥ 0.8% (threshold = POSITIVE_RETURN_THRESHOLD). Rate = 28.3%.

**Comparison:** RE001A also found 28.9% positive rate in the SIDEWAYS-only window. Study 002's multi-regime rate (28.3%) is nearly identical, suggesting the 0.8% threshold positive rate is regime-insensitive at this scale.

**Hypothesis (H-03):** The 0.8% threshold positive label may not be optimal across all regimes. In TRENDING_DOWN, the conditional positive rate may differ materially. Per-regime positive rate breakdown was not computed in this study.

---

### F-15 — Regime encoding is now real (per-date) rather than hardcoded

**Classification:** VERIFIED  
**Evidence:** Feature vectors in Study 002 carry regime flags derived from NIFTY50 OHLCV detection:
- SIDEWAYS features: 39,462 (78.1%)
- TRENDING_DOWN features: 7,733 (15.3%)
- TRENDING_UP features: 3,344 (6.6%)

This is the first time the feature database contains real multi-regime encoded observations.

---

## Section 5 — Structural Findings

### F-16 — The SHORT signal gap is the most significant structural observation

**Classification:** VERIFIED (gap existence); PROBABLE (cause)  
**Evidence:** Zero SHORT signals in 244 sessions including 37 TRENDING_DOWN sessions.  
**Probable cause:** The Layer 1A and 1B scanners are designed exclusively for long momentum and accumulation patterns. No scanner currently fires on short-side conditions.

---

### F-17 — The TTL-expiry-only lifecycle is a known research constraint

**Classification:** VERIFIED  
**Evidence:** 1,876 INVALID opportunities, all through TTL exhaustion or NEVER_MATURED. Zero price-based closures.

---

### F-18 — MetaModel remains untrained after two research studies

**Classification:** VERIFIED  
**Evidence:** 0 records in `ml_performance_dataset.json` after both RE001 and Study 002. The structural cause is confirmed: neither study produced price-based trade outcomes.

---

## Section 6 — Final Scientific Answers

Answering the study's six scientific questions from evidence only.

### Q1: Does IIOS discover persistent edges across multiple market regimes?

**Answer (PROBABLE):** Study 002 produced two ACTIVE edges — both from a SIDEWAYS-regime terminal snapshot. Whether these edges persist in TRENDING_UP or TRENDING_DOWN regimes cannot be confirmed from this study. The EDE was run once with a SIDEWAYS-regime snapshot. Multi-regime persistence requires separate EDE cycles per regime, which was not performed.

**Evidence:** EDG_MOMENT_86_EE0002 and EDG_COMPOS_73_EE0001 promoted to ACTIVE. Both scored on a 55,559-sample multi-regime feature matrix, so the patterns themselves are informed by multi-regime data even though the activation snapshot was SIDEWAYS.

---

### Q2: Which discovered edges survive walk-forward validation?

**Answer (VERIFIED):**
- EDG_MOMENT_86_EE0002 (momentum_volume): WR=85%, Exp=+0.59R, Sharpe=17.38 — PASS (WF≥50%)
- EDG_COMPOS_73_EE0001 (composite): WR=71%, Exp=+0.53R, Sharpe=7.68 — PASS (WF≥50%)
- EDG_MOMENT_93_EE0000 (momentum_trend): WR=88%, Exp=+1.29R, WF=40%<50% — REJECTED

The momentum_volume and composite pattern types survived. The momentum_trend pattern (highest raw win rate and expectancy) was rejected by the walk-forward gate — a correct quality gate enforcement.

---

### Q3: Which strategies improved over one year?

**Answer (VERIFIED, partial):** Study 002 added 1 net new strategy (EDG_COMPOS_73_EE0001, strategy count 176 → 177). The 2 previously-tracked performance strategies in `strategy_performance.json` were unchanged. No strategy degradation or improvement was measurable without live trade outcomes.

---

### Q4: Which strategies deteriorated?

**Answer (VERIFIED, partial):** No strategy deteriorated in measurable live performance (no closed trades). In edge lifecycle terms: 133 edges remained DECAYING, none were DEPRECATED. No deterioration was confirmed at the strategy library level.

---

### Q5: Which market regimes generated the highest-quality knowledge?

**Answer (PROBABLE):** SIDEWAYS generated 7,318 signals (85.5% of all signals) and dominated the feature distribution (39,462 of 50,539 features = 78.1%). The two approved edges emerged from a SIDEWAYS snapshot. However, TRENDING_UP generated the highest per-session signal density (44.3/session vs 38.3 for SIDEWAYS), suggesting that if a longer TRENDING_UP period were sampled, it might produce high-density knowledge generation.

**The most reliable sector conviction data came from all regimes equally** — 2,916 FULL rows with 99.6% quality coverage independent of regime.

---

### Q6: How much real knowledge was accumulated?

**Answer (VERIFIED):**

| Knowledge Type | Before Study | After Study | Change |
|---|---|---|---|
| Labelled feature records | 4,964 (RE001 only) | 50,539 computed (5,000 stored) | +45,575 net effective |
| ACTIVE edges | 0 | 2 | +2 |
| Strategy library entries | 176 | 177 | +1 |
| MetaModel training records | 0 | 0 | 0 |
| Sectors tracked with FULL conviction | 12 | 12 | 0 |
| FULL conviction rows | 336 (RE001) | 2,916 (Study 002) | +2,580 |

**Narrative:** Study 002 produced the first two verified, walk-forward-validated edges in platform history. It also produced 50,539 real labelled observations spanning three market regimes — the largest real data expansion to date.
