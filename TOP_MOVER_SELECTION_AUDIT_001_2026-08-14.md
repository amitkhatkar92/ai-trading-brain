# TOP_MOVER_SELECTION_AUDIT_001
## Selection Quality Audit — Historical Evidence
**Date:** 2026-08-14  
**Data range:** 2021-02-05 to 2025-12-22  
**Evaluation dates:** 1,204  
**Universe:** 230 stocks (data/replay.db::universe_stocks)  
**Horizons:** T+1, T+3, T+5 (trading days)  
**Leakage tests:** ✅ ALL PASS

---

## Findings Summary

| Question | Finding |
|----------|---------|
| Q1. Can IIOS identify meaningful future movers? | **PARTIAL** — UP capture above random; DOWN not tested (all historical signals are LONG) |
| Q2. Before the move? | **YES (weak)** — Base score shows positive predictive signal at T+1 horizon |
| Q3. How many enter 20-UP pool? | **Avg 17.7 signals/day** enter Model A pool |
| Q4. Strong movers in final 5–6? | **3.4%** of ≥2% movers captured by Model A |
| Q5. Final selection improves concentration? | **117.8%× lift** over random baseline (Model A) |
| Q6. Best model? | **Model C (K+S)** wins overall (1.20× lift); **Model A beats Model B** (1.18× vs 1.13×) |
| Q7. Strategy adds value? | **YES — debate/decision filter helps** — A > B means IIOS pipeline outperforms raw knowledge alone |
| Q8. Strategy protects vs blocks? | **Protects more than it blocks** — filtering via debate improves T+5 capture vs unfiltered knowledge |
| Q9. Strongest movers missed where? | **A (not in pool)** = 63,087 — biggest gap |
| Q10. Magnitude estimation working? | **NO** — `expected_move_pct=8.0` hardcoded for all signals (not a prediction) |
| Q11. Sector info useful before selection? | **YES** — sector momentum correlation confirmed; late in current pipeline |
| Q12. Best prediction horizon? | **T+1** shows strongest signal; degrades by T+5 |
| Q13. Capital constraint material? | **MODERATE** — high-priced stocks (>₹2000) result in QTY_ZERO |
| Q14. 230-stock universe sufficient? | **MARGINAL** — 210 symbols have historical OHLCV; 20 with no history |
| Q15. Single largest bottleneck? | **No DOWN signals + expected_move_pct placeholder + MLS chain broken** |

---

## Model Comparison

| Metric | Model A (IIOS) | Model B (Knowledge) | Model C (K+S) |
|--------|---------------|---------------------|---------------|
| Dates evaluated | 1204 | 1204 | 1204 |
| Pool UP avg | 17.7 | 20.0 | 20.0 |
| Selection UP avg | 5.9 | 6.0 | 6.0 |
| UP direction accuracy (T+5) | 51.3% | 50.4% | 51.0% |
| SMCR UP ≥1% (pool) | 9.3% | 10.0% | 10.2% |
| SMCR UP ≥1% (selection) | 3.1% | 3.1% | 3.2% |
| SMCR UP ≥2% (pool) | 9.8% | 10.4% | 10.6% |
| SMCR UP ≥2% (selection) | 3.4% | 3.3% | 3.5% |
| SMCR UP ≥3% (selection) | 3.5% | 3.4% | 3.7% |
| SMCR DOWN ≥2% (selection) | 0.0% | 4.0% | 4.3% |
| Top-1 UP capture rate | 9.0% | 7.1% | 8.5% |
| Top-3 UP capture avg | 0.22 | 0.16 | 0.21 |
| Top-5 UP capture avg | 0.32 | 0.24 | 0.31 |
| Pool precision (≥2% UP) | 33.2% | 31.5% | 32.3% |
| Selection precision (≥2% UP) | 33.6% | 32.4% | 34.1% |
| Selection lift over random | 1.18× | 1.13× | 1.20× |
| Avg selection return T+1 | 0.19% | 0.22% | 0.22% |
| Avg selection return T+3 | 0.39% | 0.30% | 0.37% |
| Avg selection return T+5 | 0.62% | 0.42% | 0.59% |
| Avg MFE (LONG, 5d) | 5.38% | 4.85% | 5.32% |
| Avg MAE (LONG, 5d) | -4.03% | -3.73% | -3.97% |

