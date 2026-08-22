# OPTIONS_RISK_AUDIT_001 — Risk-First Strategy Evaluation

**Generated:** 2026-06-19 10:01 UTC  
**Data period:** 2024-06-19 → 2026-05-20  
**Total records:** 8,532 (NIFTY + BANKNIFTY)  

> **Win rate alone is not a trading edge.**  
> This report leads with Profit Factor, Expected Value, and Drawdown.  
> A strategy with 84% WR and PF < 1.0 is a losing strategy.  

> **Note on DrawdownScale:** MaxDD and Worst Month are computed on the
> *aggregate equity curve* (all instruments × all trading days). For a
> realistic single-expiry weekly trade, divide these figures by the number
> of average weekly trades in the sample. **EV/trade and Sharpe are the
> primary per-trade-normalised metrics** — use those for position sizing.

---
## Executive Verdicts

> The only question that matters before execution: is the strategy worth trading?

| Strategy | Verdict | WR% | PF | EV/Trade | Sharpe | Sortino | Max DD | Worst Month | Kelly% |
|----------|---------|-----|----|----------|--------|---------|--------|-------------|--------|
| `BULL_PUT_SPREAD` | ⚠️ **WATCH** | 80.7% | **2.09** ✅ | +0.421R | 2.56 | 3.45 | -62.000R | -31.000R | 25.0% |
| `BEAR_CALL_SPREAD` | ⚠️ **WATCH** | 80.3% | **2.04** ✅ | +0.408R | 2.46 | 3.31 | -45.000R | -19.000R | 25.0% |
| `IRON_CONDOR` | ⚠️ **WATCH** | 75.3% | **1.22** ⚠️ | +0.136R | 0.65 | 0.79 | -116.500R | -35.500R | 13.6% |
| `SHORT_STRANGLE` | ⚠️ **WATCH** | 84.3% | **1.79** ✅ | +0.371R | 1.84 | 2.25 | -71.000R | -26.000R | 25.0% |
| `LONG_STRANGLE` | 🔴 **AVOID** | 15.7% | **0.56** 🔴 | -0.371R | -1.84 | -2.92 | -389.000R | -46.000R | 0.0% |
| `COVERED_CALL` | ⚠️ **WATCH** | 72.4% | **1.40** ✅ | +0.164R | 1.15 | 1.50 | -40.100R | -17.700R | 20.5% |
| `PROTECTIVE_PUT` | 🔴 **AVOID** | 13.4% | **0.77** 🔴 | -0.098R | -0.69 | -1.52 | -172.500R | -23.000R | 0.0% |
| `LONG_CALL` | 🔴 **AVOID** | 19.7% | **0.74** 🔴 | -0.211R | -0.95 | -1.70 | -237.000R | -46.000R | 0.0% |
| `LONG_PUT` | 🔴 **AVOID** | 19.3% | **0.72** 🔴 | -0.228R | -1.04 | -1.83 | -307.000R | -44.000R | 0.0% |

---
## The Regime Context

The data covers a period that was **predominantly RANGING (>90% of sessions).**

This single fact explains all findings below:

- **Premium sellers** (SHORT_STRANGLE, IRON_CONDOR, spreads) look excellent — they are *regime-matched*.
- **Premium buyers** (LONG_CALL, LONG_PUT, LONG_STRANGLE) look poor — they are *regime-mismatched*, not structurally broken.

> **Governance rule:** Re-evaluate debit strategies when India VIX > 20 or regime shifts to HIGH_VOL / TRENDING.

---
## Per-Strategy Risk Profile

### `BULL_PUT_SPREAD` — ⚠️ WATCH

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Profit Factor | **2.09** ✅ | Solid edge |
| Expected Value | +0.421R | Per trade in R |
| Win Rate | 80.7% | High WR ≠ profitable by itself |
| Avg Win | +1.000R | |
| Avg Loss | −+2.000R | |
| Win/Loss Ratio | 0.50× | > 1.0 = winners larger than losers |
| Kelly % | 25.0% | Optimal bet size (capped 25%) |
| Sharpe | 2.56 | Annualised (> 0.5 = acceptable) |
| Sortino | 3.45 | Downside-only risk |
| Large Losses (>2R) | 0.0% | Tail event frequency |
| Max Consec. Losses | 22 | Worst streak |
| Max Drawdown | -62.000R (-14.4%) | Recovery: 75 trades |
| Worst Week | -20.000R | |
| Worst Month | -31.000R | Best: +44.000R |
| Calmar Ratio | 0.35 | Ann. return / max DD |
| Ulcer Index | 16.075 | Lower = smoother equity curve |
| Worst Single Trade | -2.000R | |

