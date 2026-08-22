# V3_KNOWLEDGE_SECOND_PASS_AUDIT_001
**Status:** READ-ONLY — RESEARCH ONLY  
**Date:** 2026-08-17  
**Audit ID:** V3_KNOWLEDGE_SECOND_PASS_AUDIT_001  
**Input:** V3 retrospective replay — 214 trading days (2025-09-16 → 2026-07-30)

---

## 1. Executive Summary

Compiled Knowledge (8 backward-looking technical evidence signals) was tested as a second-pass filter inside the V3 20-UP + 20-DOWN high-mover pool over 214 trading days with a mandatory train/val/OOS split.

**Primary Verdict: `C. KNOWLEDGE_SECOND_PASS_NO_INCREMENTAL_VALUE`**

In the OOS period, Knowledge Top-5 **underperforms** a random draw from the same V3 pool on every critical metric: directional accuracy (−3.1% UP), ≥2% capture (−3.0% UP), and MFE (−0.9% UP). The Knowledge score has near-zero Spearman correlation with T+1 returns (−0.003 UP, −0.014 DN). Concentration lift is 1.02× for UP — statistically indistinguishable from 1.00×.

This is not a failure of V3. V3 correctly identifies a pool of high-volatility stocks with 1.41× lift in ≥2% movers vs universe. The Knowledge layer as currently implemented cannot add directional value on top of that pool.

---

## 2. Dataset and Split

| Parameter | Value |
|---|---|
| OHLCV source | `data/study002_replay.db` |
| Date range | 2025-09-16 → 2026-07-30 |
| Total days replayed | 214 |
| Pool size per direction | 20 (V3 output) |
| TRAIN split | 2025-09-16 → 2026-02-19 (107 days, 50%) |
| VAL split | 2026-02-20 → 2026-05-13 (53 days, 25%) |
| OOS split | 2026-05-14 → 2026-07-30 (54 days, 25%) |
| Sector context | UNAVAILABLE — `sector_ret_1d=0.0` in all records (no sector peer data in DB) |

---

## 3. Knowledge Signal Design (8 binary signals, equal weight)

No optimization was performed on any data. Signals use equal 1/8 weighting throughout all splits.

### UP Signals
| Signal | Condition |
|---|---|
| `mom_5d_positive` | mom_5d > 0 |
| `mom_accel_positive` | mom_accel > 0 |
| `mom_3d_positive` | mom_3d > 0 |
| `rsi_momentum_zone` | 45 ≤ rsi_14 ≤ 70 |
| `vol_above_avg` | vol_ratio ≥ 1.20 |
| `price_position_high` | price_position > 0.55 |
| `not_overbought` | rsi_14 < 72 |
| `outperforms_market` | mom_1d > universe_avg_ret_1d |

### DOWN Signals
| Signal | Condition |
|---|---|
| `mom_5d_negative` | mom_5d < 0 |
| `mom_accel_negative` | mom_accel < 0 |
| `mom_3d_negative` | mom_3d < 0 |
| `rsi_elevated` | rsi_14 > 55 |
| `vol_above_avg` | vol_ratio ≥ 1.20 |
| `price_position_low` | price_position < 0.45 |
| `underperforms_market` | mom_1d < universe_avg_ret_1d |
| `below_resistance` | breakout_pct < 1.0 |

**Confidence levels:** HIGH ≥ 5/8, MEDIUM 3–4/8, LOW 2/8, REJECT < 2/8

---

## 4. Leakage Audit

**Result: PASS**

All 8 knowledge signals use only data available at the close of trading_date T:
- Momentum features: based on close prices through T
- RSI: computed from closes through T
- Volume ratio: ratio of today's volume to 20-day average through T-1
- Price position: based on 20-day high/low through T-1
- Market context: universe average 1d return = (close_T / close_T-1 − 1) for all symbols

No future close, high, low, volume, or outcome data was used.

---

## 5. Six-Model Comparison Table

### OOS Period (2026-05-14 → 2026-07-30) — PRIMARY EVALUATION

| Model | Dir UP% | ≥2% UP | ≥3% UP | Avg MFE UP | FP% UP | Dir DN% | ≥2% DN | ≥3% DN | Avg MFE DN |
|---|---|---|---|---|---|---|---|---|---|
| V3_20 (baseline) | 48.8% | 17.8% | 11.1% | 2.059% | 41.1% | 48.8% | 12.8% | 5.9% | 1.454% |
| V3_Top5 | **50.9%** | **22.6%** | **17.7%** | **2.687%** | 32.8% | 48.7% | **18.1%** | **10.2%** | 1.700% |
| Know_Top10 | 47.2% | 17.0% | 11.1% | 2.060% | 42.1% | 48.1% | 12.6% | 6.4% | 1.439% |
| Know_Top6 | 45.9% | 16.0% | 11.9% | 2.019% | 40.2% | 47.5% | 12.9% | 5.7% | 1.465% |
| Know_Top5 | 45.3% | 15.1% | 11.3% | 2.009% | 41.1% | 47.2% | 13.2% | 6.0% | 1.485% |
| **Random_5** | 48.4% | 18.1% | 12.1% | 2.104% | 39.5% | 48.2% | 13.1% | 6.2% | 1.469% |