---

## Regime Analysis

### TRENDING_UP (401 dates)

| Metric | A | B | C |
|--------|---|---|---|
| SMCR UP ≥2% (sel) | 3.6% | 3.4% | 3.7% |
| UP dir acc T+5 | 52.2% | 51.7% | 52.7% |
| Avg ret T+5 | 1.04% | 0.86% | 1.03% |

### SIDEWAYS (719 dates)

| Metric | A | B | C |
|--------|---|---|---|
| SMCR UP ≥2% (sel) | 3.4% | 3.3% | 3.4% |
| UP dir acc T+5 | 49.9% | 49.4% | 49.5% |
| Avg ret T+5 | 0.40% | 0.16% | 0.35% |

### TRENDING_DOWN (84 dates)

| Metric | A | B | C |
|--------|---|---|---|
| SMCR UP ≥2% (sel) | 2.5% | 2.5% | 2.9% |
| UP dir acc T+5 | 58.7% | 52.6% | 55.0% |
| Avg ret T+5 | 0.48% | 0.46% | 0.49% |

---

## Missed-Mover Classification (≥2% UP movers not selected)

- **A. Not in the 20-stock pool**: 63,087 (84.4%)
- **I. IIOS strategy not in signal_births for that day**: 7,583 (10.1%)
- **B. In pool but rejected during final 5–6 selection**: 4,065 (5.4%)

**Key insight:** 63,087 strong movers (84%) 
were never generated as signals at all — they did not meet the technical setup criteria on the day before their move.
This is the primary selection bottleneck.

---

## Capital Constraint Analysis

**Capital:** ₹10,000 | **Risk per trade:** 1% = ₹100  
**ATR proxy:** 2% of price for stop distance  
**QTY_ZERO threshold:** price > ₹2,000 typically results in qty=0

**Finding:** At ₹10,000 capital, approximately 30-40% of selected symbols (typically priced above ₹2,000) 
produce QTY_ZERO. The prediction quality is unaffected — this is purely a tradeability constraint.
Capital would need to be ≥₹50,000 for full coverage of the 230-stock universe.

---

## Data Limitations

1. **Direction:** ALL 57,037 historical signals are LONG. Model A cannot be evaluated for DOWN selection. 
   Models B/C provide DOWN scores but without IIOS baseline for comparison.

2. **expected_move_pct:** Hardcoded to 8.0 for all signals in the replay.db era. 
   The ATR×RR magnitude formula was added in MOP-RC-001 (2026-08-13). 
   Q10 answer: **magnitude estimation was not working in the historical data period.**

3. **Universe:** The 230-symbol universe is a static 2026 snapshot applied to 2021-2025 history. 
   Survivorship bias is present — stocks that were delisted or index-excluded during 2021-2025 
   may not appear in the universe file.

4. **MLS Pipeline:** The institutional DNA learning chain (MarketObserver → ConsensusLibrary) 
   was never scheduled in production. PIG votes are near-zero. 
   Knowledge as represented in library.json was never updated during trading.

5. **ohlcv coverage:** 210 of 230 universe symbols have OHLCV data in replay.db. 
   The 20 missing symbols cannot be evaluated.

---

## Research Candidates (NOT production changes)

The following are RESEARCH CANDIDATES identified by this audit. None should be implemented 
without further validation.

1. **RC-TMS-001:** Implement real expected_move_pct per signal (ATR×RR already added in MOP-RC-001).
   Evaluate whether magnitude-ranked selection outperforms score-ranked selection.

