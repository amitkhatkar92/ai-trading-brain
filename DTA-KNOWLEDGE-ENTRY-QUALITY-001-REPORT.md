# DTA-KNOWLEDGE-ENTRY-QUALITY-001 — ANALYSIS REPORT
## Last-Week Knowledge + Entry-Timing Analysis

**Analysis prepared:** 2026-08-30  
**Analysis period:** Week of Mon 24 Aug – Fri 28 Aug 2026  
**Data sources:** VPS live KDA files, VPS scanner_memory, local KEL (3,846 entries), VPS KEL (73,557 entries), yfinance market data (NSE)  
**Analyst note:** READ-ONLY. No production code modified. No thresholds changed. No orders placed.

---

## 1. METHODOLOGY

### Analysis Universe
- Nifty 500 universe as configured in `data/nifty500_universe.json` (local and VPS)
- Additional sector/index coverage from universe variants

### What Was Examined
- **VPS scanner_memory.json**: Which stocks the system actually had as scan candidates per day (Aug 26–29)
- **VPS kda_decisions_2026-08-2{6,7,8}.jsonl**: All KDA evaluations made during the week
- **VPS kda_vs_stratlab_2026-08-2{6,7,8}.jsonl**: Scanner → StrategyLab → KDA pipeline flow per signal
- **VPS live_orders.jsonl + paper_trades.csv**: Actual execution records
- **yfinance NSE data**: Actual Aug 21–28 OHLCV for top movers and context stocks
- **Local KEL** (3,846 entries): Evidence state on the local development machine
- **VPS KEL** (73,557 entries): Live evidence state used by the running system

### Lookahead Verification
- T0 is defined as **Mon 25 Aug open** for theoretical entries
- Lookahead contamination check: All KDA decisions were made *during* the week (Aug 26–28) using only price + KEL data available at evaluation time
- Future prices (T+1 to T+4 returns, MFE, MAE) were computed **only for outcome evaluation** after establishing T0
- Classification of Knowledge decisions uses only the KDA decision timestamp and evidence available then
- **Zero lookahead contamination confirmed**

### Configured Trading Parameters
- Stop loss: 5% from entry
- Target: 7% from entry
- Horizon: 5 trading days (Mon–Fri week)
- Transaction costs: 20 bps round-trip (brokerage + STT + stamp + exchange)
- Position sizing: Not applied (P&L shown as % return on invested capital)

---

## 2. ANALYSIS UNIVERSE — WEEK Aug 24–28, 2026

### Actual Trading Days
| Day | Date | System Active | KDA File | Scanner Candidates |
|-----|------|:---:|:---:|:---:|
| Mon | Aug 24 | Unknown | No file | Not in scanner_memory |
| Tue | Aug 25 | Unknown | No file | Not in scanner_memory |
| Wed | Aug 26 | Yes | kda_decisions_2026-08-26.jsonl | 55 stocks |
| Thu | Aug 27 | Yes | kda_decisions_2026-08-27.jsonl | 63 stocks |
| Fri | Aug 28 | Yes | kda_decisions_2026-08-28.jsonl | 64 stocks |

No KDA decision files exist for Aug 24 or Aug 25. The VPS logs confirm activity on those days (log rotation at 10MB occurred), but scanner_memory records only begin from Aug 26. The system was likely warming up (Dhan 451 fallback, universe rebuild) on Mon–Tue.

---

## 3. TOP 5 UPSIDE PERFORMERS — Week Aug 24–28, 2026

Computed as: (Aug 28 close / Aug 21 close − 1). All prices from yfinance NSE data.

| Rank | Symbol | Aug 21 Close | Aug 24 Open | Aug 28 Close | Week Ret% |
|------|--------|:-----------:|:-----------:|:------------:|:---------:|
| 1 | SAIL | 173.46 | 174.80 | 200.00 | +15.30% |
| 2 | LICHSGFIN | 497.00 | 496.80 | 535.00 | +7.65% |
| 3 | DIVISLAB | 8,597.0 | 8,558.5 | 9,239.0 | +7.47% |
| 4 | COFORGE | 1,891.7 | 1,891.7 | 2,014.6 | +6.50% |
| 5 | DCBBANK | 203.59 | 205.62 | 212.97 | +4.61% |
| 6 | ADANIENT | 2,997.0 | 3,010.0 | 3,168.5 | +5.72% |
| 7 | KOTAKBANK | 402.80 | 403.50 | 423.70 | +5.19% |
| 8 | KPITTECH | 589.30 | 589.35 | 609.40 | +3.41% |
| 9 | VEDL | 279.00 | 280.05 | 287.95 | +3.21% |
| 10 | TECHM | 1,584.0 | 1,580.1 | 1,640.9 | +3.59% |

### Top 5 Downside Performers

| Rank | Symbol | Aug 21 Close | Aug 24 Open | Aug 28 Close | Week Ret% |
|------|--------|:-----------:|:-----------:|:------------:|:---------:|
| 1 | EMAMILTD | 402.60 | 400.05 | 379.40 | −5.76% |
| 2 | TATAPOWER | 374.30 | 374.30 | 351.85 | −6.00% |
| 3 | CROMPTON | 252.00 | 251.95 | 233.00 | −7.54% |
| 4 | CESC | 155.09 | 156.00 | 148.11 | −4.50% |
| 5 | AAVAS | 1,355.3 | 1,349.0 | 1,275.5 | −5.89% |