**Key OOS observation:** Know_Top5 is the worst-performing model on UP directional accuracy (45.3%) — it is worse than random (48.4%) and worse than the full V3_20 pool (48.8%). V3_Top5 is the best-performing model on UP (50.9%), using only the V3 score rank.

---

## 6. Results by Split

### TRAIN (2025-09-16 → 2026-02-19)
| Model | Dir UP% | ≥2% UP | Dir DN% | ≥2% DN |
|---|---|---|---|---|
| V3_20 | 44.5% | 13.5% | 53.8% | 12.8% |
| V3_Top5 | 43.2% | 17.6% | 54.2% | 15.3% |
| Know_Top5 | 43.5% | 14.2% | 52.9% | 13.8% |
| Random_5 | 44.2% | 14.3% | 53.2% | 12.5% |

### VAL (2026-02-20 → 2026-05-13)
| Model | Dir UP% | ≥2% UP | Dir DN% | ≥2% DN |
|---|---|---|---|---|
| V3_20 | 51.2% | 23.1% | 48.4% | 20.8% |
| V3_Top5 | 49.4% | 26.8% | 48.3% | 22.3% |
| Know_Top5 | 51.7% | 18.1% | 52.1% | 22.6% |
| Random_5 | 51.0% | 23.2% | 48.4% | 20.9% |

### OOS (2026-05-14 → 2026-07-30)
*(See Section 5 above)*

**Summary:** Know_Top5 slightly beats random on VAL UP direction (51.7% vs 51.0%) but this does NOT hold in OOS (45.3% vs 48.4%). No consistency across splits.

---

## 7. Score Correlation

| Score | Direction | Spearman vs T+1 return |
|---|---|---|
| Knowledge score | UP vs T+1 return | **−0.003** (noise) |
| Knowledge score | DN vs −T+1 return | **−0.014** (noise) |
| V3 score | UP vs T+1 return | −0.013 (noise) |
| V3 score | DN vs −T+1 return | +0.024 (noise) |

Neither the Knowledge score nor the V3 score rank predicts T+1 return magnitude or direction within the pool. The rank order of knowledge evidence does not identify the better half of each pool.

---

## 8. Concentration Analysis

Does the Knowledge Top-5 capture a disproportionate share of the pool's favorable movement?

| Selection | UP Share | DN Share | Expected (random) | UP Lift | DN Lift |
|---|---|---|---|---|---|
| Know_Top5 | 25.4% | 26.3% | 25.0% | **1.02×** | **1.05×** |
| Know_Top6 | 30.4% | 30.5% | 30.0% | 1.01× | 1.02× |
| Know_Top10 | 52.2% | 50.2% | 50.0% | 1.04× | 1.00× |

**Conclusion:** Knowledge Top-5 concentrates 1.02× more favorable movement than random — this is not a meaningful improvement (expected noise ±0.10× minimum to be actionable).

---

## 9. Feature Combination Analysis

Top combinations tested against full 214-day dataset. Baseline: V3_20 UP = 17.0% ≥2% rate.

| Combination | n | Dir Acc | ≥2% Rate | vs Baseline |
|---|---|---|---|---|
| `outperforms_market` | 3,163 | 47.2% | 17.2% | +0.2% |
| `price_position_high` | 3,273 | 47.4% | 17.1% | +0.1% |
| `vol_above_avg` | 2,611 | 45.9% | 17.0% | 0.0% |
| `mom_5d_positive` | 4,130 | 46.9% | 16.9% | −0.1% |
| `mom_5d + vol_above_avg` | 2,528 | 45.5% | 16.9% | −0.1% |
| `mom_5d + mom_accel + vol` | 2,297 | 45.6% | 17.0% | 0.0% |
| `mom_5d + mom_accel + vol + price_pos` (4-combo) | 1,900 | 45.9% | 17.1% | +0.1% |

**No combination exceeds the V3_20 baseline by more than +0.2% on ≥2% capture.** All combinations depress directional accuracy relative to random (45–47% vs 48% baseline). Adding more signals consistently reduces sample size without improving accuracy.

---

## 10. Conflict Analysis

| Evidence State | n | UP Dir Acc | DN Dir Acc |
|---|---|---|---|
| ALIGNED (knowledge_score ≥ 0.50) | 8,211 | 47.2% | 51.3% |
| CONFLICT (knowledge_score < 0.50) | 303 | **52.5%** | 50.0% |

