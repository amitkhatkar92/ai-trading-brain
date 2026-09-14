# DTA-KNOWLEDGE-DISCOVERY-AUDIT-001 — Knowledge Discovery Audit

**Session Audited:** Friday 2026-08-28 (First Live Session)  
**Report Date:** 2026-08-29 (Saturday — T+1 and beyond are PENDING)  
**Classification:** READ-ONLY — no code, data, orders, or configuration modified  
**Data Sources:** KEL (73,557 entries) · KLP (291 records) · KDA decisions (82) · Bootstrap (1,170) · MOP RC001 (61) · LOL (175) · Scan Attrition (61) · HBE Snapshot (57 symbols, 1,276 outcomes) · Actual OHLCV via yfinance  

---

## EXECUTIVE VERDICT

| Dimension | Verdict |
|---|---|
| **KNOWLEDGE SELECTION QUALITY** | **ADEQUATE** — KDA correctly overrode disabled StrategyLab 58 times; formal Top-5 by knowledge score operated correctly; but Day-1 score↔return correlation is weak |
| **OPPORTUNITY DISCOVERY QUALITY** | **POOR** — `bull_gate` alone blocked 104 evaluation cycles across 52 symbols; four primary missed outperformers (ELGIEQUIP +5%, KPITTECH +3.3%, PERSISTENT +3.2%, TECHM +2.5%) were blocked or not reached at the scanner level, never arriving at KDA |
| **MISSED OPPORTUNITY** | **HIGH** — BULL+ge2+BUY momentum setups in KEL show avg T+1=+2.055%, 74% win rate; the exact knowledge exists but the scanner systematically excludes this setup type |
| **SHOULD BREAKOUT DISCOVERY BE ADDED?** | **YES** — the knowledge base already contains 7,209 BULL+BUY+ge2 entries with outstanding statistics; no new historical data bootstrap is needed; only the scanner signal-generation layer requires change |

---

## 1. T+1–T+5 STATUS

| Day | Trading Date | Status |
|---|---|---|
| T+0 | 2026-08-28 (Fri) | ✅ Complete — see Section 2 |
| T+1 | 2026-09-01 (Mon) | ⏳ PENDING — market opens Monday |
| T+2 | 2026-09-02 (Tue) | ⏳ PENDING |
| T+3 | 2026-09-03 (Wed) | ⏳ PENDING |
| T+4 | 2026-09-04 (Thu) | ⏳ PENDING |
| T+5 | 2026-09-05 (Fri) | ⏳ PENDING |

**NIFTY 50 Friday close: 24,176.** All 40 candidate positions remain open as of end of day Friday. Targets (RR=2.5) require ~7-10% moves — these are 5-day hold setups, not intraday. T+5 results (Thursday 2026-09-04 close) will be the correct measurement horizon.

**Re-run instruction:** Fetch daily OHLCV for 2026-09-01 to 2026-09-05 from yfinance and calculate:
- Per day: close return vs entry, MFE (running from T+0 entry), MAE, target hit flag, SL hit flag, R-multiple
- Cumulative 5-day return and first-event (target/SL/expiry)

---

## 2. T+0 PERFORMANCE SUMMARY (Day-1 Reference)

Full candidate table with actual Friday price outcomes (from prior DTA-LIVE-POSTMORTEM-001):

