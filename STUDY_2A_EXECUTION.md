# STUDY 2A — EXECUTION RECORD
## Winner DNA Discovery — Parameters, Data Sources, Methodology, Timeline

**Study ID:** STUDY-2A  
**Status:** COMPLETE  
**Executed:** 2026-08-03T11:04:59  
**Runtime:** 67.9 seconds  
**Classification:** Historical Research — No Production Impact

---

## 1. Study Mandate

> *"Discover the fundamental characteristics that consistently distinguish future winning stocks from ordinary stocks and losing stocks using ONLY historical evidence already present in the IIOS platform."*

**Scientific constraint:** Do NOT assume what defines a winner. Allow the data to reveal the characteristics.

---

## 2. Data Sources

| Source | Records | Date Range | Purpose |
|---|---|---|---|
| `data/replay.db` (primary) | 256,268 OHLCV rows | 2021-01-01 → 2025-12-30 | 5-year historical feature base |
| `data/study002_replay.db` (supplement) | 17,813,504 bytes | 2025-08-01 → 2026-07-31 | Extend to post-2025 period |
| `data/discovered_edges.json` | 259 edges | — | Context: validated strategies |
| `data/strategy_performance.json` | 2 strategies | 2026-03-12 | Known outcome reference |
| `data/regime_probability_history.json` | 500 records | Live platform | Regime validation context |

**Deduplication rule:** Study 002 supplement includes only dates after 2025-12-30 (replay.db max date) to prevent double-counting.

**Final merged dataset:**
- **n_main (replay.db):** 250,643 observations
- **n_supplement (study002_replay.db):** 30,266 observations  
- **n_total:** 280,909 labeled feature vectors
- **Signal count (replay.db):** 57,037 signals across 5 years

---

## 3. Feature Engineering

### 3.1 Features Computed (20 non-redundant)

| # | Feature | Description | Source |
|---|---|---|---|
| 1 | `mom_1d` | 1-day price return | OHLCV |
| 2 | `mom_5d` | 5-day price return | OHLCV |
| 3 | `mom_20d` | 20-day price return | OHLCV |
| 4 | `intra_range` | (High−Low)/Close | OHLCV |
| 5 | `atr_14` | 14-day ATR as % of close | OHLCV |
| 6 | `close_pos` | (Close−Low)/(High−Low) | OHLCV |
| 7 | `gap_pct` | (Open−PrevClose)/PrevClose | OHLCV |
| 8 | `vol_ratio` | Volume / 5-day avg volume | OHLCV |
| 9 | `vol_ratio_20` | Volume / 20-day avg volume | OHLCV |
| 10 | `cons_up_days` | Consecutive rising close days (max 5) | OHLCV |
| 11 | `cons_dn_days` | Consecutive falling close days (max 5) | OHLCV |
| 12 | `prox_52w_high` | Close / 52-week high | OHLCV |
| 13 | `prox_52w_low` | Close / 52-week low | OHLCV |
| 14 | `sect_conviction` | Daily sector conviction score (0–1) | sector_conviction_daily |
| 15 | `sect_part5d` | Sector 5-day participation rate | sector_conviction_daily |
| 16 | `avg_conviction` | Avg conviction across all sectors | sector_conviction_daily |
| 17 | `sc_high` | Flag: avg_conviction > 0.6 | Derived |
| 18 | `sc_low` | Flag: avg_conviction < 0.4 | Derived |
| 19 | `regime_score` | Regime strength (0.2–0.8) | NIFTY50 OHLCV |
| 20 | `regime_bull` | Bull regime flag (0/1) | NIFTY50 OHLCV |

### 3.2 Features Excluded with Rationale

| Feature | Reason |
|---|---|
| `breadth`, `pcr` | Identical computation to `avg_conviction` — duplicate |
| `pcr_bullish` | Identical to `sc_high` — duplicate |
| `pcr_bearish` | Identical to `sc_low` — duplicate |
| `regime_volatile` | Always 0.0 in 3-regime model — zero variance |
| `sector_flow_count` | Constant 1.2 for all observations — zero variance |
| `event_count` | Constant 0.0 for all observations — zero variance |
| `vix`, `vix_low`, `vix_high` | Regime-proxy only, no independent data in replay.db |

---

## 4. Methodology

### 4.1 Group Classification

**Primary threshold (FIXED, interpretable):**
- **Group A (Winners):** forward_return ≥ +1.0%
- **Group B (Ordinary):** −1.0% < forward_return < +1.0%
- **Group C (Losers):** forward_return ≤ −1.0%

**Threshold rationale:**
- Exceeds median (+0.009%) by ~100× margin
- Aligns with 1× daily ATR for liquid NSE large-cap stocks
- Consistent with IIOS framework (RE001A used 0.8% threshold, this study uses 1.0%)
- ±1.0% is a meaningful real-world hurdle (covers transaction costs + slippage)