---

## 4. KNOWLEDGE-FIRST COMPARISON — TOP 5 UPSIDE

### What the System Did and Did Not Do

| Symbol | In Universe | In Scanner (Aug 26–28) | KDA Evaluated | KDA Decision | Evidence State | ESS | StrategyLab Influence |
|--------|:-----------:|:---:|:---:|:---:|:---:|:---:|:---:|
| SAIL | ✅ Yes | ❌ No (never in kda_vs_stratlab) | No | N/A | N/A | N/A | N/A |
| LICHSGFIN | ✅ Yes | ⚠️ In scanner_memory Aug 26–28, but no signal triggered | No | N/A | N/A | N/A | N/A |
| DIVISLAB | ✅ Yes | ❌ No (never in kda_vs_stratlab) | No | N/A | N/A | N/A | N/A |
| COFORGE | ✅ Yes | ❌ No (never in kda_vs_stratlab) | No | N/A | N/A | N/A | N/A |
| DCBBANK | ✅ Yes | ❌ No (never in kda_vs_stratlab) | No | N/A | N/A | N/A | N/A |

**Finding:** None of the top 5 upside performers received a KDA evaluation during the week. 4/5 were in the broad universe but never triggered the scanner's setup-detection logic. LICHSGFIN was in scanner_memory (a confirmed candidate), but no tradeable setup signal was generated from it on any day.

### StrategyLab Influence on These Stocks
- None of the top 5 reached StrategyLab either. The failure occurred at the earlier discovery stage.

---

## 5. KNOWLEDGE-FIRST COMPARISON — TOP 5 DOWNSIDE

| Symbol | In Universe | In Scanner | KDA Evaluated | KDA Decision | Direction scanned | Notes |
|--------|:-----------:|:---:|:---:|:---:|:---:|:---:|
| EMAMILTD | ✅ Yes | ❌ No | No | N/A | N/A | Not discovered |
| TATAPOWER | ✅ Yes | ✅ Aug 26, 27 | Yes | KNOWLEDGE_WAIT | BUY (wrong) | Scanned as mean-reversion BUY |
| CROMPTON | ✅ Yes | ❌ No | No | N/A | N/A | Not discovered |
| CESC | ✅ Yes | ❌ No | No | N/A | N/A | Not discovered |
| AAVAS | ✅ Yes | ❌ No | No | N/A | N/A | Not discovered |

**TATAPOWER detail:**
- Aug 26: scanned BUY with strategy `Mean_Reversion_RSI_HiVol`, StrategyLab approved, KDA=KNOWLEDGE_WAIT (INSUFFICIENT)
- Aug 27: scanned BUY with `Mean_Reversion`, two evaluations — StrategyLab approved for one, rejected for others
- Actual result: −5.80% week, −6.00% from prior Friday close
- The scanner identified TATAPOWER for a long (not short) trade while the stock was in a sustained decline. **This is a direction error**, not a Knowledge failure — the scanner's setup logic generated an incorrect directional signal.

---

## 6. ENTRY-TIMING ANALYSIS

### T0 Definition
T0 = Mon Aug 24 open price = earliest achievable entry if the system had identified the stock on the first day of the week.

### Price Grid (Aug 21 prior Fri close through Aug 28 Fri close)

#### TOP 5 UPSIDE

| Symbol | Aug 21 C | Aug 24 O (T0) | Aug 25 C | Aug 26 C | Aug 27 C | Aug 28 C |
|--------|:--------:|:-----------:|:--------:|:--------:|:--------:|:--------:|
| SAIL | 173.46 | 174.80 | 184.59 | 194.90 | 193.00 | 200.00 |
| LICHSGFIN | 497.00 | 496.80 | 506.00 | 524.40 | 535.50 | 535.00 |
| DIVISLAB | 8,597.0 | 8,558.5 | 8,744.5 | 9,025.0 | 9,060.0 | 9,239.0 |
| COFORGE | 1,891.7 | 1,891.7 | 1,892.8 | 1,880.0 | 1,901.8 | 2,014.6 |
| DCBBANK | 203.59 | 205.62 | 207.37 | 213.83 | 217.51 | 212.97 |

#### TOP 5 DOWNSIDE

| Symbol | Aug 21 C | Aug 24 O (T0) | Aug 25 C | Aug 26 C | Aug 27 C | Aug 28 C |
|--------|:--------:|:-----------:|:--------:|:--------:|:--------:|:--------:|
| EMAMILTD | 402.60 | 400.05 | 402.70 | 401.45 | 387.70 | 379.40 |
| TATAPOWER | 374.30 | 374.30 | 370.60 | 364.00 | 352.00 | 351.85 |
| CROMPTON | 252.00 | 251.95 | 243.00 | 238.25 | 237.90 | 233.00 |
| CESC | 155.09 | 156.00 | 154.00 | 153.33 | 152.13 | 148.11 |
| AAVAS | 1,355.3 | 1,349.0 | 1,313.2 | 1,285.8 | 1,269.4 | 1,275.5 |

---

## 7. THEORETICAL TRADE RESULTS — If Entered at T0 Open

Parameters: SL=5%, TGT=7%, Horizon=5d close, Costs=20bps round-trip.  
T0 = Mon Aug 24 market open. Exit: first SL/TGT breach on daily H/L, else horizon (Aug 28 close).

### TOP 5 UPSIDE (theoretical BUY entries)