**Verdict reasoning:** Marginally profitable: PF=2.09, EV=+0.421R — needs more real data or tighter regime filter

**Regime breakdown:**

| Regime | WR% | PF | EV/trade | Sharpe | MaxDD | Worst Month | Verdict |
|--------|-----|----|----------|--------|-------|-------------|---------|
| ALL (n=948) | 80.7% | **2.09** ✅ | +0.421R | 2.56 | -62.000R | -31.000R | ⚠️ WATCH |
| RANGING (n=889) | 80.7% | **2.08** ✅ | +0.420R | 2.55 | -58.000R | -34.000R | ⚠️ WATCH |
| TRENDING (n=31) | 80.6% | **2.08** ✅ | +0.419R | 2.51 | -4.000R | -2.000R | ✅ TRADE |
| HIGH_VOL (n=28) | 82.1% | **2.30** ✅ | +0.464R | 2.86 | -7.000R | +2.000R | ✅ TRADE |

### `BEAR_CALL_SPREAD` — ⚠️ WATCH

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Profit Factor | **2.04** ✅ | Solid edge |
| Expected Value | +0.408R | Per trade in R |
| Win Rate | 80.3% | High WR ≠ profitable by itself |
| Avg Win | +1.000R | |
| Avg Loss | −+2.000R | |
| Win/Loss Ratio | 0.50× | > 1.0 = winners larger than losers |
| Kelly % | 25.0% | Optimal bet size (capped 25%) |
| Sharpe | 2.46 | Annualised (> 0.5 = acceptable) |
| Sortino | 3.31 | Downside-only risk |
| Large Losses (>2R) | 0.0% | Tail event frequency |
| Max Consec. Losses | 16 | Worst streak |
| Max Drawdown | -45.000R (-35.7%) | Recovery: 533 trades |
| Worst Week | -17.000R | |
| Worst Month | -19.000R | Best: +46.000R |
| Calmar Ratio | 0.47 | Ann. return / max DD |
| Ulcer Index | 12.994 | Lower = smoother equity curve |
| Worst Single Trade | -2.000R | |

**Verdict reasoning:** Marginally profitable: PF=2.03, EV=+0.408R — needs more real data or tighter regime filter

**Regime breakdown:**

| Regime | WR% | PF | EV/trade | Sharpe | MaxDD | Worst Month | Verdict |
|--------|-----|----|----------|--------|-------|-------------|---------|
| ALL (n=948) | 80.3% | **2.04** ✅ | +0.408R | 2.46 | -45.000R | -19.000R | ⚠️ WATCH |
| RANGING (n=889) | 80.4% | **2.06** ✅ | +0.413R | 2.50 | -45.000R | -23.000R | ⚠️ WATCH |
| TRENDING (n=31) | 96.8% | **15.00** ✅ | +0.903R | 12.09 | -2.000R | -2.000R | ✅ TRADE |
| HIGH_VOL (n=28) | 57.1% | **0.67** 🔴 | -0.286R | -1.36 | -20.000R | -16.000R | 🔴 AVOID |

### `IRON_CONDOR` — ⚠️ WATCH

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Profit Factor | **1.22** ⚠️ | Must be > 1.0 to be profitable |
| Expected Value | +0.136R | Per trade in R |
| Win Rate | 75.3% | High WR ≠ profitable by itself |
| Avg Win | +1.000R | |
| Avg Loss | −+2.500R | |
| Win/Loss Ratio | 0.40× | > 1.0 = winners larger than losers |
| Kelly % | 13.6% | Optimal bet size (capped 25%) |
| Sharpe | 0.65 | Annualised (> 0.5 = acceptable) |
| Sortino | 0.79 | Downside-only risk |
| Large Losses (>2R) | 24.7% | Tail event frequency |
| Max Consec. Losses | 12 | Worst streak |
| Max Drawdown | -116.500R (-261.8%) | Recovery: 424 trades |
| Worst Week | -25.000R | |
| Worst Month | -35.500R | Best: +46.000R |
| Calmar Ratio | 0.06 | Ann. return / max DD |
| Ulcer Index | 49.457 | Lower = smoother equity curve |
| Worst Single Trade | -2.500R | |

**Verdict reasoning:** Marginally profitable: PF=1.22, EV=+0.136R — needs more real data or tighter regime filter

**Regime breakdown:**

