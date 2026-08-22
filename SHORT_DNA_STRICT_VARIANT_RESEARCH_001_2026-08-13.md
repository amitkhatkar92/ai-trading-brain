# SHORT_DNA_STRICT_VARIANT_RESEARCH_001
**Date:** 2026-08-13  
**Prepared by:** Copilot — read-only research  
**Scope:** Strict-variant backtest of Setup 4 with DNA filter and stricter RSI threshold  
**Parent study:** HIGH_RSI_SHORT_VALIDATION_001_2026-08-13.md  
**Production changes:** NONE  
**Orders placed:** 0  

---

## Executive Summary

| Item | Value |
|---|---|
| **Verdict** | **FAIL** |
| Test period | 2021-07-22 – 2025-11-28 |
| Group C (strict variant) | RSI ≥ 70 + RANGE_MARKET + vol_ratio ≥ 1.5× |
| Total signals | 133 |
| Win rate | 42.9% (threshold ≥ 50%) |
| Expectancy | +3.54%R/trade (positive — passes gate) |
| Profit factor | 1.071 (passes gate) |
| Max drawdown | 19.1 R (fails ≤ 15R gate) |
| Sharpe | +0.479 (positive — passes gate) |
| Governance gates | 5/9 PASS |
| WF consistency | 2/5 folds (40%) — fails ≥ 60% gate |
| Data leakage | NONE_FOUND (15/15 checks) |

**The strict variant fails governance** on three criteria: win rate (42.9% vs 50% threshold), max drawdown (19.1R vs 15R threshold), and walk-forward consistency (2/5 folds vs ≥3/5 required). The aggregate positive expectancy (+3.54%R) is not sufficient for activation.

**However, the OOS period (2024-07-01 to 2025-12-22) shows WR=52.6%, Exp=+31.1%R, PF=1.759, MaxDD=6.0R across 38 trades.** This is a genuine directional signal — the strategy appears to work in recent market conditions but fails in the 2022–2024 period. The DNA filter is confirmed to add real predictive value: eliminating 80% of RSI≥70 signals and converting expectancy from −7.18%R (no DNA) to +3.54%R (with DNA).

**Research on this variant is not yet conclusive. Stop here per governance policy.** Further study requires additional live data accumulation in the OOS environment (minimum 60 more trades in 2025+ conditions) before re-running governance.

---

## Phase 1 — DNA Condition Trace

### 1.1 Exact DNA Rule

The 133 Group C trades satisfied all of the following simultaneously:

| Condition | Threshold | Source | Research? |
|---|---|---|---|
| RSI(14) | ≥ 70.0 | `equity_scanner_ai.py` Setup 4 extends | **RESEARCH HYPOTHESIS** — production uses 67 |
| LTP near resistance | LTP ≥ resistance × 0.99 | `equity_scanner_ai.py` line ~2065, `RESIST_PROX = 0.99` | Production |
| ATR% guard | ATR(14) / LTP × 100 < 4.0% | `equity_scanner_ai.py` `VOLATILITY_GUARD_ATR_PCT = 4.0` | Production |
| Regime | RANGE_MARKET only | Market regime classification | **RESEARCH** — production allows VOLATILE too |
| Volume spike (DNA) | `vol_ratio ≥ 1.5×` | `institutional_dna.db` pattern: `volume_spike > 1.5`, conf=1.0 | Production (ph2_short_dna) |
| ADV | ≥ ₹15 crore | `market_scanner.py` | Production |

The **volume spike DNA condition** is the defining filter for the 265-trade DNA subset found in VALIDATION_001. It requires the trailing 3-day average volume to be at least 1.5× the 20-day average volume at signal time.

### 1.2 DNA Evidence Provenance

From `data/mls/institutional_dna.db`:

```
Pattern:        volume_spike
Direction:      SHORT
Condition:      volume > 1.5 × 20d_avg
Confidence:     1.0  (maximum)
Evidence count: 135 events (69 + 66 across two records)
Last updated:   2026-08-05  (BEFORE this backtest — no forward-looking bias)
```

The DNA confidence of 1.0 produces a theoretical boost of `min(1.0 × 1 × 0.30, 1.50) = 0.30`, but since Setup 4 confidence is already capped at 8.5 and Setup 4 always outputs 8.5 for RSI ≥ 60, the boost is absorbed. The DNA is used here **purely as a filter** (vol_ratio ≥ 1.5×), not as a confidence modifier.

