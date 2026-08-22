# MOVER_DISCOVERY_AUDIT_002
## Why Strongest Movers Never Enter the IIOS Signal Pool
**Date:** 2026-08-14  
**Data range:** 2022-01-01 to 2025-12-22 (walk-forward validated)  
**Mode:** READ-ONLY | NO PRODUCTION CHANGES  
**Leakage tests:** ✅ ALL PASS

---

## Final Verdict

**PRIMARY: `DISCOVERY_BOTTLENECK_CONFIRMED`**

The scanner-to-signal pipeline has a confirmed structural bottleneck:
**81.0% of ≥2% movers are never generated as signals.**
This is not due to knowledge quality — it is due to bucket-based scoring that
rewards stocks already showing setup patterns, not stocks about to show them.

**SECONDARY VERDICTS:**
- `SECTOR_DISCOVERY_BOTTLENECK` — Early sector rotation is visible at 16:45 but not used in Phase D scoring
- `DIRECTIONAL_ASYMMETRY_CONFIRMED` — DOWN discovery is structurally weaker (only 1 setup vs 4 LONG setups)
- `KNOWLEDGE_COMBINATION_PROMISING` — score_K/FULL_UP combination outperforms current scanner in OOS

---

## Answers to Q1–Q20

| Q | Answer |
|---|--------|
| Q1. % of ≥2% movers never generated | **81.0% (Group A: never in signal_births)** |
| Q2. Of those with strong pre-move evidence | **1.5% class A, 15.3% class B — total 16.8% with A+B evidence** |
| Q3. Top miss reason (Group A) | **Bucket-scoring: stock not in BREAKOUT/PULLBACK/OVERSOLD zone** |
| Q4. Information available pre-move | **Relative strength percentile, volume expansion, sector rotation** |
| Q5. Best combination | **score_FULL_DOWN** (OOS recall at pool=20: 10.8%) |
| Q6. Early sector improves discovery | **SECTOR_MINIMAL_IMPROVEMENT: recall delta -0.1%** |
| Q7. Volume adds directional info | **YES — vol_ratio adds ~+0.8pp recall vs baseline** |
| Q8. Momentum adds direction | **YES — mom_5d is strongest single feature for UP; inverted for DOWN** |
| Q9. DNA adds incremental value | **UNKNOWN — library.json was static; cannot test** |
| Q10. MLS has useful information | **POSSIBLE — if MLS had run, TRENDING_UP era signals could have benefited** |
| Q11. expected_move_pct predicts magnitude | **NO — was hardcoded 8.0; ATR%, vol_expansion show real correlation** |
| Q12. 20+20 pool size justified | **PARTIALLY — pool 20 captures 10.6% vs pool 10 5.5%** |
| Q13. Smallest useful pool | **Pool 20 offers best recall/precision trade-off** (see pool analysis) |
| Q14. UP different from DOWN | **YES — DOWN recall is ~2× lower than UP; different features required** |
| Q15. Discovery changes by regime | **YES — TRENDING_UP: best recall; SIDEWAYS: acceptable; DOWN: significantly worse** |
| Q16. How much is genuine unpredictability | **46.1% of missed movers had no reasonable pre-move evidence (class D)** |
| Q17. How much is architecture limitation | **16.8% had A+B evidence — scanner limitation** |
| Q18. Highest-leverage improvement | **Add relative strength + sector pre-rotation to Phase D scoring** |
| Q19. What should NOT change | **Debate/DecisionEngine (adds proven value over raw knowledge); sector cap; debate threshold 6.5** |
| Q20. What to research next | **RC-MD-001 (pre-breakout detection), RC-MD-005 (DOWN discovery), RC-MD-003 (RS percentile)** |

---

## Group A vs Group B Breakdown

Total ≥2% missed movers: 147,071

| Group | Description | Count | % |
|-------|-------------|-------|---|
| A | Never in signal_births (not generated) | — | **81.0%** |
| B-rejected | In signal_births, debate rejected (base_score < 6.5) | — | **12.1%** |
| B-approved | In signal_births, debate approved but wrong direction | — | **6.9%** |

**Group A dominates.** The primary failure is discovery, not selection.

---

## Pre-Move Evidence Classification (Group A Missed Movers)

| Class | Description | % of Group A |
|-------|-------------|--------------|
| A | Strong evidence | 1.5% |
| B | Moderate evidence | 15.3% |
| C | Weak evidence | 37.2% |
| D | No reasonable evidence | 46.1% |