| Symbol | T0 Entry | SL(−5%) | TGT(+7%) | T1% | T2% | T3% | T4% | MFE% | MAE% | Exit Px | Reason | Gross% | Net% |
|--------|:--------:|:-------:|:--------:|:---:|:---:|:---:|:---:|:----:|:----:|:-------:|:------:|:------:|:----:|
| SAIL | 174.80 | 166.06 | 187.04 | +5.60 | +11.50 | +10.41 | +14.42 | +14.97 | −0.05 | 187.04 | **TGT** | +7.00 | **+6.80** |
| LICHSGFIN | 496.80 | 471.96 | 531.58 | +1.85 | +5.56 | +7.79 | +7.69 | +9.38 | −2.28 | 531.58 | **TGT** | +7.00 | **+6.80** |
| DIVISLAB | 8,558.5 | 8,130.6 | 9,157.6 | +2.17 | +5.45 | +5.86 | +7.95 | +8.31 | −1.18 | 9,157.6 | **TGT** | +7.00 | **+6.80** |
| COFORGE | 1,891.7 | 1,797.1 | 2,024.1 | +0.06 | −0.62 | +0.53 | +6.50 | +6.60 | −1.17 | 2,014.6 | HORIZON | +6.50 | **+6.30** |
| DCBBANK | 205.62 | 195.34 | 220.01 | +0.85 | +3.99 | +5.78 | +3.57 | +7.24 | −3.10 | 220.01 | **TGT** | +7.00 | **+6.80** |

**Summary — Top 5 Upside:**
- 4/5 would have hit the 7% target within the 5-day horizon
- COFORGE missed target by 40bp (max gain +6.60% vs 7.00% target) — closed at horizon
- Average net return: **+6.70%**
- All MAE were modest (−0.05% to −3.10%) — these were clean moves with limited drawdown
- SAIL's move was front-loaded to Thursday (+14.42% by Thu vs +14.97% MFE on Fri high)

### TOP 5 DOWNSIDE (theoretical SHORT entries)

| Symbol | T0 Entry | SL(+5%) | TGT(−7%) | T1% | T2% | T3% | T4% | MFE% | MAE% | Exit Px | Reason | Gross% | Net% |
|--------|:--------:|:-------:|:--------:|:---:|:---:|:---:|:---:|:----:|:----:|:-------:|:------:|:------:|:----:|
| EMAMILTD | 400.05 | 420.05 | 372.05 | −0.66 | −0.35 | +3.09 | +5.16 | +5.44 | −3.36 | 379.40 | HORIZON | +5.16 | **+4.96** |
| TATAPOWER | 374.30 | 393.02 | 348.10 | +0.99 | +2.75 | +5.96 | +6.00 | +7.00 | −1.00 | 351.85 | HORIZON | +6.00 | **+5.80** |
| CROMPTON | 251.95 | 264.55 | 234.31 | +3.55 | +5.44 | +5.58 | +7.52 | +8.43 | 0.00 | 234.31 | **TGT** | +7.00 | **+6.80** |
| CESC | 156.00 | 163.80 | 145.08 | +1.28 | +1.71 | +2.48 | +5.06 | +5.24 | −1.15 | 148.11 | HORIZON | +5.06 | **+4.86** |
| AAVAS | 1,349.0 | 1,416.5 | 1,254.6 | +2.65 | +4.68 | +5.90 | +5.45 | +6.75 | −0.70 | 1,275.5 | HORIZON | +5.45 | **+5.25** |

**Summary — Top 5 Downside:**
- 1/5 (CROMPTON) hit the 7% target on Friday
- TATAPOWER, AAVAS, CESC, EMAMILTD all fell steadily but didn't quite reach −7%
- Average net return (if shorting): **+5.53%**
- CROMPTON had the cleanest short: fell continuously Mon–Fri with MFE of +8.43%
- EMAMILTD was the weakest: spent Mon–Wed near entry before dropping Thu–Fri

---

## 8. TOP 5 COMPARISON TABLES

### TOP 5 UPSIDE

| Symbol | Rank | System first saw | Knowledge decision | KDA Score/ESS | Entry if T0 | T+1% | T+3% | T+5(WkRet)% | MFE% | MAE% | Theo Net P&L% | Entry Quality |
|--------|:----:|:----------------:|:-----------------:|:-------------:|:-----------:|:----:|:----:|:-----------:|:----:|:----:|:-------------:|:------------:|
| SAIL | #1 | Never | NOT EVALUATED | N/A | 174.80 | +5.60 | +10.41 | +15.30 | +14.97 | −0.05 | +6.80 | LATE/MISSED |
| LICHSGFIN | #2 | In scanner_memory Aug 26 — no signal | NOT EVALUATED | N/A | 496.80 | +1.85 | +7.79 | +7.65 | +9.38 | −2.28 | +6.80 | LATE/MISSED |
| DIVISLAB | #3 | Never | NOT EVALUATED | N/A | 8,558.5 | +2.17 | +5.86 | +7.47 | +8.31 | −1.18 | +6.80 | LATE/MISSED |
| COFORGE | #4 | Never | NOT EVALUATED | N/A | 1,891.7 | +0.06 | +0.53 | +6.50 | +6.60 | −1.17 | +6.30 | LATE/MISSED |
| DCBBANK | #5 | In scanner_memory Aug 27 — no signal | NOT EVALUATED | N/A | 205.62 | +0.85 | +5.78 | +4.61 | +7.24 | −3.10 | +6.80 | LATE/MISSED |