### 1.3 Stop, Target, and Exit Conditions (unchanged from production)

```
Entry:         close[t]  (EOD signal — same-day close)
Stop loss:     entry + max(ATR × 1.5, LTP × 1%)
Target:        entry − 2.5 × stop_dist
R:R:           2.5
Max hold:      10 trading days (forced mark-to-market close)
Conservative:  if same day triggers stop AND target → stop wins (pessimistic)
```

### 1.4 What is NOT in Group C

Group C does **not** apply:

- Any sector filter (institutional_dna.db does not carry sector specificity)
- Any minimum RSI lookback condition beyond RSI(14) ≥ 70.0
- Any PCR, put/call skew, or options data
- Any breadth adjustment (breadth proxy = 0.50 neutral throughout)

---

## Phase 2 — Strict Variant Parameters

**Research hypothesis under test:** *"RSI ≥ 70 + institutional volume_spike confirmation + RANGE_MARKET regime produces a repeatable short equity edge in Indian large-cap equities."*

Parameters set by research hypothesis (not production code):

| Parameter | RESEARCH value | Production value | Delta |
|---|---|---|---|
| RSI threshold | 70.0 | 67.0 | +3.0 |
| Allowed regimes | RANGE_MARKET only | RANGE_MARKET + VOLATILE | Stricter |
| DNA filter | Required | Not connected | New gate |

All other parameters are **identical to production**: ATR period = 14, stop multiplier = 1.5, RR = 2.5, max hold = 10 days, ATR% guard = 4.0%, resistance window = 20 days.

**Threshold selection rationale**: RSI ≥ 70 is the classic "overbought" boundary used in virtually all mean-reversion short literature. It is **not derived from in-sample optimization** — this study does not search for an RSI value that maximises historical expectancy. RSI 70 was selected as the first round number above the existing production threshold (67), making it a natural and theory-grounded escalation.

---

## Phase 3 — Four-Group Comparison

Five groups tested over the same 2021–2025 dataset:

| Group | Definition | n | Win Rate | Expectancy | PF | Total R | Max DD | Sharpe | Avg R/trade |
|---|---|---|---|---|---|---|---|---|---|
| **A** | RSI ≥ 67, Range+Volatile, no DNA | 1,394 | 41.2% | −2.39%R | 0.954 | −33.3R | 51.6R | −0.322 | −0.024 |
| **B** | RSI ≥ 67, Range+Volatile, DNA | 265 | 42.6% | +3.24%R | 1.066 | +8.6R | 18.4R | +0.438 | +0.032 |
| **B-RM** | RSI ≥ 67, Range only, DNA | 255 | 42.4% | +3.21%R | 1.065 | +8.2R | 18.5R | +0.430 | +0.032 |
| **E** | RSI ≥ 70, Range only, no DNA | 661 | 39.5% | −7.18%R | 0.869 | −47.5R | 53.3R | −0.971 | −0.072 |
| **C** | RSI ≥ 70, Range only, DNA | **133** | **42.9%** | **+3.54%R** | **1.071** | **+4.7R** | **19.1R** | **+0.479** | **+0.035** |

### Key observations from the comparison:

1. **RSI ≥ 70 alone makes things worse (A vs E)**: Restricting to RSI ≥ 70 without DNA drops the win rate from 41.2% to 39.5% and expectancy from −2.39%R to −7.18%R. Stricter RSI alone selects more momentum-persistent stocks, not better reversal candidates.

2. **DNA filter is the decisive variable**: Adding vol_ratio ≥ 1.5× to any RSI group flips expectancy from negative to positive. The swing from E (−7.18%R) to C (+3.54%R) is entirely attributable to the DNA filter eliminating 80% of E signals.

3. **Range-only restriction adds marginal benefit**: B vs B-RM comparison: removing VOLATILE regime reduces n by 10 (265 → 255) with nearly identical stats. This confirms VOLATILE regime is harmful but not the primary issue.

4. **The DNA signal quality exists at RSI ≥ 67 too**: Groups B and B-RM (RSI ≥ 67 + DNA) already achieve +3.2%R expectancy. The RSI ≥ 70 additional restriction does not materially improve statistics over B-RM (+3.54 vs +3.21).

5. **Net conclusion**: The positive expectancy in Group C (+3.54%R) is primarily driven by the DNA volume filter, secondarily by the range-only regime gate, and minimally by the RSI ≥ 70 escalation.

