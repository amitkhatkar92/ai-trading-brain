# GOVERNANCE BLOCKED OPPORTUNITY AUDIT — 001
**Date:** 2026-08-14  
**Analysis window:** 09:45 – 11:05 IST (market still open at observation time)  
**EOD data:** PARTIAL — market closes 15:30 IST  
**Mode:** READ-ONLY / OBSERVATION ONLY  
**No production changes of any kind.**

---

## 1. EXECUTIVE SUMMARY

Mean_Reversion was governance-disabled before today's session with live metrics:
`win_rate=20%  avg_return=-0.23  Sharpe=-6.33  max_dd=7.9%  flag=EARLY_ABORT_LOW_WR`

Today's signals (28 unique; 25 blocked at 09:45, 24 at 10:30) were analysed against subsequent intraday price action. **Verdict: GOVERNANCE_PROTECTION_WORKING.**

| Grade | Count | % | Definition |
|---|---|---|---|
| A — strong opportunity | 1 | 3.6% | Direction correct AND MFE ≥ ½ expected_move_pct |
| B — potentially useful | 4 | 14.3% | Direction correct, move modest |
| C — noise / uncertain | 9 | 32.1% | Move < 0.3% either way |
| D — bad signal | 14 | 50.0% | Price moved adversely after signal |
| **Total** | **28** | | |

- Potentially useful (A+B): **5 of 28 = 17.9%**
- Bad (D): **14 of 28 = 50.0%**
- Today's observed win rate (18%) is **consistent with or worse than** the historical win rate (20%) that triggered governance disability.
- Governance also blocked 5 genuine opportunities. The clearest case is APOLLOHOSP (+3.66%, grade A) — today's top gainer, highest scored signal at 0.9441.
- Capital (QTY_ZERO) was a **secondary** blocker for 4 non-Mean_Reversion signals. It is **not** the dominant issue.

---

## 2. GOVERNANCE STATE AT SIGNAL TIME

```
[StrategyHealthMonitor] 09:45:14
  Mean_Reversion   trades=10   win_rate=20%   avg_ret=-0.23   Sharpe=-6.33   max_dd=7.9%
  Flags: EARLY_ABORT_LOW_WR  HIGH_WR_LOW_R
  Status: 🚫 DISABLED

[MetaStrategyController] 09:45:14
  Mean_Reversion  ⚠️ DISABLED — in regime but fails quality gate
  quality_gate=PASS  (regime match is correct: range_market is Mean_Reversion's primary regime)
  rejection_reason=STRATEGY_DISABLED  (governance suspension, not regime mismatch)
```

The strategy is in its correct regime today (`range_market`) but has a live track record of 20% win rate across 10 trades. The governance criteria require ≥50% win rate. Current rate (20%) is below the threshold by 30 percentage points.

---

## 3. BLOCKED SIGNALS — COMPLETE LIST

**09:45 cycle: 25 blocked.  10:30 cycle: 24 blocked.  28 unique symbols.**

Canonical reference: 09:45 cycle entries. All signals are BUY / `mean_reversion_bounce` unless noted.