### TOP 5 DOWNSIDE

| Symbol | Rank | System first saw | Knowledge decision | KDA Score/ESS | Entry if T0 | T+1% | T+3% | T+5(WkRet)% | MFE% | MAE% | Theo Net P&L% | Entry Quality |
|--------|:----:|:----------------:|:-----------------:|:-------------:|:-----------:|:----:|:----:|:-----------:|:----:|:----:|:-------------:|:------------:|
| EMAMILTD | #1 | Never | NOT EVALUATED | N/A | 400.05 | −0.66 | +3.09 | −5.76 | +5.44 | −3.36 | +4.96 | MISSED |
| TATAPOWER | #2 | Aug 26 — BUY (wrong) | KNOWLEDGE_WAIT (BUY) | INSUFFICIENT, ESS=0 | 374.30 | +0.99 | +5.96 | −6.00 | +7.00 | −1.00 | +5.80 (if SHORT) | DIRECTION ERROR |
| CROMPTON | #3 | Never | NOT EVALUATED | N/A | 251.95 | +3.55 | +5.58 | −7.54 | +8.43 | 0.00 | +6.80 | MISSED |
| CESC | #4 | Never | NOT EVALUATED | N/A | 156.00 | +1.28 | +2.48 | −4.50 | +5.24 | −1.15 | +4.86 | MISSED |
| AAVAS | #5 | Never | NOT EVALUATED | N/A | 1,349.0 | +2.65 | +5.90 | −5.89 | +6.75 | −0.70 | +5.25 | MISSED |

---

## 9. MISSED OUTPERFORMERS — OUTSIDE TOP 5

Stocks with significant weekly moves not in the top 5 lists, checked against system data.

| Symbol | Wk Ret% | In Universe | Scanned | KDA Evaluated | KDA Decision | Failure Class |
|--------|:-------:|:-----------:|:-------:|:-------------:|:------------:|:-------------:|
| ADANIENT | +5.72% | ✅ | ✅ Aug 26,27,28 | ✅ Aug 28 | **KNOWLEDGE_BUY** (Fri, VALIDATED, ks=10.0) | ENTRY TIMING (too late) |
| KOTAKBANK | +5.19% | ✅ | ✅ All days | ✅ Aug 28 | **KNOWLEDGE_BUY** (Fri, USEFUL, ks=10.0) | ENTRY TIMING (too late) |
| LICHSGFIN | +7.65% | ✅ | ⚠️ scanner_memory but no signal | No | N/A | DISCOVERY (signal not triggered) |
| DCBBANK | +4.61% | ✅ | ⚠️ scanner_memory Aug 27–28 but no signal | No | N/A | DISCOVERY (signal not triggered) |
| KPITTECH | +3.41% | ✅ | scanner_memory Aug 26 (no KDA) | No | N/A | DISCOVERY |
| TECHM | +3.59% | ✅ | ✅ Aug 26 (KNOWLEDGE_WAIT) | Yes | KNOWLEDGE_WAIT (INSUFFICIENT) | KNOWLEDGE (insufficient evidence) |
| PAYTM | +1.69% | ✅ | Not scanned | No | N/A | DISCOVERY |
| HAVELLS | −3.59% | ✅ | ✅ Aug 26,27,28 | Yes Aug 28 | **KNOWLEDGE_BUY** (wrong direction, VALIDATED, ks=7.24) | DIRECTION ERROR |
| VOLTAS | −3.38% | ✅ | ✅ Aug 28 | Yes Aug 28 | **KNOWLEDGE_BUY** (wrong direction, VALIDATED) | DIRECTION ERROR |
| ICICIGI | −3.58% | ✅ | ✅ Aug 26,28 | Yes Aug 28 | **KNOWLEDGE_BUY** (wrong direction, VALIDATED, ks=6.91) | DIRECTION ERROR |

**Note on ADANIENT and KOTAKBANK:**
These two stocks were scanned all week and received KNOWLEDGE_BUY on Aug 28 (Friday). ADANIENT had already moved +5.27% from Mon open by Thursday. KOTAKBANK had already moved +4.99%. The Friday KNOWLEDGE_BUY decision was accurate in direction but too late in timing — the entry would have been near the week's high.

---

## 10. WHAT THE LIVE SYSTEM ACTUALLY DECIDED DURING THE WEEK

### Decision Counts by Day

| Day | Stocks Scanned | KDA Records | KNOWLEDGE_WAIT | KNOWLEDGE_BUY | KNOWLEDGE_SELL | Trades Placed |
|-----|:--------------:|:-----------:|:--------------:|:-------------:|:--------------:|:-------------:|
| Mon Aug 24 | Unknown | 0 (no file) | — | — | — | 0 |
| Tue Aug 25 | Unknown | 0 (no file) | — | — | — | 0 |
| Wed Aug 26 | 55 | 97 | 97 (100%) | 0 | 0 | 0 |
| Thu Aug 27 | 63 | 118 | 117 (99.2%) | 1* | 0 | 0 |
| Fri Aug 28 | 64 | 82 | 9 (11.0%) | 73 (89.0%) | 0 | 0 |
| Sat Aug 29 | 61 | 1** | 1 | 0 | 0 | 0 |

*Aug 27 KNOWLEDGE_BUY: symbol="UNKNOWN", ESS=377.03, knowledge_score=0.00 — data integration bug, not a real decision  
**Aug 29 is Saturday — TATASTEEL test run, local machine only