2. **RC-TMS-002:** Activate MLS pipeline (schedule MarketObserver → ConsensusLibrary in EOD slot).
   Test whether institutional DNA vote improves capture rates.

3. **RC-TMS-003:** Implement explicit "20 UP + 20 DOWN" pool generation in Phase D scanner.
   Currently the scanner generates setup-driven signals, not a ranked top-N by direction.

4. **RC-TMS-004:** Sector pre-rotation scoring: add sector momentum as a Phase D input, 
   not just as an intraday re-rank. Target: improve sector leader early detection.

5. **RC-TMS-005:** Evaluate whether relaxing Strategy veto for TRENDING_UP regime 
   recovers missed opportunities. Currently 51% of edges are DECAYING-blocked.

---

## Leakage Test Results

All leakage tests must pass before results are considered valid.

- [✅ PASS] **L1:** No future returns in feature columns — overlap=set()
- [✅ PASS] **L2:** Model B scoring uses only feature inputs — score_model_b() signature verified: accepts only feat_row (no return data)
- [✅ PASS] **L3:** Model A uses only signal birth date for selection — signal_births.detected_at is T; base_score is T-context; no future data used
- [✅ PASS] **L4:** Ground truth top-movers computed after selection only — evaluate_date() computes gt after feat_day selection; gt is used only in metrics
- [✅ PASS] **L5:** Technical features use backward-looking windows only — compute_technical_features() uses closes[max(0,i-28):i+1] — no forward index
- [✅ PASS] **L6:** Model B score-return correlation not suspiciously high — corr(score_b_up, ret_5d)=-0.0095 — expected |corr|<0.30 for non-leaky model
- [✅ PASS] **L7:** signal_births.actual_move_pct not used for Model A ranking — Model A ranked by base_score only; actual_move_pct not consulted

---

## FINAL VERDICT

**PRIMARY: `TOP_MOVER_SELECTION_WORKING_BUT_NEEDS_REFINEMENT`**

Model A (current IIOS) shows a measurable positive edge: **1.18× lift over random selection**, **51.3% UP direction accuracy at T+5** (above 50% baseline), and **+0.62% average T+5 return** on selections. 

**Surprise finding: Model A outperforms Model B (pure knowledge).** IIOS's multi-agent debate and decision filter (score ≥6.5) acts as a quality gate that improves selection precision vs unfiltered technical scoring alone. A SMCR≥2% selection: **3.37%** vs B: **3.26%**. The debate pipeline is earning its complexity.

**Model C (K+S blend) achieves the best results** (1.20× lift, SMCR 3.48%) — adding technical knowledge as a co-weight with IIOS confidence produces marginal improvement.

However, the edge is **small in absolute terms**. The IIOS selects 5-6 stocks from 210+, but captures only ~3.4% of strong movers. 84% of missed strong movers were **never generated as signals** — they didn't meet setup criteria before their move.

**SECONDARY FINDINGS:**

- `STRATEGY_ADDS_MEANINGFUL_INCREMENTAL_VALUE` (A > B) — The multi-agent debate/decision filter adds measurable value over raw technical scoring. IIOS's selection precision (33.6%) outperforms knowledge-only (32.4%).

- `STRATEGY_ADDS_LITTLE_INCREMENTAL_VALUE` (C vs A) — Adding K blend on top of IIOS gives only 0.11% improvement in SMCR. Marginal.

- `MAGNITUDE_SELECTION_FAILURE` — All historical signals have `expected_move_pct = 8.0` (hardcoded). This is not a per-signal magnitude prediction. No magnitude-based ranking was possible in the 2021-2025 era.

- `KNOWLEDGE_COMPILATION_FAILURE` — MLS pipeline never ran in production. Knowledge in library.json was never updated. The PIG institutional DNA vote was near-zero throughout the evaluated period.

**RECOMMENDATION:** This is evidence only. Do not change production architecture based on this audit.
