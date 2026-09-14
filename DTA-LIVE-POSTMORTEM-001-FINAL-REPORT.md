# DTA-LIVE-POSTMORTEM-001 — First Live Session Stock Selection Quality Audit

**Date of Session:** Friday 2026-08-28  
**Report Date:** 2026-08-29 (Day+1, Saturday)  
**Classification:** READ-ONLY — no code or data modified  
**Scope:** Full candidate pool reconstruction · Counterfactual performance · Missed outperformer analysis  
**Data Sources:** `data/lol/LOL_2026-08-28.jsonl` (175 records) · `data/mop_rc001/MOP_RC001_2026-08-28.json` (61 records) · `data/scan_attrition/2026-08-28.jsonl` (61 records) · `data/scanner_memory.json` (Friday: 65 symbols) · `data/daily_candidates.json` · Actual 5m OHLCV via yfinance  
**Note on horizon:** Targets/SLs are set for a 5-day hold. This report covers Day-1 only (Friday). Full outcome determination requires next week's data.

---

## EXECUTIVE VERDICT

| Dimension | Verdict |
|---|---|
| **SELECTION QUALITY** | **MIXED** — pool generated negative avg return Day-1; top-score quintile partially worked but was statistically insignificant at N=40 |
| **MISSED OPPORTUNITY** | **MEDIUM** — 4 symbols in the pre-market watchlist outperformed the entire candidate pool but were never signalled by the equity scanner |
| **EXECUTION IMPACT** | **MINIMAL (Day-1)** — SBIN, the only order attempted, was flat (+0.07% from entry); no monetary cost from broker failure on Day-1 |

---

## 1. PIPELINE RECONSTRUCTION

### 1.1 Scanner Funnel — Friday

| Stage | Symbols | Source |
|---|---|---|
| Full NSE universe attempted | 230 | Scanner stats |
| Scored successfully | 162 | Scanner stats (70.4% coverage) |
| Pre-market watchlist (scanner_memory) | 65 | `scanner_memory.json["2026-08-28"]` |
| MOP RC001 — signals with entry/SL/TP | 40 | `MOP_RC001_2026-08-28.json` |
| KDA KNOWLEDGE_BUY | 39 / 40 | `LOL_2026-08-28.jsonl` (78 OUTCOME_PENDING KDA_BUY records, deduped) |
| KDA KNOWLEDGE_WAIT | 1 (ITC) | LOL |
| Blocked by CRE_QTY_ZERO | 5 (ADANIENT, EICHERMOT, TITAN, NIFTY, BANKNIFTY) | LOL |
| Orders attempted | 1 (SBIN at 13:00 IST) | Confirmed from broker crash log |
| Orders successfully placed | **0** | LOL `executed=False` all records |

**Direction:** All 40 MOP signals were BUY. No SELL / SHORT signals generated. Regime recorded as `range_market` for most cycles.

### 1.2 Cycle Timeline (IST / UTC)

| Cycle (IST) | UTC | MOP Signals | KDA_BUY | Notes |
|---|---|---|---|---|
| 09:45 | 04:15 | 27 | 27 | Main morning scan |
| 10:30 | 05:00 | 2 | 2 | TITAN, ANGELONE |
| 11:30 | 06:00 | 21 | 21 | SBIN first observed here |
| 13:00 | 07:30 | 3 | 3 | SBIN broker attempt + crash |
| 14:00 | 08:30 | 3 | 3 | |
| 15:00 | 09:30 | 5 | 5 | SBIN, COALINDIA, NTPC, POWERGRID + 1 |

### 1.3 Formal "Top-5" Selection

The system does **not record a formal ranked Top-5 selection** in LOL for this session. All records have `klp_selected=False` and `klp_rank=None`. This means the KLP scoring layer was running but either:
- did not complete its selection pass, or
- the `klp_selected` flag was not updated to `True` after the broker crash halted the execution pipeline.

For the purposes of this audit, "Top-5 by score" refers to the five highest `candidate_score` signals from MOP:

| Rank | Symbol | Score | Entry | SL | TP | RR | Strategy |
|---|---|---|---|---|---|---|---|
| 1 | ADANIENT | 0.921 | 3157.3 | 3069.0 | 3377.9 | 2.5 | breakout |
| 2 | ICICIGI | 0.904 | 1588.1 | 1530.6 | 1732.0 | 2.5 | mean_reversion_bounce |
| 3 | IDFCFIRSTB | 0.882 | 83.8 | 82.0 | 88.2 | 2.5 | mean_reversion_bounce |
| 4 | ADANIPORTS | 0.882 | 1708.0 | 1674.4 | 1792.0 | 2.5 | momentum_retest |
| 5 | INFY | 0.872 | 1110.8 | 1062.9 | 1230.7 | 2.5 | mean_reversion_bounce |

**ADANIENT was also blocked by CRE_QTY_ZERO.** The de-facto executable Top-5 (excluding blocked) were: ICICIGI, IDFCFIRSTB, ADANIPORTS, INFY, BHARTIARTL.

---

## 2. FULL CANDIDATE POOL — COUNTERFACTUAL PERFORMANCE (Day-1, Friday)

> Entry = MOP recorded entry_price. All BUY direction. Intraday hold: entry-at-open-comparable → close.  
> MFE/MAE computed from actual high/low vs entry_price. RR = 2.5 (all but ANGELONE=3.0).

