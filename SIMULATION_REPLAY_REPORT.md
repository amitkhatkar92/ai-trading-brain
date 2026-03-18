# AI Trading Brain — 30-Day Historical Market Replay Simulation Report

**Generated :** 2026-03-16 15:51:22
**Simulation duration :** 24.7s
**Period replayed :** 2026-01-30 → 2026-03-13  (30 trading days)
**Mode :** Paper Trading (no live orders)
**Data source :** yfinance historical OHLCV + India VIX + 31 Nifty 100 equities

---

## Section 1 — Executive Summary


| Item | Value |
|------|-------|
| Period | 2026-01-30 → 2026-03-13 |
| Days simulated | 30 |
| Total signals generated | 286 |
| Trades executed | 6 |
| Trade approval rate | 2.1% |
| Win rate | 50.0% |
| Total PnL | ₹36,393 |
| Profit factor | 3.96  —  Excellent ( >2.5 ) |
| Max drawdown | 0.90% |
| Avg R-multiple | +0.75R |
| Nifty 50 return (period) | -8.57% |
| Cycle errors | 0 |
| Avg events per day (pipeline depth) | 24 |

---

## Section 2 — Day-by-Day Results

| Day | Date | Nifty Close (Δ%) | VIX | Regime | Signals | Trades |
|-----|------|-----------------|-----|--------|---------|--------|
| 1 | 2026-01-30 | 25,321 (-0.39%) | 13.6 | RegimeLabel.BULL_TREND | 13 | 0 |
| 2 | 2026-02-02 | 25,088 (-0.92%) | 13.9 | RegimeLabel.BULL_TREND | 7 | 0 |
| 3 | 2026-02-03 | 25,728 (+2.55%) | 12.9 | RegimeLabel.BULL_TREND | 12 | 1 |
| 4 | 2026-02-04 | 25,776 (+0.19%) | 12.2 | RegimeLabel.BULL_TREND | 7 | 0 |
| 5 | 2026-02-05 | 25,643 (-0.52%) | 12.2 | RegimeLabel.BULL_TREND | 10 | 0 |
| 6 | 2026-02-06 | 25,694 (+0.20%) | 11.9 | RegimeLabel.BULL_TREND | 10 | 0 |
| 7 | 2026-02-09 | 25,867 (+0.68%) | 12.2 | RegimeLabel.BULL_TREND | 11 | 0 |
| 8 | 2026-02-10 | 25,935 (+0.26%) | 11.7 | RegimeLabel.BULL_TREND | 10 | 0 |
| 9 | 2026-02-11 | 25,954 (+0.07%) | 11.6 | RegimeLabel.BULL_TREND | 10 | 1 |
| 10 | 2026-02-12 | 25,807 (-0.56%) | 11.7 | RegimeLabel.BULL_TREND | 9 | 0 |
| 11 | 2026-02-13 | 25,471 (-1.30%) | 13.3 | RegimeLabel.BULL_TREND | 8 | 0 |
| 12 | 2026-02-16 | 25,683 (+0.83%) | 13.3 | RegimeLabel.BULL_TREND | 9 | 0 |
| 13 | 2026-02-17 | 25,725 (+0.17%) | 12.7 | RegimeLabel.BULL_TREND | 8 | 0 |
| 14 | 2026-02-18 | 25,819 (+0.37%) | 12.2 | RegimeLabel.BULL_TREND | 10 | 0 |
| 15 | 2026-02-19 | 25,454 (-1.41%) | 13.5 | RegimeLabel.BULL_TREND | 6 | 0 |
| 16 | 2026-02-20 | 25,571 (+0.46%) | 14.4 | RegimeLabel.RANGE_MARKET | 12 | 1 |
| 17 | 2026-02-23 | 25,713 (+0.55%) | 14.2 | RegimeLabel.BULL_TREND | 8 | 0 |
| 18 | 2026-02-24 | 25,425 (-1.12%) | 14.2 | RegimeLabel.RANGE_MARKET | 15 | 1 |
| 19 | 2026-02-25 | 25,482 (+0.23%) | 13.5 | RegimeLabel.BULL_TREND | 9 | 1 |
| 20 | 2026-02-26 | 25,497 (+0.06%) | 13.1 | RegimeLabel.BULL_TREND | 8 | 0 |
| 21 | 2026-02-27 | 25,179 (-1.25%) | 13.7 | RegimeLabel.BULL_TREND | 11 | 0 |
| 22 | 2026-03-02 | 24,866 (-1.24%) | 17.1 | RegimeLabel.RANGE_MARKET | 14 | 1 |
| 23 | 2026-03-04 | 24,480 (-1.55%) | 21.1 | RegimeLabel.BEAR_MARKET | 6 | 0 |
| 24 | 2026-03-05 | 24,766 (+1.17%) | 17.9 | RegimeLabel.BULL_TREND | 10 | 0 |
| 25 | 2026-03-06 | 24,450 (-1.27%) | 19.9 | RegimeLabel.BEAR_MARKET | 6 | 0 |
| 26 | 2026-03-09 | 24,028 (-1.73%) | 23.4 | RegimeLabel.VOLATILE | 16 | 0 |
| 27 | 2026-03-10 | 24,262 (+0.97%) | 18.9 | RegimeLabel.RANGE_MARKET | 9 | 0 |
| 28 | 2026-03-11 | 23,867 (-1.63%) | 21.1 | RegimeLabel.BEAR_MARKET | 6 | 0 |
| 29 | 2026-03-12 | 23,639 (-0.95%) | 21.5 | RegimeLabel.BEAR_MARKET | 6 | 0 |
| 30 | 2026-03-13 | 23,151 (-2.06%) | 22.6 | RegimeLabel.VOLATILE | 10 | 0 |

---

## Section 3 — Quantitative Metrics

## Quantitative Metrics

| Metric | Value |
|--------|-------|
| Total signals generated | 286 |
| Trades executed | 6 |
| Trade approval rate | 2.1% |
| Win rate | 50.0% |
| Avg R-multiple | +0.75R |
| Gross PnL (simulated) | ₹36,393 |
| Total trading costs | ₹2,506 |
| Net PnL (after costs) | ₹33,888 |
| Avg cost per trade | ₹418 |
| Profit factor | 3.96  —  Excellent ( >2.5 ) |
| Max drawdown | 0.90% |
| Days with trades | 6 / 30 |
| Cycle errors | 0 |
| SL missing count | 0 |
| RR < 1.0 count | 0 |
| Strategy-regime alignment | 0.0% |

## Per-Strategy Breakdown

| Strategy | Trades | Win Rate | Avg R | Total PnL |
|----------|--------|----------|-------|-----------|
| Mean_Reversion_RSI_HiVol | 3 | 67% | +1.33R | ₹17,908 |
| Momentum_Retest | 2 | 50% | +0.75R | ₹21,396 |
| EDG_MACRO__78_EE0000 | 1 | 0% | -1.00R | ₹-2,911 |

## Trade Distribution by Regime

| Regime | Trades |
|--------|--------|
| BULL_TREND | 3 |
| RANGE_MARKET | 3 |
| BEAR_MARKET | 0 |
| VOLATILE | 0 |
---

## Section 3a — Trading Cost Simulation (Zerodha / NSE Intraday Equity)

> Costs are estimated per trade: ₹20 brokerage each leg, STT 0.1 % on sell,
> exchange charge 0.00325 %, SEBI 0.0001 %, GST 18 %, slippage 0.1 %.

| Cost Component | Total (₹) |
|----------------|-----------|
| Brokerage (₹20 × 2 × trades) | ₹240 |
| STT (0.1 % sell side) | ₹1,069 |
| Slippage (0.1 % market impact) | ₹1,069 |
| **Total costs** | **₹2,506** |
| Avg cost per trade | ₹418 |
| Gross simulated PnL | ₹36,393 |
| **Net PnL (after costs)** | **₹33,888** |

---

## Section 4 — Risk & Compliance Analysis

### Passed

- ✅ All trades have stop-loss set
- ✅ All trades met minimum R:R ≥ 1.0
- ✅ Max drawdown 0.90% (≤ 5%)

### Issues Found

- ⚠ Strategy-regime alignment only **0%** (target ≥ 60%) — strategies may not be well-suited to current regime

### Kill-Switch Behaviour (RiskGuardian)
The RiskGuardian ran for every cycle with VIX and drawdown data from the
historical replay.  Its thresholds (VIX > 45, daily loss > 2%) were not
triggered during this 30-day window, which is consistent with
normal market conditions.

### SL & Position Sizing
- Stop-loss compliance : 6/6 trades
- RR ≥ 1 compliance    : 6/6 trades

---