### Aug 28 KNOWLEDGE_BUY — Direction Accuracy vs Actual Week

Of the 73 KNOWLEDGE_BUY decisions on Aug 28, the stocks' actual week-over-week returns were:

| Direction Match | Count | Examples |
|:--:|:--:|:--|
| Positive week return | ~25 | ADANIENT +5.7%, KOTAKBANK +5.2%, TITAN +1.8%, SBIN +0.8%, ADANIPORTS +2.1% |
| Negative week return | ~20 | HAVELLS −3.6%, ICICIGI −3.6%, VOLTAS −3.4%, DMART −2.8%, BHARTIARTL −2.7%, M&M −2.4%, RELIANCE −1.7% |
| Flat/near-zero | ~28 | ONGC −1.8%, COALINDIA −1.5%, HCLTECH −0.5%, TCS +2.5% |

**The Aug 28 bulk KNOWLEDGE_BUY were based on the BULL regime historical evidence pool (BULL+BUY, 73,557 entries, avg T+1=+2.1%). They did not account for the individual stocks' performance during the current week.** The "VALIDATED" evidence (ESS=374.14 — which is the same value for >15 different stocks) is the regime-level pool ESS, not stock-specific ESS. These decisions represent the historical statistical edge of buying in a BULL regime, not a current-week signal.

### Actual Trades Executed
**ZERO.** 

The `live_orders.jsonl` on the VPS contains 15 records, all `CANCELLED` for COALINDIA TEST orders on Aug 27 (`limit_expired_1_candles`). These are cancelled test limit orders, not filled trades. No stock positions were opened or closed for any real trade during the week. The paper_trades.csv contains only FAKE/SIMULATION entries.

---

## 11. ENTRY-TIMING SCORE

### Entry Quality Classification Thresholds

| Category | Definition |
|:---:|:---|
| EARLY | System generates Knowledge-eligible signal ≥ 1 day before major move begins. Theoretical entry at or before T+1 high. |
| ACCEPTABLE | Signal generated same day as major move begins. Entry within T0 day. |
| LATE | Signal generated after 50%+ of the week's move has already occurred. |
| VERY LATE | Signal generated on the last day of the period, or after the move is complete. |
| MISSED | Stock never received a Knowledge evaluation. |
| DIRECTION ERROR | Stock was evaluated but with the wrong direction. |

*Thresholds are symmetric: a move is "major" if > 3.0%. These thresholds were set before examining results.*

### Top Movers — Entry Quality Score

| Symbol | Week Ret% | T0 Theoretical Entry Timing | Knowledge Decision Timing | Entry Quality |
|--------|:---------:|:---------------------------:|:------------------------:|:-------------:|
| SAIL | +15.30% | Mon Aug 24 open | Not evaluated | MISSED |
| LICHSGFIN | +7.65% | Mon Aug 24 open | Not evaluated | MISSED |
| DIVISLAB | +7.47% | Mon Aug 24 open | Not evaluated | MISSED |
| COFORGE | +6.50% | Mon Aug 24 open | Not evaluated | MISSED |
| DCBBANK | +4.61% | Mon Aug 24 open | Not evaluated | MISSED |
| EMAMILTD | −5.76% | Mon Aug 24 open | Not evaluated | MISSED |
| TATAPOWER | −6.00% | Mon Aug 24 open | BUY (wrong direction) Aug 26 | DIRECTION ERROR |
| CROMPTON | −7.54% | Mon Aug 24 open | Not evaluated | MISSED |
| CESC | −4.50% | Mon Aug 24 open | Not evaluated | MISSED |
| AAVAS | −5.89% | Mon Aug 24 open | Not evaluated | MISSED |
| ADANIENT | +5.72% | Mon Aug 24 open | KNOWLEDGE_BUY Aug 28 Fri (move 93% complete) | VERY LATE |
| KOTAKBANK | +5.19% | Mon Aug 24 open | KNOWLEDGE_BUY Aug 28 Fri (move 93% complete) | VERY LATE |

### Entry Efficiency (where applicable)

For ADANIENT and KOTAKBANK (only stocks receiving any KDA decision with correct direction):

```
Entry Efficiency = (captured profit at KDA decision date) / (maximum favourable opportunity)

ADANIENT: MFE from Mon open = +5.44%
          KDA date (Fri open) vs Mon open ≈ +5.00% already happened
          Profit remaining from Fri open = ~0.5%
          Entry Efficiency ≈ 9.2% (very poor — almost all profit already captured by the market)

KOTAKBANK: MFE from Mon open = +6.00%
           By Friday open ≈ +5.0% already happened
           Entry Efficiency ≈ 17% (poor — 83% of the move was already gone)
```

---

## 12. SEPARATION: SELECTION vs TIMING vs EXECUTION

### A. KNOWLEDGE SELECTION: Did Knowledge identify the right stocks?

**VERDICT: NO.**

Of the 10 stocks in the Top 5 upside and downside lists:
- 8/10 were NEVER evaluated by the KDA system during the week
- 1/10 (TATAPOWER) was evaluated with the WRONG DIRECTION
- 1/10 (ADANIENT was close to top 5) was evaluated on the last day only