| Regime | WR% | PF | EV/trade | Sharpe | MaxDD | Worst Month | Verdict |
|--------|-----|----|----------|--------|-------|-------------|---------|
| ALL (n=948) | 75.3% | **1.22** ⚠️ | +0.136R | 0.65 | -116.500R | -35.500R | ⚠️ WATCH |
| RANGING (n=889) | 75.8% | **1.25** ⚠️ | +0.153R | 0.74 | -110.500R | -35.500R | ⚠️ WATCH |
| TRENDING (n=31) | 83.9% | **2.08** ✅ | +0.435R | 2.40 | -4.000R | -2.000R | ✅ TRADE |
| HIGH_VOL (n=28) | 50.0% | **0.40** 🔴 | -0.750R | -3.04 | -25.000R | -20.000R | 🔴 AVOID |

### `SHORT_STRANGLE` — ⚠️ WATCH

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Profit Factor | **1.79** ✅ | Solid edge |
| Expected Value | +0.371R | Per trade in R |
| Win Rate | 84.3% | High WR ≠ profitable by itself |
| Avg Win | +1.000R | |
| Avg Loss | −+3.000R | |
| Win/Loss Ratio | 0.33× | > 1.0 = winners larger than losers |
| Kelly % | 25.0% | Optimal bet size (capped 25%) |
| Sharpe | 1.84 | Annualised (> 0.5 = acceptable) |
| Sortino | 2.25 | Downside-only risk |
| Large Losses (>2R) | 15.7% | Tail event frequency |
| Max Consec. Losses | 12 | Worst streak |
| Max Drawdown | -71.000R (-67.0%) | Recovery: 424 trades |
| Worst Week | -26.000R | |
| Worst Month | -26.000R | Best: +46.000R |
| Calmar Ratio | 0.27 | Ann. return / max DD |
| Ulcer Index | 22.510 | Lower = smoother equity curve |
| Worst Single Trade | -3.000R | |

**Verdict reasoning:** Marginally profitable: PF=1.79, EV=+0.371R — needs more real data or tighter regime filter

**Regime breakdown:**

| Regime | WR% | PF | EV/trade | Sharpe | MaxDD | Worst Month | Verdict |
|--------|-----|----|----------|--------|-------|-------------|---------|
| ALL (n=948) | 84.3% | **1.79** ✅ | +0.371R | 1.84 | -71.000R | -26.000R | ⚠️ WATCH |
| RANGING (n=889) | 84.8% | **1.86** ✅ | +0.393R | 1.97 | -69.000R | -26.000R | ⚠️ WATCH |
| TRENDING (n=31) | 93.5% | **4.83** ✅ | +0.742R | 5.36 | -3.000R | 0.000R | ✅ TRADE |
| HIGH_VOL (n=28) | 57.1% | **0.44** 🔴 | -0.714R | -2.56 | -26.000R | -20.000R | 🔴 AVOID |

### `LONG_STRANGLE` — 🔴 AVOID

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Profit Factor | **0.56** 🔴 | Must be > 1.0 to be profitable |
| Expected Value | -0.371R | Per trade in R |
| Win Rate | 15.7% | High WR ≠ profitable by itself |
| Avg Win | +3.000R | |
| Avg Loss | −+1.000R | |
| Win/Loss Ratio | 3.00× | > 1.0 = winners larger than losers |
| Kelly % | 0.0% | Optimal bet size (capped 25%) |
| Sharpe | -1.84 | Annualised (> 0.5 = acceptable) |
| Sortino | -2.92 | Downside-only risk |
| Large Losses (>2R) | 0.0% | Tail event frequency |
| Max Consec. Losses | 126 | Worst streak |
| Max Drawdown | -389.000R (-19450.0%) | Recovery: 113 trades |
| Worst Week | -11.000R | |
| Worst Month | -46.000R | Best: +26.000R |
| Calmar Ratio | -0.05 | Ann. return / max DD |
| Ulcer Index | 202.730 | Lower = smoother equity curve |
| Worst Single Trade | -1.000R | |

**Verdict reasoning:** Negative expectancy: PF=0.56, EV=-0.371R, 126 consecutive losses possible

**Regime breakdown:**