## Section 4a — Monte Carlo Equity Simulation

> 1,000 bootstrap simulations · 6 trades each  · Starting capital ₹1,000,000

### Equity Distribution

| Scenario | Final Equity | Return |
|----------|-------------|--------|
| Best 5% (p95) | ₹1,077,846 | +7.8% |
| Median (p50)  | ₹1,034,403 | +3.4% |
| Worst 5% (p5) | ₹994,940 | -0.5% |

### Drawdown & Risk

| Metric | Value |
|--------|-------|
| Median max drawdown | 0.9% |
| 95th-pct max drawdown (conservative) | 1.9% |
| 99th-pct max drawdown (extreme) | 2.5% |
| Probability of loss (final < capital) | 8.5% |
| Probability of ruin (equity < 50%) | 0.0% |
| Sharpe estimate (annualised) | 21.45 |

### Verdict: ✅ ROBUST

> Equity curve is stable across 95 % of simulations — suitable for live paper trading.
---

## Section 4b — Strategy Fragility Test

> Each noise level degrades entry price adversely (BUY fills higher,
> SELL fills lower).  SL and target remain fixed.  Tests execution
> robustness: does the edge survive imperfect fills?

| Noise (%) | Trades | Win Rate | Profit Factor | Avg R | Net PnL |
|-----------|--------|----------|---------------|-------|---------|
| 0.00 **←base** | 6 | 50% | 3.96 | +0.75R | ₹36,393 |
| 0.25 | 6 | 50% | 3.53 | +0.61R | ₹33,721 |
| 0.50 | 6 | 50% | 3.16 | +0.50R | ₹31,049 |
| 1.00 **←gate** | 6 | 50% | 2.57 | +0.31R | ₹25,704 |
| 1.50 | 6 | 50% | 2.10 | +0.17R | ₹20,359 |
| 2.00 | 6 | 50% | 1.73 | +0.06R | ₹15,015 |

**PF decay per 1 % of noise:** 1.392  (lower = more robust)

### Verdict: ✅ ROBUST

> Edge holds at 1 % noise (PF 2.57 ≥ 1.5).  Strategy survives realistic execution variance.
---

## Section 4c — Limit-Order Entry Simulation

> **Problem:** The market-order fragility test shows PF collapses at 0.5 % noise.
> **Solution tested here:** Place every entry as a limit order at the signal price.
> A BUY limit fills only when the day's LOW ≤ entry; a SELL limit fills only when
> HIGH ≥ entry.  If the order does not fill, no trade is taken.
> Fill price = exactly the limit price — zero adverse slippage.

### Fill Rate Summary (limit at exact signal price)

| Metric | Value |
|--------|-------|
| Total orders (market would have taken) | 6 |
| Orders that would fill as limits | 6 (100.0%) |
| Unfilled (no trade taken) | 0 |
| Win rate (filled trades) | 50.0% |
| Profit factor (filled trades) | 3.96 |
| Avg R-multiple (filled trades) | +0.75R |
| Net PnL (filled trades) | ₹36,393 |

### Tightness Analysis

> Shows how fill rate and PF change as the limit is placed *inside* the range
> (offset = how many % below entry for BUY, above for SELL).

| Offset (%) | Filled | Fill Rate | PF | Win Rate | Avg R | Net PnL |
|------------|--------|-----------|----|----------|-------|---------|
| 0.00 **← at price** | 6/6 | 100.0% | 3.96 | 50% | +0.75R | ₹36,393 |
| 0.10 | 6/6 | 100.0% | 3.96 | 50% | +0.75R | ₹36,393 |
| 0.25 | 5/6 | 83.3% | 7.70 | 60% | +1.10R | ₹42,373 |
| 0.50 | 4/6 | 66.7% | 5.15 | 50% | +0.75R | ₹26,240 |
| 1.00 | 3/6 | 50.0% | 9.54 | 67% | +1.33R | ₹29,151 |

### Fragility of Limit-Filled Trades

> Market-order fragility (from Section 4b) vs. limit-order fragility.
> Limit orders neutralise adverse fill slippage — PF should be far
> more stable under noise.

| Noise (%) | Market-Order PF | Limit-Order PF | Improvement |
|-----------|-----------------|----------------|-------------|
| 0.00 | 3.96 | 3.96 | +0.00 |
| 0.25 | — | 3.53 | — |
| 0.50 | — | 3.16 | — |
| 1.00 | 2.57 | 2.57 | +0.00 |

**Limit PF@1% noise:** 2.57  (market was 2.57)

### Verdict: ✅ STRONG

> Limit orders fill 100% of the time and PF holds at 2.57 under 1% noise.  Switch to limit entries immediately.
---

## Section 4d — Market Capture Ratio (MCR)

> **What this measures:** How much of the available market movement the AI captures in each regime.  A high capture ratio in your primary regime confirms the strategy is genuinely aligned — not just profitable by chance.

### Overall

| Item | Value |
|------|-------|
| Total market movement (sum of |Nifty chg %|) | +26.65% |
| Total system return (PnL / capital) | +3.6393% |
| **Overall capture ratio** | **+13.7%** — 🟠 WEAK |
| Total trades across all regimes | 6 |

> 🏆 **Primary regime edge:** `RANGE_MARKET` — highest capture ratio.

### Regime-by-Regime Breakdown

| Regime | Days | Trades | Market Move | System Return | Capture Ratio | Avg Trade Capture | Win Rate | Assessment |
|--------|------|--------|-------------|---------------|--------------|-------------------|----------|------------|
| RANGE_MARKET | 4 | 3 | +3.80% | +1.7908% | +47.2% | +53.3% | 67% | 🟢 DOMINANT |
| BULL_TREND | 20 | 3 | +13.66% | +1.8485% | +13.5% | +6.7% | 33% | 🟠 WEAK |
| BEAR_MARKET | 4 | 0 | +5.40% | +0.0000% | +0.0% | +0.0% | 0% | 🟠 WEAK |
| VOLATILE | 2 | 0 | +3.79% | +0.0000% | +0.0% | +0.0% | 0% | 🟠 WEAK |

### Interpretation

| Capture Ratio | Label | Meaning |
|---------------|-------|---------|
| ≥ 40% | 🟢 DOMINANT | Strong alpha — this regime is your sweet spot |
| 15–40% | 🟡 MODERATE | Positive edge — room to optimise |
| 0–15% | 🟠 WEAK | Marginal capture — consider disabling strategies |
| < 0% | 🔴 NEGATIVE | AI loses when market moves — avoid this regime |

✅ **Strategy-regime alignment confirmed** in: `RANGE_MARKET`

### MCR vs Institutional Standard

> Institutional quant desks require strategy capture ≥ 20–30% of the market move in the strategy's target regime before allocating capital.

⚠ Overall capture **13.7%** is below the 20% institutional threshold.  Focus on the highest-capture regime(s) and restrict trading in low-capture environments.
---

## Section 4e -- Edge Half-Life (EHL) Analysis

> **What this measures:** How many 5-minute candles after a signal the strategy retains at least half of its original R-multiple edge. The result directly calibrates three execution timing parameters.

### Summary

| Item | Value |
|------|-------|
| Baseline edge (R at delay=0) | +0.750R |
| Half-life threshold (50% of baseline) | +0.375R |
| **Edge Half-Life** | **beyond max delay tested (>6 candles)** |
| Per-candle adverse drift modelled | 0.0118% of entry price |
| Trades analysed | 6 |

### R-Multiple Decay by Entry Delay

| Candles Delayed | Avg R | % of Baseline | Edge Status |
|-----------------|-------|---------------|-------------|
| 0 candles (0 min) | +0.750R | 100% | Full strength |
| 1 candles (5 min) | +0.746R | 99% | Full strength |
| 2 candles (10 min) | +0.742R | 99% | Full strength |
| 3 candles (15 min) | +0.738R | 98% | Full strength |
| 4 candles (20 min) | +0.733R | 98% | Full strength |
| 5 candles (25 min) | +0.729R | 97% | Full strength |
| 6 candles (30 min) | +0.725R | 97% | Full strength |

### Per-Strategy Half-Life

| Strategy | Trades | R@0 | Half-Life | Interpretation |
|----------|--------|-----|-----------|----------------|
| Mean_Reversion_RSI_HiVol | 3 | +1.333R | >6c | Slow decay -- persist beyond 6 candles |
| Momentum_Retest | 2 | +0.750R | >6c | Slow decay -- persist beyond 6 candles |
| EDG_MACRO__78_EE0000 | 1 | -1.000R | >6c | Slow decay -- persist beyond 6 candles |

### Calibration vs Current Execution Parameters