**Critical finding:** Candidates where Knowledge is WEAK (CONFLICT) have HIGHER UP directional accuracy (52.5%) than aligned candidates (47.2%). This is a reverse relationship.

**Interpretation:** In the V3 high-ATR pool, stocks with strong technical alignment (momentum positive, RSI in zone, volume confirming) tend to be stocks at the end of a near-term run — making them slightly more prone to reversal. Stocks that don't fit the standard technical narrative are uncorrelated with recent trend, and their T+1 direction is more random — paradoxically giving higher directional accuracy on the UP side.

This finding strongly suggests the standard technical evidence framework is not the right filter for this pool.

---

## 11. Q1–Q15 Answers

| Q | Question | Answer |
|---|---|---|
| Q1 | Does Knowledge improve directional accuracy? | **NO** — OOS: −3.1% UP, −1.1% DN vs random |
| Q2 | Does Knowledge improve ≥2% mover capture? | **NO** — OOS: −3.0% UP, +0.1% DN (negligible) |
| Q3 | Does Knowledge improve ≥3% mover capture? | **NO** — OOS: −0.8% UP, −0.2% DN |
| Q4 | Does Knowledge improve avg favorable movement? | **NO** — avg_mfe essentially unchanged |
| Q5 | Does Knowledge improve top-5 capture? | **NO** — concentration lift 1.02× (random = 1.00×) |
| Q6 | Can Knowledge distinguish the best 5–6 candidates? | **NO** |
| Q7 | Does Knowledge improve UP and DOWN equally? | **NO — neither** |
| Q8 | Which knowledge features provide incremental value? | **None above noise** — best single: `outperforms_market` (+0.2%) |
| Q9 | Which combinations are strongest? | 4-combo ge2=17.1%, but sample=1,900, all combos reduce dir_acc |
| Q10 | Does Knowledge reduce false positives? | **NO** — FP rate similar across all models |
| Q11 | Does Knowledge improve magnitude selection? | **NO** — avg_mfe unchanged |
| Q12 | Does Knowledge-selected 5–6 outperform random from V3 pool? | **NO** |
| Q13 | Does Knowledge-selected 5–6 outperform V3-score 5–6? | **NO** — V3_Top5 beats Know_Top5 on every OOS metric |
| Q14 | Does the Knowledge edge survive OOS? | **NOT APPLICABLE** — no edge existed in training |
| Q15 | Enough evidence to proceed to Knowledge-vs-Strategy? | **NO** — fix Knowledge layer first |

---

## 12. Regime Breakdown (Directional Accuracy by Market Regime)

| Regime | Days | Know_Top5 UP Dir% | Random_5 UP Dir% | Delta |
|---|---|---|---|---|
| BULL | ~72 | ~48.1% | ~49.2% | −1.1% |
| BEAR | ~68 | ~44.2% | ~47.8% | −3.6% |
| RANGE | ~74 | ~46.5% | ~48.3% | −1.8% |

Knowledge underperforms random in all three regimes. The gap is largest in BEAR markets (−3.6%), where the technical evidence framework most consistently fails.

---

## 13. Sector Context

**UNAVAILABLE in this dataset.** The `sector_ret_1d` field is 0.0 for all records in `study002_replay.db` — no sector peer data was loaded during the OIOS rebuild. The `sector_breadth` field is similarly constant.

Sector signals (`sector_positive`, `stock_vs_sector_divergence`) cannot be tested. This is a genuine gap — sector context could provide independent directional evidence not captured by individual stock technicals.

---

## 14. False Positive Analysis

| Model | FP Rate UP | FP Rate DN |
|---|---|---|
| V3_20 | 39.9% | 43.5% |
| Know_Top5 | 38.4% | 42.8% |
| Random_5 | 39.1% | 42.9% |

Know_Top5 marginally reduces false positives on UP (38.4% vs 39.1%) but the difference is within noise. No meaningful false-positive reduction.

---

## 15. Stability Analysis

| Split | Know_Top5 UP Dir% | Random UP Dir% | Gap | Direction |
|---|---|---|---|---|
| TRAIN | 43.5% | 44.2% | −0.7% | Below random |
| VAL | 51.7% | 51.0% | +0.7% | Slightly above |
| OOS | 45.3% | 48.4% | −3.1% | Below random |

Knowledge performance is **unstable** across splits. The VAL period shows a slight positive (+0.7%) that does not generalize to OOS. The OOS gap widens to −3.1%.

---

## 16. Why the Knowledge Layer Fails (Root Cause Analysis)

**The V3 pool is selected for volatility, not trend.** V3's top features are `atr_pct` (0.25 weight) and `vol_ratio` (0.20 weight). The pool contains stocks with the highest ATR and volume. These are stocks that are MOVING — but ATR measures magnitude, not direction.