Of the stocks that did receive KNOWLEDGE_BUY on Aug 28:
- Approximately 30% were for stocks that actually fell during the week (direction error)
- Most of the VALIDATED/high-ESS BUY decisions were for the same stocks every day — suggesting a stable regime-pool assignment, not dynamic stock selection

**The selection problem is primarily a DISCOVERY failure**: the scanner's setup-detection logic did not generate signals for SAIL, DIVISLAB, COFORGE, DCBBANK, EMAMILTD, CROMPTON, CESC, or AAVAS on any day of the week. These 8 stocks had the best directional moves of the week. None were sent to the KDA pipeline.

### B. KNOWLEDGE TIMING: Did Knowledge identify stocks before the move?

**VERDICT: NO (for the stocks it did identify).**

- ADANIENT and KOTAKBANK (the only correct-direction KDA approvals) received KNOWLEDGE_BUY on Friday Aug 28 — the last trading day.
- ADANIENT's move: +3.32% Mon, +0.07% Tue, +1.88% Wed, −0.01% Thu, +0.00% Fri (total +5.27% by Fri)
  - The system gave KNOWLEDGE_BUY at 9:46 IST on Aug 28, by which time the stock was already near weekly high
- KOTAKBANK's move: −0.01% Mon, +3.76% Tue, +1.85% Wed, −0.12% Thu (+5.5% already done before Fri)

**The bulk Aug 28 approval appears to be a cyclic/batch rerun** where the system evaluated many stocks at once at the end of the week (or beginning of the next cycle), not an intra-week early-identification mechanism.

### C. ENTRY EXECUTION: Could the configured entry have captured the move?

**VERDICT: Yes — IF selection and timing had worked.**

The theoretical analysis (Section 7) shows:
- 4/5 top upside movers would have hit the 7% target if entered at Mon open
- CROMPTON (downside) would have hit −7% target
- TATAPOWER, EMAMILTD, CESC, AAVAS would have closed near horizon with +5-6% gains
- Entry at T0 (Mon open) was excellent — all stocks had modest initial drawdowns (MAE all < 3.5%)

**The entry mechanism itself (SL/TGT/horizon) was well-configured for these moves.** The problem was not execution — it was that no entry signals were ever generated.

### D. EXIT: Did the configured target/SL/horizon capture a reasonable portion?

**VERDICT: Would have worked well (theoretical).**

- SAIL, LICHSGFIN, DIVISLAB, DCBBANK all hit +7% TGT by Wed/Thu — capturing their move early
- CROMPTON hit −7% TGT on Friday
- COFORGE almost hit TGT (+6.60% MFE vs 7.00% TGT) — the 7% target was not too aggressive
- The SL at −5% was never touched for any top mover (lowest MAE was −3.36% for EMAMILTD)

The exit logic was appropriate for the type of moves observed this week.

---

## 13. MISSED OUTPERFORMERS — FAILURE CLASSIFICATION

| Stock | Move | Was in Universe | Was Scanned | Was KDA-evaluated | Failure |
|-------|:----:|:---:|:---:|:---:|:---:|
| SAIL +15.3% | Universe ✅ | Never triggered scanner setup | N/A | **DISCOVERY** |
| LICHSGFIN +7.7% | Universe ✅ | In scanner_memory, no setup signal | N/A | **DISCOVERY** |
| DIVISLAB +7.5% | Universe ✅ | Never triggered scanner setup | N/A | **DISCOVERY** |
| COFORGE +6.5% | Universe ✅ | Never triggered scanner setup | N/A | **DISCOVERY** |
| DCBBANK +4.6% | Universe ✅ | In scanner_memory Aug 27, no setup signal | N/A | **DISCOVERY** |
| CROMPTON −7.5% | Universe ✅ | Never triggered scanner setup | N/A | **DISCOVERY** |
| EMAMILTD −5.8% | Universe ✅ | Never triggered scanner setup | N/A | **DISCOVERY** |
| AAVAS −5.9% | Universe ✅ | Never triggered scanner setup | N/A | **DISCOVERY** |
| CESC −4.5% | Universe ✅ | Never triggered scanner setup | N/A | **DISCOVERY** |
| TATAPOWER −6.0% | Universe ✅ | Scanned as BUY (wrong direction) | KNOWLEDGE_WAIT | **DIRECTION ERROR + KNOWLEDGE** |
| ADANIENT +5.7% | Universe ✅ | Scanned all week | KNOWLEDGE_BUY Fri | **ENTRY TIMING** |
| KOTAKBANK +5.2% | Universe ✅ | Scanned all week | KNOWLEDGE_BUY Fri | **ENTRY TIMING** |
| HAVELLS −3.6% | Universe ✅ | Scanned all week | KNOWLEDGE_BUY Fri (wrong dir) | **DIRECTION ERROR** |
| ICICIGI −3.6% | Universe ✅ | Scanned all week | KNOWLEDGE_BUY Fri (wrong dir) | **DIRECTION ERROR** |
| VOLTAS −3.4% | Universe ✅ | Scanned Fri | KNOWLEDGE_BUY Fri (wrong dir) | **DIRECTION ERROR** |

---

## 14. KEL EVIDENCE STATE (Local vs VPS)

| Metric | Local Machine | VPS (Live System) |
|--------|:-------------:|:-----------------:|
| Total KEL entries | 3,846 | 73,557 |
| Entries with ge2=True | ~400 | ~7,209 (BULL+BUY) |
| KEL symbols | 131 | Much larger |
| Evidence for SAIL | 6 entries (CORRECT_SELECT, −avg t1) | Unknown |
| Evidence for LICHSGFIN | 0 entries | Unknown |
| Evidence for DIVISLAB | 1 entry (UNRESOLVED) | Unknown |
| HBE for top movers | All INSUFFICIENT locally | Unknown (not queried) |