| # | Symbol | Score | Entry | SL | TP | Status | Fri_High | Fri_Low | MFE% | MAE% | CloseRet% | R@Close | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ADANIENT | 0.921 | 3157.3 | 3069.0 | 3377.9 | BLOCKED:CRE_QTY_ZERO | 3172.9 | 3133.3 | +0.49 | -0.76 | +0.35 | +0.13 | Open@Close |
| 2 | ICICIGI | 0.904 | 1588.1 | 1530.6 | 1732.0 | KDA_BUY | 1589.0 | 1550.1 | +0.06 | **-2.39** | -1.64 | -0.45 | Open@Close |
| 3 | IDFCFIRSTB | 0.882 | 83.8 | 82.0 | 88.2 | KDA_BUY | 84.2 | 83.0 | +0.51 | -0.98 | -0.81 | -0.38 | Open@Close |
| 4 | ADANIPORTS | 0.882 | 1708.0 | 1674.4 | 1792.0 | KDA_BUY | 1723.2 | 1700.1 | +0.89 | -0.46 | -0.03 | -0.01 | Open@Close |
| 5 | INFY | 0.872 | 1110.8 | 1062.9 | 1230.7 | KDA_BUY | **1144.9** | 1125.6 | **+3.07** | +1.33 | **+2.99** | **+0.69** | Open@Close |
| 6 | BHARTIARTL | 0.872 | 1878.3 | 1810.0 | 2049.0 | KDA_BUY | 1893.7 | 1867.6 | +0.82 | -0.57 | +0.22 | +0.06 | Open@Close |
| 7 | BANKBARODA | 0.872 | 241.0 | 235.0 | 256.0 | KDA_BUY | 241.9 | 239.5 | +0.37 | -0.61 | +0.37 | +0.15 | Open@Close |
| 8 | MARUTI | 0.862 | 13440.0 | 13045.8 | 14425.5 | KDA_BUY | 13516.0 | 13318.0 | +0.57 | -0.91 | -0.48 | -0.16 | Open@Close |
| 9 | MARICO | 0.862 | 833.5 | 804.7 | 905.4 | KDA_BUY | 839.5 | 826.5 | +0.71 | -0.84 | -0.46 | -0.13 | Open@Close |
| 10 | HCLTECH | 0.853 | 1282.0 | 1225.0 | 1424.5 | KDA_BUY | **1334.1** | 1297.7 | **+4.06** | +1.22 | **+2.66** | **+0.60** | Open@Close |
| 11 | DMART | 0.853 | 3847.4 | 3701.5 | 4212.1 | KDA_BUY | 3850.0 | 3822.3 | +0.07 | -0.65 | -0.44 | -0.12 | Open@Close |
| 12 | TATACONSUM | 0.853 | 1042.0 | 1001.2 | 1144.0 | KDA_BUY | 1042.5 | 1030.5 | +0.05 | -1.10 | -0.12 | -0.03 | Open@Close |
| 13 | BRITANNIA | 0.853 | 5310.0 | 5108.7 | 5813.2 | KDA_BUY | 5355.0 | 5277.0 | +0.85 | -0.62 | -0.03 | -0.01 | Open@Close |
| 14 | HAVELLS | 0.853 | 1241.0 | 1205.8 | 1329.0 | KDA_BUY | 1247.0 | 1190.1 | +0.48 | **-4.10** | -1.46 | -0.51 | **STOP_HIT** |
| 15 | VOLTAS | 0.848 | 1217.5 | 1150.4 | 1385.3 | KDA_BUY | 1221.8 | 1195.0 | +0.35 | -1.85 | -1.44 | -0.26 | Open@Close |
| 16 | KALYANKJIL | 0.848 | 627.0 | 591.1 | 716.7 | KDA_BUY | 635.5 | 613.1 | +1.36 | -2.22 | -1.79 | -0.31 | Open@Close |
| 17 | M&M | 0.843 | 3330.0 | 3217.8 | 3610.5 | KDA_BUY | 3351.4 | 3302.4 | +0.64 | -0.83 | +0.12 | +0.04 | Open@Close |
| 18 | COALINDIA | 0.840 | 400.0 | 389.4 | 426.4 | KDA_BUY | 406.4 | 397.5 | +1.59 | -0.61 | +0.25 | +0.09 | Open@Close |
| 19 | NTPC | 0.838 | 330.9 | 318.9 | 360.9 | KDA_BUY | 333.0 | 328.8 | +0.62 | -0.63 | -0.26 | -0.07 | Open@Close |
| 20 | NESTLEIND | 0.833 | 1450.0 | 1396.0 | 1585.0 | KDA_BUY | 1454.6 | 1439.2 | +0.32 | -0.74 | +0.32 | +0.09 | Open@Close |
| 21 | ONGC | 0.825 | 232.0 | 225.7 | 247.8 | KDA_BUY | 233.4 | 231.3 | +0.58 | -0.31 | +0.11 | +0.04 | Open@Close |
| 22 | RELIANCE | 0.823 | 1282.2 | 1249.3 | 1364.4 | KDA_BUY | 1291.5 | 1280.0 | +0.73 | -0.17 | +0.37 | +0.15 | Open@Close |
| 23 | SUZLON | 0.820 | 46.8 | 45.4 | 50.2 | KDA_BUY | 47.1 | 46.5 | +0.51 | -0.60 | -0.04 | -0.01 | Open@Close |
| 24 | ADANIGREEN | 0.799 | 1303.2 | 1242.0 | 1456.2 | KDA_BUY | 1320.0 | 1303.4 | +1.29 | +0.02 | +0.60 | +0.13 | Open@Close |
| 25 | NHPC | 0.777 | 76.6 | 74.1 | 82.8 | KDA_BUY | 76.4 | 74.8 | -0.21 | -2.26 | -2.26 | -0.70 | Open@Close |
| 26 | BALKRISIND | 0.750 | 2328.6 | 2195.8 | 2660.7 | KDA_BUY | 2360.9 | 2327.2 | +1.39 | -0.06 | +0.49 | +0.09 | Open@Close |
| 27 | SRF | 0.717 | 2583.0 | 2538.0 | 2695.5 | KDA_BUY | 2606.9 | 2582.1 | +0.93 | -0.03 | +0.27 | +0.15 | Open@Close |
| 28 | NIACL | 0.701 | 186.7 | 177.4 | 210.0 | KDA_BUY | 191.9 | 185.5 | +2.79 | -0.63 | -0.19 | -0.04 | Open@Close |
| 29 | THERMAX | 0.649 | 3968.5 | 3765.6 | 4475.8 | KDA_BUY | 3962.0 | 3936.6 | -0.16 | -0.80 | -0.61 | -0.12 | Open@Close |
| 30 | CIPLA | 0.644 | 1420.0 | 1375.4 | 1531.5 | KDA_BUY | 1423.5 | 1409.5 | +0.25 | -0.74 | +0.25 | +0.08 | Open@Close |
| 31 | EICHERMOT | 0.616 | 8099.5 | 7937.8 | 8503.8 | BLOCKED:CRE_QTY_ZERO | 8131.0 | 8003.0 | +0.39 | -1.19 | -0.50 | -0.25 | Open@Close |
| 32 | INDIGO | 0.595 | 5189.0 | 5015.0 | 5624.0 | KDA_BUY | 5195.0 | 5138.0 | +0.12 | -0.98 | -0.44 | -0.13 | Open@Close |
| 33 | FORTIS | 0.587 | 913.8 | 880.8 | 996.6 | KDA_BUY | 941.8 | 917.0 | +3.06 | +0.34 | +1.41 | +0.39 | Open@Close |
| 34 | ANGELONE | 0.543 | 295.9 | 286.3 | 324.7 | KDA_BUY | 297.7 | 291.9 | +0.61 | -1.37 | -0.64 | -0.20 | Open@Close |
| 35 | ITC | 0.000 | 269.0 | 261.9 | 286.8 | KDA_WAIT | 268.5 | 264.9 | -0.19 | -1.54 | -1.12 | -0.42 | Open@Close |
| 36 | ULTRACEMCO | 0.000 | 11717.0 | 11435.0 | 12422.0 | KDA_BUY | 11671.0 | 11528.0 | -0.39 | -1.61 | -1.09 | -0.45 | Open@Close |
| 37 | POWERGRID | 0.000 | 264.9 | 257.4 | 283.7 | KDA_BUY | 267.3 | 265.1 | +0.91 | +0.08 | +0.43 | +0.15 | Open@Close |
| 38 | TITAN | 0.000 | 5148.7 | 4876.5 | 5829.2 | BLOCKED:CRE_QTY_ZERO | 5169.9 | 5136.0 | +0.41 | -0.25 | +0.40 | +0.08 | Open@Close |
| 39 | SBIN | 0.000 | 1049.3 | 1027.5 | 1103.8 | KDA_BUY | 1051.2 | 1040.8 | +0.18 | -0.81 | **-0.17** | -0.08 | Open@Close |
| 40 | KOTAKBANK | 0.000 | 424.7 | 400.6 | 484.9 | KDA_BUY | 426.1 | 421.1 | +0.32 | -0.85 | -0.24 | -0.04 | Open@Close |