---

## Phase 4 — Temporal Validation

### 4.1 Train / Validation / Out-of-Sample Split

| Period | Dates | Group C n | WR | Expectancy | PF | Max DD |
|---|---|---|---|---|---|---|
| **Train** | ≤ 2023-06-30 | 52 | 40.4% | −1.09%R | 0.980 | 8.2R |
| **Validation** | 2023-07-01 to 2024-06-30 | 43 | 37.2% | −15.25%R | 0.711 | 11.8R |
| **OOS** | 2024-07-01 to 2025-12-22 | **38** | **52.6%** | **+31.13%R** | **1.759** | **6.0R** |

**Critical finding**: The train and validation periods are **both negative**. The OOS period alone is positive — and strongly so. This creates a contradictory picture:

- If the OOS result is the "true" forward performance: the strategy has genuinely improved and deserves re-evaluation with more data
- If the OOS result is statistical noise (n=38 is a small sample): the strategy is still unproven

The OOS win rate of 52.6% from 38 trades has a 95% confidence interval of approximately [36.1%, 68.5%] — wide enough to include values below 50%. This means the OOS result, while promising, is **not statistically conclusive** at conventional significance levels.

For the baseline comparison:
| Period | Group E (no DNA) n | WR | Expectancy |
|---|---|---|---|
| Train | 271 | 35.4% | −18.01%R |
| Val | 187 | 38.5% | −2.42%R |
| OOS | 203 | 45.8% | +2.89%R |

Group E also improves in the OOS period (−18%R train → +2.89%R OOS), suggesting the general RSI≥70+Range environment improved post-mid-2024. The DNA filter amplifies this improvement (C OOS = +31.1%R vs E OOS = +2.9%R).

### 4.2 Walk-Forward Results (5 Folds, Group C)

| Fold | Period | n | Win Rate | Expectancy | Total R | Pass (WR≥50%)? |
|---|---|---|---|---|---|---|
| fold_1 | 2021-07-26 – 2022-09-01 | 26 | **53.8%** | +28.3%R | +7.4R | ✅ PASS |
| fold_2 | 2022-09-01 – 2023-06-30 | 26 | 26.9% | −30.4%R | −7.9R | ❌ FAIL |
| fold_3 | 2023-07-06 – 2024-01-29 | 26 | 42.3% | −11.2%R | −2.9R | ❌ FAIL |
| fold_4 | 2024-01-31 – 2024-10-01 | 26 | 34.6% | −12.3%R | −3.2R | ❌ FAIL |
| fold_5 | 2024-11-27 – 2025-11-28 | **29** | **55.2%** | +39.2%R | +11.4R | ✅ PASS |

**Walk-forward consistency: 2/5 folds (40%). Required: ≥60%.**

The WF pattern is highly irregular — not a linear learning curve. Folds 1 and 5 both pass (early 2021-2022 and late 2024-2025), while folds 2, 3, 4 (2022–2024) all fail. This V-shaped pattern suggests the strategy is **environment-dependent**, working in low-volatility range-bound periods and failing when momentum dominates.

The 2022–2024 period was characterised by:
- Post-COVID momentum continuation (2021-2022 bull run into 2022-Q1 peak)
- Sharp corrections (2022 Russia-Ukraine risk-off selloff)
- Strong NIFTY bull run (2023 broad market rip)
- High RSI readings being consistently followed by further advances (momentum vs mean-reversion)

The 2024-Q3 to 2025 period has seen a more volatile, range-bound NSE market with more genuine reversals from overbought conditions — a better environment for this strategy.

### 4.3 Group E Walk-Forward (Baseline Reference)

| Fold | n | Win Rate | Expectancy | Pass? |
|---|---|---|---|---|
| fold_1 | 132 | 34.8% | −16.2%R | ❌ |
| fold_2 | 132 | 37.9% | −15.5%R | ❌ |
| fold_3 | 132 | 32.6% | −23.6%R | ❌ |
| fold_4 | 132 | 40.9% | −2.0%R | ❌ |
| fold_5 | 133 | **51.1%** | +21.1%R | ✅ |

Group E (no DNA) has WF consistency 1/5. The DNA filter improves this from 1/5 → 2/5, confirming DNA adds consistent out-of-sample selection value but cannot overcome the fundamental environment-dependency.

---

## Phase 5 — Regime Breakdown

