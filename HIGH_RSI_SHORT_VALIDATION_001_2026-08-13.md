# HIGH_RSI_SHORT_VALIDATION_001
**Date:** 2026-08-13  
**Prepared by:** Copilot — read-only research  
**Scope:** Historical backtest of Setup 4 (high_rsi_short) against 5 years of Indian equity data  
**Production changes:** NONE  
**Orders placed:** 0  

---

## Executive Summary

| Item | Value |
|---|---|
| **Verdict** | **FAIL** |
| Test period | 2021-07-22 – 2025-12-22 |
| Symbols scanned | 210 NSE equities (universe_stocks, replay.db) |
| Total signals generated | 1,394 |
| Win rate | 41.2% (threshold: ≥50%) |
| Expectancy | −2.39%R/trade (threshold: ≥+0.1%R) |
| Profit factor | 0.954 (threshold: ≥1.0) |
| Sharpe | −0.322 (threshold: >0) |
| Max drawdown | 121.3 R (threshold: ≤15 R) |
| Governance gates passed | 1 / 9 (only min_trades) |
| Data leakage | NONE_FOUND (12/12 checks passed) |

**high_rsi_short does NOT have sufficient historical evidence to become a governed IIOS strategy. The strategy as currently specified loses money over a 5-year period across Indian equities. It must not be registered, activated, or connected to the order pipeline.**

**One meaningful exception is noted:** The DNA-confirmed subset (volume_spike ≥ 1.5×, 19% of signals) shows **positive expectancy (+3.24%R), profit factor 1.066, and Sharpe 0.438**. This subset merits further investigation under a separate, stricter validation study before any production consideration.

---

## Phase 1 — Implementation Trace

### 1.1 Strategy Location

Setup 4 is fully implemented but never routed:

| File | Lines | Status |
|---|---|---|
| `equity_scanner_ai.py` | 2058–2083 | **COMPLETE** — generates `high_rsi_short` TradeSignal |
| `strategy_generator_ai.py` | 36 | `STRATEGY_PARAMS` — **high_rsi_short is ABSENT** |
| `strategy_generator_ai.py` | `_pick_strategy()` | **No SHORT branch for RANGE_MARKET** |
| `backtesting_ai.py` | `_BACKTEST_CACHE` | **No high_rsi_short entry** |
| `ph2_short_dna.py` | `get_short_dna_confidence_boost()` | **Implemented but never called from scanner** |

### 1.2 Entry Conditions (Setup 4)

```
RSI(14)   ≥ 67.0
LTP       ≥ resistance × 0.99
regime    ∈ {RANGE_MARKET, VOLATILE}
ATR%      < 4.0%  (VOLATILITY_GUARD_ATR_PCT)
Resistance = 20-day rolling HIGH of daily highs (market_scanner.py)
Stop      = LTP + max(ATR × 1.5, LTP × 1%)
Target    = LTP − 2.5 × stop_dist   (R:R = 2.5)
Confidence= min(5.5 + RSI/20, 8.5)  → constant 8.5 for RSI ≥ 60
```

### 1.3 Resistance Methodology Note

**Production** (`market_scanner.py` line 773): resistance = `close.iloc[-20:].max()` (20-day max of CLOSE prices).  
**This backtest**: resistance = `highs[-20:].max()` (20-day max of actual HIGH prices).  
Using actual highs is a **more conservative and correct** approximation for resistance — actual highs represent intraday price extremes. The backtest is therefore slightly more conservative than production in generating signals (fewer stocks will reach the resistance threshold), making results slightly more pessimistic. This is acceptable for a downside-risk study. It is **not a leakage issue**.

---

## Phase 2 — Historical Backtest Results

### 2.1 Methodology