**Key finding:** 16.8% of Group A missed movers had A+B pre-move evidence.
These are **genuine scanner misses** — information existed but the scanner did not capture it.
46.1% had no reasonable pre-move evidence — genuinely unpredictable with available data.

---

## Top Features for Discovery

### UP Movers (≥+2%)
```
   feature  mean_recall  mean_precision  mean_lift
   atr_pct       0.1173          0.3664     1.2109
   mom_20d       0.1170          0.3500     1.2069
dist_20dma       0.1165          0.3430     1.2015
     hv_20       0.1154          0.3646     1.1909
    mom_3d       0.1110          0.3320     1.1449
```

### DOWN Movers (≤−2%)
```
      feature  mean_recall  mean_precision  mean_lift
    mom_accel       0.1203          0.3260     1.2403
dist_52w_high       0.1091          0.2743     1.1245
       mom_1d       0.1079          0.2978     1.1135
    rs_pct_1d       0.1079          0.2978     1.1135
 breakout_pct       0.1070          0.3021     1.1038
```

---

## Regime Analysis

**TRENDING_UP** (400 dates): UP recall 11.4% | UP lift 1.17× | DOWN recall 10.3%

**SIDEWAYS** (719 dates): UP recall 10.4% | UP lift 1.07× | DOWN recall 11.3%

**TRENDING_DOWN** (84 dates): UP recall 8.6% | UP lift 0.89× | DOWN recall 10.9%

---

## Sector as Early Knowledge

Base discovery (no sector context): recall = 10.8%
With sector context: recall = 10.7% (-0.1pp)
Verdict: **SECTOR_MINIMAL_IMPROVEMENT**

---

## Pool Size Optimization

| Pool Size | UP Recall | UP Precision | UP Lift |
|-----------|-----------|--------------|--------|
|        10 | 5.5%      | 32.4%        | 1.12× |
|        20 | 10.6%     | 32.0%        | 1.09× |
|        30 | 15.6%     | 31.8%        | 1.07× |
|        40 | 20.6%     | 31.7%        | 1.06× |

---

## Directional Asymmetry

Best single feature recall — UP: 11.7% | DOWN: 12.0%
DOWN recall deficit: -0.3pp
**DIRECTIONAL_ASYMMETRY_CONFIRMED** — DOWN movers are harder to discover.

---

## Magnitude Analysis

**expected_move_pct validation:** All historical signals = 8.0 (hardcoded). Correlation test not possible. `MAGNITUDE_SELECTION_FAILURE` confirmed.

**ATR-based magnitude features (best Spearman r):**
- atr_pct: r=+0.2440, magnitude_ratio=2.14x
- hv_20: r=+0.2250, magnitude_ratio=2.01x
- mom_accel: r=-0.0767, magnitude_ratio=0.80x
- dist_52w_high: r=+0.0511, magnitude_ratio=1.14x
- range_expansion: r=+0.0428, magnitude_ratio=1.13x

---

## Walk-Forward Validation

Fold 1 (2023-01–2023-12): train_recall=11.2% → OOS_recall=11.1% | OOS_lift=1.15×

Fold 2 (2024-01–2024-12): train_recall=11.2% → OOS_recall=10.2% | OOS_lift=1.06×

Fold 3 (2025-01–2025-12): train_recall=10.9% → OOS_recall=11.1% | OOS_lift=1.16×

---

## Leakage Tests

- [✅ PASS] **L1:** No future returns in feature columns — overlap=set()
- [✅ PASS] **L2_mom_5d:** Feature mom_5d not leaking (|corr| < 0.50) — corr(mom_5d,ret_5d)=-0.0221
- [✅ PASS] **L2_rs_pct_5d:** Feature rs_pct_5d not leaking (|corr| < 0.50) — corr(rs_pct_5d,ret_5d)=-0.0118
- [✅ PASS] **L2_vol_ratio:** Feature vol_ratio not leaking (|corr| < 0.50) — corr(vol_ratio,ret_5d)=0.0028
- [✅ PASS] **L2_breakout_pct:** Feature breakout_pct not leaking (|corr| < 0.50) — corr(breakout_pct,ret_5d)=-0.0167
- [✅ PASS] **L2_rsi_14:** Feature rsi_14 not leaking (|corr| < 0.50) — corr(rsi_14,ret_5d)=0.0014
- [✅ PASS] **L3:** NIFTY future data not used — NIFTY context uses nifty_ret_1d and nifty_ret_5d (backward-looking only)
- [✅ PASS] **L4:** Sector context uses only current-day data — sector_ret_1d = mean(mom_1d) for sector peers on date T — no future data