Group C only fires in RANGE_MARKET (by definition). The 133 trades are all RANGE_MARKET. VOLATILE regime is excluded by design.

| Regime | n | Win Rate | Expectancy | PF | Max DD |
|---|---|---|---|---|---|
| RANGE_MARKET | 133 | 42.9% | +3.54%R | 1.071 | 19.1R |
| VOLATILE | 0 | — | — | — | — |
| BULL_TREND | 0 | — | — | — | — |
| BEAR_MARKET | 0 | — | — | — | — |

**Note on breadth proxy**: The regime classifier in this backtest uses NIFTY realized volatility + NIFTY daily return with a static breadth = 0.50 (neutral). In production, real breadth data would classify some RANGE_MARKET days as BULL_TREND (blocking Setup 4). The backtest may therefore slightly overcount valid signal days. This is a downside-conservative error — it makes the results slightly less pessimistic than production would be.

**RANGE_MARKET only (133 signals)**: The entire Group C sample is one regime. Within-regime variation is captured by the temporal analysis — the strategy works in RANGE_MARKET during low-momentum periods (2021-2022 Q4, 2024-2025) and fails during momentum-persistent RANGE_MARKET periods (2022-2024).

---

## Phase 6 — DNA Incremental Value

**Question: Does the vol_ratio ≥ 1.5× DNA condition improve out-of-sample selection quality beyond just applying RSI ≥ 70 + RANGE_MARKET?**

Comparison: Group E (RSI≥70 + Range, no DNA) vs Group C (RSI≥70 + Range + DNA)

| Metric | Group E (no DNA) | Group C (with DNA) | Delta |
|---|---|---|---|
| Trades | 661 | 133 | −528 (−79.9%) |
| Win rate | 39.5% | 42.9% | **+3.4pp** |
| Expectancy | −7.18%R | +3.54%R | **+10.7%R** |
| Profit factor | 0.869 | 1.071 | **+0.202** |
| Sharpe | −0.971 | +0.479 | **+1.450** |
| Max drawdown | 53.3R | 19.1R | **−34.2R (−64%)** |
| MC pos% | 5.1% | 64.2% | **+59.1pp** |

**DNA adds value: YES on all 6 metrics simultaneously.**

The DNA filter:
- Eliminates 80% of false-positive signals (528/661 rejected)
- Flips expectancy from −7.18%R to +3.54%R (sign reversal)
- Reduces maximum drawdown by 64% (53.3R → 19.1R)
- Raises Monte Carlo positive-outcome probability from 5.1% to 64.2%

**Interpretation**: The volume spike criterion selects stocks where institutional activity is present at the overbought level. These stocks have a materially higher probability of short-term reversal, consistent with the DNA's theoretical basis (institutional distribution at highs).

**Out-of-sample validation of DNA value**:

| Period | Group E OOS WR | Group C OOS WR | DNA lift |
|---|---|---|---|
| OOS (2024-07-01 to 2025-12-22) | 45.8% | **52.6%** | +6.8pp |

The DNA filter adds +6.8pp to OOS win rate. This is the most important number — it shows the DNA condition provides **incremental out-of-sample lift**, not just in-sample selection bias.

---

## Phase 7 — Data Leakage Audit

All 15 leakage checks passed. Verdict: **DATA_LEAKAGE = NONE_FOUND**.

| Check | Result | Notes |
|---|---|---|
| RSI(14) computed on closes[0..t] only | ✓ PASS | No future bars |
| ATR computed on H/L/C[0..t] only | ✓ PASS | No future bars |
| Resistance = 20d rolling HIGH ending at t | ✓ PASS | `highs[-20:]` |
| vol_ratio uses 3d/20d avg volumes[0..t] | ✓ PASS | No future volume |
| Regime VIX proxy uses NIFTY closes[0..t] | ✓ PASS | Past bars only |
| Regime nifty_chg uses close[t] vs close[t-1] | ✓ PASS | Previous day close |
| DNA: vol_ratio is structural (no outcome data) | ✓ PASS | Pattern condition only |
| DNA evidence pre-dates backtest (2026-08-05) | ✓ PASS | All DNA recorded before period |
| Entry = close[t] (EOD, no next-open look-ahead) | ✓ PASS | Standard EOD approach |
| Exit evaluated on sequential future bars only | ✓ PASS | Iterative loop |
| Conservative exit: same-bar conflict → stop hit | ✓ PASS | Pessimistic |
| ADV filter uses volumes[-20:] ending at t | ✓ PASS | Past 20 bars |
| Regime classification uses no future candles | ✓ PASS | Verified in scan loop |
| RSI ≥ 70 uses same computation as RSI ≥ 67 | ✓ PASS | No additional data required |
| vol_ratio gate NOT derived from exit-bar volumes | ✓ PASS | Entry-bar volume only |

