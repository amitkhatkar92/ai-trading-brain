# MOVER DISCOVERY V3 — Research Report
**Date:** 2026-08-14
**Database:** data/replay.db (2021-2025, 256,268 OHLCV rows)
**Mode:** RESEARCH / SHADOW — no production changes

---

## A. What Existing Discovery Does

The production Phase D scanner runs at 16:45 IST. It:
1. Loads 35-day OHLCV for 230 symbols
2. Classifies each symbol into hard buckets:
   - BREAKOUT: within 2% of 20d resistance (BREAKOUT_PROXIMITY_PCT=0.02)
   - PULLBACK: RSI 50–65, in bull regime, near support
   - OVERSOLD: RSI ≤ 40
   - OVERBOUGHT: RSI ≥ 65 (SHORT candidate)
   - VOLUME_EXPAND: vol_ratio ≥ 1.8
3. Scores by bucket membership
4. Applies MIN_PREPARED_SCORE=0.55 floor (hard rejection)
5. Applies sector cap (20%) and max count (120)

Result: only symbols already in recognisable setup states are selected.
Pre-breakout, mid-range, and moderate-volume stocks are systematically excluded.

---

## B. What V3 Changes

V3 replaces hard gates with continuous scoring:
- Volume is a score component (not a gate)
- Distance-from-resistance is a score component (not a gate)
- RSI zones 40–65 are included (not excluded)
- Two separate directional pools (UP and DOWN)
- Universe-percentile ranking removes absolute-threshold sensitivity

---

## C. Why Each Change Is Supported by AUDIT_002

| Production gate | AUDIT_002 evidence | V3 response |
|-----------------|-------------------|-------------|
| vol_ratio ≥ 1.8 (hard) | 92.8% of missed movers had vol_ratio < 1.8 | Continuous vol score |
| ltp within 2% of resistance | 88.4% of missed movers were >2% from resistance | Continuous dist-resistance feature |
| RSI only <40 or >65 | 30.7% had RSI 45–55 (no bucket) | RSI-zone scoring for entire range |
| Separate UP scoring | All 57,037 signals were LONG | Separate DOWN pool |
| 8.0 magnitude constant | spearman_r ≈ 0 (confirmed) | atr_pct (r=0.244) for magnitude |

---

## D. UP Feature Set (Weights)

| Feature | Weight | Justification |
|---------|--------|---------------|
| atr_pct | 0.25 | Top single feature, lift 1.21× (AUDIT_002) |
| mom_5d | 0.20 | Trend persistence, lift 1.21× |
| rs_pct_5d | 0.20 | Relative strength in universe |
| vol_ratio | 0.20 | Accumulation signal |
| mom_accel | 0.15 | Momentum building |

---

## E. DOWN Feature Set (Weights)

| Feature | Weight | Justification |
|---------|--------|---------------|
| neg_mom_5d | 0.30 | Inverted momentum (primary DOWN signal) |
| neg_mom_accel | 0.25 | Top DOWN feature in AUDIT_002, lift 1.24× |
| vol_expansion | 0.20 | Volume into decline (score_DOWN_C, lift 1.26×) |
| atr_pct | 0.15 | Volatility premium for reversals |
| rsi_overbought | 0.10 | Overbought positioning |

Sector: DISABLED by default (AUDIT_002: lift_delta = −0.013)

---

## F. Pool-Size Results (OOS)

| Pool | UP Lift | UP Recall | UP Precision | DOWN Lift |
|------|---------|-----------|--------------|-----------|
| 10 | 1.633 | 0.080 | 0.190 | 1.419 |
| 15 | 1.561 | 0.115 | 0.185 | 1.401 |
| 20 | 1.537 | 0.151 | 0.183 | 1.323 |
| 25 | 1.482 | 0.183 | 0.177 | 1.265 |
| 30 | 1.416 | 0.209 | 0.172 | 1.224 |
| 40 | 1.346 | 0.263 | 0.165 | 1.188 |

---

## G. In-Sample Results (2021–2023)

UP:
  Recall:    0.1813
  Precision: 0.2096
  Lift:      1.8176

DOWN:
  Recall:    0.1325
  Precision: 0.1435
  Lift:      1.3221

---

## H. OOS Results (2024–2025)

UP:
  Recall:    0.1514
  Precision: 0.1829
  Lift:      1.5371

DOWN:
  Recall:    0.1301
  Precision: 0.1504
  Lift:      1.3228

---

## I. Leakage Results

Violations: 0
Status: CLEAN
All features are PIT-safe (backward-looking windows only).

---

## J. Existing vs V3 Overlap

Total ≥2% movers: 60,449
  UP movers:   32,546
  DOWN movers: 27,903

Existing scanner coverage:
  UP:   6,761  (20.8%)
  DOWN: 5,281  (18.9%)

V3 top-20 coverage:
  UP:   4,775  (14.7%)
  DOWN: 3,508  (12.6%)

Both existing + V3:
  UP:   2,584  (7.9%)
  DOWN: 251  (0.9%)

Average daily overlap fraction: 0.325

Group distribution:
  Group A (existing scanner never saw): 48,407  (80.1%)
  Group B (existing scanner included):  12,042  (19.9%)

---

## K. Newly Recovered Movers by V3

UP movers recovered by V3 (not in existing scanner): 2,191
DOWN movers recovered by V3:                         3,257

Walk-forward validation:
| Fold | UP Lift | UP Recall | DOWN Lift | DOWN Recall |
|------|---------|-----------|-----------|-------------|
| OOS_2023-01_2023-12 | 1.979 | 0.193 | 1.452 | 0.141 |
| OOS_2024-01_2024-12 | 1.568 | 0.155 | 1.415 | 0.139 |
| OOS_2025-01_2025-12 | 1.505 | 0.148 | 1.230 | 0.121 |

---

## L. False-Positive Impact

UP false-positive rate (pool=20): 0.8027 (80.3% of V3 UP selections are non-movers)
DOWN false-positive rate:         0.8550 (85.5%)

Average ATR% of V3-selected UP candidates:   3.95%
Average ATR% of V3-selected DOWN candidates: 4.14%

Note: 68% FP rate is expected at pool=20 (confirmed in AUDIT_002).
V3 is a discovery/prioritisation layer, not a precision filter.
Full debate + risk evaluation remains required before any trade.

---

## M. Recommended Next Step

1. Activate shadow mode in production at 16:45 (read-only, no side effects)
2. Collect 20 trading days of shadow logs (data/mover_discovery_v3_shadow.jsonl)
3. Compare shadow overlap with live CandidateStore results
4. If OOS lift holds in live shadow: begin research on V3 → strategy integration
5. Do NOT integrate V3 into live trading without ≥60 days of shadow validation

---

## FINAL VERDICT

GO criterion:
  OOS UP lift   ≥ 1.10  → Actual: 1.5371
  OOS DOWN lift ≥ 1.10  → Actual: 1.3228
  Leakage clean          → YES

**VERDICT: GO**

V3 research module may proceed to shadow mode deployment.
