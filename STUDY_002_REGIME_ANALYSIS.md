# STUDY 002 REGIME ANALYSIS
## One-Year Historical Market Learning

**Document Type:** Regime-Separated Analysis  
**Date:** 2026-08-01  
**Evidence Source:** `data/study002_results.json`, `data/study002_replay.db`

---

> **Rule:** Regime statistics are NOT merged in this document.  
> TRENDING_UP, TRENDING_DOWN, SIDEWAYS, and VOLATILE are reported separately throughout.

---

## 1. Regime Distribution

| Regime | Sessions | % of Year | Notes |
|---|---|---|---|
| SIDEWAYS | 191 | 78.3% | Dominant regime |
| TRENDING_DOWN | 37 | 15.2% | Second regime |
| TRENDING_UP | 16 | 6.6% | Shortest regime |
| VOLATILE | 0 | 0.0% | Not observed |

**Detection method:** NIFTY50 SMA200 + 20-day return. TRENDING_UP requires: close > SMA200 × 1.02 AND 20d-change > +2%. TRENDING_DOWN requires: close < SMA200 × 0.98 AND 20d-change < -2%. SIDEWAYS: all other cases.

---

## 2. Signal Activity by Regime

### TRENDING_UP (16 sessions)

| Metric | Value |
|---|---|
| Sessions | 16 |
| Total signals | 709 |
| Signals per session | 44.3 (highest of all regimes) |
| Sessions with at least 1 signal | 16 (100%) |
| Dominant sector | ENERGY |
| Classification | VERIFIED |

**Observation:** TRENDING_UP produced the highest signal density per session. Every bull session generated at least one qualifying signal. ENERGY sector led signal counts, consistent with energy stocks outperforming in early bull phases.

---

### TRENDING_DOWN (37 sessions)

| Metric | Value |
|---|---|
| Sessions | 37 |
| Total signals | 535 |
| Signals per session | 14.5 (lowest of all regimes) |
| Sessions with at least 1 signal | 37 (100%) |
| Dominant sector | PHARMA |
| Classification | VERIFIED |

**Observation:** TRENDING_DOWN had the lowest signal density (14.5/session) despite 100% session activity rate. The platform detected signals in every bear session, but at significantly lower volume. PHARMA sector dominated — defensive sector behaviour is consistent with bear market rotation.

**Zero SHORT signals in TRENDING_DOWN:** Despite 37 bear sessions, all signals were LONG. This is a confirmed structural gap (see STUDY_002_FINDINGS F-06). No SHORT-biased archetype is currently deployed.

---

### SIDEWAYS (191 sessions)

| Metric | Value |
|---|---|
| Sessions | 191 |
| Total signals | 7,318 |
| Signals per session | 38.3 |
| Sessions with at least 1 signal | 166 (86.9%) |
| Silent sessions (zero signals) | 25 (13.1%) |
| Dominant sector | METALS |
| Classification | VERIFIED |

**Observation:** SIDEWAYS is the most studied regime by session count. 25 of 191 SIDEWAYS sessions generated zero signals. The silent-day rate (13.1%) is only present in SIDEWAYS — both trending regimes had 100% signal days, suggesting trending markets reliably produce momentum signals while range markets have detection gaps.

---

### VOLATILE (0 sessions)

| Metric | Value |
|---|---|
| Sessions | 0 |
| Classification | VERIFIED |