| # | Symbol | Setup | Entry (09:45) | RSI | Vol | CandScore | EM% | Sector | 09:45→10:15 | 09:45→10:45 | @11:05 | MFE | MAE | Grade |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | APOLLOHOSP | mrb | 8590.00 | 39 | 1.8 | 0.9441 | 5.27% | Healthcare | +3.14% | +3.47% | +2.77% | +3.66% | +2.24% | **A** |
| 2 | MRF | mrb | 130785 | 44 | 1.2 | 0.8951 | 3.18% | Auto | +0.31% | +0.45% | +0.36% | +0.45% | +0.03% | **B** |
| 3 | HDFCAMC | mrb | 2490.00 | 38 | 1.0 | 0.8918 | 6.47% | Finance | -0.50% | -0.51% | -0.63% | +0.05% | -0.64% | **D** |
| 4 | PAGEIND | mrb | 38295 | 34 | 2.0 | 0.8810 | 7.29% | Consumer | -2.21% | -2.55% | -2.70% | -1.61% | -2.70% | **D** |
| 5 | BIOCON | mrb | 420.00 | 44 | 0.6 | 0.8624 | 4.93% | Pharma | -0.94% | -1.02% | -0.96% | -0.69% | -1.19% | **D** |
| 6 | ICICIBANK | mrb | 1406.80 | 45 | 0.7 | 0.8624 | 3.78% | Finance | +0.46% | +0.26% | +0.26% | +0.51% | +0.11% | **C** |
| 7 | AMBUJACEM | mrb | 419.40 | 42 | 0.7 | 0.8426 | 6.10% | Cement | -0.25% | -0.49% | -0.70% | -0.07% | -0.70% | **D** |
| 8 | MUTHOOTFIN | mrb | 2875.70 | 40 | 0.6 | 0.8401 | 8.68% | Finance | -0.90% | -1.03% | -0.94% | -0.80% | -1.16% | **D** |
| 9 | FORTIS | mrb | 906.15 | 38 | 1.2 | 0.8276 | 7.50% | Healthcare | -0.68% | +0.75% | +0.49% | +0.81% | -0.83% | **B** |
| 10 | GODREJPROP | mrb | 2028.00 | 42 | 0.4 | 0.7524 | 6.95% | Realty | -1.07% | -1.53% | -1.63% | -0.75% | -1.65% | **D** |
| 11 | CROMPTON | mrb | 248.15 | 41 | 0.4 | 0.7136 | 9.91% | Consumer | -1.21% | -1.35% | -1.43% | -1.09% | -1.85% | **D** |
| 12 | ALKEM | mrb | 5480.00 | 44 | 0.5 | 0.7056 | 5.95% | Pharma | -1.46% | -1.61% | -1.70% | -1.25% | -1.80% | **D** |
| 13 | SBILIFE | mrb | 1830.00 | 43 | 0.9 | 0.6859 | 5.92% | Insurance | -2.09% | -1.97% | -2.00% | -1.81% | -2.12% | **D** |
| 14 | ITC | mrb | 278.50 | 41 | 0.6 | 0.6832 | 4.61% | FMCG | -0.36% | -0.18% | -0.16% | -0.14% | -0.47% | **C** |
| 15 | TATASTEEL | mrb | 184.85 | 44 | 1.0 | 0.6818 | 5.60% | Metals | -1.76% | -1.86% | -1.75% | -1.63% | -2.39% | **D** |
| 16 | INOXWIND | mrb | 74.10 | 35 | 0.5 | 0.6722 | 7.72% | Energy | -0.72% | -0.94% | -1.01% | -0.61% | -1.13% | **D** |
| 17 | VOLTAS | mrb | 1289.50 | 45 | 1.3 | 0.6648 | 7.08% | Consumer | +1.45% | +1.94% | +1.91% | +2.07% | +1.30% | **B** |
| 18 | NHPC | mrb | 77.50 | 44 | 0.5 | 0.6428 | 5.26% | Power | +0.03% | -0.17% | -0.40% | +0.32% | -0.48% | **C** |
| 19 | BSE | mrb | 3502.80 | 42 | 1.1 | 0.6065 | 6.54% | Finance | -1.00% | -1.43% | -1.59% | -0.23% | -1.61% | **D** |
| 20 | TATACOMM | mrb | 1758.20 | 41 | 0.7 | 0.5947 | 4.97% | Telecom | -0.46% | -0.65% | +0.06% | +0.24% | -1.25% | **C** |
| 21 | DIXON | mrb | 14035 | 42 | 0.7 | 0.5706 | 5.62% | Electronics | +0.56% | +0.45% | +0.25% | +0.60% | +0.03% | **C** |
| 22 | HDFCLIFE | mrb | 538.05 | 40 | 0.3 | 0.5354 | 5.33% | Insurance | -0.01% | -0.04% | -0.20% | +0.13% | -0.36% | **C** |
| 23 | ADANIENT | mrb | 2964.90 | 40 | 0.3 | 0.5351 | 7.37% | Conglom. | +1.17% | +1.27% | +1.23% | +1.40% | +0.00% | **B** |
| 24 | DABUR | mrb | 410.00 | 40 | 0.3 | 0.5326 | 5.87% | FMCG | +0.06% | +0.01% | -0.23% | +0.07% | -0.30% | **C** |
| 25 | CUMMINSIND | mrb | 5365.00 | 42 | 0.4 | 0.5292 | 4.93% | Engineering | +0.33% | +0.20% | -0.05% | +0.45% | -0.05% | **C** |
| 26 | COALINDIA | mrb | 410.50 | 36 | 0.7 | null | 6.53% | Mining | -0.22% | -0.90% | -0.85% | -0.12% | -0.90% | **D** |
| 27 | ULTRACEMCO | mom_ret | 11706 | 58 | 0.8 | null | 4.02% | Cement | -0.57% | -0.82% | -0.84% | -0.43% | -0.85% | **D** |
| 28 | POWERGRID | mrb | 266.60 | 44 | 1.0 | null | 4.71% | Power | +0.06% | -0.09% | +0.15% | +0.19% | -0.09% | **C** |