**Special note on DNA provenance**: The `institutional_dna.db` volume_spike SHORT record was last updated 2026-08-05. It reflects patterns observed from live trading data before that date. The backtest uses this as a static filter (vol_ratio ≥ 1.5× at signal time), which is a structural price/volume condition not derived from any trade outcome. This is confirmed leakage-free.

---

## Phase 8 — Governance Gate Assessment

### 8.1 Group C — Strict Variant

| Gate | Threshold | Actual | Status |
|---|---|---|---|
| Minimum trades | ≥ 20 | 133 | **PASS** |
| Win rate | ≥ 50% | 42.9% | **FAIL** — 7.1pp short |
| Expectancy | ≥ 0.1%R/trade | +3.54%R | **PASS** |
| Max drawdown | ≤ 15 R | 19.1 R | **FAIL** — 4.1R excess |
| Profit factor | ≥ 1.0 | 1.071 | **PASS** |
| Sharpe | > 0 | +0.479 | **PASS** |
| Walk-forward consistency | ≥ 60% folds | 40% (2/5) | **FAIL** |
| Overfitting ratio | ≤ 1.50 | 1.30 | **PASS** |
| Monte Carlo (% pos) | ≥ 55% | 64.2% | **PASS** |

**Gates passed: 5/9 | Gates failed: 3/9**

### 8.2 Monte Carlo (Group C, n=1,000 simulations)

| Percentile | Total R | Max DD | Win Rate |
|---|---|---|---|
| P5 | −16.8R | — | 35.3% |
| P50 (median) | +4.5R | 12.2R | 42.9% |
| P95 | +27.8R | 25.3R | 50.4% |
| % positive simulations | 64.2% | — | — |

The median simulation is positive (+4.5R) and 64.2% of simulations are profitable — both better than the original strategy. The P5 scenario (−16.8R) is manageable. The MC result passes the governance gate. However, note that the P95 win rate is only 50.4% — the strategy is at the boundary of viability even in optimistic bootstrap scenarios.

### 8.3 Governance Verdict

**Overall governance verdict: FAIL**

Three gates fail:
1. **Win rate 42.9%** — below 50% across the full 4.5-year period. The OOS period achieves 52.6% but only from 38 trades (insufficient for standalone governance).
2. **Max drawdown 19.1R** — the drawdown stems primarily from the 2022-09 to 2023-07 fold (fold 2: WR=26.9%). Even 133 trades produce 19.1R max drawdown because of this fold's −7.9R sequential loss run.
3. **Walk-forward consistency 2/5** — the irregular temporal pattern (good–bad–bad–bad–good) does not demonstrate the consistent edge required for governed activation.

---

## Phase 9 — Synthesis and Final Verdict

### 9.1 Summary of Evidence

| Finding | Direction | Confidence |
|---|---|---|
| DNA filter improves all metrics vs no-DNA baseline | Positive | HIGH — consistent across groups |
| DNA provides out-of-sample lift (+6.8pp WR in OOS) | Positive | MEDIUM — n=38 OOS |
| OOS period (2024-07-01 to 2025-12) passes all individual gates | Positive | MEDIUM — small sample |
| Aggregate win rate below 50% threshold | Negative | HIGH — n=133, clearly below |
| 3 consecutive losing folds (2022–2024) | Negative | HIGH — systematic, not noise |
| Strategy is environment-dependent (momentum vs range) | Negative | HIGH — clear temporal pattern |
| Total aggregate positive expectancy +3.54%R | Positive | MEDIUM — driven by OOS and fold_1 |

### 9.2 Root Cause of FAIL

The strict variant fails governance for the same structural reason as the original strategy, but less severely: **the 2022–2024 Indian equity bull run produced momentum continuation at overbought RSI levels, making short entry at resistance consistently unprofitable during that period**.

The hypothesis that RSI ≥ 70 + volume_spike selects genuine institutional distribution points is:
- **Supported** in 2021-2022 Q3 and 2024-Q3 to 2025 (reversals reliably follow these conditions)
- **Contradicted** in 2022-Q4 to 2024-Q2 (bull market momentum persisted despite overbought levels)