| Parameter | Current Value | EHL-Derived Recommendation | Status |
|-----------|--------------|---------------------------|--------|
| `LIMIT_CANDLE_EXPIRY` | 3 candles | 3 candles | OK -- exact match |
| `AET_MAX_WAIT_CANDLES` | 2 candles | 2 candles | OK -- exact match |
| `REENTRY_WINDOW_CANDLES` | 10 candles | 10 candles | OK -- exact match |

### Verdict

> Edge persists beyond the max tested delay (6 candles / 30 min). This is characteristic of slow-decay strategies (trend-following). Current timing parameters are conservative -- no urgent tuning needed.

> **Drift model note:** adverse drift per candle is empirically derived from average |Nifty daily change| across the replay period divided by 75 intraday candles. Actual slippage may vary.
---

## Section 4f -- Edge Distribution Map (EDM)

### Summary Statistics

| Metric | Value |
|--------|-------|
| Total trades | 6 |
| Win / Loss / Even | 3 / 3 / 0 |
| Win rate | 50.0% |
| Avg R (all trades) | +0.750R |
| Avg winning R | +2.500R |
| Avg losing R | -1.000R |
| Payoff ratio | 2.50x |
| Tail profit ratio | 2.50x  (distributed) |
| Loss concentration (worst 25%) | 33.3% of gross loss |

### Edge Profile

**Profile: Balanced**

Moderate win-rate and payoff ratio. Equal emphasis on stop-loss control and letting winners run. Kelly fraction: standard sizing (f ~ 0.20). Review per-strategy profiles for more granular guidance.

### R-Multiple Distribution

```
Bin           Trades  Bar
-------------------------------------------------------
-0.8R              3  ##############################
+2.2R              1  ##########
+2.8R              2  ####################
```

_Bins: each bucket spans 0.5R.  Overflow bins (<-3R and >=+5R) capture extreme outliers._

### Interpretation

- Balanced distribution — both win frequency and win size contribute to PnL.
- Standard risk management applies. Review per-strategy profiles below for strategy-specific guidance.

### Per-Strategy Profiles

| Strategy | Trades | Win% | AvgR | Payoff | Profile |
|----------|--------|------|------|--------|---------|
| Mean_Reversion_RSI_HiVol | 3 | 66.7% | +1.333R | 2.50x | Balanced |
| Momentum_Retest | 2 | 50.0% | +0.750R | 2.50x | Balanced |
| EDG_MACRO__78_EE0000 | 1 | 0.0% | -1.000R | 0.00x | Balanced |
---

## Section 5 — Decision Trace Files

1207 trace file(s) written to `simulation_logs/decision_trace/`:

- `day_01_2024-09-20.json`
- `day_01_2024-09-23.json`
- `day_01_2025-06-23.json`
- `day_01_2025-09-09.json`
- `day_01_2025-12-15.json`
- `day_01_2026-01-28.json`
- `day_01_2026-01-29.json`
- `day_01_2026-01-30.json`
- `day_01_2026-03-02.json`
- `day_01_2026-03-04.json`
- `day_01_2026-03-05.json`
- `day_02_2024-09-23.json`
- `day_02_2024-09-24.json`
- `day_02_2025-06-24.json`
- `day_02_2025-09-10.json`
- `day_02_2025-12-16.json`
- `day_02_2026-01-29.json`
- `day_02_2026-01-30.json`
- `day_02_2026-02-02.json`
- `day_02_2026-03-04.json`
- `day_02_2026-03-05.json`
- `day_02_2026-03-06.json`
- `day_03_2024-09-24.json`
- `day_03_2024-09-25.json`
- `day_03_2025-06-25.json`
- `day_03_2025-09-11.json`
- `day_03_2025-12-17.json`
- `day_03_2026-01-30.json`
- `day_03_2026-02-02.json`
- `day_03_2026-02-03.json`
- `day_03_2026-03-05.json`
- `day_03_2026-03-06.json`
- `day_03_2026-03-09.json`
- `day_04_2024-09-25.json`
- `day_04_2024-09-26.json`
- `day_04_2025-06-26.json`
- `day_04_2025-09-12.json`
- `day_04_2025-12-18.json`
- `day_04_2026-02-02.json`
- `day_04_2026-02-03.json`
- `day_04_2026-02-04.json`
- `day_04_2026-03-06.json`
- `day_04_2026-03-09.json`
- `day_04_2026-03-10.json`
- `day_05_2024-09-26.json`
- `day_05_2024-09-27.json`
- `day_05_2025-06-27.json`
- `day_05_2025-09-15.json`
- `day_05_2025-12-19.json`
- `day_05_2026-02-03.json`
- `day_05_2026-02-04.json`
- `day_05_2026-02-05.json`
- `day_05_2026-03-09.json`
- `day_05_2026-03-10.json`
- `day_05_2026-03-11.json`
- `day_06_2024-09-27.json`
- `day_06_2024-09-30.json`
- `day_06_2025-06-30.json`
- `day_06_2025-09-16.json`
- `day_06_2025-12-22.json`
- `day_06_2026-02-04.json`
- `day_06_2026-02-05.json`
- `day_06_2026-02-06.json`
- `day_06_2026-03-10.json`
- `day_06_2026-03-11.json`
- `day_06_2026-03-12.json`
- `day_07_2024-09-30.json`
- `day_07_2024-10-01.json`
- `day_07_2025-07-01.json`
- `day_07_2025-09-17.json`
- `day_07_2025-12-23.json`
- `day_07_2026-02-05.json`
- `day_07_2026-02-06.json`
- `day_07_2026-02-09.json`
- `day_07_2026-03-11.json`
- `day_07_2026-03-12.json`
- `day_07_2026-03-13.json`
- `day_08_2024-10-01.json`
- `day_08_2024-10-03.json`
- `day_08_2025-07-02.json`
- `day_08_2025-09-18.json`
- `day_08_2025-12-24.json`
- `day_08_2026-02-06.json`
- `day_08_2026-02-09.json`
- `day_08_2026-02-10.json`
- `day_09_2024-10-03.json`
- `day_09_2024-10-04.json`
- `day_09_2025-07-03.json`
- `day_09_2025-09-19.json`
- `day_09_2025-12-26.json`
- `day_09_2026-02-09.json`
- `day_09_2026-02-10.json`
- `day_09_2026-02-11.json`
- `day_100_2025-02-11.json`
- `day_100_2025-02-12.json`
- `day_100_2025-11-14.json`
- `day_100_2026-02-03.json`
- `day_101_2025-02-12.json`
- `day_101_2025-02-13.json`
- `day_101_2025-11-17.json`
- `day_101_2026-02-04.json`
- `day_102_2025-02-13.json`
- `day_102_2025-02-14.json`
- `day_102_2025-11-18.json`
- `day_102_2026-02-05.json`
- `day_103_2025-02-14.json`
- `day_103_2025-02-17.json`
- `day_103_2025-11-19.json`
- `day_103_2026-02-06.json`
- `day_104_2025-02-17.json`
- `day_104_2025-02-18.json`
- `day_104_2025-11-20.json`
- `day_104_2026-02-09.json`
- `day_105_2025-02-18.json`
- `day_105_2025-02-19.json`
- `day_105_2025-11-21.json`
- `day_105_2026-02-10.json`
- `day_106_2025-02-19.json`
- `day_106_2025-02-20.json`
- `day_106_2025-11-24.json`
- `day_106_2026-02-11.json`
- `day_107_2025-02-20.json`
- `day_107_2025-02-21.json`
- `day_107_2025-11-25.json`
- `day_107_2026-02-12.json`
- `day_108_2025-02-21.json`
- `day_108_2025-02-24.json`
- `day_108_2025-11-26.json`
- `day_108_2026-02-13.json`
- `day_109_2025-02-24.json`
- `day_109_2025-02-25.json`
- `day_109_2025-11-27.json`
- `day_109_2026-02-16.json`
- `day_10_2024-10-04.json`
- `day_10_2024-10-07.json`
- `day_10_2025-07-04.json`
- `day_10_2025-09-22.json`
- `day_10_2025-12-29.json`
- `day_10_2026-02-10.json`
- `day_10_2026-02-11.json`
- `day_10_2026-02-12.json`
- `day_110_2025-02-25.json`
- `day_110_2025-02-27.json`
- `day_110_2025-11-28.json`
- `day_110_2026-02-17.json`
- `day_111_2025-02-27.json`
- `day_111_2025-02-28.json`
- `day_111_2025-12-01.json`
- `day_111_2026-02-18.json`
- `day_112_2025-02-28.json`
- `day_112_2025-03-03.json`
- `day_112_2025-12-02.json`
- `day_112_2026-02-19.json`
- `day_113_2025-03-03.json`
- `day_113_2025-03-04.json`
- `day_113_2025-12-03.json`
- `day_113_2026-02-20.json`
- `day_114_2025-03-04.json`
- `day_114_2025-03-05.json`
- `day_114_2025-12-04.json`
- `day_114_2026-02-23.json`
- `day_115_2025-03-05.json`
- `day_115_2025-03-06.json`
- `day_115_2025-12-05.json`
- `day_115_2026-02-24.json`
- `day_116_2025-03-06.json`
- `day_116_2025-03-07.json`
- `day_116_2025-12-08.json`
- `day_116_2026-02-25.json`
- `day_117_2025-03-07.json`
- `day_117_2025-03-10.json`
- `day_117_2025-12-09.json`
- `day_117_2026-02-26.json`
- `day_118_2025-03-10.json`
- `day_118_2025-03-11.json`
- `day_118_2025-12-10.json`
- `day_118_2026-02-27.json`
- `day_119_2025-03-11.json`
- `day_119_2025-03-12.json`
- `day_119_2025-12-11.json`
- `day_119_2026-03-02.json`
- `day_11_2024-10-07.json`
- `day_11_2024-10-08.json`
- `day_11_2025-07-07.json`
- `day_11_2025-09-23.json`
- `day_11_2025-12-30.json`
- `day_11_2026-02-11.json`
- `day_11_2026-02-12.json`
- `day_11_2026-02-13.json`
- `day_120_2025-03-12.json`
- `day_120_2025-03-13.json`
- `day_120_2025-12-12.json`
- `day_120_2026-03-04.json`
- `day_121_2025-03-13.json`
- `day_121_2025-03-17.json`
- `day_121_2025-12-15.json`
- `day_121_2026-03-05.json`
- `day_122_2025-03-17.json`
- `day_122_2025-03-18.json`
- `day_122_2025-12-16.json`
- `day_122_2026-03-06.json`
- `day_123_2025-03-18.json`
- `day_123_2025-03-19.json`
- `day_123_2025-12-17.json`
- `day_123_2026-03-09.json`
- `day_124_2025-03-19.json`
- `day_124_2025-03-20.json`
- `day_124_2025-12-18.json`
- `day_124_2026-03-10.json`
- `day_125_2025-03-20.json`
- `day_125_2025-03-21.json`
- `day_125_2025-12-19.json`
- `day_125_2026-03-11.json`
- `day_126_2025-03-21.json`
- `day_126_2025-03-24.json`
- `day_126_2025-12-22.json`
- `day_126_2026-03-12.json`
- `day_127_2025-03-24.json`
- `day_127_2025-03-25.json`
- `day_127_2025-12-23.json`
- `day_128_2025-03-25.json`
- `day_128_2025-03-26.json`
- `day_128_2025-12-24.json`
- `day_129_2025-03-26.json`
- `day_129_2025-03-27.json`
- `day_129_2025-12-26.json`
- `day_12_2024-10-08.json`
- `day_12_2024-10-09.json`
- `day_12_2025-07-08.json`
- `day_12_2025-09-24.json`
- `day_12_2025-12-31.json`
- `day_12_2026-02-12.json`
- `day_12_2026-02-13.json`
- `day_12_2026-02-16.json`
- `day_130_2025-03-27.json`
- `day_130_2025-03-28.json`
- `day_130_2025-12-29.json`
- `day_131_2025-03-28.json`
- `day_131_2025-04-01.json`
- `day_131_2025-12-30.json`
- `day_132_2025-04-01.json`
- `day_132_2025-04-02.json`
- `day_132_2025-12-31.json`
- `day_133_2025-04-02.json`
- `day_133_2025-04-03.json`
- `day_133_2026-01-01.json`
- `day_134_2025-04-03.json`
- `day_134_2025-04-04.json`
- `day_134_2026-01-02.json`
- `day_135_2025-04-04.json`
- `day_135_2025-04-07.json`
- `day_135_2026-01-05.json`
- `day_136_2025-04-07.json`
- `day_136_2025-04-08.json`
- `day_136_2026-01-06.json`
- `day_137_2025-04-08.json`
- `day_137_2025-04-09.json`
- `day_137_2026-01-07.json`
- `day_138_2025-04-09.json`
- `day_138_2025-04-11.json`
- `day_138_2026-01-08.json`
- `day_139_2025-04-11.json`
- `day_139_2025-04-15.json`
- `day_139_2026-01-09.json`
- `day_13_2024-10-09.json`
- `day_13_2024-10-10.json`
- `day_13_2025-07-09.json`
- `day_13_2025-09-25.json`
- `day_13_2026-01-01.json`
- `day_13_2026-02-13.json`
- `day_13_2026-02-16.json`
- `day_13_2026-02-17.json`
- `day_140_2025-04-15.json`
- `day_140_2025-04-16.json`
- `day_140_2026-01-12.json`
- `day_141_2025-04-16.json`
- `day_141_2025-04-17.json`
- `day_141_2026-01-13.json`
- `day_142_2025-04-17.json`
- `day_142_2025-04-21.json`
- `day_142_2026-01-14.json`
- `day_143_2025-04-21.json`
- `day_143_2025-04-22.json`
- `day_143_2026-01-16.json`
- `day_144_2025-04-22.json`
- `day_144_2025-04-23.json`
- `day_144_2026-01-19.json`
- `day_145_2025-04-23.json`
- `day_145_2025-04-24.json`
- `day_145_2026-01-20.json`
- `day_146_2025-04-24.json`
- `day_146_2025-04-25.json`
- `day_146_2026-01-21.json`
- `day_147_2025-04-25.json`
- `day_147_2025-04-28.json`
- `day_147_2026-01-22.json`
- `day_148_2025-04-28.json`
- `day_148_2025-04-29.json`
- `day_148_2026-01-23.json`
- `day_149_2025-04-29.json`
- `day_149_2025-04-30.json`
- `day_149_2026-01-27.json`
- `day_14_2024-10-10.json`
- `day_14_2024-10-11.json`
- `day_14_2025-07-10.json`
- `day_14_2025-09-26.json`
- `day_14_2026-01-02.json`
- `day_14_2026-02-16.json`
- `day_14_2026-02-17.json`
- `day_14_2026-02-18.json`
- `day_150_2025-04-30.json`
- `day_150_2025-05-02.json`
- `day_150_2026-01-28.json`
- `day_151_2025-05-02.json`
- `day_151_2025-05-05.json`
- `day_151_2026-01-29.json`
- `day_152_2025-05-05.json`
- `day_152_2025-05-06.json`
- `day_152_2026-01-30.json`
- `day_153_2025-05-06.json`
- `day_153_2025-05-07.json`
- `day_153_2026-02-02.json`
- `day_154_2025-05-07.json`
- `day_154_2025-05-08.json`
- `day_154_2026-02-03.json`
- `day_155_2025-05-08.json`
- `day_155_2025-05-09.json`
- `day_155_2026-02-04.json`
- `day_156_2025-05-09.json`
- `day_156_2025-05-12.json`
- `day_156_2026-02-05.json`
- `day_157_2025-05-12.json`
- `day_157_2025-05-13.json`
- `day_157_2026-02-06.json`
- `day_158_2025-05-13.json`
- `day_158_2025-05-14.json`
- `day_158_2026-02-09.json`
- `day_159_2025-05-14.json`
- `day_159_2025-05-15.json`
- `day_159_2026-02-10.json`
- `day_15_2024-10-11.json`
- `day_15_2024-10-14.json`
- `day_15_2025-07-11.json`
- `day_15_2025-09-29.json`
- `day_15_2026-01-05.json`
- `day_15_2026-02-17.json`
- `day_15_2026-02-18.json`
- `day_15_2026-02-19.json`
- `day_160_2025-05-15.json`
- `day_160_2025-05-16.json`
- `day_160_2026-02-11.json`
- `day_161_2025-05-16.json`
- `day_161_2025-05-19.json`
- `day_161_2026-02-12.json`
- `day_162_2025-05-19.json`
- `day_162_2025-05-20.json`
- `day_162_2026-02-13.json`
- `day_163_2025-05-20.json`
- `day_163_2025-05-21.json`
- `day_163_2026-02-16.json`
- `day_164_2025-05-21.json`
- `day_164_2025-05-22.json`
- `day_164_2026-02-17.json`
- `day_165_2025-05-22.json`
- `day_165_2025-05-23.json`
- `day_165_2026-02-18.json`
- `day_166_2025-05-23.json`
- `day_166_2025-05-26.json`
- `day_166_2026-02-19.json`
- `day_167_2025-05-26.json`
- `day_167_2025-05-27.json`
- `day_167_2026-02-20.json`
- `day_168_2025-05-27.json`
- `day_168_2025-05-28.json`
- `day_168_2026-02-23.json`
- `day_169_2025-05-28.json`
- `day_169_2025-05-29.json`
- `day_169_2026-02-24.json`
- `day_16_2024-10-14.json`
- `day_16_2024-10-15.json`
- `day_16_2025-07-14.json`
- `day_16_2025-09-30.json`
- `day_16_2026-01-06.json`
- `day_16_2026-02-18.json`
- `day_16_2026-02-19.json`
- `day_16_2026-02-20.json`
- `day_170_2025-05-29.json`
- `day_170_2025-05-30.json`
- `day_170_2026-02-25.json`
- `day_171_2025-05-30.json`
- `day_171_2025-06-02.json`
- `day_171_2026-02-26.json`
- `day_172_2025-06-02.json`
- `day_172_2025-06-03.json`
- `day_172_2026-02-27.json`
- `day_173_2025-06-03.json`
- `day_173_2025-06-04.json`
- `day_173_2026-03-02.json`
- `day_174_2025-06-04.json`
- `day_174_2025-06-05.json`
- `day_174_2026-03-04.json`
- `day_175_2025-06-05.json`
- `day_175_2025-06-06.json`
- `day_175_2026-03-05.json`
- `day_176_2025-06-06.json`
- `day_176_2025-06-09.json`
- `day_176_2026-03-06.json`
- `day_177_2025-06-09.json`
- `day_177_2025-06-10.json`
- `day_177_2026-03-09.json`
- `day_178_2025-06-10.json`
- `day_178_2025-06-11.json`
- `day_178_2026-03-10.json`
- `day_179_2025-06-11.json`
- `day_179_2025-06-12.json`
- `day_179_2026-03-11.json`
- `day_17_2024-10-15.json`
- `day_17_2024-10-16.json`
- `day_17_2025-07-15.json`
- `day_17_2025-10-01.json`
- `day_17_2026-01-07.json`
- `day_17_2026-02-19.json`
- `day_17_2026-02-20.json`
- `day_17_2026-02-23.json`
- `day_180_2025-06-12.json`
- `day_180_2025-06-13.json`
- `day_180_2026-03-12.json`
- `day_181_2025-06-13.json`
- `day_181_2025-06-16.json`
- `day_182_2025-06-16.json`
- `day_182_2025-06-17.json`
- `day_183_2025-06-17.json`
- `day_183_2025-06-18.json`
- `day_184_2025-06-18.json`
- `day_184_2025-06-19.json`
- `day_185_2025-06-19.json`
- `day_185_2025-06-20.json`
- `day_186_2025-06-20.json`
- `day_186_2025-06-23.json`
- `day_187_2025-06-23.json`
- `day_187_2025-06-24.json`
- `day_188_2025-06-24.json`
- `day_188_2025-06-25.json`
- `day_189_2025-06-25.json`
- `day_189_2025-06-26.json`
- `day_18_2024-10-16.json`
- `day_18_2024-10-17.json`
- `day_18_2025-07-16.json`
- `day_18_2025-10-03.json`
- `day_18_2026-01-08.json`
- `day_18_2026-02-20.json`
- `day_18_2026-02-23.json`
- `day_18_2026-02-24.json`
- `day_190_2025-06-26.json`
- `day_190_2025-06-27.json`
- `day_191_2025-06-27.json`
- `day_191_2025-06-30.json`
- `day_192_2025-06-30.json`
- `day_192_2025-07-01.json`
- `day_193_2025-07-01.json`
- `day_193_2025-07-02.json`
- `day_194_2025-07-02.json`
- `day_194_2025-07-03.json`
- `day_195_2025-07-03.json`
- `day_195_2025-07-04.json`
- `day_196_2025-07-04.json`
- `day_196_2025-07-07.json`
- `day_197_2025-07-07.json`
- `day_197_2025-07-08.json`
- `day_198_2025-07-08.json`
- `day_198_2025-07-09.json`
- `day_199_2025-07-09.json`
- `day_199_2025-07-10.json`
- `day_19_2024-10-17.json`
- `day_19_2024-10-18.json`
- `day_19_2025-07-17.json`
- `day_19_2025-10-06.json`
- `day_19_2026-01-09.json`
- `day_19_2026-02-23.json`
- `day_19_2026-02-24.json`
- `day_19_2026-02-25.json`
- `day_200_2025-07-10.json`
- `day_200_2025-07-11.json`
- `day_201_2025-07-11.json`
- `day_201_2025-07-14.json`
- `day_202_2025-07-14.json`
- `day_202_2025-07-15.json`
- `day_203_2025-07-15.json`
- `day_203_2025-07-16.json`
- `day_204_2025-07-16.json`
- `day_204_2025-07-17.json`
- `day_205_2025-07-17.json`
- `day_205_2025-07-18.json`
- `day_206_2025-07-18.json`
- `day_206_2025-07-21.json`
- `day_207_2025-07-21.json`
- `day_207_2025-07-22.json`
- `day_208_2025-07-22.json`
- `day_208_2025-07-23.json`
- `day_209_2025-07-23.json`
- `day_209_2025-07-24.json`
- `day_20_2024-10-18.json`
- `day_20_2024-10-21.json`
- `day_20_2025-07-18.json`
- `day_20_2025-10-07.json`
- `day_20_2026-01-12.json`
- `day_20_2026-02-24.json`
- `day_20_2026-02-25.json`
- `day_20_2026-02-26.json`
- `day_210_2025-07-24.json`
- `day_210_2025-07-25.json`
- `day_211_2025-07-25.json`
- `day_211_2025-07-28.json`
- `day_212_2025-07-28.json`
- `day_212_2025-07-29.json`
- `day_213_2025-07-29.json`
- `day_213_2025-07-30.json`
- `day_214_2025-07-30.json`
- `day_214_2025-07-31.json`
- `day_215_2025-07-31.json`
- `day_215_2025-08-01.json`
- `day_216_2025-08-01.json`
- `day_216_2025-08-04.json`
- `day_217_2025-08-04.json`
- `day_217_2025-08-05.json`
- `day_218_2025-08-05.json`
- `day_218_2025-08-06.json`
- `day_219_2025-08-06.json`
- `day_219_2025-08-07.json`
- `day_21_2024-10-21.json`
- `day_21_2024-10-22.json`
- `day_21_2025-07-21.json`
- `day_21_2025-10-08.json`
- `day_21_2026-01-13.json`
- `day_21_2026-02-25.json`
- `day_21_2026-02-26.json`
- `day_21_2026-02-27.json`
- `day_220_2025-08-07.json`
- `day_220_2025-08-08.json`
- `day_221_2025-08-08.json`
- `day_221_2025-08-11.json`
- `day_222_2025-08-11.json`
- `day_222_2025-08-12.json`
- `day_223_2025-08-12.json`
- `day_223_2025-08-13.json`
- `day_224_2025-08-13.json`
- `day_224_2025-08-14.json`
- `day_225_2025-08-14.json`
- `day_225_2025-08-18.json`
- `day_226_2025-08-18.json`
- `day_226_2025-08-19.json`
- `day_227_2025-08-19.json`
- `day_227_2025-08-20.json`
- `day_228_2025-08-20.json`
- `day_228_2025-08-21.json`
- `day_229_2025-08-21.json`
- `day_229_2025-08-22.json`
- `day_22_2024-10-22.json`
- `day_22_2024-10-23.json`
- `day_22_2025-07-22.json`
- `day_22_2025-10-09.json`
- `day_22_2026-01-14.json`
- `day_22_2026-02-26.json`
- `day_22_2026-02-27.json`
- `day_22_2026-03-02.json`
- `day_230_2025-08-22.json`
- `day_230_2025-08-25.json`
- `day_231_2025-08-25.json`
- `day_231_2025-08-26.json`
- `day_232_2025-08-26.json`
- `day_232_2025-08-28.json`
- `day_233_2025-08-28.json`
- `day_233_2025-08-29.json`
- `day_234_2025-08-29.json`
- `day_234_2025-09-01.json`
- `day_235_2025-09-01.json`
- `day_235_2025-09-02.json`
- `day_236_2025-09-02.json`
- `day_236_2025-09-03.json`
- `day_237_2025-09-03.json`
- `day_237_2025-09-04.json`
- `day_238_2025-09-04.json`
- `day_238_2025-09-05.json`
- `day_239_2025-09-05.json`
- `day_239_2025-09-08.json`
- `day_23_2024-10-23.json`
- `day_23_2024-10-24.json`
- `day_23_2025-07-23.json`
- `day_23_2025-10-10.json`
- `day_23_2026-01-16.json`
- `day_23_2026-02-27.json`
- `day_23_2026-03-02.json`
- `day_23_2026-03-04.json`
- `day_240_2025-09-08.json`
- `day_240_2025-09-09.json`
- `day_241_2025-09-09.json`
- `day_241_2025-09-10.json`
- `day_242_2025-09-10.json`
- `day_242_2025-09-11.json`
- `day_243_2025-09-11.json`
- `day_243_2025-09-12.json`
- `day_244_2025-09-12.json`
- `day_244_2025-09-15.json`
- `day_245_2025-09-15.json`
- `day_245_2025-09-16.json`
- `day_246_2025-09-16.json`
- `day_246_2025-09-17.json`
- `day_247_2025-09-17.json`
- `day_247_2025-09-18.json`
- `day_248_2025-09-18.json`
- `day_248_2025-09-19.json`
- `day_249_2025-09-19.json`
- `day_249_2025-09-22.json`
- `day_24_2024-10-24.json`
- `day_24_2024-10-25.json`
- `day_24_2025-07-24.json`
- `day_24_2025-10-13.json`
- `day_24_2026-01-19.json`
- `day_24_2026-03-02.json`
- `day_24_2026-03-04.json`
- `day_24_2026-03-05.json`
- `day_250_2025-09-22.json`
- `day_250_2025-09-23.json`
- `day_251_2025-09-23.json`
- `day_251_2025-09-24.json`
- `day_252_2025-09-24.json`
- `day_252_2025-09-25.json`
- `day_253_2025-09-25.json`
- `day_253_2025-09-26.json`
- `day_254_2025-09-26.json`
- `day_254_2025-09-29.json`
- `day_255_2025-09-29.json`
- `day_255_2025-09-30.json`
- `day_256_2025-09-30.json`
- `day_256_2025-10-01.json`
- `day_257_2025-10-01.json`
- `day_257_2025-10-03.json`
- `day_258_2025-10-03.json`
- `day_258_2025-10-06.json`
- `day_259_2025-10-06.json`
- `day_259_2025-10-07.json`
- `day_25_2024-10-25.json`
- `day_25_2024-10-28.json`
- `day_25_2025-07-25.json`
- `day_25_2025-10-14.json`
- `day_25_2026-01-20.json`
- `day_25_2026-03-04.json`
- `day_25_2026-03-05.json`
- `day_25_2026-03-06.json`
- `day_260_2025-10-07.json`
- `day_260_2025-10-08.json`
- `day_261_2025-10-08.json`
- `day_261_2025-10-09.json`
- `day_262_2025-10-09.json`
- `day_262_2025-10-10.json`
- `day_263_2025-10-10.json`
- `day_263_2025-10-13.json`
- `day_264_2025-10-13.json`
- `day_264_2025-10-14.json`
- `day_265_2025-10-14.json`
- `day_265_2025-10-15.json`
- `day_266_2025-10-15.json`
- `day_266_2025-10-16.json`
- `day_267_2025-10-16.json`
- `day_267_2025-10-17.json`
- `day_268_2025-10-17.json`
- `day_268_2025-10-20.json`
- `day_269_2025-10-20.json`
- `day_269_2025-10-21.json`
- `day_26_2024-10-28.json`
- `day_26_2024-10-29.json`
- `day_26_2025-07-28.json`
- `day_26_2025-10-15.json`
- `day_26_2026-01-21.json`
- `day_26_2026-03-05.json`
- `day_26_2026-03-06.json`
- `day_26_2026-03-09.json`
- `day_270_2025-10-21.json`
- `day_270_2025-10-23.json`
- `day_271_2025-10-23.json`
- `day_271_2025-10-24.json`
- `day_272_2025-10-24.json`
- `day_272_2025-10-27.json`
- `day_273_2025-10-27.json`
- `day_273_2025-10-28.json`
- `day_274_2025-10-28.json`
- `day_274_2025-10-29.json`
- `day_275_2025-10-29.json`
- `day_275_2025-10-30.json`
- `day_276_2025-10-30.json`
- `day_276_2025-10-31.json`
- `day_277_2025-10-31.json`
- `day_277_2025-11-03.json`
- `day_278_2025-11-03.json`
- `day_278_2025-11-04.json`
- `day_279_2025-11-04.json`
- `day_279_2025-11-06.json`
- `day_27_2024-10-29.json`
- `day_27_2024-10-30.json`
- `day_27_2025-07-29.json`
- `day_27_2025-10-16.json`
- `day_27_2026-01-22.json`
- `day_27_2026-03-06.json`
- `day_27_2026-03-09.json`
- `day_27_2026-03-10.json`
- `day_280_2025-11-06.json`
- `day_280_2025-11-07.json`
- `day_281_2025-11-07.json`
- `day_281_2025-11-10.json`
- `day_282_2025-11-10.json`
- `day_282_2025-11-11.json`
- `day_283_2025-11-11.json`
- `day_283_2025-11-12.json`
- `day_284_2025-11-12.json`
- `day_284_2025-11-13.json`
- `day_285_2025-11-13.json`
- `day_285_2025-11-14.json`
- `day_286_2025-11-14.json`
- `day_286_2025-11-17.json`
- `day_287_2025-11-17.json`
- `day_287_2025-11-18.json`
- `day_288_2025-11-18.json`
- `day_288_2025-11-19.json`
- `day_289_2025-11-19.json`
- `day_289_2025-11-20.json`
- `day_28_2024-10-30.json`
- `day_28_2024-10-31.json`
- `day_28_2025-07-30.json`
- `day_28_2025-10-17.json`
- `day_28_2026-01-23.json`
- `day_28_2026-03-09.json`
- `day_28_2026-03-10.json`
- `day_28_2026-03-11.json`
- `day_290_2025-11-20.json`
- `day_290_2025-11-21.json`
- `day_291_2025-11-21.json`
- `day_291_2025-11-24.json`
- `day_292_2025-11-24.json`
- `day_292_2025-11-25.json`
- `day_293_2025-11-25.json`
- `day_293_2025-11-26.json`
- `day_294_2025-11-26.json`
- `day_294_2025-11-27.json`
- `day_295_2025-11-27.json`
- `day_295_2025-11-28.json`
- `day_296_2025-11-28.json`
- `day_296_2025-12-01.json`
- `day_297_2025-12-01.json`
- `day_297_2025-12-02.json`
- `day_298_2025-12-02.json`
- `day_298_2025-12-03.json`
- `day_299_2025-12-03.json`
- `day_299_2025-12-04.json`
- `day_29_2024-10-31.json`
- `day_29_2024-11-01.json`
- `day_29_2025-07-31.json`
- `day_29_2025-10-20.json`
- `day_29_2026-01-27.json`
- `day_29_2026-03-10.json`
- `day_29_2026-03-11.json`
- `day_29_2026-03-12.json`
- `day_300_2025-12-04.json`
- `day_300_2025-12-05.json`
- `day_301_2025-12-05.json`
- `day_301_2025-12-08.json`
- `day_302_2025-12-08.json`
- `day_302_2025-12-09.json`
- `day_303_2025-12-09.json`
- `day_303_2025-12-10.json`
- `day_304_2025-12-10.json`
- `day_304_2025-12-11.json`
- `day_305_2025-12-11.json`
- `day_305_2025-12-12.json`
- `day_306_2025-12-12.json`
- `day_306_2025-12-15.json`
- `day_307_2025-12-15.json`
- `day_307_2025-12-16.json`
- `day_308_2025-12-16.json`
- `day_308_2025-12-17.json`
- `day_309_2025-12-17.json`
- `day_309_2025-12-18.json`
- `day_30_2024-11-01.json`
- `day_30_2024-11-04.json`
- `day_30_2025-08-01.json`
- `day_30_2025-10-21.json`
- `day_30_2026-01-28.json`
- `day_30_2026-03-11.json`
- `day_30_2026-03-12.json`
- `day_30_2026-03-13.json`
- `day_310_2025-12-18.json`
- `day_310_2025-12-19.json`
- `day_311_2025-12-19.json`
- `day_311_2025-12-22.json`
- `day_312_2025-12-22.json`
- `day_312_2025-12-23.json`
- `day_313_2025-12-23.json`
- `day_313_2025-12-24.json`
- `day_314_2025-12-24.json`
- `day_314_2025-12-26.json`
- `day_315_2025-12-26.json`
- `day_315_2025-12-29.json`
- `day_316_2025-12-29.json`
- `day_316_2025-12-30.json`
- `day_317_2025-12-30.json`
- `day_317_2025-12-31.json`
- `day_318_2025-12-31.json`
- `day_318_2026-01-01.json`
- `day_319_2026-01-01.json`
- `day_319_2026-01-02.json`
- `day_31_2024-11-04.json`
- `day_31_2024-11-05.json`
- `day_31_2025-08-04.json`
- `day_31_2025-10-23.json`
- `day_31_2026-01-29.json`
- `day_320_2026-01-02.json`
- `day_320_2026-01-05.json`
- `day_321_2026-01-05.json`
- `day_321_2026-01-06.json`
- `day_322_2026-01-06.json`
- `day_322_2026-01-07.json`
- `day_323_2026-01-07.json`
- `day_323_2026-01-08.json`
- `day_324_2026-01-08.json`
- `day_324_2026-01-09.json`
- `day_325_2026-01-09.json`
- `day_325_2026-01-12.json`
- `day_326_2026-01-12.json`
- `day_326_2026-01-13.json`
- `day_327_2026-01-13.json`
- `day_327_2026-01-14.json`
- `day_328_2026-01-14.json`
- `day_328_2026-01-16.json`
- `day_329_2026-01-16.json`
- `day_329_2026-01-19.json`
- `day_32_2024-11-05.json`
- `day_32_2024-11-06.json`
- `day_32_2025-08-05.json`
- `day_32_2025-10-24.json`
- `day_32_2026-01-30.json`
- `day_330_2026-01-19.json`
- `day_330_2026-01-20.json`
- `day_331_2026-01-20.json`
- `day_331_2026-01-21.json`
- `day_332_2026-01-21.json`
- `day_332_2026-01-22.json`
- `day_333_2026-01-22.json`
- `day_333_2026-01-23.json`
- `day_334_2026-01-23.json`
- `day_334_2026-01-27.json`
- `day_335_2026-01-27.json`
- `day_335_2026-01-28.json`
- `day_336_2026-01-28.json`
- `day_336_2026-01-29.json`
- `day_337_2026-01-29.json`
- `day_337_2026-01-30.json`
- `day_338_2026-01-30.json`
- `day_338_2026-02-02.json`
- `day_339_2026-02-02.json`
- `day_339_2026-02-03.json`
- `day_33_2024-11-06.json`
- `day_33_2024-11-07.json`
- `day_33_2025-08-06.json`
- `day_33_2025-10-27.json`
- `day_33_2026-02-02.json`
- `day_340_2026-02-03.json`
- `day_340_2026-02-04.json`
- `day_341_2026-02-04.json`
- `day_341_2026-02-05.json`
- `day_342_2026-02-05.json`
- `day_342_2026-02-06.json`
- `day_343_2026-02-06.json`
- `day_343_2026-02-09.json`
- `day_344_2026-02-09.json`
- `day_344_2026-02-10.json`
- `day_345_2026-02-10.json`
- `day_345_2026-02-11.json`
- `day_346_2026-02-11.json`
- `day_346_2026-02-12.json`
- `day_347_2026-02-12.json`
- `day_347_2026-02-13.json`
- `day_348_2026-02-13.json`
- `day_348_2026-02-16.json`
- `day_349_2026-02-16.json`
- `day_349_2026-02-17.json`
- `day_34_2024-11-07.json`
- `day_34_2024-11-08.json`
- `day_34_2025-08-07.json`
- `day_34_2025-10-28.json`
- `day_34_2026-02-03.json`
- `day_350_2026-02-17.json`
- `day_350_2026-02-18.json`
- `day_351_2026-02-18.json`
- `day_351_2026-02-19.json`
- `day_352_2026-02-19.json`
- `day_352_2026-02-20.json`
- `day_353_2026-02-20.json`
- `day_353_2026-02-23.json`
- `day_354_2026-02-23.json`
- `day_354_2026-02-24.json`
- `day_355_2026-02-24.json`
- `day_355_2026-02-25.json`
- `day_356_2026-02-25.json`
- `day_356_2026-02-26.json`
- `day_357_2026-02-26.json`
- `day_357_2026-02-27.json`
- `day_358_2026-02-27.json`
- `day_358_2026-03-02.json`
- `day_359_2026-03-02.json`
- `day_359_2026-03-04.json`
- `day_35_2024-11-08.json`
- `day_35_2024-11-11.json`
- `day_35_2025-08-08.json`
- `day_35_2025-10-29.json`
- `day_35_2026-02-04.json`
- `day_360_2026-03-04.json`
- `day_360_2026-03-05.json`
- `day_361_2026-03-05.json`
- `day_361_2026-03-06.json`
- `day_362_2026-03-06.json`
- `day_362_2026-03-09.json`
- `day_363_2026-03-09.json`
- `day_363_2026-03-10.json`
- `day_364_2026-03-10.json`
- `day_364_2026-03-11.json`
- `day_365_2026-03-11.json`
- `day_365_2026-03-12.json`
- `day_36_2024-11-11.json`
- `day_36_2024-11-12.json`
- `day_36_2025-08-11.json`
- `day_36_2025-10-30.json`
- `day_36_2026-02-05.json`
- `day_37_2024-11-12.json`
- `day_37_2024-11-13.json`
- `day_37_2025-08-12.json`
- `day_37_2025-10-31.json`
- `day_37_2026-02-06.json`
- `day_38_2024-11-13.json`
- `day_38_2024-11-14.json`
- `day_38_2025-08-13.json`
- `day_38_2025-11-03.json`
- `day_38_2026-02-09.json`
- `day_39_2024-11-14.json`
- `day_39_2024-11-18.json`
- `day_39_2025-08-14.json`
- `day_39_2025-11-04.json`
- `day_39_2026-02-10.json`
- `day_40_2024-11-18.json`
- `day_40_2024-11-19.json`
- `day_40_2025-08-18.json`
- `day_40_2025-11-06.json`
- `day_40_2026-02-11.json`
- `day_41_2024-11-19.json`
- `day_41_2024-11-21.json`
- `day_41_2025-08-19.json`
- `day_41_2025-11-07.json`
- `day_41_2026-02-12.json`
- `day_42_2024-11-21.json`
- `day_42_2024-11-22.json`
- `day_42_2025-08-20.json`
- `day_42_2025-11-10.json`
- `day_42_2026-02-13.json`
- `day_43_2024-11-22.json`
- `day_43_2024-11-25.json`
- `day_43_2025-08-21.json`
- `day_43_2025-11-11.json`
- `day_43_2026-02-16.json`
- `day_44_2024-11-25.json`
- `day_44_2024-11-26.json`
- `day_44_2025-08-22.json`
- `day_44_2025-11-12.json`
- `day_44_2026-02-17.json`
- `day_45_2024-11-26.json`
- `day_45_2024-11-27.json`
- `day_45_2025-08-25.json`
- `day_45_2025-11-13.json`
- `day_45_2026-02-18.json`
- `day_46_2024-11-27.json`
- `day_46_2024-11-28.json`
- `day_46_2025-08-26.json`
- `day_46_2025-11-14.json`
- `day_46_2026-02-19.json`
- `day_47_2024-11-28.json`
- `day_47_2024-11-29.json`
- `day_47_2025-08-28.json`
- `day_47_2025-11-17.json`
- `day_47_2026-02-20.json`
- `day_48_2024-11-29.json`
- `day_48_2024-12-02.json`
- `day_48_2025-08-29.json`
- `day_48_2025-11-18.json`
- `day_48_2026-02-23.json`
- `day_49_2024-12-02.json`
- `day_49_2024-12-03.json`
- `day_49_2025-09-01.json`
- `day_49_2025-11-19.json`
- `day_49_2026-02-24.json`
- `day_50_2024-12-03.json`
- `day_50_2024-12-04.json`
- `day_50_2025-09-02.json`
- `day_50_2025-11-20.json`
- `day_50_2026-02-25.json`
- `day_51_2024-12-04.json`
- `day_51_2024-12-05.json`
- `day_51_2025-09-03.json`
- `day_51_2025-11-21.json`
- `day_51_2026-02-26.json`
- `day_52_2024-12-05.json`
- `day_52_2024-12-06.json`
- `day_52_2025-09-04.json`
- `day_52_2025-11-24.json`
- `day_52_2026-02-27.json`
- `day_53_2024-12-06.json`
- `day_53_2024-12-09.json`
- `day_53_2025-09-05.json`
- `day_53_2025-11-25.json`
- `day_53_2026-03-02.json`
- `day_54_2024-12-09.json`
- `day_54_2024-12-10.json`
- `day_54_2025-09-08.json`
- `day_54_2025-11-26.json`
- `day_54_2026-03-04.json`
- `day_55_2024-12-10.json`
- `day_55_2024-12-11.json`
- `day_55_2025-09-09.json`
- `day_55_2025-11-27.json`
- `day_55_2026-03-05.json`
- `day_56_2024-12-11.json`
- `day_56_2024-12-12.json`
- `day_56_2025-09-10.json`
- `day_56_2025-11-28.json`
- `day_56_2026-03-06.json`
- `day_57_2024-12-12.json`
- `day_57_2024-12-13.json`
- `day_57_2025-09-11.json`
- `day_57_2025-12-01.json`
- `day_57_2026-03-09.json`
- `day_58_2024-12-13.json`
- `day_58_2024-12-16.json`
- `day_58_2025-09-12.json`
- `day_58_2025-12-02.json`
- `day_58_2026-03-10.json`
- `day_59_2024-12-16.json`
- `day_59_2024-12-17.json`
- `day_59_2025-09-15.json`
- `day_59_2025-12-03.json`
- `day_59_2026-03-11.json`
- `day_60_2024-12-17.json`
- `day_60_2024-12-18.json`
- `day_60_2025-09-16.json`
- `day_60_2025-12-04.json`
- `day_60_2026-03-12.json`
- `day_61_2024-12-18.json`
- `day_61_2024-12-19.json`
- `day_61_2025-09-17.json`
- `day_61_2025-12-05.json`
- `day_62_2024-12-19.json`
- `day_62_2024-12-20.json`
- `day_62_2025-09-18.json`
- `day_62_2025-12-08.json`
- `day_63_2024-12-20.json`
- `day_63_2024-12-23.json`
- `day_63_2025-09-19.json`
- `day_63_2025-12-09.json`
- `day_64_2024-12-23.json`
- `day_64_2024-12-24.json`
- `day_64_2025-09-22.json`
- `day_64_2025-12-10.json`
- `day_65_2024-12-24.json`
- `day_65_2024-12-26.json`
- `day_65_2025-09-23.json`
- `day_65_2025-12-11.json`
- `day_66_2024-12-26.json`
- `day_66_2024-12-27.json`
- `day_66_2025-09-24.json`
- `day_66_2025-12-12.json`
- `day_67_2024-12-27.json`
- `day_67_2024-12-30.json`
- `day_67_2025-09-25.json`
- `day_67_2025-12-15.json`
- `day_68_2024-12-30.json`
- `day_68_2024-12-31.json`
- `day_68_2025-09-26.json`
- `day_68_2025-12-16.json`
- `day_69_2024-12-31.json`
- `day_69_2025-01-01.json`
- `day_69_2025-09-29.json`
- `day_69_2025-12-17.json`
- `day_70_2025-01-01.json`
- `day_70_2025-01-02.json`
- `day_70_2025-09-30.json`
- `day_70_2025-12-18.json`
- `day_71_2025-01-02.json`
- `day_71_2025-01-03.json`
- `day_71_2025-10-01.json`
- `day_71_2025-12-19.json`
- `day_72_2025-01-03.json`
- `day_72_2025-01-06.json`
- `day_72_2025-10-03.json`
- `day_72_2025-12-22.json`
- `day_73_2025-01-06.json`
- `day_73_2025-01-07.json`
- `day_73_2025-10-06.json`
- `day_73_2025-12-23.json`
- `day_74_2025-01-07.json`
- `day_74_2025-01-08.json`
- `day_74_2025-10-07.json`
- `day_74_2025-12-24.json`
- `day_75_2025-01-08.json`
- `day_75_2025-01-09.json`
- `day_75_2025-10-08.json`
- `day_75_2025-12-26.json`
- `day_76_2025-01-09.json`
- `day_76_2025-01-10.json`
- `day_76_2025-10-09.json`
- `day_76_2025-12-29.json`
- `day_77_2025-01-10.json`
- `day_77_2025-01-13.json`
- `day_77_2025-10-10.json`
- `day_77_2025-12-30.json`
- `day_78_2025-01-13.json`
- `day_78_2025-01-14.json`
- `day_78_2025-10-13.json`
- `day_78_2025-12-31.json`
- `day_79_2025-01-14.json`
- `day_79_2025-01-15.json`
- `day_79_2025-10-14.json`
- `day_79_2026-01-01.json`
- `day_80_2025-01-15.json`
- `day_80_2025-01-16.json`
- `day_80_2025-10-15.json`
- `day_80_2026-01-02.json`
- `day_81_2025-01-16.json`
- `day_81_2025-01-17.json`
- `day_81_2025-10-16.json`
- `day_81_2026-01-05.json`
- `day_82_2025-01-17.json`
- `day_82_2025-01-20.json`
- `day_82_2025-10-17.json`
- `day_82_2026-01-06.json`
- `day_83_2025-01-20.json`
- `day_83_2025-01-21.json`
- `day_83_2025-10-20.json`
- `day_83_2026-01-07.json`
- `day_84_2025-01-21.json`
- `day_84_2025-01-22.json`
- `day_84_2025-10-21.json`
- `day_84_2026-01-08.json`
- `day_85_2025-01-22.json`
- `day_85_2025-01-23.json`
- `day_85_2025-10-23.json`
- `day_85_2026-01-09.json`
- `day_86_2025-01-23.json`
- `day_86_2025-01-24.json`
- `day_86_2025-10-24.json`
- `day_86_2026-01-12.json`
- `day_87_2025-01-24.json`
- `day_87_2025-01-27.json`
- `day_87_2025-10-27.json`
- `day_87_2026-01-13.json`
- `day_88_2025-01-27.json`
- `day_88_2025-01-28.json`
- `day_88_2025-10-28.json`
- `day_88_2026-01-14.json`
- `day_89_2025-01-28.json`
- `day_89_2025-01-29.json`
- `day_89_2025-10-29.json`
- `day_89_2026-01-16.json`
- `day_90_2025-01-29.json`
- `day_90_2025-01-30.json`
- `day_90_2025-10-30.json`
- `day_90_2026-01-19.json`
- `day_91_2025-01-30.json`
- `day_91_2025-01-31.json`
- `day_91_2025-10-31.json`
- `day_91_2026-01-20.json`
- `day_92_2025-01-31.json`
- `day_92_2025-02-01.json`
- `day_92_2025-11-03.json`
- `day_92_2026-01-21.json`
- `day_93_2025-02-01.json`
- `day_93_2025-02-03.json`
- `day_93_2025-11-04.json`
- `day_93_2026-01-22.json`
- `day_94_2025-02-03.json`
- `day_94_2025-02-04.json`
- `day_94_2025-11-06.json`
- `day_94_2026-01-23.json`
- `day_95_2025-02-04.json`
- `day_95_2025-02-05.json`
- `day_95_2025-11-07.json`
- `day_95_2026-01-27.json`
- `day_96_2025-02-05.json`
- `day_96_2025-02-06.json`
- `day_96_2025-11-10.json`
- `day_96_2026-01-28.json`
- `day_97_2025-02-06.json`
- `day_97_2025-02-07.json`
- `day_97_2025-11-11.json`
- `day_97_2026-01-29.json`
- `day_98_2025-02-07.json`
- `day_98_2025-02-10.json`
- `day_98_2025-11-12.json`
- `day_98_2026-01-30.json`
- `day_99_2025-02-10.json`
- `day_99_2025-02-11.json`
- `day_99_2025-11-13.json`
- `day_99_2026-02-02.json`