**Percentile threshold also computed (for comparison):**
- p25 = −1.108% (Loser boundary)
- p75 = +1.142% (Winner boundary)
- These are close to the fixed ±1.0% threshold, confirming appropriateness

### 4.2 Statistical Tests

| Test | Purpose | Library |
|---|---|---|
| Mann-Whitney U | Non-parametric group difference test | scipy.stats |
| Cohen's d | Effect size (pooled std) | Custom implementation |
| Mutual Information | Feature-label dependency | sklearn.feature_selection |
| Random Forest | Ensemble importance (100 trees, depth 8) | sklearn.ensemble |
| Combined score | (MI_norm + RF_norm + d_norm) / 3 | Custom |

### 4.3 DNA Pattern Discovery

**Algorithm:** Decision Tree (sklearn.tree.DecisionTreeClassifier)  
**Max depth:** 5  
**Min samples per leaf:** 50  
**Class weight:** None (raw class frequencies)  

**Temporal split for walk-forward validation:**
- Train: 2021-02-01 → 2025-06-25 (80% of dates = 224,100 observations)
- Test: 2025-06-26 → 2026-07-29 (20% of dates = 56,809 observations)

**Pattern acceptance criteria (initial filter):**
- Support ≥ 0.02% of training data (≥ 45 training samples)
- Confidence ≥ 35% (34% above 26.85% base rate)
- Lift ≥ 1.30 (30% above base rate)

**Walk-forward validation criteria (final filter):**
- |test_confidence − train_confidence| < 15%
- test_confidence ≥ 25%

**Confidence calculation (corrected):**  
`conf = values[winner_idx] / values.sum()` where `values = tree_.value[node][0]`  
Note: sklearn stores class proportions as floats in `tree_.value`; using raw index (1) directly would give `int(0.89) = 0` — a known bug corrected in this study.

### 4.4 Cluster Analysis

**Algorithm:** KMeans (sklearn.cluster)  
**Feature selection:** Top 20 ranked features  
**Standardization:** StandardScaler (zero mean, unit variance)  
**Cluster count selection:** Silhouette score over k=2..8  
**Sample:** Winners only (Group A)

### 4.5 Feature Decile Analysis

For each feature in Top 20: split all 280,909 observations into 10 equal-count deciles; compute winner rate per decile. Reveals monotonic relationships and threshold effects not captured by linear statistics.

---

## 5. Processing Timeline

| Stage | Step | Duration |
|---|---|---|
| Stage 0 | Data loading + feature extraction (280,909 vectors) | ~60s |
| Stage 1 | Group classification | <1s |
| Stage 2 | Feature statistics (MWU, Cohen's d × 20 features) | <1s |
| Stage 3 | Feature ranking (RF training on 224K samples) | ~3s |
| Stage 4 | DNA pattern discovery (DT + walk-forward) | <1s |
| Stage 5 | Loser DNA discovery | <1s |
| Stage 6 | Cluster analysis (KMeans k=2..8) | ~2s |
| Stage 7 | Decile analysis | <1s |
| **Total** | | **67.9 seconds** |

---

## 6. Production Safety Verification

| Check | Status |
|---|---|
| No production DB modified | ✅ Read-only access |
| No strategy parameters changed | ✅ Analysis only |
| No new market data fetched | ✅ Local data only |
| No live trading affected | ✅ Paper mode active |
| replay.db and study002_replay.db isolated from live trading | ✅ Separate files |

---

## 7. Known Defects and Limitations

| Defect | Description | Impact |
|---|---|---|
| D-01 | sklearn `tree_.value` stores proportions not counts in this version — fixed with ratio computation | None — corrected |
| D-02 | `avg_conviction`, `breadth`, `pcr` were identical features in ede_feature_db.json — deduplicated | Reduced feature count from 34 to 20 |
| D-03 | `regime_volatile` always 0 — dropped | None — zero-variance |
| D-04 | Sector data not available for 21 delisted/failed symbols | <9% of universe; unlikely to bias |
| D-05 | Regime labels are derived from NIFTY50 price only (no VIX, PCR data in replay.db) | Regime classification less precise than live system |
| D-06 | Cluster silhouette=0.168 (low) — natural clusters are not distinct | Documented; cluster findings classified as HYPOTHESIS |

---

## 8. Output Files

| File | Size | Description |
|---|---|---|
| `data/study002a_results.json` | ~2MB | Complete machine-readable results |
| `STUDY_2A_EXECUTION.md` | This document | Methodology and execution record |
| `WINNER_DNA_REPORT.md` | See file | Winner characteristics and DNA patterns |
| `LOSER_DNA_REPORT.md` | See file | Loser characteristics and anti-patterns |
| `FEATURE_IMPORTANCE_REPORT.md` | See file | Full feature ranking and statistics |
| `DNA_CLUSTER_REPORT.md` | See file | Cluster analysis results |
| `STATISTICAL_VALIDATION_REPORT.md` | See file | Walk-forward validation results |

---

*Generated by study002a_pipeline.py | IIOS Research Division | 2026-08-03*