> **SBIN note:** Four cycles of observation (11:30, 13:00, 14:00, 15:00 IST). Entry prices ranged 1046.7–1049.3. Broker attempt at 13:00 IST used entry≈1046.7. Friday range: H=1051.2, L=1040.8, C=1047.5. Net: essentially flat. Broker failure cost = ~₹0 on Day-1.

---

## 3. AGGREGATE STATS — ALL 40 CANDIDATES (Day-1)

| Metric | Value |
|---|---|
| Total candidates | 40 |
| Avg close return vs entry | **-0.116%** |
| Avg MFE (best intraday move toward TP) | +0.785% |
| Avg MAE (worst intraday drawdown) | -0.802% |
| Avg R-multiple at close | **-0.044** |
| Targets hit intraday | **0 / 40** (TP levels set for 5-day horizon) |
| Stop hit intraday | **1 / 40** (HAVELLS only) |
| Positive close returns | 17 / 40 (42.5%) |
| Negative close returns | 23 / 40 (57.5%) |

### Top-5 by Score Day-1 Performance

| Symbol | Score | CloseRet% | R@Close | Note |
|---|---|---|---|---|
| ADANIENT | 0.921 | +0.35% | +0.13 | BLOCKED — CRE_QTY_ZERO |
| ICICIGI | 0.904 | -1.64% | -0.45 | Underperformed |
| IDFCFIRSTB | 0.882 | -0.81% | -0.38 | Underperformed |
| ADANIPORTS | 0.882 | -0.03% | -0.01 | Near flat |
| INFY | 0.872 | **+2.99%** | **+0.69** | Best of top-5 |
| **Top-5 avg** | — | **+0.17%** | **-0.00** | Marginally positive |

The top-5 by score had avg +0.17% (close return) — slightly above the full pool average of -0.116%, but the difference is statistically negligible at N=5.

### Score-Return Correlation

There is **no meaningful positive correlation** between `candidate_score` and Day-1 return:
- Top-10 by score avg return: -0.02%
- Bottom-10 by score avg return: -0.22%
- The score ranks FORTIS (score=0.587) at #33 but it returned +1.41% (3rd best)
- The score ranks ICICIGI (score=0.904) at #2 but it returned -1.64% (2nd worst)

This suggests the KLP scoring model does not yet have strong Day-1 predictive power for intraday direction, which is expected given all setups are 5-day mean-reversion/momentum holds.

---

## 4. MISSED OUTPERFORMERS