Each file contains a full ordered log of every EventBus event emitted during that day's cycle, from `CYCLE_STARTED` through `CYCLE_COMPLETE`, enabling step-by-step audit of every decision.

---

## Section 6 — Final Assessment

### Overall Simulation Score: 10/10

🟢 **EXCELLENT** — The system demonstrates hedge-fund-grade design, sound risk controls, and clean paper-trade execution.

### Dimension Scores

| Dimension | Score | Assessment |
|-----------|-------|------------|
| Hedge-fund design consistency | 8/10 | Low alignment — review strategy assignment ⚠ |
| Logic quality & layer integration | 10/10 | Zero pipeline errors ✅ |
| Risk control effectiveness | 10/10 | Full risk compliance ✅ |
| Paper-trade readiness | 10/10 | Ready for extended paper monitoring ✅ |

### Detailed Assessment

All four assessment dimensions score highly. The 7-day replay confirms the architecture is production-ready for extended paper trading. Recommend running a 30-day paper monitoring phase before considering live capital.

### Recommendations
4. **Tune strategy-regime mapping** — alignment at 0% (< 60% target). Review `STRATEGY_REGIME_FIT` in metrics.py and MetaStrategyController.

---
*Report generated by `simulation_replay/run_replay.py` — AI Trading Brain*