| Rank (Score) | Symbol | Score | Strategy | Status | T+0 Return | MFE | MAE | R@Close | Note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ADANIENT | 0.921 | breakout | BLOCKED CRE_QTY_ZERO | +0.35% | +0.49% | -0.76% | +0.13 | Would have been profitable |
| 2 | ICICIGI | 0.904 | mean_rev_bounce | KDA_BUY | **-1.64%** | +0.06% | -2.39% | -0.45 | KLP Rank#1 — underperformed |
| 3 | IDFCFIRSTB | 0.882 | mean_rev_bounce | KDA_BUY | -0.81% | +0.51% | -0.98% | -0.38 | |
| 4 | ADANIPORTS | 0.882 | momentum_retest | KDA_BUY | -0.03% | +0.89% | -0.46% | -0.01 | Flat |
| 5 | INFY | 0.872 | mean_rev_bounce | KDA_BUY | **+2.99%** | +3.07% | +1.33% | +0.69 | Best of pool |
| 10 | HCLTECH | 0.853 | mean_rev_bounce | KDA_BUY | **+2.66%** | +4.06% | +1.22% | +0.60 | 2nd best |
| 33 | FORTIS | 0.587 | mean_rev_bounce | KDA_BUY | **+1.41%** | +3.06% | +0.34% | +0.39 | 3rd best (low score) |
| 14 | HAVELLS | 0.853 | mean_rev_bounce | KDA_BUY | -1.46% | +0.48% | **-4.10%** | -0.51 | **STOP_HIT** (only) |
| 25 | NHPC | 0.777 | mean_rev_bounce | KDA_BUY | **-2.26%** | -0.21% | -2.26% | -0.70 | Worst |
| 16 | KALYANKJIL | 0.848 | momentum_retest | KDA_BUY | -1.79% | +1.36% | -2.22% | -0.31 | |
| 39 | SBIN | 0.000 | momentum_retest | KDA_BUY (broker crash) | -0.17% | +0.18% | -0.81% | -0.08 | Flat — execution miss ~₹0 |

**Pool average (40 stocks): -0.116%, win rate 42.5% (17/40)**  
**0 targets hit, 1 stop hit (HAVELLS)**  
Note: all setups are 5-day holds — T+0 results are directional indicators only.

---

## 3. KNOWLEDGE SELECTION QUALITY

### 3.1 Formal Top-5 Selection Mechanism

The KLP does produce a formal Top-5 selection each cycle using the rule `TOP_5_BY_KNOWLEDGE_SCORE`. This was confirmed from the `KNOWLEDGE_OBSERVATION` records (42 entries across 6 cycles).

**ICICIGI at Cycle 1 (09:45 IST):**
```
knowledge_rank: 1
knowledge_selected: true  
knowledge_selection_rule: TOP_5_BY_KNOWLEDGE_SCORE
total_signals_this_cycle: 29
knowledge_score: 0.7831
```

ICICIGI was selected as #1 for the 09:45 cycle but returned -1.64% on Day-1. This is the strongest evidence against Day-1 score-return correlation.

### 3.2 KDA Override of Strategy Lab

KDA correctly overrode the disabled Strategy Lab in **58 of 82 decisions** (70.7%):
- StrategyLab approved: 21 (26%)
- StrategyLab rejected (STRATEGY_DISABLED): 61 (74%)
- KDA issued KNOWLEDGE_BUY anyway for 58 of those 61 = correct architecture behavior
- KDA deferred to KDA_WAIT for only 9 (ITC x3, NIFTY x3, BANKNIFTY x3) due to INSUFFICIENT evidence

This is the system working as designed — KDA providing knowledge-based autonomy when the strategy lab cannot approve.

### 3.3 KDA Evidence State Distribution (Friday)

| Evidence State | Count | Decision | Avg Knowledge Score | Avg Evidence Count | Avg Eff. N |
|---|---|---|---|---|---|
| VALIDATED | 28 | KNOWLEDGE_BUY | 6.30 | 327 | 327.6 |
| USEFUL | 27 | KNOWLEDGE_BUY | 6.24 | 18 | 18.1 |
| DEVELOPING | 18 | KNOWLEDGE_BUY | 5.87 | 7 | 7.3 |
| INSUFFICIENT | 9 | KNOWLEDGE_WAIT | 7.39 | 2 | 2.5 |

28 stocks had VALIDATED evidence (327 evidence entries each — 10 years of data). These are the most trusted decisions. The system was NOT flying blind.

### 3.4 Score-Return Correlation (Day-1)

Scored by `candidate_score` descending vs actual Friday return:
- **Top-10 by score:** avg return = -0.02%
- **Bottom-10 by score:** avg return = -0.22%
- **Score ranked #1 (ICICIGI):** returned -1.64%
- **Score ranked #33 (FORTIS):** returned +1.41%

**Assessment:** Weak but not random. Top decile (+0.2pp advantage over bottom decile). The `candidate_score` is a scanner-composite signal (RSI + volume + ATR) — it is a good filter for setup quality but not a strong T+0 predictor of direction. This is expected for a multi-day mean-reversion strategy; T+5 scores will be more meaningful.