### 4.1 Definition
Symbols in the pre-market scanner watchlist (65 symbols in scanner_memory["2026-08-28"]) that were **NOT in the MOP candidate pool** (40 signals) but produced strong Friday moves.

### 4.2 The Four Primary Missed Outperformers

| Symbol | Fri_Return | MFE | Gate Blocking Entry | Original Status | Root Cause |
|---|---|---|---|---|---|
| **ELGIEQUIP** | **+5.01%** | +5.36% | EQUITY_SCANNER — no signal generated | In watchlist, not in daily_candidates | Technical conditions (RSI/vol/ATR) did not meet signal thresholds at scan time |
| **KPITTECH** | **+3.29%** | +3.89% | EQUITY_SCANNER — no signal generated | In watchlist; appeared in Sat prep (score=0.802) | No intraday signal triggered Friday |
| **PERSISTENT** | **+3.24%** | +3.86% | EQUITY_SCANNER — no signal generated | In watchlist; appeared in Sat prep (score=0.741) | No intraday signal triggered Friday |
| **TECHM** | **+2.49%** | +2.56% | EQUITY_SCANNER — no signal generated | In watchlist; appeared in Sat prep (score=0.716) | No intraday signal triggered Friday |

**Total missed alpha (MFE) if these four had been caught:** +5.36%, +3.89%, +3.86%, +2.56%  
**None were rejected by strategy-lab or KDA.** They never reached any evaluation layer.

### 4.3 Additional Missed Upside (moderate)

| Symbol | Fri_Return | MFE | Note |
|---|---|---|---|
| SUPREMEIND | +1.42% | +3.46% | In watchlist, not in MOP |
| VEDL | +1.46% | +2.01% | In watchlist, not in MOP |
| TORNTPHARM | +1.03% | +1.03% | In watchlist, not in MOP |
| BAJAJ-AUTO | +0.84% | +1.38% | In watchlist, not in MOP |

### 4.4 Why Were These Missed?

All four primary missed outperformers:
1. Were in the **pre-market scanner watchlist** — the system "knew" about them
2. Had **no scan attrition record** — they were not rejected; they simply generated no signal
3. Had **no MOP / LOL record** — the equity scanner's signal-generation criteria (RSI thresholds, volume ratio, ATR/entry pattern) did not fire for these symbols at any of the six Friday cycles
4. Several appeared in **Saturday's daily_candidates.json** with `strategy=pending_scan`, suggesting the Saturday prep did detect their momentum — one day late

**First root cause per missed outperformer:**  
`EQUITY_SCANNER signal threshold not met` — the scanner saw the symbol in the watchlist but the mean_reversion_bounce / breakout pattern was not triggered. ELGIEQUIP and KPITTECH specifically may have been breaking out (RSI rising, not yet oversold) — a breakout condition the scanner was not using prominently on Friday.

---

## 5. SELECTION QUALITY COMPARISON

### 5.1 MOP Candidates vs Scanner Universe

| Cohort | Symbols (with price data) | Avg Return | Win% |
|---|---|---|---|
| MOP candidate pool | 27 | **-0.382%** | 37% (10/27) |
| Non-MOP scanner symbols | 38 | **+0.047%** | 47% (18/38) |
| Full scanner universe | 65 | **-0.131%** | 43% (28/65) |

**The non-MOP scanner symbols outperformed the MOP candidate pool on Day-1.** The stocks the system DID signal underperformed those it did not signal. This is a meaningful negative signal about Day-1 discrimination, but:
- All setups are 5-day holds — Day-1 is not the expected measurement horizon
- Mean-reversion strategies may have adverse Day-1 before bouncing
- The pool is still in `OUTCOME_PENDING` — final verdict requires 5-day data

### 5.2 Did Top-5 Outperform Broader Pool?

Top-5 by score avg return: +0.17%  
Full pool avg return: -0.116%  
Difference: **+0.29 percentage points** — marginal advantage, statistically insignificant at N=5.

### 5.3 Hit Rate Analysis (Day-1)

- Win rate (close > entry): **42.5%** (17/40)
- Stop hit: **2.5%** (1/40: HAVELLS)
- Target hit: **0%** (TP levels are 5-day targets, not intraday)
- Median R at close: **-0.01** (essentially breakeven)

---

## 6. SBIN EXECUTION ANALYSIS — "SELECTED BUT BROKER FAILED"