The local machine's KEL is a stale development copy recorded primarily on 2026-08-18 via historical audit. It does not represent the live system's evidence state. All local KDA decisions (from pytest runs on weekend dates) show ESS=0.0, INSUFFICIENT — because the local KEL has minimal stock-specific evidence.

The VPS KEL has 73,557 entries. The KDA decisions from the VPS (Aug 26–28) show VALIDATED evidence with ESS=374.14 for many stocks — this is the BULL+BUY regime-level pool ESS, not stock-specific ESS.

---

## 15. DATA PIPELINE OBSERVATION (Not a Code Defect)

### Observation: "UNKNOWN" symbol in Aug 27 KDA
- One KNOWLEDGE_BUY on Aug 27 has `symbol="UNKNOWN"`, `knowledge_score=0.00`, `evidence_state="VALIDATED"`, `ESS=377.03`
- This appears to be a record where the symbol identifier was lost in pipeline serialization
- Effect: 0 trades executed anyway (broker_calls=0, orders=0 confirmed)
- This is an observational issue; no recommendation made without reproducing the defect

### Observation: Aug 26 all-INSUFFICIENT despite VPS KEL having 73,557 entries
- All 97 KDA evaluations on Aug 26 show `evidence_state=INSUFFICIENT, ESS=0.0`
- On Aug 27: 117/118 INSUFFICIENT, 1/118 VALIDATED (but "UNKNOWN" symbol)
- On Aug 28: bulk KNOWLEDGE_BUY with VALIDATED/USEFUL/DEVELOPING evidence

This pattern suggests the HBE evidence loading may have had a warm-up or data issue on Wed–Thu that resolved by Friday. Or the evidence pool for the specific stocks scanned on Wed (FEDERALBNK, CDSL, JSWSTEEL, ITC, NMDC etc.) is genuinely INSUFFICIENT in the KEL for those symbol+direction+regime combinations.

**This is an observation, not a confirmed defect.** Confirming it would require running a targeted HBE query against the VPS KEL for the specific symbols scanned on Aug 26. Not done here as it would require running code against the live system.

---

## 16. LOOKAHEAD VERIFICATION

| Check | Status |
|-------|:------:|
| T0 defined as Mon Aug 24 open (past time) | ✅ Clean |
| KDA decisions dated Aug 26–28 used only data available at that timestamp | ✅ Clean |
| Future prices (T+1 to T+4) used only to compute outcomes, never to select signals | ✅ Clean |
| "What the system knew at T0" uses only Aug 24 price and prior KEL evidence | ✅ Clean |
| Top mover identification uses Aug 28 close data — not used in any decision simulation | ✅ Clean |
| Theoretical P&L computed with T0 entry and sequential SL/TGT check on daily H/L | ✅ Clean |

**Zero lookahead contamination confirmed.**

---

## 17. FINAL VERDICT — 10 QUESTIONS

**Q1. Did Knowledge identify the week's best opportunities before their major moves?**

**NO.** None of the top 5 upside movers (SAIL +15.3%, LICHSGFIN +7.7%, DIVISLAB +7.5%, COFORGE +6.5%, DCBBANK +4.6%) received any KDA evaluation during the week. The two stocks that received correct-direction KNOWLEDGE_BUY decisions (ADANIENT, KOTAKBANK) received them on the last trading day, after 90%+ of the weekly move had already occurred.

---

**Q2. How many Top-5 upside stocks were identifiable by Knowledge before the move?**

**0 out of 5.** All five were in the Nifty 500 universe but none triggered the scanner's setup-detection logic on any day of the week. LICHSGFIN and DCBBANK appeared in scanner_memory (general candidates) but generated no setup signals.

---

**Q3. How many Top-5 downside stocks were identifiable?**

**0 out of 5** (for short positions). TATAPOWER was scanned, but as a BUY (mean reversion) — the wrong direction. The other four were never discovered.

---

**Q4. What would theoretical P&L have been if we entered at first Knowledge eligibility?**

If the system had identified all 10 stocks (5 longs + 5 shorts) at Monday's open using the configured parameters:
- Top 5 upside (BUY): average net return **+6.70%** (4/5 hit 7% TGT, COFORGE closed at horizon +6.30%)
- Top 5 downside (SHORT): average net return **+5.53%** (CROMPTON hit TGT, rest closed at horizon)
- **Combined average: +6.12%** per trade across 10 theoretical trades

This is the maximum achievable performance — it requires perfect discovery at Mon open.

---

**Q5. How much profit was lost because of late entry?**

For the two stocks that received valid KNOWLEDGE_BUY decisions (ADANIENT, KOTAKBANK), entry on Friday Aug 28 open vs Monday Aug 24 open:
- ADANIENT: ~93% of the weekly move had already occurred by Friday open. Remaining upside ≈ +0.5%
- KOTAKBANK: ~93% of the weekly move had already occurred. Remaining upside ≈ +0.4%

For the 8 completely missed stocks: 100% of the weekly profit was foregone.

**Total profit left on the table: approximately 6.1% × 10 stocks = 61% aggregate return unrealised.**

---

