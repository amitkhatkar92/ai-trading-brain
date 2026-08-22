# STUDY 002 EDGE DISCOVERY
## One-Year Historical Market Learning

**Document Type:** Edge Discovery Analysis  
**Date:** 2026-08-01  
**Evidence Source:** `data/study002_results.json`, `data/discovered_edges.json`

---

## 1. Discovery Cycle Parameters

| Parameter | Value |
|---|---|
| Feature matrix | 55,559 rows × 58 features |
| Positive rate | 28.3% |
| Pattern precision threshold | ≥ 58% |
| Pattern support threshold | ≥ 15 samples |
| Walk-forward consistency threshold | ≥ 50% |
| Expectancy threshold | ≥ 0.08R |
| MarketSnapshot date | 2026-07-30 |
| MarketSnapshot regime | SIDEWAYS (RANGE_MARKET) |
| EDE elapsed | 4.1 seconds |

---

## 2. Patterns Discovered

Three patterns were extracted from the decision tree with precision ≥ 58% and support ≥ 15 samples.

| Pattern Ref | Category | Precision | Support | WF Consistency | Expectancy | Decision |
|---|---|---|---|---|---|---|
| Pattern A | momentum_trend | 93% | — | 40% | +1.287R | **REJECTED** |
| Pattern B | momentum_volume | 86% | — | ≥ 50% | +0.588R | **APPROVED** |
| Pattern C | composite | 73% | — | ≥ 50% | +0.531R | **APPROVED** |

**REJECTED pattern note:** Pattern A had the highest raw win rate (88%) and expectancy (+1.29R) of all three patterns. It was correctly rejected because WF consistency (40%) fell below the 50% threshold. This rejection confirms the quality gate is functioning — high in-sample metrics did not bypass the out-of-sample filter.

---

## 3. Approved Edges

### EDG_MOMENT_86_EE0002 — momentum_volume

| Attribute | Value |
|---|---|
| **Status** | ACTIVE |
| **Category** | momentum_volume |
| **Win Rate** | 85% |
| **Expectancy** | +0.588R |
| **Sharpe Ratio** | 17.38 |
| **Max Drawdown** | 0% |
| **Walk-Forward** | PASS (≥ 50%) |
| **Composite Score** | 6.24 |
| **Fat Tail Risk** | 0% |
| **Previous status** | CANDIDATE (upgraded to ACTIVE in this cycle) |
| **Net change** | CANDIDATE → ACTIVE (update, not new creation) |

**Interpretation:** This edge was previously in CANDIDATE status (created from synthetic-data bootstrap). Study 002's 50,539 real feature vectors provided sufficient evidence for walk-forward validation to pass, upgrading it to ACTIVE. The Sharpe ratio of 17.38 is unusually high — this reflects the in-sample quality of the pattern on historical NSE data, not a live forward-tested result. This metric should be interpreted with caution until live outcomes are available.

**Classification:** VERIFIED (metrics from platform computation)

---

### EDG_COMPOS_73_EE0001 — composite

| Attribute | Value |
|---|---|
| **Status** | ACTIVE |
| **Category** | composite |
| **Win Rate** | 71% |
| **Expectancy** | +0.531R |
| **Sharpe Ratio** | 7.68 |
| **Max Drawdown** | 10% |
| **Walk-Forward** | PASS (≥ 50%) |
| **Composite Score** | 5.88 |
| **Fat Tail Risk** | 0% |
| **Previous status** | New creation in this cycle |
| **Net change** | Created → ACTIVE (new edge from Study 002 data) |
| **Added to evolved_strategies.json** | Yes (strategy count 176 → 177) |

**Interpretation:** This is the first edge created entirely from real NSE OHLCV data and immediately promoted to ACTIVE status. The composite category indicates it combines multiple feature types (momentum, volume, sector conviction). WR=71% with Exp=+0.53R is more modest than Pattern A's metrics, but its walk-forward stability justified approval.