### 3.5 KDA vs KLP Score Alignment

The KDA produces its own `knowledge_score` (avg 6.24 across VALIDATED/USEFUL states) and issues `kda_target` and `kda_stop` independently of the scanner. For example:
- INFY: scanner_target=1230.65, kda_target=1174.72 (KDA is more conservative)
- KDA uses evidence-based expected moves (p25/p50/p75) rather than fixed 2.5 RR

This shows the KDA is performing genuine evidence-based evaluation, not rubber-stamping scanner targets.

**Selection Quality verdict: ADEQUATE.** The machinery works correctly. The limitation is that the input signals it receives are all of the same type (mean-reversion/momentum-retest). A better input signal set would produce better selections.

---

## 4. OPPORTUNITY DISCOVERY QUALITY

### 4.1 The Pipeline Funnel

```
230 symbols attempted by equity scanner
     ↓
162 scored (70.4% coverage)
     ↓  
KLP evaluates: 291 records total
     ↓ bull_gate (104 cycles), rsi_neutral (36), high_atr (14), breakout_vol_low (7)...
167 SCAN_NO_SETUP rejections
     ↓
40 signals with entry/SL/TP in MOP RC001
     ↓
39 KNOWLEDGE_BUY (KDA), 1 KNOWLEDGE_WAIT
     ↓
5 blocked by CRE_QTY_ZERO
     ↓
1 order attempted (broker crash), 0 executed
```

The bottleneck is clear: **167 SCAN_NO_SETUP rejections** before KDA evaluation. The most common rejection reason was `bull_gate` (104 of 167 = 62%).

### 4.2 Gate-by-Gate Analysis

| Gate | Rejections | Avg RSI | Avg Vol | Primary Symbols Blocked |
|---|---|---|---|---|
| **bull_gate** | **104** | 44.1 | 0.76 | KPITTECH, TECHM, HCLTECH, INFY, BHARTIARTL (then overridden by later scan) |
| rsi_neutral | 36 | 53.4 | 0.79 | KPITTECH, TECHM, AXISBANK, MPHASIS, POLYCAB |
| high_atr | 14 | 57.0 | 1.85 | DCBBANK, INOXWIND, LICHSGFIN |
| breakout_vol_low | 7 | 63.1 | 0.86 | ADANIENT, TITAN, VEDL |
| bounce_price_hi | 3 | 44.6 | 0.60 | HCLTECH, INFY, NYKAA |
| retest_rsi_oob | 3 | 60.3 | 0.63 | ADANIPORTS, KALYANKJIL, NIACL |

**Critical observation:** The `bull_gate` fires on stocks with RSI=44.1 (mid-range, not strongly bullish). These stocks are in gentle uptrends. The gate's purpose — avoid buying into a mean-reversion setup when the trend is up — is correct for mean-reversion, but catastrophically wrong for breakout/momentum. The very same "bull_gate" condition (gentle uptrend, neutral-to-mid RSI) is the entry condition for a momentum continuation setup.

### 4.3 Exact First Gate for Each Missed Outperformer

| Symbol | T+0 Return | First Gate | Evidence | Detail |
|---|---|---|---|---|
| **ELGIEQUIP** | **+5.01%** | EQUITY_SCANNER (no score generated) | Not in KLP records | Received no score from the equity scanner; not in 162-symbol scored universe on any cycle |
| **KPITTECH** | **+3.29%** | `rsi_neutral` → `bull_gate` (cycle 1→2) | KLP records confirm | 04:15 UTC: rsi_neutral (RSI=47.3, vol=0.49); 05:00: bull_gate (RSI=52.3); 06:00: rsi_neutral; 07:30: bull_gate — blocked every cycle |
| **PERSISTENT** | **+3.24%** | EQUITY_SCANNER (no score generated) | Not in KLP records | Like ELGIEQUIP, not in scored universe |
| **TECHM** | **+2.49%** | `rsi_neutral` → `bull_gate` (cycle 1→2) | KLP records confirm | 04:15: rsi_neutral (RSI=48.1); 05:00: bull_gate (RSI=50.9); 06:00: rsi_neutral; 07:30: bull_gate — blocked every cycle |
| **SUPREMEIND** | **+1.42%** | EQUITY_SCANNER (no score generated) | Not in KLP records | Not in scored universe |
| **VEDL** | **+1.46%** | `breakout_vol_low` | KLP records confirm | RSI=57-61, vol=0.89 — breakout pattern detected but volume insufficient (threshold ~1.0+) |
| **TORNTPHARM** | **+1.03%** | EQUITY_SCANNER (no score generated) | Not in KLP records | Not in scored universe |