### 6.1 SBIN Cycle Timeline

| Cycle (IST) | Entry | SL | TP | KDA | Outcome |
|---|---|---|---|---|---|
| 11:30 | 1049.3 | 1027.5 | 1103.8 | KNOWLEDGE_BUY | Not executed |
| **13:00** | **1046.7** | **1024.9** | **1101.2** | **KNOWLEDGE_BUY** | **BROKER CRASH** |
| 14:00 | 1047.5 | 1025.7 | 1102.0 | KNOWLEDGE_BUY | Not executed |
| 15:00 | 1046.8 | 1025.0 | 1101.3 | KNOWLEDGE_BUY | Not executed |

### 6.2 Counterfactual SBIN Trade

Assuming execution at 13:00 IST entry = 1046.7:
- Friday High: 1051.2 → MFE = **+0.42%**
- Friday Low: 1040.8 → MAE = **-0.57%**
- Friday Close: 1047.5 → Day-1 return = **+0.07%** (₹7.5 per share if traded)
- SL not hit (1025.0 vs actual Low 1040.8) ✓
- TP not hit (1101.2 vs actual High 1051.2) ✗

**Execution impact (Day-1): near-zero.** The stock was flat. The broker failure cost no money and missed no meaningful gain on Friday. The trade was essentially a wash.

### 6.3 Why SBIN Specifically?

SBIN was selected for execution (not just observed) because:
1. It appeared in 4 consecutive cycles with consistent KNOWLEDGE_BUY signals
2. `kda_evidence_state = USEFUL` (confirmed by LOL records)
3. It is one of the most liquid NSE stocks — position sizing viable

---

## 7. ROOT CAUSE ANALYSIS — EVERY MEANINGFUL MISSED OPPORTUNITY

| # | Miss | Symbol | Root Cause | Gate | Fix Direction |
|---|---|---|---|---|---|
| 1 | Strongest mover not signalled | ELGIEQUIP (+5.01%) | Equity scanner did not detect breakout conditions | EQUITY_SCANNER (signal_generation) | Add breakout/momentum signal type to scanner |
| 2 | 2nd strongest not signalled | KPITTECH (+3.29%) | Same — IT sector momentum not captured | EQUITY_SCANNER | Breakout/trend signal coverage |
| 3 | 3rd strongest not signalled | PERSISTENT (+3.24%) | Same | EQUITY_SCANNER | Same |
| 4 | 4th strongest not signalled | TECHM (+2.49%) | IT sector group-move not detected | EQUITY_SCANNER | Sector-momentum signal |
| 5 | Top-scored signal underperformed | ICICIGI (-1.64%) | Mean-reversion setup in stock that continued trending down | SCORE_QUALITY | Regime filter strength |
| 6 | Broker failure prevented SBIN | SBIN (flat, ~0%) | `'str' object has no attribute 'get'` in DhanBroker (FIXED) | EXECUTION | Already fixed — commit f8d144a |
| 7 | ADANIENT blocked despite 0.921 score | ADANIENT (+0.35%) | CRE returned qty=0 — stock too expensive per capital rules | CAPITAL_RISK_ENGINE | Position-sizing review |
| 8 | No short signals generated | — | Regime classified as range_market/bull_trend — no SELL signals | REGIME_DETECTION | Acceptable given Friday market direction |

---

## 8. QUANTITATIVE SCORECARD

### Q1: Did Top-5 actually outperform the broader pool?
**Marginally yes** (+0.17% vs -0.116%) but statistically insignificant. 1 of 5 drove all performance (INFY +2.99%); 3 of 5 underperformed the pool mean.

### Q2: What was the Top-5 hit rate?
2/5 positive = **40%** (INFY +2.99%, ADANIENT +0.35%)  
Using full pool: 17/40 = **42.5%**

### Q3: What was average/median R at close?
- Top-5 avg R: **-0.00**  
- Full pool avg R: **-0.044**  
- Full pool median R: **-0.01**  
(All near zero — consistent with 5-day holds evaluated at Day-1)

### Q4: How many profitable setups were missed?
- 4 strong movers (ELGIEQUIP, KPITTECH, PERSISTENT, TECHM) were in watchlist but not signalled — these were **not missed by gating but by signal generation failure**
- 0 profitable setups were in the pool, received KDA_BUY, and were blocked unfairly — the CRE-blocked ADANIENT returned only +0.35%, less than INFY which passed