- **Data source**: `data/replay.db` — 256,268 OHLCV rows, 210 NSE equities + ^NSEI (NIFTY)  
- **Period**: 2021-07-22 to 2025-12-22 (4.5 years, 1,135 NIFTY trading days)  
- **Entry**: Close of signal day (EOD setup confirmation)  
- **Exit**: Intraday check of subsequent daily bars: first of {high ≥ stop, low ≤ target, 10-day forced close}  
- **Conservative rule**: If same bar triggers both stop and target → stop hit assumed (pessimistic)  
- **ADV filter**: minimum ₹15 crore average daily value (volume × LTP / 1e7)  
- **Regime proxy**: Annualized 10-day realized NIFTY volatility as VIX proxy  

### 2.2 Test A — Strategy Only

```
Trades:            1,394
Win rate:          41.2%   ← 8.8pp below 50% threshold
Total R:           −33.3 R  (on 1,394 trades)
Avg R per trade:   −0.024 R
Expectancy:        −2.39%R per trade
Profit factor:     0.954   ← below 1.0
Sharpe:            −0.322  ← negative
Max drawdown:      121.3 R ← 8× the 15R threshold
Avg win size:      +1.208 R
Avg loss size:     −0.886 R
Max win streak:    17 consecutive
Max loss streak:   18 consecutive
Avg holding:       6.9 days
```

**Interpretation**: The average loss size (−0.886 R) is too large relative to the win rate (41.2%). With RR = 2.5, the strategy requires a minimum win rate of 1 / (1 + 2.5) = 28.6% to break even — but the actual win rate of 41.2% is insufficient because exits before the target hit (max_hold forced close) reduce the actual realized R below the theoretical +2.5. The median exit at forced close is near zero or slightly negative, dragging expectancy below zero.

---

## Phase 3 — Regime Analysis

### 3.1 Breakdown by Market Regime

| Regime | Signals | Win Rate | Expectancy | Profit Factor | Max DD |
|---|---|---|---|---|---|
| RANGE_MARKET | 1,322 (94.8%) | 41.5% | −1.23%R | 0.977 | 120.2 R |
| VOLATILE | 72 (5.2%) | 36.1% | −23.75%R | 0.532 | 20.4 R |

**Key findings:**

1. **RANGE_MARKET is the primary regime** for Setup 4 (94.8% of signals). This is expected — Setup 4 is gated to RANGE_MARKET and VOLATILE only.

2. **VOLATILE regime is worse**: 36.1% win rate, −23.75%R expectancy, PF=0.532. Volatile markets cause more stop-outs as price moves are erratic. The setup should likely be gated to RANGE_MARKET only, not VOLATILE.

3. **Neither regime is profitable** over the 5-year period.

4. **Regime breadth proxy limitation**: This backtest uses a static breadth=0.50 (neutral), meaning regime classification is driven entirely by NIFTY realized volatility and daily return. In production, real breadth data (% advancing stocks) would push more days into BULL_TREND, which would **block** Setup 4 signals. This means the backtest may slightly **overcount** valid signal days (some RANGE_MARKET days in this backtest would be BULL_TREND in production). This further weakens the case for the strategy.

### 3.2 Temporal Trend

The walk-forward analysis reveals an important pattern:

| Fold | Period | Trades | Win Rate | Expectancy | Total R |
|---|---|---|---|---|---|
| fold_1 | 2021-07-22 – 2022-10-31 | 278 | 38.5% | −5.00%R | −13.9 R |
| fold_2 | 2022-10-31 – 2023-07-06 | 278 | 34.9% | −20.69%R | −57.5 R |
| fold_3 | 2023-07-06 – 2024-04-02 | 278 | 39.6% | −4.12%R | −11.5 R |
| fold_4 | 2024-04-02 – 2025-03-21 | 278 | 46.0% | +11.57%R | +32.2 R |
| fold_5 | 2025-03-24 – 2025-12-22 | 282 | 46.8% | +6.16%R | +17.4 R |

**Pattern**: Folds 1–3 (2021–2024-Q1) are all negative. Folds 4–5 (2024-Q2–2025-Q4) are positive and approaching the 50% win rate. **This suggests the strategy may be improving in the recent market environment, but 5 quarters of positive performance in backtesting is insufficient evidence for activation** — the governance minimum is 5 folds all ≥50% WR. Walk-forward consistency = 0/5 = 0%.