| Regime | WR% | PF | EV/trade | Sharpe | MaxDD | Worst Month | Verdict |
|--------|-----|----|----------|--------|-------|-------------|---------|
| ALL (n=948) | 15.7% | **0.56** 🔴 | -0.371R | -1.84 | -389.000R | -46.000R | 🔴 AVOID |
| RANGING (n=889) | 15.2% | **0.54** 🔴 | -0.393R | -1.97 | -372.000R | -46.000R | 🔴 AVOID |
| TRENDING (n=31) | 6.5% | **0.21** 🔴 | -0.742R | -5.36 | -22.000R | -10.000R | 🔴 AVOID |
| HIGH_VOL (n=28) | 42.9% | **2.25** ✅ | +0.714R | 2.56 | -12.000R | -6.000R | ✅ TRADE |

### `COVERED_CALL` — ⚠️ WATCH

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Profit Factor | **1.40** ✅ | Solid edge |
| Expected Value | +0.164R | Per trade in R |
| Win Rate | 72.4% | High WR ≠ profitable by itself |
| Avg Win | +0.800R | |
| Avg Loss | −+1.500R | |
| Win/Loss Ratio | 0.53× | > 1.0 = winners larger than losers |
| Kelly % | 20.5% | Optimal bet size (capped 25%) |
| Sharpe | 1.15 | Annualised (> 0.5 = acceptable) |
| Sortino | 1.50 | Downside-only risk |
| Large Losses (>2R) | 0.0% | Tail event frequency |
| Max Consec. Losses | 16 | Worst streak |
| Max Drawdown | -40.100R (-44.3%) | Recovery: 282 trades |
| Worst Week | -12.700R | |
| Worst Month | -17.700R | Best: +36.800R |
| Calmar Ratio | 0.21 | Ann. return / max DD |
| Ulcer Index | 14.119 | Lower = smoother equity curve |
| Worst Single Trade | -1.500R | |

**Verdict reasoning:** Marginally profitable: PF=1.40, EV=+0.164R — needs more real data or tighter regime filter

**Regime breakdown:**

| Regime | WR% | PF | EV/trade | Sharpe | MaxDD | Worst Month | Verdict |
|--------|-----|----|----------|--------|-------|-------------|---------|
| ALL (n=948) | 72.4% | **1.40** ✅ | +0.164R | 1.15 | -40.100R | -17.700R | ⚠️ WATCH |
| RANGING (n=889) | 72.0% | **1.37** ✅ | +0.156R | 1.09 | -47.000R | -21.700R | ⚠️ WATCH |
| TRENDING (n=31) | 96.8% | **16.00** ✅ | +0.726R | 12.67 | -1.500R | -1.500R | ✅ TRADE |
| HIGH_VOL (n=28) | 57.1% | **0.71** 🔴 | -0.186R | -1.16 | -15.000R | -12.000R | 🔴 AVOID |

### `PROTECTIVE_PUT` — 🔴 AVOID

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Profit Factor | **0.77** 🔴 | Must be > 1.0 to be profitable |
| Expected Value | -0.098R | Per trade in R |
| Win Rate | 13.4% | High WR ≠ profitable by itself |
| Avg Win | +2.500R | |
| Avg Loss | −+0.500R | |
| Win/Loss Ratio | 5.00× | > 1.0 = winners larger than losers |
| Kelly % | 0.0% | Optimal bet size (capped 25%) |
| Sharpe | -0.69 | Annualised (> 0.5 = acceptable) |
| Sortino | -1.52 | Downside-only risk |
| Large Losses (>2R) | 0.0% | Tail event frequency |
| Max Consec. Losses | 151 | Worst streak |
| Max Drawdown | -172.500R (-784.1%) | Recovery: 113 trades |
| Worst Week | -5.500R | |
| Worst Month | -23.000R | Best: +32.000R |
| Calmar Ratio | -0.03 | Ann. return / max DD |
| Ulcer Index | 83.235 | Lower = smoother equity curve |
| Worst Single Trade | -0.500R | |

**Verdict reasoning:** Negative expectancy: PF=0.77, EV=-0.098R, 151 consecutive losses possible

**Regime breakdown:**

| Regime | WR% | PF | EV/trade | Sharpe | MaxDD | Worst Month | Verdict |
|--------|-----|----|----------|--------|-------|-------------|---------|
| ALL (n=948) | 13.4% | **0.77** 🔴 | -0.098R | -0.69 | -172.500R | -23.000R | 🔴 AVOID |
| RANGING (n=889) | 13.5% | **0.78** 🔴 | -0.095R | -0.67 | -172.500R | -23.000R | 🔴 AVOID |
| TRENDING (n=31) | 16.1% | **0.96** 🔴 | -0.016R | -0.10 | -4.500R | -2.000R | 🔴 AVOID |
| HIGH_VOL (n=28) | 7.1% | **0.39** 🔴 | -0.286R | -2.62 | -9.000R | -4.000R | 🔴 AVOID |