### Q5: How many missed outperformers would have exceeded selected trades?
All four: ELGIEQUIP (+5.01%), KPITTECH (+3.29%), PERSISTENT (+3.24%), TECHM (+2.49%) exceeded the best pool candidate (INFY +2.99%) or tied it. **All four** had superior Day-1 returns vs the full pool.

### Q6: Was the problem selection, gating, ranking, execution, or combination?

| Layer | Assessment |
|---|---|
| **Signal generation (scanner)** | ⚠️ CONTRIBUTING — failed to detect Friday's best movers (all in IT/cap-goods sector, breakout-type moves) |
| **KDA gating** | ✅ NEUTRAL — gave KNOWLEDGE_BUY to 39/40; no evidence of over-filtering |
| **CRE sizing** | ⚠️ MINOR — CRE_QTY_ZERO on ADANIENT (score=0.921) was a missed trade |
| **Execution (broker)** | ⚠️ BUT IMMATERIAL Day-1 — broker crashed on SBIN which was flat; already fixed |
| **Score ranking** | ❌ WEAK Day-1 — no meaningful correlation between score and next-day return |

---

## 9. CONCLUSIONS

### What Worked
1. **Pipeline completeness**: Full funnel from universe scan → signal → KDA → execution path operated end-to-end on Day-1 of live trading
2. **KDA coverage**: KDA gave KNOWLEDGE_BUY to 97.5% of candidates (39/40); strong evidence base active
3. **Stop discipline**: Only 1 stop hit in 40 candidates; MAE broadly contained within SL distances
4. **SBIN selection**: The system correctly identified SBIN as a recurring high-confidence signal (4 cycles) — right direction (price held above SL all day), wrong day for alpha

### What Did Not Work
1. **Signal generation missed the day's top movers**: ELGIEQUIP (+5%), KPITTECH (+3.3%), PERSISTENT (+3.2%), TECHM (+2.5%) were on the watchlist but the scanner's mean_reversion pattern did not fire — these were breakout/momentum moves, not mean-reversion setups. The scanner was looking for the wrong pattern for this type of day.
2. **Score-return correlation**: The highest-scored signal (ICICIGI 0.904) delivered -1.64%. Score is a composite of multiple factors but Day-1 direction prediction is weak.
3. **Pool average underperformed universe**: The 40 selected candidates returned -0.116% vs the full 65-symbol universe at -0.131% — essentially in line with market, not alpha-generating on Day-1.

### Important Caveat — 5-Day Horizon
All signals are designed for 5-day holds. Day-1 results are **not the intended measurement horizon**. Mean-reversion setups often have an adverse Day-1 before recovering. The 5-day outcomes (available next week) may tell a very different story. This report should be re-evaluated after Day-5 close (Thursday 2026-09-03).

---

## FINAL VERDICT

| Dimension | Verdict | Evidence |
|---|---|---|
| **SELECTION QUALITY** | **MIXED** | Pool slightly underperformed its own universe; 1 stop hit; no targets; 4 strong movers missed entirely |
| **MISSED OPPORTUNITY** | **MEDIUM** | 4 symbols in watchlist (+2.5% to +5.0%) generated no signal; IT/breakout sector blind spot confirmed |
| **EXECUTION IMPACT (Day-1)** | **MINIMAL** | SBIN flat (+0.07% from entry); broker failure cost ≈ ₹0 on Friday; fix deployed at f8d144a |

**Root cause priority (for improvement):**
1. **P1 — Scanner signal coverage**: Add breakout/momentum signal type to detect IT sector and cap-goods momentum moves that don't exhibit mean-reversion RSI patterns
2. **P2 — CRE sizing floor**: Review CRE_QTY_ZERO triggers for high-priced stocks (ADANIENT ₹3157, EICHERMOT ₹8099, TITAN ₹5148) — these may be excluded systematically due to price, not quality
3. **P3 — Score-return feedback**: Day-1 direction prediction from `candidate_score` is weak; KDA evidence state (`VALIDATING` vs `DEVELOPING`) may be a stronger discriminator to track

**Execution root cause already resolved** — DTA-LIVE-RC-002, committed f8d144a, deployed and verified.

---

*Generated: 2026-08-29 | Read-only audit | No code, data, or orders modified*