**Classification:** VERIFIED (metrics from platform computation)

---

## 4. Rejected Edge

### EDG_MOMENT_93_EE0000 — momentum_trend

| Attribute | Value |
|---|---|
| **Status** | CANDIDATE |
| **Category** | momentum_trend |
| **Win Rate** | 88% |
| **Expectancy** | +1.287R |
| **Sharpe Ratio** | 30.97 |
| **Max Drawdown** | 0% |
| **Walk-Forward** | 40% — **FAIL** (threshold: ≥ 50%) |
| **Composite Score** | 4.46 |
| **Rejection reason** | WF consistency 40% < 50% minimum |

**Interpretation:** This pattern's Sharpe ratio (30.97) and expectancy (+1.29R) would appear highly attractive without the walk-forward gate. The rejection demonstrates the quality gate's function: patterns that appear strong in-sample but fail out-of-sample consistency are not promoted. This pattern remains as a CANDIDATE for re-evaluation in Study 003 with a larger or more diverse dataset.

**Classification:** VERIFIED (rejection is a confirmed platform decision)

---

## 5. Edge Lifecycle State After Study 002

| Status | Count | Change vs Pre-Study |
|---|---|---|
| ACTIVE | 2 | +2 (from 0) |
| CANDIDATE | 125 | +1 |
| DECAYING | 132 | -1 |
| DEPRECATED | 0 | 0 |
| **Total** | **259** | **+2** |

---

## 6. Top 15 Edges by Composite Score (Post-Study)

| Rank | Edge ID | Category | Status | Score | Sharpe | WR | Exp_R |
|---|---|---|---|---|---|---|---|
| 1 | EDG_MOMENT_86_EE0002 | momentum_volume | ACTIVE | 6.24 | 17.38 | 85% | +0.59R |
| 2 | EDG_COMPOS_73_EE0001 | composite | ACTIVE | 5.88 | 7.68 | 71% | +0.53R |
| 3 | EDG_MOMENT_93_EE0000 | momentum_trend | CANDIDATE | 4.46 | 30.97 | 88% | +1.29R |
| 4 | EDG_VOLATI_99_EE0003 | volatility | CANDIDATE | 2.94 | 32.22 | 100% | +0.75R |
| 5–15 | EDG_MOMENT_100/98/97/96/95_* | momentum_volume | DECAYING | 2.63–2.71 | 43–62 | 100% | +0.88–0.94R |

**Observation:** The DECAYING edges show WR=100% and Sharpe >40 — these appear from synthetic bootstrap data and are clearly unrealistic. Their DECAYING status correctly reflects the evaluation against real OHLCV evidence. They are candidates for DEPRECATED status as more real-data cycles accumulate.

---

## 7. Strategy Library Change

| Metric | Before | After |
|---|---|---|
| Total strategies | 176 | 177 |
| New strategies | — | EDG_COMPOS_73_EE0001 |
| Strategies from real data | 0 | 1 |
| Strategies from synthetic data | 176 | 176 (unchanged) |

EDG_COMPOS_73_EE0001 is the **first strategy in the library derived from real NSE market data** rather than the original synthetic bootstrap.

---

## 8. Observations for Study 003

1. **EDG_MOMENT_93_EE0000 (WR=88%, Exp=+1.29R)** remains as CANDIDATE. A larger or differently-sampled dataset may push its WF consistency above 50%. Worth monitoring.

2. **The two ACTIVE edges should be evaluated in live paper trading.** Their metrics are based on backtesting only. Forward performance will determine whether they graduate to fully trusted edges.

3. **The 10+ DECAYING edges with WR=100%** are artefacts of synthetic bootstrap data. A dedicated clean-up cycle (running EDE with real-only data) should eventually push them to DEPRECATED.

4. **A TRENDING_UP-snapshot EDE cycle** has never been run. The current two ACTIVE edges were promoted under a SIDEWAYS snapshot. Their characteristics under a bull-regime snapshot are unknown.