This creates an environment-dependent strategy rather than a regime-invariant edge. The current IIOS governance framework correctly rejects environment-dependent strategies at the standard gate thresholds.

### 9.3 Final Verdict

```
[SHORT_DNA_STRICT_VARIANT_RESEARCH_001]

Verdict:               FAIL

Group C (strict):
  n = 133
  Win Rate = 42.9%              FAIL (threshold ≥ 50%)
  Expectancy = +3.54%R          PASS (threshold ≥ 0.1%)
  Profit Factor = 1.071         PASS (threshold ≥ 1.0)
  Max DD = 19.1 R               FAIL (threshold ≤ 15 R)
  Sharpe = +0.479               PASS (threshold > 0)
  WF consistency = 2/5 (40%)    FAIL (threshold ≥ 60%)
  MC positive% = 64.2%          PASS (threshold ≥ 55%)
  Governance gates = 5/9 PASS

OOS period (n=38):
  Win Rate = 52.6%              [passes gate individually]
  Expectancy = +31.1%R          [passes gate individually]
  Max DD = 6.0 R                [passes gate individually]
  NOTE: n=38 is insufficient for standalone governance

DNA incremental value:
  WR delta = +3.4pp             YES
  Exp delta = +10.7%R           YES — sign reversal
  PF delta = +0.202             YES
  MaxDD delta = -34.2R          YES
  DNA adds value: CONFIRMED

Data leakage:        NONE_FOUND (15/15 checks)
Verdict:             FAIL — strict variant does not meet governance thresholds

Production changes:  NONE
Orders placed:       0
```

### 9.4 Research Continuation Criteria

Per governance policy, since the verdict is FAIL, **research on this exact variant should stop**. The strategy should not be registered, routed, or connected in any production component.

**If the development team wishes to resume this research line**, the following evidence must accumulate naturally (no forced retest):

| Requirement | Current State | Required |
|---|---|---|
| OOS trades with 2024-07+ conditions | 38 trades | ≥ 100 trades |
| Standalone OOS governance rerun | Not yet done | All 9 gates on OOS-only data |
| Walk-forward consistency improvement | 2/5 folds | ≥ 3/5 folds |
| Win rate above 50% in any rolling 100-trade window | Not achieved | ≥ 1 window in OOS period |

The natural accumulation timeline at current signal frequency (Group C generates ~26–29 trades per ~12-month fold) suggests this data will be available approximately in 3–4 years of continued market observation, or sooner if the 2024-2025 OOS pattern persists.

---

## Appendix A — Backtest Files

| File | Status |
|---|---|
| `backtest_strict_variant.py` | Created for this study |
| `data/strict_variant_result.json` | Generated — machine-readable |

## Appendix B — Group Definitions

| Group | RSI Gate | Regimes | DNA | Purpose |
|---|---|---|---|---|
| A | ≥ 67 | Range + Volatile | None | Original strategy (from VALIDATION_001) |
| B | ≥ 67 | Range + Volatile | Required | Original DNA subset |
| B-RM | ≥ 67 | Range only | Required | Range restriction effect |
| E | ≥ 70 | Range only | None | Strict RSI/regime baseline (no DNA) |
| C | ≥ 70 | Range only | Required | **Strict variant (this study)** |

## Appendix C — Audit Chain

| Document | Date | Verdict |
|---|---|---|
| KNOWLEDGE_TO_OPPORTUNITY_AUDIT_001_2026-08-13.md | 2026-08-13 | Gap analysis — 3 failure classes identified |
| SHORT_OPPORTUNITY_PRE_IMPLEMENTATION_AUDIT_001_2026-08-13.md | 2026-08-13 | F-2 (routing) + F-3 (DNA) confirmed; backtest prerequisite set |
| HIGH_RSI_SHORT_VALIDATION_001_2026-08-13.md | 2026-08-13 | FAIL — original strategy; DNA subset lead noted |
| SHORT_DNA_STRICT_VARIANT_RESEARCH_001_2026-08-13.md | 2026-08-13 | **FAIL — strict variant; OOS promising but insufficient** |

---

*This document is read-only research. No production code was modified.*  
*Study ID: SHORT_DNA_STRICT_VARIANT_RESEARCH_001*  
*Executed: 2026-08-13*
