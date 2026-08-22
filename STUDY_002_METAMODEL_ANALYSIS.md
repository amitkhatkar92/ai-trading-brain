# STUDY 002 METAMODEL ANALYSIS
## One-Year Historical Market Learning

**Document Type:** MetaModel Status and Gap Analysis  
**Date:** 2026-08-01  
**Evidence Source:** `data/study002_results.json`, `meta_learning/`

---

## 1. MetaModel Status

| Attribute | Value |
|---|---|
| **Model trained** | No |
| **Training records** | 0 |
| **Records required (minimum)** | 10 |
| **Dataset file** | `data/ml_performance_dataset.json` |
| **Dataset exists** | No |
| **Structural blocker** | No closed trade outcomes from either RE001 or Study 002 |

---

## 2. Architecture Review

The MetaModel is a k-NN regressor (`meta_learning/meta_model.py`) that predicts strategy R-multiple given a feature vector of current market conditions.

**Training data format (PerformanceRecord):**
```
{strategy: str, market_features: dict, r_multiple: float, return_pct: float, won: bool}
```

**Input pipeline:**
```
Trade close event → PerformanceDataset.add_from_trade() → ml_performance_dataset.json
```

**Activation condition:**
- Minimum 10 records required before fit is attempted
- 20+ records for statistically meaningful predictions

---

## 3. Why the MetaModel Has Not Trained

The root cause is structural, not a platform defect.

**Causal chain:**

```
No price-based exits in replay framework
       ↓
All 1,966 opportunities closed via TTL expiry only
       ↓
TTL expiry does not produce a trade_pnl_pct
       ↓
PerformanceDataset receives 0 records
       ↓
ml_performance_dataset.json is never created
       ↓
MetaModel cannot train
```

**This causal chain has now been confirmed across:**
- RE001: 29 sessions, 66 opportunities → 0 closed
- Study 002: 244 sessions, 1,966 opportunities → 0 closed

**Classification:** VERIFIED — the gap is a data dependency, not a platform failure.

---

## 4. Impact of Untrained MetaModel

| Layer | MetaModel Role | Impact When Untrained |
|---|---|---|
| Layer 3 — MetaLearning | Predict optimal strategy weights for current regime | Falls back to equal-weight allocation |
| Layer 10 — Debate | Inform strategy selection score | MetaModel vote uses neutral prior |
| Layer 6 — CapitalRiskEngine | Regime-adjusted position sizing | No MetaModel weighting applied |

The live trading system operates with fallback logic when MetaModel is untrained. This is designed behaviour — the system does not fail, it degrades gracefully.

---

## 5. Path to MetaModel Activation

### Path 1 — Live Paper Trading (Preferred)

Live paper trading generates real intraday price movement. The OrderManager simulates stop-loss and target execution. When a trade closes (stop hit, target hit, or manual close), it records outcome data to `strategy_performance.json` and eventually populates `ml_performance_dataset.json` through the LearningEngine.

**Estimated time:** 20 live trades = minimum viable. At current opportunity creation rate (1,966 per 244 sessions ≈ 8/session), and assuming 10-20% hit active status, 10-20 live paper trades per month is plausible.

**Classification:** PROBABLE — depends on live paper trading execution rate.

---

### Path 2 — Extended Replay with Price-Based Simulation

Augment the historical replay framework to simulate intraday price movement using daily OHLCV data (e.g., if target is N%, and the high exceeds current_price × (1+N%), the target is considered hit). This would generate synthetic trade outcomes from historical data.

**Risk:** The simulation would be deterministic and may overfit to daily OHLC structure. Outcomes would be approximate, not real.

**Classification:** HYPOTHESIS — has not been implemented or tested.

---

### Path 3 — Seeding from Existing Strategy Performance Tracker

`strategy_performance.json` currently tracks 2 strategies with minimal data. If the StrategyPerformanceTracker accumulates enough outcomes from live paper trading, these can be converted to MetaModel training records.

**Status:** 2 strategies tracked → insufficient for MetaModel training.

---

## 6. MetaModel Progress Across Studies

| Study | Duration | Opportunities | Closed | ML Records | Trained |
|---|---|---|---|---|---|
| RE001 | 29 sessions | 66 | 0 | 0 | No |
| Study 002 | 244 sessions | 1,966 | 0 | 0 | No |
| **Cumulative** | **273 sessions** | **2,032** | **0** | **0** | **No** |

The MetaModel has never trained across 273 simulated sessions. This is a confirmed long-term structural gap that requires a different input source (live paper trading) rather than a longer replay.

---

## 7. Recommendations for Study 003

1. **Do not target MetaModel activation through replay alone.** The replay framework cannot produce price-based exits. Any further replay study will continue to yield 0 MetaModel records.

2. **Run live paper trading for 30-60 days before Study 003.** This will accumulate trade outcomes that can be fed to the MetaModel.

3. **Monitor `strategy_performance.json`** for any accumulation after live paper trades. The StrategyPerformanceTracker is the upstream supplier of MetaModel observations.

4. **Consider implementing price-based exit simulation** in the replay framework as a research enhancement (Path 2 above). This is a code change requiring explicit user authorisation.

---

## 8. MetaModel Readiness Assessment

| Assessment | Status | Evidence |
|---|---|---|
| Architecture functional | **READY** | `meta_learning/meta_model.py` initialises and fits correctly when data is present |
| Training data pipeline | **READY** | `PerformanceDataset.add_from_trade()` correctly formats records |
| Minimum data | **NOT MET** | 0 records; need ≥ 10 |
| Practical activation | **REQUIRES** live paper trading | Cannot be reached through replay alone |

The MetaModel will activate as soon as 10 closed trade outcomes are delivered to `PerformanceDataset`. The architecture is ready — the data is not.