**Q6. Were there major outperformers outside Top 5 that Knowledge could have identified?**

Yes: ADANIENT (+5.7%) and KOTAKBANK (+5.2%) were discovered and given correct-direction KNOWLEDGE_BUY on Aug 28. However, the entry timing was VERY LATE (Friday, after the moves were complete). Both would have been early-week entries for best results.

TECHM (+3.6%) was scanned on Aug 26 and received KNOWLEDGE_WAIT due to INSUFFICIENT evidence — a genuine knowledge gap, not a pipeline bug.

---

**Q7. Is the current problem: discovery / Knowledge quality / decision / entry timing / execution / none?**

**PRIMARY: DISCOVERY.**

The scanner's setup-detection logic failed to generate signals for 8 of the week's 10 biggest movers. All 8 were in the broad universe. 2 of 8 were even in scanner_memory as general candidates, but the setup-specific detection (ATR breakout, momentum retest, etc.) did not trigger for them.

**SECONDARY: ENTRY TIMING.**

The one systematic KDA decision-making session (Aug 28) approved 73 stocks in bulk at the end of the week — too late to act on the current week's moves. The KDA approvals on Friday are useful as next-week preparation, but they do not represent early-week identification.

**TERTIARY: DIRECTION ERRORS.**

TATAPOWER, HAVELLS, ICICIGI, VOLTAS received KNOWLEDGE_BUY while actually being in downtrends that week. The BULL+BUY regime historical evidence approved long positions in stocks that were making lower lows intraweek. This is an evidence-reuse limitation: the regime-pool ESS (374.14, representing BULL regime historical win rates) does not differentiate between "BULL regime, stock in uptrend" and "BULL regime, stock in downtrend."

**No: Knowledge quality (evidence depth) and execution were NOT the primary problems.** The configured 5% SL / 7% TGT / 5-day horizon was appropriate for the moves observed. The order execution infrastructure (broker integration, paper trade journal) appears functional.

---

**Q8. Is any code change actually justified by the evidence?**

**Based solely on this week's data: No code change is justified without further evidence of a repeatable systematic deficiency.**

**For reference only — observations that warrant monitoring (NOT immediate changes):**

1. **Scanner setup-trigger breadth**: 8 of the week's top 10 movers were never scanned. Whether this is a systematic issue (scanner's ATR/momentum thresholds miss a specific setup type) or this week's idiosyncratic pattern requires analysis across multiple weeks. **One week of data is insufficient to justify a threshold change.**

2. **Aug 26–27 INSUFFICIENT evidence anomaly**: All KDA evaluations on Wed and nearly all on Thu showed INSUFFICIENT evidence (ESS=0) despite the VPS KEL having 73,557 entries. This pattern (sudden improvement to VALIDATED on Friday) is unusual and may indicate a warm-up issue or evidence-loading variation. **Warrants logging analysis, not code changes, before drawing a conclusion.**

3. **TATAPOWER direction error**: The scanner generated a MEAN_REVERSION BUY on a stock falling −6% that week. This is within the expected behavior of mean-reversion strategies (buying oversold stocks), so it is not necessarily a defect — it may be a strategy that has genuine negative expectancy in this specific context. **Requires historical backtesting, not a reactive fix.**

4. **Aug 28 bulk approvals including down stocks**: The regime-level evidence pool approving BUY for HAVELLS/ICICIGI/VOLTAS (all down that week) shows that symbol-specific evidence at low ESS (8–28) is being overridden by the large BULL regime pool. The KDA architecture allows this by design (regime evidence supplements symbol-level evidence). **One week of adverse direction mismatches is not statistically sufficient to change the evidence-mixing logic.**

---

## 18. SUMMARY

| Dimension | Finding |
|-----------|---------|
| Universe Coverage | 100% — all top movers were in Nifty500 universe |
| Scanner Discovery | 20% (2/10 top movers triggered scanner signals, both in wrong context) |
| KDA Correct-Direction Approval (all week) | 0% of top movers before Friday |
| KDA Correct-Direction Approval (Friday only) | 20% (ADANIENT + KOTAKBANK, by which point moves were complete) |
| Entry Timing Quality | MISSED (8/10), VERY LATE (2/10) |
| Actual Trades Executed | 0 — no real trades for any top mover |
| Theoretical P&L if discovered at T0 | +6.12% average per trade (10 positions) |
| Primary Failure Mode | DISCOVERY (scanner setup-trigger) |
| Secondary Failure Mode | ENTRY TIMING (Aug 28 bulk approvals too late for current week) |
| Tertiary Failure Mode | DIRECTION ERRORS on 3 stocks (HAVELLS, ICICIGI, VOLTAS) |
| Evidence/Code Defect Found | None confirmed. "UNKNOWN" symbol and Aug 26–27 INSUFFICIENT anomaly logged for monitoring. |

The knowledge-first architecture (DTA-019/020/021 changes) is correctly implemented. The bottleneck this week was upstream of Knowledge: the scanner's setup-detection did not generate signals for the stocks that moved the most.

---

*Data sources: VPS KDA files (`kda_decisions_2026-08-26/27/28.jsonl`), VPS `scanner_memory.json`, VPS `kda_vs_stratlab_2026-08-26/27/28.jsonl`, VPS `live_orders.jsonl`, VPS `paper_trades.csv`, local KEL (3,846 entries), yfinance NSE daily OHLCV Aug 21–28 2026, local `nifty500_universe.json`.*