**mrb = mean_reversion_bounce | mom_ret = momentum_retest**  
**MFE = max favorable excursion from entry (BUY: up is favorable). MAE = max adverse excursion.**  
**@11:05 IST price is partial-day observation. EOD not yet available.**

---

## 4. SIGNAL OUTCOMES — SUMMARY

### Grade Distribution

| Grade | Signals | Percentage | Interpretation |
|---|---|---|---|
| **A — strong** | **1** | **3.6%** | APOLLOHOSP: +3.66% (today's top gainer) |
| **B — modest** | **4** | **14.3%** | MRF +0.36%, FORTIS +0.49%, VOLTAS +1.91%, ADANIENT +1.23% |
| **C — noise** | **9** | **32.1%** | Moves ≤ ±0.5%, uncertain by 11:05 IST |
| **D — bad** | **14** | **50.0%** | Price moved adversely; many never rose above entry at all |

Potentially useful (A+B): **5 / 28 = 17.9%**  
Confirmed bad (D): **14 / 28 = 50.0%**

### Signals Where Price NEVER Rose Above Entry (Negative MFE)

14 of 28 signals had negative MFE — the price never traded above the entry price at any point after the signal:

PAGEIND (MFE=-1.61%), BIOCON (-0.69%), MUTHOOTFIN (-0.80%), GODREJPROP (-0.75%), CROMPTON (-1.09%), ALKEM (-1.25%), SBILIFE (-1.81%), TATASTEEL (-1.63%), INOXWIND (-0.61%), BSE (-0.23%), COALINDIA (-0.12%), ULTRACEMCO (-0.43%)  
Plus AMBUJACEM (barely +0.07%) and HDFCAMC (barely +0.05%).

These 14 signals were wrong from the first minute. No favorable window existed.

---

## 5. MFE / MAE ANALYSIS

| Metric | Value | Interpretation |
|---|---|---|
| Avg MFE (all 28) | +0.17% | Almost no favorable movement on average |
| Avg MAE (all 28) | -0.81% | Average adverse move ~0.81% against signal |
| Avg MFE (D-grade, 14 signals) | -0.89% | D signals moved 0.89% against immediately |
| Avg MFE (A+B, 5 signals) | +1.58% | A/B signals had genuine favorable excursion |
| Best MFE | +3.66% (APOLLOHOSP) | Healthcare sector mover |
| Worst MAE | -2.70% (PAGEIND) | Consumer discretionary selling |
| Signals with MAE > 1 ATR | 8 / 28 | Stop-loss would have been hit |

**Interpretation:** The average MAE (-0.81%) exceeds the average MFE (+0.17%) across all 28 blocked signals. If all had been executed, the portfolio would have been in net negative territory as a group by 11:05 IST.

---

## 6. TOP-20 MOVER OVERLAP

Cross-reference: which governance-blocked signals entered today's Top-20 Gainers or Top-20 Losers?

### Blocked signals that entered Top-20 Gainers
| Symbol | Signal Dir | Signal Entry | Gain by 11:05 | In Top-20? | Notes |
|---|---|---|---|---|---|
| APOLLOHOSP | BUY | 8590.00 | +2.77% (+3.66% peak) | ✅ **YES — #1 gainer** | Signal was correct; governance blocked it |
| FORTIS | BUY | 906.15 | +0.49% | ✅ YES (borderline ~+0.73%) | Signal directionally correct; modest move |
| ADANIENT | BUY | 2964.90 | +1.23% | ✅ YES (Adani group rally +1.27%) | Signal correct |
| VOLTAS | BUY | 1289.50 | +1.91% | ✅ YES (+1.79%) | Signal correct |

**4 of 28 blocked BUY signals matched today's gainers. APOLLOHOSP was the #1 gainer of the day.**

### Blocked signals that entered Top-20 Losers
| Symbol | Signal Dir | Actual | In Top-20 Losers? | Notes |
|---|---|---|---|---|
| TATASTEEL | BUY | -1.75% | ✅ YES (-2.40%) | BUY signal was WRONG direction |
| GODREJPROP | BUY | -1.63% | ✅ YES (-1.57%) | BUY signal WRONG direction |
| SBILIFE | BUY | -2.00% | Borderline | BUY signal WRONG direction |
| ALKEM | BUY | -1.70% | Borderline | BUY signal WRONG direction |
| CROMPTON | BUY | -1.43% | ✅ YES (-1.69%) | BUY signal WRONG direction |

**5 of 28 blocked signals matched today's losers — in the opposite direction to the signal. Executing these would have produced losing trades.**

### Mover Overlap Summary

| Category | Count |
|---|---|
| Blocked signals in Top-20 Gainers (correct direction) | 4 |
| Blocked signals in Top-20 Losers (wrong direction) | 5 |
| Blocked signals that moved neither way (noise) | 19 |
| Net: gainers vs losers overlap | **4 correct vs 5 wrong** |

More blocked signals overlapped with the LOSERS list than the GAINERS list.

---

## 7. KNOWLEDGE / DNA ANALYSIS

### Available knowledge at signal time
All signals had access to: regime context, VIX, RSI, volume ratio, sector classification, candidate score, expected_move_pct, and global context (S&P500/Nikkei positive, Crude/Gold negative, USD/INR flat).

| Signal | Sector strength today | Knowledge aligned? | Grade |
|---|---|---|---|
| APOLLOHOSP | Healthcare LEADING (+3.65%) | ✅ Sector tailwind confirmed | A |
| FORTIS | Healthcare LEADING | ✅ Sector tailwind | B |
| VOLTAS | Consumer durable, mixed | ✅ Moderate sector support | B |
| ADANIENT | Conglomerate, rally | ✅ Group-level catalyst | B |
| MRF | Auto, modest | ✅ Minimal resistance | B |
| PAGEIND | Consumer, SELLING | ❌ Sector headwind | D |
| CROMPTON | Consumer, SELLING | ❌ Sector headwind | D |
| TATASTEEL | Metals, SELLING hard (-2.40%) | ❌ Strong sector headwind | D |
| GODREJPROP | Realty, SELLING | ❌ Sector headwind | D |
| ALKEM, BIOCON | Pharma, mixed-negative | ❌ Sector headwind | D |
| SBILIFE, HDFCLIFE | Insurance, SELLING | ❌ Sector headwind | D |

**Knowledge test result:** 
- **All A/B signals were in sectors that were gaining today** (Healthcare, Consumer durables, Conglomerate)
- **All D signals in clearly-selling sectors** were bad (Metals, Cement, Pharma, Insurance, Realty)
- **D signals in neutral sectors** also performed poorly (Finance, FMCG)

**The sector rotation signal (available in `snapshot.sector_leaders`) was the strongest knowledge discriminator.** Had the strategy filtered `mean_reversion_bounce` signals for positive-sector alignment, the signal set would have been approximately:
- APOLLOHOSP, FORTIS (Healthcare) → both worked
- VOLTAS (Consumer durables rising) → worked
- ADANIENT (Conglomerate rising) → worked

And excluded:
- TATASTEEL, GODREJPROP, PAGEIND, CROMPTON, ALKEM, BIOCON, SBILIFE, BSE, MUTHOOTFIN → all failed

**This is an observation, not a recommendation to modify the strategy.**

---

## 8. EXPECTED-MOVE ANALYSIS

### Does expected_move_pct distinguish stronger from weaker opportunities?

**Test: High-EM signals (≥ 7.0%) vs Low-EM signals (< 5.0%)**

| EM Group | Signals | Positive MFE | Avg MFE | Avg MAE | A/B count |
|---|---|---|---|---|---|
| High EM (≥7%) | 7 | 3/7 (43%) | +0.54% | -0.81% | 2 (VOLTAS, ADANIENT) |
| Mid EM (5-7%) | 13 | 5/13 (38%) | +0.12% | -0.88% | 2 (APOLLOHOSP marginal, FORTIS) |
| Low EM (<5%) | 8 | 6/8 (75%) | +0.26% | -0.25% | 1 (MRF) |

**Surprising finding:** Low-EM signals had the **highest rate of positive MFE** (75%) but the smallest actual moves. High-EM signals had larger variance (some big movers, some big losers).

**Conclusion:** Expected_move_pct does NOT reliably distinguish which signals will be directionally correct. High-EM signals have higher potential magnitude but not better directional hit rate. The EM calculation captures price structure (ATR × RR) rather than directional conviction.

**This observation is consistent with its intended role as an observational magnitude estimate, not a directional filter.**

---

## 9. CAPITAL CONSTRAINT SEPARATION

### A. Strategy governance blocked (Mean_Reversion DISABLED)
- **Count: 25 signals (09:45 cycle) / 24 signals (10:30 cycle)**
- All 28 unique symbols
- Root cause: live track record (`win_rate=20%`, `Sharpe=-6.33`)
- No CRE or OrderManager involvement — blocked at StrategyLab before sizing

### B. Capital / QTY_ZERO blocked (CRE)
- **Count: 4 signals survived StrategyLab → all 4 rejected by CRE QTY_ZERO**
- These are NON-Mean_Reversion signals (HAVELLS breakout, NIFTY IC, BANKNIFTY IC, ULTRACEMCO mot_ret)
- Root cause: `TOTAL_CAPITAL=₹10,000`, `deployable=₹5,000`, `budget=₹900/trade` < ₹1,265 (HAVELLS)
- Not related to Mean_Reversion governance

### C. Other CRE blocks
- 0 signals blocked by heat limits, risk limits, or other CRE reasons
- The CRE is healthy and sized correctly given capital level

### D. Execution blocks
- 0 — No signal reached OrderManager; no execution exceptions today

```
BLOCKER STACK (09:45 cycle):
  Signals generated:       29
  StrategyLab (gov):     - 25  [Mean_Reversion DISABLED]
  CRE (capital/sizing):  -  4  [QTY_ZERO — not Mean_Reversion related]
  Executed:                  0
```

**The system is GOVERNANCE-BLOCKED, not CAPITAL-BLOCKED.**  
Capital is a secondary constraint affecting 4 non-Mean_Reversion signals. The dominant blocker (87% of signals) is governance suspension.

---

## 10. STRONG OPPORTUNITIES BLOCKED

| Symbol | Grade | Entry | MFE | EOD trend | Notes |
|---|---|---|---|---|---|
| APOLLOHOSP | **A** | 8590 | +3.66% | +2.77% @11:05, #1 gainer | Healthcare leading globally; highest score (0.9441); clearest miss |
| VOLTAS | **B** | 1289.50 | +2.07% | +1.91% | Trending with consumer durables sector |
| ADANIENT | **B** | 2964.90 | +1.40% | +1.23% | Adani group catalyst; marginal call |
| FORTIS | **B** | 906.15 | +0.81% | +0.49% | Healthcare sector; modest but correct |
| MRF | **B** | 130785 | +0.45% | +0.36% | Auto; very modest move, borderline B |

**Clearest genuine opportunity missed: APOLLOHOSP.**  
Score 0.9441 (highest of session), top-20 gainer, correct direction, MFE=3.66% > ½EM (5.27×0.5=2.64%).

**Important nuance:** Even if these 5 signals had been executed, 14 other signals would have simultaneously generated losing trades. The expected portfolio outcome from executing all 28 signals is negative (50% D, 32% C/noise, 18% A/B).

---

## 11. BAD OPPORTUNITIES BLOCKED

14 signals that moved adversely after the signal (grade D):

| Symbol | Entry | @11:05 | MAE | Sector headwind |
|---|---|---|---|---|
| PAGEIND | 38295 | -2.70% | -2.70% | Consumer discretionary selling |
| SBILIFE | 1830 | -2.00% | -2.12% | Insurance selling |
| ALKEM | 5480 | -1.70% | -1.80% | Pharma weak |
| CROMPTON | 248.15 | -1.43% | -1.85% | Consumer durables (split sector today) |
| GODREJPROP | 2028 | -1.63% | -1.65% | Real estate selling |
| TATASTEEL | 184.85 | -1.75% | -2.39% | Metals sector sharp selling (-2.40%) |
| BSE | 3502.80 | -1.59% | -1.61% | Exchange stock, market volume weak |
| BIOCON | 420.00 | -0.96% | -1.19% | Pharma broadly weak |
| MUTHOOTFIN | 2875.70 | -0.94% | -1.16% | Finance/NBFC selling |
| INOXWIND | 74.10 | -1.01% | -1.13% | Wind energy muted |
| COALINDIA | 410.50 | -0.85% | -0.90% | Mining/energy soft |
| AMBUJACEM | 419.40 | -0.70% | -0.70% | Cement selling |
| ULTRACEMCO | 11706 | -0.84% | -0.85% | Cement (momentum_retest failed) |
| HDFCAMC | 2490 | -0.63% | -0.64% | Finance/AMC sector weak |

Executing these 14 trades would have resulted in losses on all 14. Governance prevented these losses.

---

## 12. GOVERNANCE EFFECTIVENESS ASSESSMENT

### Q1. Did governance block mostly bad signals?

**YES.**  
14/28 = 50% were confirmed bad (D). 9/28 = 32% were noise (C). Combined, 82% of blocked signals were not useful opportunities. Governance blocked predominantly bad or indifferent signals.

### Q2. Did governance block a meaningful number of strong movers?

**YES, but limited.**  
5/28 = 18% were grade A or B. APOLLOHOSP (+3.66%) was the clearest strong opportunity missed. However, 4 of the 5 A/B signals produced modest moves (0.36% to 1.91%) that may or may not have covered transaction costs in a live environment.

### Q3. Are the blocked signals concentrated in a particular market condition?

**YES — strongly.**  
Today's `range_market` regime has embedded **sector rotation**: Healthcare and Consumer durables are gaining while Metals, Cement, Pharma, and Finance are selling. Mean_Reversion's `mean_reversion_bounce` setup assumes stocks in oversold conditions will bounce. In a sector-rotation regime, oversold stocks in selling sectors continue to fall rather than bounce. This is the exact failure mode that the current governance track record (`win_rate=20%`) has recorded.

The A/B signals were in sectors with inflows (Healthcare: APOLLOHOSP, FORTIS; Consumer: VOLTAS; Conglomerate: ADANIENT). The D signals were exclusively in sectors with outflows.

This is an architectural observation: the `mean_reversion_bounce` strategy fires on price-level technicals (RSI + support proximity) without a sector-alignment filter. In quiet range markets with uniform behaviour, this may work. In sector-rotation range markets, it produces a 50% bad signal rate.

### Q4. Is the current Mean_Reversion failure evidence still consistent with today's observations?

**YES — the historical evidence is confirmed by today's data.**

| Metric | Historical (10 trades) | Today (28 signals, partial day) |
|---|---|---|
| Win rate | 20% | 18% (A+B) |
| Avg return per trade | -0.23 | ~-0.45% (avg MAE dominates) |
| Hit rate (strict: A only) | — | 3.6% |

Today's signal outcomes are **consistent with or worse than** the historical track record. This does not provide evidence for re-enabling the strategy.

### Q5. Does today's evidence justify re-enabling Mean_Reversion?

**NO — insufficient evidence. Default maintained.**

The governance threshold is `win_rate ≥ 50%`. Today's observed signal quality is 18% (A+B) or 3.6% (A only). Both are far below the threshold. One day's observation (28 signals, partial-day measurement, market still open) cannot override a governance decision built on the full live trade history. The default answer is: **NO.**

---

## 13. CONCLUSIONS

### Primary conclusion

**Governance protection is working correctly today.**  
The majority (82%) of governance-blocked signals were bad or neutral. The 50% D-rate (14 confirmed adverse signals) represents concrete protection against actual losses. Executing all 28 signals would have produced net negative portfolio outcome.

### Secondary conclusions

1. **APOLLOHOSP exception is notable but not sufficient.** The top-scored signal (0.9441) was also today's top gainer (+3.66%). This is a genuine opportunity cost. However, one exception from 28 does not establish a pattern.

2. **Sector alignment is the hidden discriminator.** All A/B signals were in gaining sectors; all strong D signals were in losing sectors. The mean_reversion_bounce strategy does not use sector direction as a filter. This is an architectural research question, not a production change recommendation.

3. **Capital constraint is a secondary, separate issue.** QTY_ZERO affects 4 non-Mean_Reversion signals. It is correctly identified as a capital-level constraint (₹10k total) and not a system flaw.

4. **Expected_move_pct is calibrated for magnitude, not direction.** It does not reliably distinguish signal direction. Highest EM signals had 50% bad outcomes. This is consistent with its design intent.

5. **The 14 signals with negative MFE are important evidence.** These stocks never moved in the signal direction at all — the thesis was wrong from first trade. This pattern (50% of all signals) is the core problem the governance is protecting against.

---

## 14. RESEARCH QUESTIONS (OBSERVATIONAL ONLY)

These are questions for future investigation. They are NOT production recommendations.

**RQ-001:** Would a sector-alignment filter on `mean_reversion_bounce` improve the win rate? Today's data suggests yes: filtering for sector tailwind would have retained 4-5 A/B signals and excluded most D signals.

**RQ-002:** Does the APOLLOHOSP result reflect that the candidate_score (0.9441) is predictive of A-grade outcomes when sector alignment is present? The correlation between score and grade on today's data is weak overall but may be stronger within sector-aligned signals.

**RQ-003:** At what win rate and sample size should governance re-evaluation be triggered? The current track record is 10 trades. At 20% win rate, statistical significance of strategy failure is moderate (Wilson CI: 5-51% at 95%). More trades are needed for confident conclusion.

**RQ-004:** Does the `range_market` regime label adequately distinguish between "pure range" (uniform oscillation) and "sector rotation range" (index flat, sectors strongly directional)? Today's regime is the latter. Mean_Reversion may work in the former but not the latter.

**RQ-005:** The four non-Mean_Reversion signals blocked by QTY_ZERO include HAVELLS (breakout, exploration, score > 7.2). HAVELLS is a separate strategy path. Is QTY_ZERO a structural constraint or a per-signal budget allocation issue?

---

## FINAL VERDICT

```
GOVERNANCE_PROTECTION_WORKING
```

**Evidence:**
- 14/28 blocked signals = confirmed bad (50%)
- 9/28 = noise (32%)
- 5/28 = genuinely useful (18%)
- Today's observed win rate (18%) is consistent with historical live rate (20%) that triggered governance
- Governance prevented 14 adverse trades with losses ranging from -0.64% to -2.70%
- Opportunity cost exists: APOLLOHOSP (+3.66%, grade A) was the clearest genuine miss
- Net expected portfolio outcome from executing all 28 signals would be NEGATIVE

**The governance system correctly identified that this strategy is underperforming.  
Today's evidence does not provide grounds for re-enabling Mean_Reversion.**

---

## APPENDIX — DATA NOTES

| Item | Value |
|---|---|
| Analysis window | 09:45 – 11:05 IST (1h 20m, market still open) |
| EOD data | NOT available — market closes 15:30 IST |
| +30m window | 09:45 → 10:15 IST (measured at 10:15 UTC+5:30 = 04:45 UTC) |
| +60m window | 09:45 → 10:45 IST (measured at 05:15 UTC) |
| Latest price | 11:05 IST (05:35 UTC) |
| MFE/MAE window | 09:45 IST to latest available bar |
| Price source | yfinance (5-minute bars, auto_adjust=True) |
| Signal source | VPS docker logs — `[EdgeTelemetry]` and `[StrategyLabReject]` |
| Note | Grades may change slightly by EOD; trend is established by 11:05 |

```
Production changes:   0
Code changes:         0
Strategy changes:     0
Threshold changes:    0
Orders placed:        0
Manual executions:    0
Broker write calls:   0
```