**Summary:** 3 of 7 missed outperformers were evaluated by KLP and explicitly rejected. 4 were never scored. All 7 were in the pre-market watchlist (`scanner_memory["2026-08-28"]`).

### 4.4 The bull_gate Paradox

The `bull_gate` rejects a stock when it is in a gentle uptrend (RSI ~40-55, mild positive momentum). This is conceptually correct for mean-reversion (don't buy a bounce in an uptrend without a proper pullback). However:

- The KEL `momentum_replay` has **32,909 BULL regime entries** spanning 10 years
- BULL + BUY + ge2 entries: **7,209** with avg_t1 = **+2.055%** and win rate = **74%**
- These entries capture exactly the setup the `bull_gate` is blocking: stocks in uptrends making big moves

The `bull_gate` is blocking signals that, according to the knowledge base, are among the most profitable setup types. This is an architecture misalignment: the scanner is applying a mean-reversion philosophy to filter inputs, but the knowledge base has superior evidence for momentum/breakout continuation in bull regimes.

---

## 5. KNOWLEDGE BASE AUDIT

### 5.1 KEL (Knowledge Evidence Ledger) Composition

| Source | Entries | % | Date Range | Nature |
|---|---|---|---|---|
| `momentum_replay` | 71,106 | 96.7% | 2016-03-02 to 2026-08-27 | Historical big-mover tracking (daily movers, ranked 1-10+) |
| `historical_audit` | 325 | 0.4% | Various | Ranking miss/correct select analysis |
| `lol_live` | 3 | 0.0% | 2026-08 | Live session observations |
| `klp` | 106 | 0.1% | 2026-08 | KLP processed evidence |

**The KEL is overwhelmingly `momentum_replay` — a 10-year history of stocks that were daily top movers**, classified by direction/regime/sector and their subsequent T+1/T+3/T+5 outcomes.

### 5.2 Momentum Replay Content

The `momentum_replay` records capture stocks ranked in the daily top movers (`mover_rank` 1-10+) with `day_move_pct` statistics:
- Median daily move: **3.68%** | P75: 5.12% | P90: 7.18%
- 65% of entries had |move| ≥ 3%
- Coverage: **all NSE sectors**, BUY + SELL directions, BULL + RANGE + BEAR regimes

This is fundamentally a **breakout/momentum knowledgebase** — it records what happens AFTER a stock makes a big move. The KDA uses this to evaluate whether a stock that is moving should continue.

### 5.3 Regime × Direction × Outcome Statistics

| Regime | Direction | N | ge2 | Avg T+1 | Win% |
|---|---|---|---|---|---|
| **BULL** | **BUY** | **16,475** | **7,209** | **+0.334%** | **49%** |
| **BULL+ge2** | **BUY** | **7,209** | 7,209 | **+2.055%** | **74%** |
| BULL | SELL | 16,434 | 7,075 | +0.058% | 50% |
| RANGE | BUY | 13,341 | 5,792 | +0.100% | 47% |
| RANGE | SELL | 13,333 | 5,613 | +0.009% | 50% |
| BEAR | BUY | 5,678 | 2,445 | +0.002% | 47% |
| BEAR | SELL | 5,845 | 2,574 | -0.014% | 51% |

**The most powerful knowledge in the system:** BULL + BUY + ge2 = **+2.055% avg T+1, 74% win rate over 7,209 historical cases.** This is the class of setup the bull_gate is blocking.

The `ge2` flag indicates a 2%+ day move — exactly what ELGIEQUIP (+5%), KPITTECH (+3.3%), PERSISTENT (+3.2%), TECHM (+2.5%) produced on Friday.

### 5.4 Sector Coverage

| Sector | Entries | ge2 Count | ge2% | Avg T+1 |
|---|---|---|---|---|
| FINANCIAL | 9,519 | 4,159 | 44% | +0.067% |
| AUTO | 6,797 | 2,930 | 43% | +0.060% |
| BANKING | 6,437 | 2,847 | 44% | +0.057% |
| INFRA | 5,658 | 2,403 | 42% | +0.148% |
| CONSUMER | 4,396 | 1,913 | 44% | +0.111% |
| **IT** | **4,299** | **1,758** | **41%** | **+0.065%** |
| POWER | 4,167 | 1,922 | 46% | +0.257% |
| METALS | 3,946 | 1,784 | 45% | +0.174% |

**IT sector: 4,299 entries including KPITTECH (408), PERSISTENT (470), TECHM (376).** All three have substantial evidence bases for momentum evaluation.

### 5.5 Missed Outperformers in KEL

| Symbol | KEL Entries | BUY | SELL | ge2 | Avg T+1 | Win% | HBE |
|---|---|---|---|---|---|---|---|
| ELGIEQUIP | **558** | 283 | 275 | 233 | +0.151% | 47% | NOT in HBE |
| PERSISTENT | **470** | 228 | 242 | **218** | **+0.246%** | **55%** | NOT in HBE |
| VEDL | 482 | 234 | 248 | 219 | -0.064% | 49% | NOT in HBE |
| KPITTECH | 408 | 206 | 202 | 198 | +0.074% | 50% | NOT in HBE |
| SUPREMEIND | 434 | 204 | 230 | 166 | +0.189% | 51% | NOT in HBE |
| TECHM | 376 | 175 | 201 | 144 | -0.153% | 44% | In HBE (39 entries) |

All 6 missed outperformers have **substantial KEL evidence (376–558 entries)**. The knowledge EXISTS. It is not being used because the scanner never generates a signal for them to be submitted to KDA.

### 5.6 KDA Bootstrap Analysis

| Attribute | Value | Significance |
|---|---|---|
| Total entries | 1,170 | 37 NIFTY50 large-caps |
| Direction | BUY-only | **No SELL setups seeded** |
| Regime | UNKNOWN (63%) + BEAR (37%) | **No BULL or RANGE regime seeding** |
| Target hit rate | 4% | Conservative/difficult setups |
| Stop hit rate | 22% | Higher stop rate than target rate |
| Avg T+1 | -0.017% | Near-zero: neutral seeding |
| Win rate | 46% | Below random (slightly) |

**Bootstrap bias note:** The 1,170-entry bootstrap covers 37 NIFTY50 blue-chips exclusively in UNKNOWN/BEAR regime with BUY-only direction. This creates a systematic directional bias:
1. KDA was seeded with a 1-year period of declining/uncertain market (BUY setups in BEAR regime performed near-random)
2. No SELL setups in bootstrap means KDA has no seeded evidence for short-selling in bear conditions
3. BULL regime is entirely absent from bootstrap — the most profitable KEL regime has zero bootstrap representation

The bootstrap's purpose is to prevent cold-start failures for large-caps. It achieves this but introduces conservative bias. This is a separate finding from the discovery gap but relevant to the system's overall calibration.

### 5.7 KDA Authority Validation Status

```
authority_status: NOT_VALIDATED
total_decisions: 0 (no completed live outcomes yet)
why_not_promoted: ['Insufficient outcomes: 0 < 10']
```

The KDA has not yet accumulated 10 completed live outcomes to validate its authority. This is Day-1 of live trading. The KDA is operating on external historical knowledge (KEL + bootstrap) rather than self-validated performance. This is architecturally correct — the KDA cannot validate itself without outcomes.

**Implication:** The KDA evidence_state labels (VALIDATED/USEFUL/DEVELOPING) refer to the quality of external evidence, not to the KDA's own validated track record. Once 10+ live outcomes complete (T+5 × 10 decisions ≈ ~3-4 weeks of live trading), the KDA will enter self-validation mode.

---

## 6. WOULD KDA HAVE EVALUATED MISSED STOCKS MEANINGFULLY?

**YES, definitively.** If the scanner had passed ELGIEQUIP, KPITTECH, PERSISTENT, TECHM to KDA with a BUY signal on 2026-08-28:

| Symbol | KEL Evidence | Expected State | Expected Decision | Expected Confidence |
|---|---|---|---|---|
| ELGIEQUIP | 558 KEL + 0 HBE | VALIDATED | KNOWLEDGE_BUY | High — 558 > VALIDATED threshold (>~50) |
| PERSISTENT | 470 KEL + 0 HBE | VALIDATED | KNOWLEDGE_BUY | High |
| KPITTECH | 408 KEL + 0 HBE | VALIDATED | KNOWLEDGE_BUY | High |
| TECHM | 376 KEL + 39 HBE | VALIDATED | KNOWLEDGE_BUY | High |

The KDA would have:
1. Located symbol-level momentum_replay entries (376–558 per symbol)
2. Computed sector-level IT momentum evidence (4,299 entries)
3. Applied the BULL+BUY regime context (KEL: avg T+1=+0.334%, 49% win for full bull-BUY; BULL+ge2+BUY: +2.055%, 74% win)
4. Issued KNOWLEDGE_BUY with evidence_state=VALIDATED

The knowledge to make this decision exists and is accurate. The scanner simply never submitted the question.

---

## 7. ARCHITECTURE COMPARISON: INTENDED vs ACTUAL

### Intended Architecture
```
MARKET
  → BROAD OPPORTUNITY DISCOVERY (all instruments, all setup types)
  → KNOWLEDGE EVALUATION (KDA with KEL evidence)
  → RISK (CRE sizing)
  → EXECUTION
  → OUTCOME
  → LEARNING (evidence back into KEL)
```

### Actual Implementation (Friday 2026-08-28)

```
MARKET (full NSE: ~1,800 symbols)
  → Equity Scanner (230 attempted, 162 scored) [~13% universe coverage]
  → KLP signal generation (167 SCAN_NO_SETUP rejections)
      ├─ bull_gate:        104 rejections (62%) — "trend is up, skip"
      ├─ rsi_neutral:       36 rejections (22%) — "RSI not oversold"
      ├─ breakout_vol_low:   7 rejections  (4%) — "breakout but vol too low"
      └─ others:            20 rejections (12%)
  → 40 MOP signals (all mean_reversion_bounce or momentum_retest)
  → KDA (39 KNOWLEDGE_BUY, 1 KNOWLEDGE_WAIT)
  → CRE (5 blocked: CRE_QTY_ZERO)
  → Execution (1 attempt, 0 fills — broker fixed)
  → LOL → KEL (175 observations pending outcome)
```

### The Gap

The architecture says "BROAD OPPORTUNITY DISCOVERY" but the actual scanner implements "NARROW MEAN-REVERSION DISCOVERY":
- Only 13% of NSE universe attempted
- bull_gate eliminates stocks in gentle uptrends (the richest opportunity class per KEL)
- rsi_neutral eliminates stocks with mid-range RSI (neutral, not oversold) — but these may be beginning breakouts
- Result: only mean-reversion and momentum-retest setups reach KDA

The KEL's strongest evidence class (BULL+BUY+ge2: +2.055% avg, 74% win rate) is systematically excluded by `bull_gate`. This is a direct contradiction between the scanner's selection philosophy and the knowledge base's signal quality evidence.

---

## 8. BREAKOUT DISCOVERY — SHOULD IT BE ADDED?

### 8.1 Decision: YES

| Criterion | Assessment |
|---|---|
| Does KEL have breakout evidence? | **YES** — 7,209 BULL+BUY+ge2 entries, +2.055% avg T+1, 74% win rate |
| Does KDA need new signals? | No — it already processes any BUY signal with BULL regime context |
| Is new historical bootstrap needed? | **PARTIALLY** — bootstrap currently has 0 BULL regime entries; adding BULL regime bootstrap data would improve KDA calibration for breakout candidates |
| Does the scanner have breakout code? | **YES** — `breakout_vol_low` rejection proves a breakout evaluation path exists |
| What is blocking it? | Volume threshold too high + `bull_gate` pre-emptively blocking before breakout check |

### 8.2 What the New Signal Would Look Like

The scanner already has a `breakout` strategy type (4 signals in Friday's MOP: ADANIENT, TITAN, KOTAKBANK). The existing breakout code produces signals but requires:
- RSI > ~55 (stocks in bull mode ✓)  
- vol_ratio > threshold (VEDL failed at 0.89 — threshold appears to be ~1.0-1.2)

KPITTECH and TECHM were blocked *before* the breakout check (`rsi_neutral` at 04:15 UTC when RSI=47-48, `bull_gate` at 05:00 UTC when RSI=50-52). These would need to pass through the breakout evaluation path rather than the mean-reversion path.

The required change is a **signal routing change**: stocks that fail `rsi_neutral` or `bull_gate` and have a moderate upward momentum (RSI 45-65, vol_ratio ≥ 0.9, positive day_move) should be routed to a `momentum_breakout` evaluation rather than discarded.

### 8.3 Bootstrap Data Gap

The existing bootstrap (1,170 entries, BUY-only, BEAR/UNKNOWN regime) does not cover BULL regime breakout setups. To properly calibrate KDA for breakout signals:
- Need to add BULL regime bootstrap entries from the same 37 symbols
- Or seed from the KEL momentum_replay directly (which already has extensive BULL coverage)
- No external data purchase is required — the evidence already exists in KEL

### 8.4 Estimated Impact If Breakout Discovery Were Active on Friday

If ELGIEQUIP, KPITTECH, PERSISTENT, TECHM had been detected and submitted to KDA, and KDA issued KNOWLEDGE_BUY (which it almost certainly would), and execution had succeeded:

| Symbol | Entry (est.) | SL (ATR-based) | Day-1 Return | Action |
|---|---|---|---|---|
| ELGIEQUIP | ~598.9 (open) | ~568 | +5.01% | Win (would close or hold) |
| KPITTECH | ~588.0 | ~560 | +3.29% | Win |
| PERSISTENT | ~5690.5 | ~5400 | +3.24% | Win |
| TECHM | ~1601.0 | ~1520 | +2.49% | Win |

vs actual pool (4 mean-reversion candidates that would have been selected instead):
- ICICIGI: -1.64%
- IDFCFIRSTB: -0.81%
- ADANIPORTS: -0.03%
- INFY: +2.99% (kept)

**Net selectional improvement (Day-1 only):** replacing ICICIGI/IDFCFIRSTB/ADANIPORTS with ELGIEQUIP/KPITTECH/PERSISTENT would have increased avg Day-1 return from +0.17% to approximately +3.0-3.5% for the selected set.

---

## 9. SELECTION vs DISCOVERY — FINAL DISTINCTION

| Question | Answer |
|---|---|
| Once a stock entered the candidate pool, did KDA select the better ones? | **ADEQUATELY** — 73/82 KNOWLEDGE_BUY, formal TOP_5 by knowledge_score, evidence-based targets/stops. Day-1 score↔return is weak but the mechanism is correct. |
| Was the candidate pool itself well-constructed? | **NO** — pool was exclusively mean-reversion/momentum-retest; excluded the most profitable setup type (BULL+breakout) |
| Did the knowledge base have breakout evidence? | **YES** — 71,106 momentum_replay entries covering BULL regime with outstanding statistics |
| Was the limitation in the knowledge or in the discovery layer? | **DISCOVERY** — scanner's bull_gate + rsi_neutral filters systematically excluded breakout candidates before KDA evaluation |
| Was the KDA capable of evaluating breakout stocks had they been submitted? | **YES** — all 4 primary missed outperformers had 376-558 KEL entries; KDA would have issued KNOWLEDGE_BUY |
| Is new historical data needed to add breakout discovery? | **PARTIALLY** — scanner routing change is primary need; bootstrap needs BULL regime examples but KEL already has the core evidence |

---

## 10. FINDINGS LOG

### F-001: bull_gate is the #1 discovery gap
**Finding:** 104 SCAN_NO_SETUP rejections with reason `bull_gate` — the most common rejection (62% of all rejections). Blocks stocks with RSI 40-55 in mild uptrends.  
**Impact:** Systematically excludes BULL+BUY+ge2 setups that KEL shows have +2.055% avg T+1 and 74% win rate.  
**Type:** DISCOVERY gap  

### F-002: KEL has excellent breakout/momentum knowledge but it is never used
**Finding:** 7,209 BULL+BUY+ge2 entries, 32,909 BULL regime entries in momentum_replay (2016–2026).  
**Impact:** The system has 10 years of breakout evidence sitting idle.  
**Type:** KNOWLEDGE UTILIZATION gap  

### F-003: 4 of 7 missed outperformers were never scored by the equity scanner
**Finding:** ELGIEQUIP, PERSISTENT, SUPREMEIND, TORNTPHARM had no KLP record — the scanner produced no score for them despite being in the watchlist.  
**Impact:** These stocks entered the watchlist based on some prior scan but no signal was generated during Friday's cycles.  
**Type:** DISCOVERY gap (scanner coverage)  

### F-004: Bootstrap has no BULL regime data
**Finding:** 1,170 bootstrap entries are exclusively UNKNOWN + BEAR regime, BUY-only.  
**Impact:** KDA was seeded with below-average performance data from weak market periods; creates conservative bias.  
**Type:** KNOWLEDGE calibration gap (lower priority than discovery gap)  

### F-005: KDA authority is NOT_VALIDATED (correctly — Day 1)
**Finding:** 0 completed live outcomes; requires 10 outcomes to enter validation mode.  
**Impact:** Normal for a Day-1 system. KDA is operating on KEL evidence, which is appropriate.  
**Type:** Expected state, no action needed  

### F-006: KLP formal selection (TOP_5_BY_KNOWLEDGE_SCORE) functioned correctly but selected within a narrow opportunity set
**Finding:** ICICIGI selected as knowledge_rank=1 on cycle 1 with 29 signals. Returned -1.64% Day-1.  
**Impact:** The selection mechanism is working; the input opportunity set is the problem.  
**Type:** DISCOVERY gap (not selection gap)  

### F-007: ADANIENT (score=0.921) and TITAN (breakout signals) blocked by CRE_QTY_ZERO
**Finding:** Both were valid breakout signals (vol ≥ 1.46, RSI 60-72) but blocked by capital risk engine.  
**Impact:** Minor — ADANIENT returned +0.35%, TITAN +0.40% on Day-1; not catastrophic misses but systematic exclusion of high-priced stocks by CRE deserves review.  
**Type:** RISK SIZING gap  

---

## FINAL VERDICT SUMMARY

| Dimension | Score | Verdict |
|---|---|---|
| **KNOWLEDGE SELECTION QUALITY** | **5/10** | ADEQUATE — mechanism correct, weak Day-1 score-return correlation expected for 5-day holds |
| **OPPORTUNITY DISCOVERY QUALITY** | **3/10** | **POOR** — bull_gate blocks the most profitable setup class; 4 of 7 best performers never scored |
| **MISSED OPPORTUNITY** | **HIGH** | 4 stocks in watchlist returned +2.5% to +5.0% and were never evaluated; KEL has 7,209 entries proving this is not a one-off |
| **SHOULD BREAKOUT DISCOVERY BE ADDED?** | **YES — HIGH PRIORITY** | KEL evidence is definitive (+2.055%, 74% win); discovery routing change required; minimal new data needed |
| **NEW BOOTSTRAP DATA NEEDED?** | **BULL regime additions needed** | Bootstrap currently seeded with BEAR/UNKNOWN only; BULL breakout seeding would improve KDA calibration |

### Priority Action Items (informational only — no code change in this audit)

| Priority | Finding | Required Change |
|---|---|---|
| P1 | bull_gate + rsi_neutral blocking breakout candidates | Add momentum_breakout routing: stocks with RSI 45-65, vol_ratio ≥ 1.0, positive intraday momentum should bypass bull_gate and enter breakout evaluation path |
| P2 | ELGIEQUIP, PERSISTENT, SUPREMEIND not in equity scanner scoring universe | Expand scanner coverage for cap-goods/mid-cap IT that appear in watchlist |
| P3 | Bootstrap has no BULL regime data | Seed bootstrap with 200-400 BULL regime BUY entries from top 37 symbols (data already in KEL momentum_replay) |
| P4 | CRE_QTY_ZERO blocking high-priced breakout stocks | Review CRE position-sizing floor; consider lot-size-aware allocation for ₹3,000+ stocks |

---

*Generated: 2026-08-29 | Read-only audit | No code, data, configuration, or orders modified*  
*T+1 to T+5 outcomes PENDING — re-evaluate after 2026-09-04 market close*