### `LONG_CALL` — 🔴 AVOID

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Profit Factor | **0.74** 🔴 | Must be > 1.0 to be profitable |
| Expected Value | -0.211R | Per trade in R |
| Win Rate | 19.7% | High WR ≠ profitable by itself |
| Avg Win | +3.000R | |
| Avg Loss | −+1.000R | |
| Win/Loss Ratio | 3.00× | > 1.0 = winners larger than losers |
| Kelly % | 0.0% | Optimal bet size (capped 25%) |
| Sharpe | -0.95 | Annualised (> 0.5 = acceptable) |
| Sortino | -1.70 | Downside-only risk |
| Large Losses (>2R) | 0.0% | Tail event frequency |
| Max Consec. Losses | 64 | Worst streak |
| Max Drawdown | -237.000R (-718.2%) | Recovery: 4 trades |
| Worst Week | -10.000R | |
| Worst Month | -46.000R | Best: +38.000R |
| Calmar Ratio | -0.05 | Ann. return / max DD |
| Ulcer Index | 103.034 | Lower = smoother equity curve |
| Worst Single Trade | -1.000R | |

**Verdict reasoning:** Negative expectancy: PF=0.74, EV=-0.211R, 64 consecutive losses possible

**Regime breakdown:**

| Regime | WR% | PF | EV/trade | Sharpe | MaxDD | Worst Month | Verdict |
|--------|-----|----|----------|--------|-------|-------------|---------|
| ALL (n=948) | 19.7% | **0.74** 🔴 | -0.211R | -0.95 | -237.000R | -46.000R | 🔴 AVOID |
| RANGING (n=889) | 19.6% | **0.73** 🔴 | -0.217R | -0.99 | -237.000R | -46.000R | 🔴 AVOID |
| TRENDING (n=31) | 3.2% | **0.10** 🔴 | -0.871R | -8.74 | -26.000R | -10.000R | 🔴 AVOID |
| HIGH_VOL (n=28) | 42.9% | **2.25** ✅ | +0.714R | 2.56 | -16.000R | -10.000R | ⚠️ WATCH |

### `LONG_PUT` — 🔴 AVOID

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Profit Factor | **0.72** 🔴 | Must be > 1.0 to be profitable |
| Expected Value | -0.228R | Per trade in R |
| Win Rate | 19.3% | High WR ≠ profitable by itself |
| Avg Win | +3.000R | |
| Avg Loss | −+1.000R | |
| Win/Loss Ratio | 3.00× | > 1.0 = winners larger than losers |
| Kelly % | 0.0% | Optimal bet size (capped 25%) |
| Sharpe | -1.04 | Annualised (> 0.5 = acceptable) |
| Sortino | -1.83 | Downside-only risk |
| Large Losses (>2R) | 0.0% | Tail event frequency |
| Max Consec. Losses | 89 | Worst streak |
| Max Drawdown | -307.000R (-3070.0%) | Recovery: 115 trades |
| Worst Week | -11.000R | |
| Worst Month | -44.000R | Best: +54.000R |
| Calmar Ratio | -0.04 | Ann. return / max DD |
| Ulcer Index | 148.952 | Lower = smoother equity curve |
| Worst Single Trade | -1.000R | |

**Verdict reasoning:** Negative expectancy: PF=0.72, EV=-0.228R, 89 consecutive losses possible

**Regime breakdown:**

| Regime | WR% | PF | EV/trade | Sharpe | MaxDD | Worst Month | Verdict |
|--------|-----|----|----------|--------|-------|-------------|---------|
| ALL (n=948) | 19.3% | **0.72** 🔴 | -0.228R | -1.04 | -307.000R | -44.000R | 🔴 AVOID |
| RANGING (n=889) | 19.3% | **0.72** 🔴 | -0.226R | -1.03 | -303.000R | -44.000R | 🔴 AVOID |
| TRENDING (n=31) | 19.4% | **0.72** 🔴 | -0.226R | -1.01 | -9.000R | -6.000R | 🔴 AVOID |
| HIGH_VOL (n=28) | 17.9% | **0.65** 🔴 | -0.286R | -1.32 | -18.000R | -8.000R | 🔴 AVOID |

---
## Rankings

**By Profit Factor (higher = better):**