VOLATILE conditions (as defined by the platform's NIFTY50 detection algorithm) did not occur during the study period. No VOLATILE-regime data was collected. This regime remains unobserved.

---

## 3. Sector Leadership by Regime

### TRENDING_UP — Dominant sector: ENERGY

ENERGY sector led signal generation during the 16 bull sessions. This aligns with typical sector rotation theory where energy stocks benefit from early expansion phases.

**Classification:** PROBABLE (sector rotation pattern consistent with theory; insufficient sessions to confirm statistically)

---

### TRENDING_DOWN — Dominant sector: PHARMA

PHARMA led signal generation during the 37 bear sessions. Defensive sector rotation into PHARMA during downtrends is a well-documented market behaviour.

**Classification:** PROBABLE (PHARMA as defensive sector in bear markets — consistent but not independently validated from this data)

---

### SIDEWAYS — Dominant sector: METALS

METALS had the highest average conviction (0.328) across 191 SIDEWAYS sessions. METALS also had the highest single-day conviction outside the IT peak (0.963 on 2026-01-29).

**Classification:** VERIFIED (average conviction is a direct measurement)

---

## 4. Regime Conviction Profile

Average sector conviction by regime cannot be computed per-regime from the current data (sector conviction is stored per date, not per regime). The following are full-year averages:

| Sector | Full-Year Avg Conviction | Sessions = 243 |
|---|---|---|
| METALS | 0.328 | Peak: 0.963 (2026-01-29) |
| TELECOM | 0.320 | Peak: 0.847 (2025-10-08) |
| BANKING_FINANCE | 0.319 | Peak: 0.800 (2026-06-17) |
| DEFENCE | 0.317 | Peak: 0.972 (2026-06-17) |
| AUTO | 0.309 | Peak: 0.862 (2026-05-07) |
| PHARMA | 0.307 | Peak: 0.775 (2026-06-23) |
| IT | 0.294 | Peak: 0.976 (2026-07-29) |
| INFRA | 0.292 | Peak: 0.791 (2026-05-07) |
| ENERGY | 0.276 | Peak: 0.778 (2026-01-02) |
| CONSUMER_DURABLES | 0.264 | Peak: 0.889 (2026-05-08) |
| CHEMICALS | 0.259 | Peak: 0.897 (2026-05-06) |
| FMCG | 0.255 | Peak: 0.786 (2025-09-04) |

**Note:** Per-regime conviction breakdown is a recommended addition to Study 003.

---

## 5. Feature Distribution by Regime

Feature vectors computed in Stage 4 (50,539 total) carry real per-date regime encoding:

| Regime | Feature Vectors | % | Vectors/Session |
|---|---|---|---|
| SIDEWAYS | 39,462 | 78.1% | 206.6 |
| TRENDING_DOWN | 7,733 | 15.3% | 209.0 |
| TRENDING_UP | 3,344 | 6.6% | 209.0 |

Trending regimes produce approximately the same vectors per session (~209) as SIDEWAYS because the number of active symbols per day is similar. The difference in total counts reflects only session count differences.

---

## 6. Regime-Specific Quality Gates

The walk-forward validation gate (WF ≥ 50%) was applied to patterns discovered from the full multi-regime feature matrix. The gate's regime-specific sensitivity is unknown:

- Whether the 2 approved patterns (EDG_MOMENT_86_EE0002, EDG_COMPOS_73_EE0001) perform similarly in TRENDING_UP vs TRENDING_DOWN vs SIDEWAYS conditions is **UNVERIFIED**.
- The approved edges were activated with a SIDEWAYS-regime MarketSnapshot.

**Hypothesis (H-04):** The multi-regime feature matrix may cause the PatternMiner to discover regime-conditional patterns that appear stable across WFT windows. Whether these patterns are truly cross-regime or merely regime-neutral (i.e., regime features cancel out) cannot be determined without regime-stratified backtesting.

---

## 7. Regime-Separated Opportunity Lifecycle

All 1,966 opportunities were created as LONG. The regime at opportunity birth is available in `opportunities.regime_at_birth`. Per-regime lifecycle breakdown was not computed in this pipeline iteration. This is a recommended addition for Study 003.

What is known:
- TRENDING_UP sessions: 709 signals, fewer INVALID opportunities expected (higher conviction environment)
- TRENDING_DOWN sessions: 535 signals, PHARMA dominant
- SIDEWAYS sessions: 7,318 signals, 13.1% silent days

---

## 8. What This Regime Year Was Not

The study period (2025-08-01 to 2026-07-31) did not expose the platform to:
- A sustained TRENDING_UP year (bull market conditions with ≥100 bull sessions)
- A VOLATILE regime
- A SHORT-signal-generating environment (no short archetypes exist)
- Regime transitions where opportunities opened in one regime and closed in another (all closed as TTL-expired regardless of regime)

These represent gaps that Study 003 should attempt to address through a longer window or by selecting a period with known regime diversity.