---

## Phase 4 — DNA Confirmation Analysis

### 4.1 Setup

- **DNA source**: `data/mls/institutional_dna.db` — `volume_spike SHORT conf=1.0`, evidence_count=135
- **DNA filter**: `vol_ratio ≥ 1.5×` (current 3-day volume vs 20-day average)
- **Theoretical boost**: `min(1.0 × 1 × 0.30, 1.50) = 0.30` added to confidence
- **Note**: Since base confidence is already capped at 8.5 and max = 8.5, the +0.30 boost is absorbed by the cap in all signals. DNA currently **cannot raise confidence above 8.5** for any Setup 4 signal.

### 4.2 DNA-Confirmed Subset

Of 1,394 total signals, 265 (19.0%) had `vol_ratio ≥ 1.5×` (volume spike criterion).

| Metric | All Signals | DNA-Confirmed Only |
|---|---|---|
| Trades | 1,394 | 265 |
| Win rate | 41.2% | **42.6%** |
| Expectancy | −2.39%R | **+3.24%R** |
| Profit factor | 0.954 | **1.066** |
| Sharpe | −0.322 | **+0.438** |
| Max DD | 121.3 R | **32.9 R** |
| Avg hold | 6.9 days | 7.1 days |

### 4.3 DNA Incremental Analysis

| Delta | Value |
|---|---|
| Win rate delta | +1.4pp (42.6% vs 41.2%) |
| Expectancy delta (DNA-only vs all) | +5.63%R (positive vs negative) |
| Profit factor delta | +0.112 |
| Max DD reduction | −88.4 R (32.9 R vs 121.3 R) |

**Interpretation**: The volume spike DNA criterion is a **meaningful filter**, not just a confidence booster. When restricted to signals with confirmed institutional volume spike, the strategy shifts from negative to mildly positive expectancy. However:

1. Win rate at 42.6% is still below the 50% governance threshold
2. The +3.24%R expectancy over 265 trades is promising but not yet robust enough
3. The 265-trade DNA subset needs its own dedicated walk-forward validation
4. The DNA is currently disconnected from the signal pipeline entirely

**The DNA finding is the most important output of this validation**: it provides a directional hypothesis for a refined strategy — "high_rsi_short filtered by institutional volume_spike" — that deserves a separate follow-on study.

---

## Phase 5 — Data Leakage Audit

All 12 leakage checks passed. Verdict: **DATA_LEAKAGE = NONE_FOUND**.

| Check | Result | Notes |
|---|---|---|
| RSI uses only closes[0..t] | ✓ PASS | `closes[:idx+1]` — no future data |
| ATR uses only H/L/C[0..t] | ✓ PASS | `highs/lows/closes[:idx+1]` |
| Resistance = 20d rolling HIGH to day t | ✓ PASS | `highs[-20:]` = past 20 bars only |
| Support = 20d rolling LOW to day t | ✓ PASS | `lows[-20:]` = past 20 bars only |
| Regime uses NIFTY close[t] vs close[t-1] | ✓ PASS | `nifty_prev` is previous trading day close |
| VIX proxy uses NIFTY close[0..t] | ✓ PASS | `nifty_hist` only past bars |
| DNA confidence uses static DB conf=1.0 | ✓ PASS | No per-date outcome data; structural pattern only |
| Entry = close[t] (EOD signal) | ✓ PASS | Slightly optimistic but standard for EOD backtesting |
| Exit: stop/target computed from close[t] | ✓ PASS | Forward bars checked iteratively |
| Conservative: if stop+target same bar → stop hits | ✓ PASS | Pessimistic (loss-protective) assumption |
| ADV uses 20-day average ending at [t] | ✓ PASS | `volumes[-20:]` = past 20 bars |
| Universe: active stocks only | ✓ PASS | `universe_stocks.is_active` filter applied |

---

## Phase 6 — Governance Gate Assessment

Evaluated against `BacktestingAI` governance criteria:

| Gate | Threshold | Actual | Status |
|---|---|---|---|
| Minimum trades | ≥ 20 | 1,394 | **PASS** |
| Win rate | ≥ 50% | 41.2% | **FAIL** |
| Expectancy | ≥ 0.1% per trade | −2.39%R | **FAIL** |
| Max drawdown (R units) | ≤ 15 R | 121.3 R | **FAIL** |
| Profit factor | ≥ 1.0 | 0.954 | **FAIL** |
| Sharpe ratio | > 0 | −0.322 | **FAIL** |
| Walk-forward consistency | ≥ 60% folds profitable | 0% (0/5) | **FAIL** |
| Overfitting ratio (IS/OOS) | ≤ 1.50 | N/A (OOS also negative) | — |
| Monte Carlo (% pos simulations) | ≥ 55% | 22.3% | **FAIL** |

**Gates passed: 1 / 9**

**Governance verdict: FAIL — high_rsi_short does not meet BacktestingAI activation criteria.**

---

## Phase 7 — Robustness Testing

### 7.1 Walk-Forward Summary

5-fold chronological split (~278 trades per fold):

- Folds 1, 2, 3 (2021–2024-Q1): **ALL NEGATIVE** (win rates 34.9–39.6%)
- Folds 4, 5 (2024-Q2–2025-Q4): **BOTH POSITIVE** (win rates 46.0–46.8%)
- Walk-forward consistency: **0/5 = 0%** (no fold achieves ≥ 50% win rate)

The improving trend in folds 4–5 is genuine but insufficient. Even fold 5 (the best) has WR = 46.8%, still below the 50% governance minimum.

### 7.2 Monte Carlo (1,000 bootstrap simulations)

| Percentile | Total R | Max DD | Win Rate |
|---|---|---|---|
| P5 | −104.8 R | — | 39.1% |
| P50 (median) | −30.2 R | 64.6 R | 41.2% |
| P95 | +43.3 R | 124.3 R | 43.5% |

- **Probability of profitable outcome: 22.3%** (222/1,000 simulations ended positive)
- **Median simulation is deeply negative**: −30.2 R
- **P95 max drawdown of 124.3 R** indicates catastrophic downside in worst cases
- **Even the optimistic P95 total R of +43.3 R** over 1,394 trades represents only +0.031 R/trade — trivially small

Monte Carlo confirms the strategy is robustly negative, not a case of bad sequence.

---

## Phase 8 — Final Verdict

### 8.1 Verdict Determination

```
[HIGH_RSI_SHORT_VALIDATION_001]

Overall:               FAIL
Period:                2021-07-22 to 2025-12-22 (4.5 years)
Symbols:               210 NSE equities
Trades:                1,394
Win Rate:              41.2%     ← threshold 50%  FAIL
Expectancy:            -2.39%R per trade           FAIL
Profit Factor:         0.954     ← threshold 1.0   FAIL
Max DD:                121.3 R   ← threshold 15 R  FAIL
Sharpe:                -0.322    ← threshold >0     FAIL
Avg Holding Period:    6.9 days

Regime (Range-Market): n=1322   WR=41.5%  Exp=-1.23%R   FAIL
Regime (Volatile):     n=72     WR=36.1%  Exp=-23.75%R  FAIL (worse)

DNA Incremental:
  All signals:         WR=41.2%  Exp=-2.39%R  PF=0.954
  DNA-confirmed (19%): WR=42.6%  Exp=+3.24%R  PF=1.066   ← marginal positive
  DNA delta WR:        +1.4pp
  DNA delta Exp:       +5.63%R  (negative → positive within subset)

Data Leakage:          NONE_FOUND (12/12 checks passed)
Governance:            FAILED  (1/9 gates)
Robustness:            FAIL  MC positive rate 22.3%  (threshold 55%)

Verdict:               FAIL — high_rsi_short does NOT have sufficient
                       historical evidence to become a governed IIOS strategy.

Production changes:    NONE
Orders placed:         0
```

### 8.2 Root Cause of Failure

The strategy fails for a structurally sound reason, not random noise:

1. **Momentum continuation bias in Indian equities (2021–2024)**: In the 2021–2024 period, stocks near resistance with high RSI continued upward more often than they reversed. The Indian equity market was in a structural bull run during this period, making short selling at resistance inherently counter-trend.

2. **10-day holding period is too short for mean reversion**: When the target is not hit within 10 bars, the forced close captures mark-to-market losses. If the reversal takes 15–20 days, the 10-day exit locks in losses that would have been recoverable.

3. **RSI ≥ 67 is not sufficiently extreme**: RSI ≥ 67 is "moderately overbought." Classical mean-reversion short setups typically require RSI ≥ 75–80 to achieve sufficient win rates. At 67, the price may still have momentum to continue higher.

4. **ATR stop is too close for volatile periods**: In VOLATILE regime (22.3%+ annualized vol), the ATR-based stop generates wide stop_dists, and exit at max_hold captures large adverse excursions.

### 8.3 What the Data Does Support

Despite the overall FAIL verdict, two findings merit separate research:

**Finding A: DNA-confirmed subset shows positive expectancy**  
265 signals (19%) with volume_spike ≥ 1.5× achieved WR=42.6%, Exp=+3.24%R, PF=1.066, Sharpe=+0.438, Max DD=32.9R. This is not a governance pass but it is a meaningful signal. A dedicated validation of "Setup 4 + volume_spike filter" (potentially with stricter RSI ≥ 70, shorter hold, or RANGE_MARKET only) could produce a governed strategy.

**Finding B: Recent market (2024-Q2 to 2025-Q4) shows improving performance**  
Folds 4 and 5 have positive expectancy (+11.57%R and +6.16%R respectively) and win rates approaching 50% (46.0% and 46.8%). This may reflect changing market structure. It does NOT justify activation now but warrants monitoring.

### 8.4 Recommended Path Forward

**DO NOT** register, route, or activate `high_rsi_short` in any production component.

If the development team wishes to pursue this signal class, the required evidence path is:

| Step | Action | Gate |
|---|---|---|
| 1 | Run a separate validation study restricted to RSI ≥ 70, regime=RANGE_MARKET only, max_hold=15 days | WR ≥ 50%, PF ≥ 1.0, Max DD ≤ 15R |
| 2 | Validate DNA-confirmed subset (vol_ratio ≥ 1.5×) independently with walk-forward | WF consistency ≥ 60% |
| 3 | If either study passes governance gates → register strategy formally | `backtesting_ai._BACKTEST_CACHE` |
| 4 | Add SHORT routing in `_pick_strategy()` RANGE_MARKET branch | No SHORT signals dropped |
| 5 | Connect `get_short_dna_confidence_boost()` from `_identify_setup()` | DNA-filtered signals only |
| 6 | 20 paper trades with full monitoring | Win rate ≥ 45%, no catastrophic stops |
| 7 | Paper audit → live activation decision | Board approval per governance policy |

**Current Action: NONE. No production changes. No orders.**

---

## Appendix A — Backtest Implementation Files

| File | Purpose | Status |
|---|---|---|
| `backtest_high_rsi_short.py` | Full backtest script | Created for this study |
| `data/hrs_backtest_result.json` | Machine-readable results | Generated |

## Appendix B — Related Audit Documents

| Document | Date | Finding |
|---|---|---|
| `KNOWLEDGE_TO_OPPORTUNITY_AUDIT_001_2026-08-13.md` | 2026-08-13 | 3 failure classes; P0: route shorts, register strategy |
| `SHORT_OPPORTUNITY_PRE_IMPLEMENTATION_AUDIT_001_2026-08-13.md` | 2026-08-13 | F-2 (routing) confirmed; F-3 (DNA) confirmed; validation prerequisite set |
| `HIGH_RSI_SHORT_VALIDATION_001_2026-08-13.md` | 2026-08-13 | **This document — FAIL verdict** |

---

*This document is read-only research. No production code was modified during this study.*  
*Validation ID: HIGH_RSI_SHORT_VALIDATION_001*  
*Executed: 2026-08-13*