| Rank | Strategy | Profit Factor |
|------|----------|---------------|
| 1 | `BULL_PUT_SPREAD` | 2.090 |
| 2 | `BEAR_CALL_SPREAD` | 2.035 |
| 3 | `SHORT_STRANGLE` | 1.787 |
| 4 | `COVERED_CALL` | 1.396 |
| 5 | `IRON_CONDOR` | 1.221 |
| 6 | `PROTECTIVE_PUT` | 0.773 |
| 7 | `LONG_CALL` | 0.737 |
| 8 | `LONG_PUT` | 0.718 |
| 9 | `LONG_STRANGLE` | 0.559 |

**By Expected Value per trade (higher = better):**

| Rank | Strategy | EV/trade (R) |
|------|----------|--------------|
| 1 | `BULL_PUT_SPREAD` | 0.421 |
| 2 | `BEAR_CALL_SPREAD` | 0.408 |
| 3 | `SHORT_STRANGLE` | 0.371 |
| 4 | `COVERED_CALL` | 0.164 |
| 5 | `IRON_CONDOR` | 0.136 |
| 6 | `PROTECTIVE_PUT` | -0.098 |
| 7 | `LONG_CALL` | -0.211 |
| 8 | `LONG_PUT` | -0.228 |
| 9 | `LONG_STRANGLE` | -0.371 |

**By Sharpe Ratio (higher = better):**

| Rank | Strategy | Sharpe |
|------|----------|--------|
| 1 | `BULL_PUT_SPREAD` | 2.562 |
| 2 | `BEAR_CALL_SPREAD` | 2.465 |
| 3 | `SHORT_STRANGLE` | 1.838 |
| 4 | `COVERED_CALL` | 1.152 |
| 5 | `IRON_CONDOR` | 0.650 |
| 6 | `PROTECTIVE_PUT` | -0.692 |
| 7 | `LONG_CALL` | -0.955 |
| 8 | `LONG_PUT` | -1.040 |
| 9 | `LONG_STRANGLE` | -1.838 |

**By Max Drawdown (less negative = better):**

| Rank | Strategy | Max DD (R) |
|------|----------|------------|
| 1 | `COVERED_CALL` | -40.100R |
| 2 | `BEAR_CALL_SPREAD` | -45.000R |
| 3 | `BULL_PUT_SPREAD` | -62.000R |
| 4 | `SHORT_STRANGLE` | -71.000R |
| 5 | `IRON_CONDOR` | -116.500R |
| 6 | `PROTECTIVE_PUT` | -172.500R |
| 7 | `LONG_CALL` | -237.000R |
| 8 | `LONG_PUT` | -307.000R |
| 9 | `LONG_STRANGLE` | -389.000R |

---
## Production Readiness Gate

> Strategy promoted only when: PF > 1.3, EV > 0.1R, Sharpe > 0.5, MaxDD within acceptable range.

| Strategy | PF > 1.3? | EV > 0.1R? | Sharpe > 0.5? | Max DD < −15R? | Gate |
|----------|-----------|------------|---------------|----------------|------|
| `BULL_PUT_SPREAD` | ✅ 2.09 | ✅ +0.421R | ✅ 2.56 | ❌ -62.00R | ❌ FAIL |
| `BEAR_CALL_SPREAD` | ✅ 2.04 | ✅ +0.408R | ✅ 2.46 | ❌ -45.00R | ❌ FAIL |
| `IRON_CONDOR` | ❌ 1.22 | ✅ +0.136R | ✅ 0.65 | ❌ -116.50R | ❌ FAIL |
| `SHORT_STRANGLE` | ✅ 1.79 | ✅ +0.371R | ✅ 1.84 | ❌ -71.00R | ❌ FAIL |
| `LONG_STRANGLE` | ❌ 0.56 | ❌ -0.371R | ❌ -1.84 | ❌ -389.00R | ❌ FAIL |
| `COVERED_CALL` | ✅ 1.40 | ✅ +0.164R | ✅ 1.15 | ❌ -40.10R | ❌ FAIL |
| `PROTECTIVE_PUT` | ❌ 0.77 | ❌ -0.098R | ❌ -0.69 | ❌ -172.50R | ❌ FAIL |
| `LONG_CALL` | ❌ 0.74 | ❌ -0.211R | ❌ -0.95 | ❌ -237.00R | ❌ FAIL |
| `LONG_PUT` | ❌ 0.72 | ❌ -0.228R | ❌ -1.04 | ❌ -307.00R | ❌ FAIL |

---
*Generated by OPTIONS_RISK_AUDIT_001.*  
*Win rate is context. Profit factor is reality. Drawdown is the cost.*  
*No live trading code was modified.*