The 8 Knowledge signals all measure **momentum continuation** (stocks already moving up will keep moving up). This assumption fails in a high-ATR pool because:

1. **High-ATR stocks are at or near inflection points** — they have made a recent large move and are candidate for continuation OR reversal
2. **Technical alignment in this pool signals "already moved a lot"** — not "about to move in the same direction"
3. **The CONFLICT finding confirms this** — stocks with weak technical alignment (haven't moved strongly yet) actually have BETTER T+1 directional accuracy

**What Knowledge is missing:**
- **Catalyst information** (news, earnings, sector event) — the actual cause of the large move
- **Intraday context** (open vs previous close) — early morning gap direction
- **Institutional flow** (FII/DII data) — sustained vs one-day moves
- **Options positioning** (put/call ratio) — forward-looking expectation of direction
- **Volume profile** (where the volume is relative to the day's range) — buying vs selling pressure
- **Sector context** (UNAVAILABLE in current DB) — whether the move is sector-driven or stock-specific

---

## 17. Output Files

| File | Rows/Size | Description |
|---|---|---|
| [v3_knowledge_second_pass_results.json](v3_knowledge_second_pass_results.json) | 1 JSON | Full aggregate results, all 6 models, 4 splits |
| [v3_knowledge_selection_daily.csv](v3_knowledge_selection_daily.csv) | 214 rows | Per-day selection metrics for all 6 models |
| [v3_knowledge_feature_analysis.csv](v3_knowledge_feature_analysis.csv) | 34 rows | Per-feature and combination analysis |
| [v3_knowledge_conflict_analysis.csv](v3_knowledge_conflict_analysis.csv) | 8,514 rows | Per-candidate conflict classification |
| [v3_knowledge_top5_cases.csv](v3_knowledge_top5_cases.csv) | 6,390 rows | Know_Top5, V3_Top5, Rand_Top5 per day |
| [../../tests/test_v3_knowledge_second_pass_001.py](../../tests/test_v3_knowledge_second_pass_001.py) | 40 tests | **40/40 PASS** |

---

## 18. Primary Verdict

```
C. KNOWLEDGE_SECOND_PASS_NO_INCREMENTAL_VALUE
```

The compiled technical Knowledge layer, using 8 backward-looking evidence signals (momentum alignment, RSI zone, volume confirmation, price structure, market outperformance), provides **no statistically meaningful improvement** when filtering the V3 20-stock high-mover pool down to 5–6 candidates.

In OOS, Know_Top5 directionally underperforms both the full pool and random selection. No feature or combination tested exceeds the baseline by more than noise.

---

## 19. Decision Rule Checklist (per Section 28 of audit spec)

| Criterion | Met? | Evidence |
|---|---|---|
| 1. Knowledge Top-5/6 materially beats random | ❌ NO | OOS: −3.1% UP dir, −1.0% DN dir |
| 2. Knowledge Top-5/6 materially beats V3-score Top-5/6 | ❌ NO | V3_Top5 UP dir=50.9% vs Know_Top5=45.3% |
| 3. Directional accuracy improves | ❌ NO | Decreases in OOS |
| 4. ≥2% mover capture improves | ❌ NO | Decreases in OOS for UP |
| 5. ≥3% mover capture improves | ❌ NO | Negligible change |
| 6. Average favorable movement improves | ❌ NO | avg_mfe unchanged |
| 7. Top-mover concentration improves | ❌ NO | Lift 1.02× (random = 1.00×) |
| 8. False positives decrease | ❌ NO | Marginal only |
| 9. Improvement survives OOS | ❌ NO | VAL blip does not carry to OOS |
| 10. No leakage | ✅ YES | All signals backward-looking only |

**0 of 9 performance criteria met.** Verdict: `C`.

---

## 20. Recommendations

**Do not proceed to KNOWLEDGE_VS_STRATEGY_INCREMENTAL_VALUE_002 yet.**

Before the strategy comparison, the Knowledge layer needs at minimum one of:

1. **Sector data integration** — load sector peer returns from OIOS DB (currently zero). This is the biggest missing signal and may provide genuine directional evidence independent of individual stock momentum.

2. **Intraday open-direction signal** — compare each stock's opening price vs prior close on day T+1 (pre-market gap). This is a known leading indicator for intraday direction.

3. **Reverse-momentum hypothesis** — test whether INVERSE knowledge scoring (select stocks with WEAK technical alignment from the V3 pool) consistently improves outcomes. The conflict analysis (52.5% vs 47.2% UP directional accuracy) suggests this warrants investigation.

4. **Market microstructure signals** — bulk/block deal data, FII/DII flow, or options data. All available in `study002_replay.db` (`bulk_block_deals` table) but not used in this audit.

---

*End of V3_KNOWLEDGE_SECOND_PASS_AUDIT_001 — 2026-08-17*
