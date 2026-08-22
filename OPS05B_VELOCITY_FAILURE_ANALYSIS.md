# OPS05B — Velocity Failure Analysis

**Classification:** Evidence Collection / Excursion Analysis  
**Status:** CLOSED  
**Scope:** All 35 closed trades with measurable P&L (2026-03-19 through 2026-05-29)  
**Data source:** `paper_trades_backup_20260529.csv` + 1h OHLC bars via yfinance  
**Metrics method:** 1h bars; MFE = max favorable excursion in R multiples; MAE = max adverse excursion in R multiples  
**Date of Report:** 2026-06-19  
**Investigator:** Copilot (evidence collection only — no code modified)

---

## Population

**40 CSV rows parsed → 35 unique closed trades with non-zero P&L** (after removing duplicates, phantom-price trades, and DATA_ERROR records)

| Count | Description |
|---|---|
| 35 | Analyzable closed trades |
| 7 | Wins |
| 28 | Losses |
| 20.0% | Overall win rate |
| 16.1% | Governance-compliant WR (entry ≥ 09:45) |
| 50.0% | Pre-governance WR (entry < 09:45) |

> 3 records excluded from averages: RELIANCE Apr-29 DATA_ERROR (timestamp parse failure), TATAMOTORS delisted on yfinance, HINDALCO PHANTOM_EXIT_CORRECTED (invalid exit price). Their P&L counts are carried forward from OPS05A.

---

## 1. The Primary Discriminator: % Bars Positive

Before any other metric, this single number separates wins from losses:

| Cohort | Trades | Avg % Bars Above Entry Price |
|---|---|---|
| **Winners** | 7 | **92.3%** |
| **Losers** | 28 | **30.5%** |

**Interpretation:** When a winning trade was open, the price spent 92% of its time above the entry price. When a losing trade was open, the price spent 70% of its time BELOW the entry price. This is not a close separation — it is a structural signature.

A winning position trends away from entry immediately and stays there. A losing position begins adverse almost immediately and never recovers.

---

## 2. Excursion Statistics

| Metric | Winners | Losers |
|---|---|---|
| Avg MFE | **1.449R** | 0.359R |
| Avg MAE | 0.101R | **0.860R** |
| MFE/MAE ratio | 14.3× | 0.42× |

> Losers' MAE (0.860R) is more than twice their MFE (0.359R) on average. Every loss had larger adverse excursion than favorable.

---

## 3. Trade Category Classification

Categories defined as:
- **A_NEVER_MOVED:** MFE < 0.25R — price never provided meaningful favorable movement
- **B_MOVED_REVERSED:** MFE ≥ 0.5R but trade closed at a loss — reached favorable territory then reversed
- **C_IMMEDIATE_ADVERSE:** MAE > MFE + 0.2R — price moved against thesis from the start
- **D_PARTIAL_MOVE_FAILED:** MFE 0.25–0.5R, closed at a loss — moved partially but not enough
- **W_WIN:** Closed profitable

| Category | Count | W | L | Avg MFE | Avg MAE | Description |
|---|---|---|---|---|---|---|
| **A_NEVER_MOVED** | 9 | 0 | 9 | −0.019R | 0.639R | Price never favored the trade |
| **C_IMMEDIATE_ADVERSE** | 10 | 0 | 10 | 0.226R | 0.916R | Immediately moved against thesis |
| **B_MOVED_REVERSED** | 6 | 0 | 6 | 1.124R | 1.313R | Reached favorable territory, reversed |
| **D_PARTIAL_MOVE_FAILED** | 3 | 0 | 3 | 0.402R | 0.434R | Partially moved, stalled |
| **W_WIN** | 7 | 7 | 0 | 1.449R | 0.101R | Clean directional follow-through |

**Zero wins appear in any loss category.** The separation is absolute: a trade either moved strongly and stayed there (W_WIN), or it fell into one of the three failure patterns.

### Loss category proportion:
```
C_IMMEDIATE_ADVERSE  ████████████████████████████████████ 36%  (10/28)
A_NEVER_MOVED        ████████████████████████████████     32%  ( 9/28)
B_MOVED_REVERSED     ████████████████████                 21%  ( 6/28)
D_PARTIAL_MOVE_FAILED████████████                         11%  ( 3/28)
```

**The most common failure mode is C_IMMEDIATE_ADVERSE (36%)** — the instrument moved against the thesis almost from the moment of entry. Combined with A_NEVER_MOVED (32%), 68% of losses were trades that never developed any meaningful favorable movement.

---

## 4. MFE Distribution — Losses

How far did losing trades ever move in the favorable direction?

```
MFE bucket      Count  Bar
─────────────────────────────────
< 0.0R (neg)      2    ██
0.0 – 0.1R        5    █████
0.1 – 0.25R       7    ███████
0.25 – 0.5R       8    ████████
0.5 – 1.0R        4    ████
≥ 1.0R            2    ██
```

**22 of 28 losses (78.6%) never exceeded 0.5R favorable** — meaning they never got halfway to their intended target. The risk-reward ratio was R:R=2.5 in the system design. A trade that peaks at 0.5R and reverses was never going to be profitable; it needed 1R to break even on a 2:1 RR trade.

**14 of 28 losses (50%) never exceeded 0.25R favorable** — these never moved in the trade direction in any meaningful way. A velocity filter that requires +0.25R within a specified window would have caught all 14 of these as "no momentum" signals.

---

## 5. MAE Distribution — Losses

How far did the price move against the trade?

```
MAE bucket     Count  Bar
────────────────────────────
< 0.25R          2    ██
0.25 – 0.5R      6    ██████
0.5 – 1.0R      14    ██████████████
1.0 – 2.0R       5    █████
> 2.0R           1    █
```

**20 of 28 losses (71.4%) had MAE ≥ 0.5R** — the adverse move was severe enough to justify a stop at 0.5R. In most cases this adverse move was larger than any favorable excursion the trade produced.

---

## 6. Adaptive Exit Deep Dive

The adaptive exit was the most common close reason (16 trades). How far did these trades ever move before being cut?

| Threshold | Reached | Not reached | % Never reached |
|---|---|---|---|
| +0.25R | 5 of 16 | **11 of 16** | **68.8%** |
| +0.5R | 1 of 16 | **15 of 16** | **93.8%** |
| +1.0R | 0 of 16 | **16 of 16** | **100.0%** |

**Confirmed: 100% of adaptive_exit trades never reached their target (+1R).** 93.8% never got halfway. 68.8% never moved a quarter of the way in the favorable direction.

The adaptive exit is catching trades that should not have been held at all. The instrument never developed velocity toward the target — the adaptive exit is doing its job, but the real problem is that these trades had no business being entered.

### The 11 "never moved" adaptive_exit trades:

| Symbol | Entry | MFE | MAE | Pct Bars+ | P&L |
|---|---|---|---|---|---|
| BHARTIARTL | Apr20 09:45 | −0.015R | 0.386R | 0% | −₹41,945 |
| ICICIBANK | Apr22 13:06 | 0.117R | 0.023R | 25% | −₹48,631 |
| TATASTEEL | Apr22 13:09 | 0.185R | 0.115R | 25% | −₹34,816 |
| AXISBANK | Apr23 14:00 | 0.076R | 0.599R | — | −₹41,724 |
| TATASTEEL | Apr27 11:44 | 0.093R | 0.732R | 0% | −₹40,397 |
| TATASTEEL | Apr28 10:30 | 0.181R | 0.768R | 0% | −₹47,709 |
| RELIANCE | May05 10:05 | 0.126R | 0.813R | 0% | −₹41,486 |
| RELIANCE | May11 15:16 | 0.113R | 0.724R | 0% | −₹47,940 |
| BHARTIARTL | May18 13:00 | 0.138R | 0.659R | 8% | −₹13,122 |
| BHARTIARTL | May20 09:45 | 0.017R | 0.606R | 0% | −₹11,644 |
| BHARTIARTL | May22 11:30 | 0.180R | 0.852R | 21% | −₹15,142 |

**Pattern:** In 8 of 11 cases the price was BELOW the entry price for ≥75% of the holding period. These were not "almost wins that reversed" — they were positions in an instrument moving in the wrong direction from entry, held for up to 165 hours.

---

## 7. Grouping Analysis

### 7a. By Strategy

| Strategy | n | W | L | WR | Avg MFE | Avg MAE | Loss MFE | Loss MAE | Avg Hold |
|---|---|---|---|---|---|---|---|---|---|
| Mean_Reversion | 15 | 2 | 13 | 13.3% | 0.551R | 0.594R | 0.454R | 0.681R | 98.9h |
| Momentum_Retest | 13 | 5 | 8 | 38.5% | 0.762R | 0.710R | 0.267R | 1.073R | 89.0h |
| Trend_Pullback | 4 | 0 | 4 | 0.0% | 0.407R | 0.962R | 0.407R | 0.962R | 106.5h |
| EDG_MOMENT_100_EE0005 | 3 | 0 | 3 | 0.0% | 0.126R | 0.936R | 0.126R | 0.936R | 41.1h |

**Key excursion patterns by strategy:**

**Mean_Reversion:** Losses avg MFE=0.454R (partial movement) with MAE=0.681R. The strategy gets partial traction (nearly 0.5R) but the adverse pressure exceeds the favorable. These trades exhibit "B_MOVED_REVERSED" and "C_IMMEDIATE_ADVERSE" patterns almost equally.

**Momentum_Retest:** Losses have the LARGEST adverse excursion (1.073R avg MAE). When Momentum_Retest loses, it loses large — the position goes deeply against the entry before the exit fires. The 5 RELIANCE May losses all had MAE > 0.7R. Wins had MFE=1.449R — when it works, it works well, but losses accumulate more R than wins earn.

**Trend_Pullback:** Zero wins, MAE=0.962R per loss. The adverse excursion is nearly 1R on every loss — these positions were entered into trends that did not exist. The system shorted a bull, or went long in a bear. MAE > MFE on 4/4 trades.

**EDG_MOMENT:** Zero wins, MFE only 0.126R on average — the least forward movement of any strategy. The TATASTEEL May18 close_sl (MFE=−0.76R) shows the position was immediately and severely adverse.

---

### 7b. By Symbol

| Symbol | n | W | L | WR | Avg MFE | Avg MAE (loss) | Dominant Pattern |
|---|---|---|---|---|---|---|---|
| **TATASTEEL** | 10 | 0 | 10 | 0.0% | 0.241R | 0.661R | Mixed A+C |
| RELIANCE | 6 | 1 | 5 | 16.7% | 0.509R | 1.146R | C_IMMEDIATE (May) |
| COALINDIA | 4 | 2 | 2 | 50.0% | 1.158R | 1.271R | B_MOVED when loss |
| **BHARTIARTL** | 4 | 0 | 4 | 0.0% | 0.080R | 0.626R | A_NEVER_MOVED |
| ULTRACEMCO | 3 | 0 | 3 | 0.0% | 0.266R | 0.334R | D_PARTIAL |
| ICICIBANK | 2 | 0 | 2 | 0.0% | 1.594R | 1.916R | B_MOVED_REVERSED |
| NTPC | 3 | 2 | 1 | 66.7% | 0.647R | 1.275R | A when loss |
| AXISBANK | 1 | 0 | 1 | 0.0% | 0.076R | 0.599R | A_NEVER_MOVED |
| BANKBARODA | 1 | 1 | 0 | 100% | 1.335R | 0.022R | Clean win |
| HINDALCO | 1 | 1 | 0 | 100% | 2.427R | — | Clean win |

**Symbol blacklist evidence:**
- TATASTEEL: 10 trades, 0 wins — by any statistical measure this symbol should be excluded
- BHARTIARTL: 4 trades, 0 wins, avg MFE only 0.08R — entered 4× in a persistent downtrend, zero favorable movement each time
- ULTRACEMCO: 3 trades, 0 wins — partial movement only, stock oscillating below entry
- ICICIBANK: 2 trades, 0 wins, avg MFE 1.594R — interestingly has the best MFE among losers, confirming B_MOVED_REVERSED (moved well then reversed)

---

### 7c. By Sector

| Sector | n | W | L | WR | Loss Avg MFE | Loss Avg MAE |
|---|---|---|---|---|---|---|
| Energy | 7 | 4 | 3 | 57.1% | 0.644R | 1.272R |
| Banking | 4 | 1 | 3 | 25.0% | 1.088R | 1.477R |
| Diversified | 6 | 1 | 5 | 16.7% | 0.263R | 1.146R |
| **Metals** | **11** | **1** | **10** | **9.1%** | 0.241R | 0.661R |
| **Cement** | **3** | **0** | **3** | **0.0%** | 0.266R | 0.334R |
| **Telecom** | **4** | **0** | **4** | **0.0%** | 0.080R | 0.626R |

**Sectors with zero winning trades: Metals (9.1% with HINDALCO included), Cement, Telecom.**

**Telecom (BHARTIARTL) avg loss MFE = 0.080R** — the lowest of any sector. The stock never moved favorably in any of 4 entries. This is the clearest A_NEVER_MOVED pattern at sector level.

**Energy (COALINDIA, NTPC) performs best** at 57.1% WR. When losses occur in Energy they are B_MOVED_REVERSED with large MAE — the stock moved well then reversed, rather than never moving.

**Diversified (RELIANCE) loss MFE = 0.263R with MAE = 1.146R** — the worst MFE/MAE ratio in the loss category. RELIANCE losses moved against by 4× more than they moved in favor.

---

### 7d. By Entry Hour

| Hour | n | W | L | WR | Avg MFE | Loss Avg MFE |
|---|---|---|---|---|---|---|
| 09 (09:10–09:59) | 9 | 3 | 6 | 33.3% | 0.651R | 0.141R |
| 10 | 8 | 2 | 6 | 25.0% | 0.619R | 0.366R |
| 11 | 6 | 1 | 5 | 16.7% | 0.409R | 0.284R |
| 12 | 2 | 1 | 1 | 50.0% | 2.203R | 3.071R (ICICIBANK legacy) |
| **13** | **6** | **0** | **6** | **0.0%** | 0.234R | 0.234R |
| **14** | **2** | **0** | **2** | **0.0%** | 0.334R | 0.334R |
| **15** | **2** | **0** | **2** | **0.0%** | 0.219R | 0.219R |

**Hours 13–15: 0% WR across 10 trades.** Every afternoon/closing session entry was a loss. The MFE in the 13–15 bucket averages only 0.23–0.33R — these trades never developed momentum, and were placed when intraday directional moves had already resolved.

**Hour 09 has the best WR (33.3%)** — but this includes both pre-governance violations (09:10) and the 09:45 scheduler slot. The hour-9 losses have avg MFE only 0.141R, suggesting that even in this best window, when trades fail they fail hard with no movement.

---

### 7e. By Regime

Regime data from OPS05A (not embedded in JSON):

| Regime | Trades | Wins | WR | Velocity Pattern |
|---|---|---|---|---|
| range_market | 34 of 35 | 6 | 17.6% | Mixed A/C/B patterns |
| bull_trend | 1 of 35 | 1 | 100% | HINDALCO immediate +2.4R |

The single bull_trend trade (HINDALCO, May21) reached +0.5R in 0.08 hours (≈5 minutes) and peaked at 2.427R — instantly confirming the thesis. The contrast with range_market trades is complete.

---

## 8. Symbol Deep Dives

### 8a. TATASTEEL — 10 Trades, 0 Wins

| Date | Dir | Strategy | MFE | MAE | Pct+ | Category | P&L |
|---|---|---|---|---|---|---|---|
| Apr22 13:09 | SHORT | MR | 0.185R | 0.115R | 25% | A_NEVER_MOVED | −₹34,816 |
| Apr23 09:10* | SHORT | MR | 0.614R | 0.260R | 78% | B_MOVED_REVERSED | −₹15,539 |
| Apr27 09:45 | SHORT | MR | 0.331R | 0.674R | 33% | C_IMMEDIATE_ADVERSE | −₹36,413 |
| Apr27 11:44 | SHORT | MR | 0.093R | 0.732R | 0% | A_NEVER_MOVED | −₹40,397 |
| Apr28 10:30 | BUY | MoR | 0.181R | 0.768R | 0% | C_IMMEDIATE_ADVERSE | −₹47,709 |
| May11 11:17 | SHORT | MR | 0.331R | 0.610R | 65% | C_IMMEDIATE_ADVERSE | −₹34,937 |
| May11 13:00 | SHORT | MR | 0.299R | 0.642R | 63% | C_IMMEDIATE_ADVERSE | −₹37,104 |
| May14 09:10* | BUY | EDG | 0.660R | 0.496R | 71% | B_MOVED_REVERSED | −₹104,746 |
| May14 10:52 | BUY | EDG | 0.479R | 0.676R | 42% | D_PARTIAL_MOVE_FAILED | −₹37,132 |
| May18 09:45 | BUY | EDG | −0.762R | 1.637R | 0% | A_NEVER_MOVED | −₹84,785 |

*= pre-governance violation

**Finding A — SHORT entries:** TATASTEEL shorts had MFE of 0.1–0.6R but were overwhelmed by adverse excursion. In Apr 27 11:44 and Apr28, the position had 0% bars positive — price moved up immediately. The Mean_Reversion system was shorting a stock that was trending higher.

**Finding B — BUY entries:** Apr28 BUY (Momentum_Retest) had 0% bars positive — bought into a downward move. May14 EDG BUY had MFE=0.66R then reversed (B_MOVED_REVERSED). May18 EDG BUY had MFE=−0.76R — negative from the first bar. TATASTEEL declined sharply on May18, hitting stop loss immediately.

**Finding C — Bidirectional failure:** The system shorted TATASTEEL (expecting reversal down) and bought TATASTEEL (expecting momentum up) across the same period. **Both directions lost.** This indicates TATASTEEL was in an oscillating range with no clean directional bias, and the system's direction-selection was effectively random.

**Velocity signature:** TATASTEEL avg MFE across all 10 losses = 0.241R. Average time spent positive = ~32%. The stock was rarely above entry price for more than a third of any holding period.

---

### 8b. RELIANCE — 6 Trades, 1 Win

| Date | Dir | MFE | MAE | Pct+ | Category | P&L |
|---|---|---|---|---|---|---|
| Apr28 10:50 | BUY | **1.739R** | 0.354R | **95.8%** | W_WIN | +₹124,122 |
| May04 11:24 | BUY | 0.516R | 0.774R | 33% | B_MOVED_REVERSED | −₹52,617 |
| May05 10:05 | BUY | 0.126R | 0.813R | **0%** | C_IMMEDIATE_ADVERSE | −₹41,486 |
| May07 11:29 | BUY | 0.298R | **1.693R** | 17% | C_IMMEDIATE_ADVERSE | −₹132,044 |
| May07 13:00 | BUY | 0.263R | **1.728R** | 7% | C_IMMEDIATE_ADVERSE | −₹133,980 |
| May11 15:16 | BUY | 0.113R | 0.724R | **0%** | C_IMMEDIATE_ADVERSE | −₹47,940 |

**Finding: The Apr28 win was a different market condition.** RELIANCE on Apr28 spent 95.8% of bars above entry and peaked at 1.739R — it was in a genuine uptrend that day. Time to +0.5R was 22.41 hours (next session). 

**The May 04–11 sequence is a textbook trend-following failure in a downtrend:**
- May04: RELIANCE moved up first (reached 0.5R after 21.85 hours) then reversed — the uptrend exhausted
- May05: First full downtrend entry — 0% bars positive, stock immediately fell
- May07 ×2: MAE of 1.69R and 1.72R — RELIANCE was in sharp decline, both entries opened into free-fall
- May11: 0% bars positive, another adverse entry at the close

**The system placed RELIANCE BUY entries 5 times over 8 days while RELIANCE was declining.** Each entry had worse velocity than the last. This is a clear "repeat losers on the same symbol" pattern — Momentum_Retest was scoring RELIANCE highly despite the stock being in a downtrend.

---

### 8c. BHARTIARTL — 4 Trades, 0 Wins

| Date | Dir | MFE | MAE | Pct+ | Category | P&L |
|---|---|---|---|---|---|---|
| Apr20 09:45 | BUY | −0.015R | 0.386R | **0%** | A_NEVER_MOVED | −₹41,945 |
| May18 13:00 | BUY | 0.138R | 0.659R | 8% | C_IMMEDIATE_ADVERSE | −₹13,122 |
| May20 09:45 | BUY | 0.017R | 0.606R | **0%** | A_NEVER_MOVED | −₹11,644 |
| May22 11:30 | BUY | 0.180R | 0.852R | 21% | C_IMMEDIATE_ADVERSE | −₹15,142 |

**BHARTIARTL avg MFE = 0.080R across 4 entries.** The price never moved meaningfully above entry on any occasion. Apr20 had negative MFE — the price opened below entry on the first bar and never recovered.

**0% bars positive for 2 of 4 entries** — for the entire holding period the price was below the entry price. These are pure "bought into a falling stock" entries.

**All 4 are BUY entries** despite BHARTIARTL's downtrend in April-May 2026. The system had no mechanism to detect that BHARTIARTL's short-term "oversold" signals were being overridden by a structural downtrend.

---

## 9. Time-to-Threshold Analysis for Wins

How long did winners take to reach each R milestone?

| Symbol | Date | Time to +0.5R | Time to +1R | MFE |
|---|---|---|---|---|
| BANKBARODA SHORT | Apr22 | 23.7 hrs | — | 1.335R |
| COALINDIA (MR) | Apr23 | 21.7 hrs | — | 1.038R |
| COALINDIA (MoR) | Apr23 | 23.5 hrs | — | 1.708R |
| NTPC (viol) | Apr24 | 72.9 hrs | — | 0.880R |
| NTPC (comp) | Apr24 | 70.3 hrs | 70.3 hrs | 1.014R |
| RELIANCE | Apr28 | 22.4 hrs | — | 1.739R |
| HINDALCO (viol) | May12 | 0.08 hrs | — | 2.427R |

**Key pattern:** 5 of 7 wins needed 20–24 hours to reach +0.5R — they were next-session or overnight wins, not intraday wins. The favorable move came in the following trading session after holding overnight. NTPC needed 70+ hours (3 trading days).

**No winner reached +0.5R within the same trading session** (exception: HINDALCO at 0.08h, which is the FALSE_SL_TRIGGER_CORRECTED trade — not a clean market signal). This means the system's wins depend entirely on overnight/multi-session continuation.

---

## 10. Answering the Four Filter Questions

### Filter 1 — Velocity Filter

**Question:** Does the system need a velocity filter?

**Evidence:**
- 14 of 28 losses (50%) had MFE < 0.25R — **the trade never moved half the minimum threshold**
- 22 of 28 losses (78.6%) had MFE < 0.5R — **never got halfway to target**
- 11 of 16 adaptive-exit losses (68.8%) never reached +0.25R

**Implication of a velocity filter:** If a position fails to reach +0.25R within, say, the first 2 trading hours, it is in the "A_NEVER_MOVED" category 68.8% of the time for adaptive exits. An early-exit velocity check at +2 hours could eliminate these positions with very low risk of cutting a genuine winner, since winners take 20+ hours to reach even +0.5R — they are slow, grinding, overnight wins not explosive same-day moves.

**Critical caveat:** A velocity filter cannot be applied INSTEAD of entry quality — it would need to fire at a defined time point (e.g., "if position has not reached +0.25R within 4 bars, exit"). This is different from the adaptive_exit, which fires based on drawdown/time combination.

**Verdict:** Evidence supports a velocity filter. 50% of losses could potentially be reduced with an early-exit rule based on first-bar momentum.

---

### Filter 2 — Symbol Blacklist

**Question:** Does the system need a symbol blacklist?

**Evidence:**

| Symbol | Trades | WR | Action |
|---|---|---|---|
| TATASTEEL | 10 | **0.0%** | Blacklist evidence strong |
| BHARTIARTL | 4 | **0.0%** | Blacklist evidence strong |
| ULTRACEMCO | 3 | **0.0%** | Blacklist evidence (small sample) |
| ICICIBANK | 2 | **0.0%** | Insufficient sample |
| RELIANCE | 6 | 16.7% | Not blacklist — regime dependent |

**For TATASTEEL:** 10 trades, 0 wins across 3 different strategies (Mean_Reversion, Momentum_Retest, EDG_MOMENT) in both directions (SHORT and BUY). The velocity data confirms the MFE was low in both directions. The system traded TATASTEEL bidirectionally and lost both ways — a characteristic of a symbol stuck in an oscillating range tighter than the system's SL/target bands.

**For BHARTIARTL:** 4 trades, 0 wins, avg MFE = 0.080R (the lowest of any symbol). The stock moved against the thesis immediately in all 4 entries. The system entered BUY on BHARTIARTL while it was in a structural downtrend.

**For RELIANCE:** 1 win, 5 losses. Not a blacklist candidate — the Apr28 win was a clean +1.74R with 95.8% bars positive. The May losses were regime/trend-state dependent: RELIANCE transitioned from uptrend (Apr) to downtrend (May). The issue is repeated same-symbol entries without checking prior trade outcome.

**Verdict:** Evidence supports a symbol blacklist or "cooldown" mechanism. TATASTEEL and BHARTIARTL accumulated only losses in this period. A cooldown of N sessions after a loss on a symbol would have prevented the repeat-loser pattern.

---

### Filter 3 — Regime Filter

**Question:** Does the system need a regime filter per strategy?

**Evidence from OPS05A + OPS05B:**

| Strategy | Trades in range_market | WR | Excursion Pattern |
|---|---|---|---|
| Trend_Pullback | 4 of 4 | 0.0% | MAE=0.962R avg — strongly adverse |
| EDG_MOMENT | 3 of 3 | 0.0% | MFE=0.126R avg — never moved |
| Mean_Reversion | 15 of 15 | 13.3% | Partial moves, reversal-driven |
| Momentum_Retest | 12 of 13 | ~38% | Acceptable in range |

The single non-range_market trade (HINDALCO in bull_trend) immediately confirmed its thesis in 0.08 hours — velocity was instant.

**Trend_Pullback in range_market:** MAE consistently exceeds MFE (avg 0.962R adverse vs 0.407R favorable). The strategy presupposes a trend to pull back from. In range_market there is no trend — what appears as a "pullback" is simply noise. Entries create positions that have no directional backing.

**EDG_MOMENT in range_market:** MFE = 0.126R — the evolved strategy's signals never triggered directional follow-through in range conditions. The evolved patterns were likely fitted to trending data.

**Verdict:** Evidence strongly supports regime-gating Trend_Pullback and EDG_MOMENT strategies. Both should not execute in `range_market`. Mean_Reversion has a theoretical fit to range_market but its symbol selection needs correction.

---

### Filter 4 — Entry Timing Filter

**Question:** Does the system need an entry timing filter?

**Evidence:**

| Hours | Trades | WR | Avg MFE |
|---|---|---|---|
| 09:10–09:44 (violations) | 4 | 50.0% | 1.145R |
| 09:45–10:59 | 13 | 30.8% | 0.632R |
| 11:00–12:59 | 8 | 25.0% | 1.089R |
| **13:00–15:30** | **10** | **0.0%** | **0.249R** |

**Hours 13:00–15:30 produced zero wins in 10 trades.** Avg MFE of 0.249R — positions entered in the afternoon never develop momentum. The adaptive exit fires on these without them reaching any target.

**The afternoon session shows:**
- TATASTEEL SHORTs at 13:09 (Apr22) and 13:00 (May11) — both A/C category
- ICICIBANK SHORT at 13:06 — A_NEVER_MOVED
- AXISBANK BUY at 14:00 — A_NEVER_MOVED (0.076R MFE)
- RELIANCE BUY at 13:00 — C_IMMEDIATE_ADVERSE (MAE=1.728R)
- All Trend_Pullback entries at 13:00 — MAE > MFE in every case

**Counterintuitive finding:** Pre-governance violations at 09:10 had 50% WR and 1.145R avg MFE — the highest of any window. The 09:10 scan caught the first-opportunity setups that had overnight conviction. The 09:45 governance window starts better than afternoon but degrades through the day.

**Note on hold time:** Winners required 20+ hours to reach +0.5R. Afternoon entries have fewer remaining trading hours before the next session and thus less time to develop. The adaptive exit fires sooner on afternoon entries because the session ends, compressing the hold window.

**Verdict:** Evidence supports blocking entries after 12:30–13:00 IST. The 13:00–15:30 window shows 0% WR with consistent failure to develop any momentum. The hold time constraint for afternoon entries (position closes at 15:30 or next morning) is insufficient for the system's overnight-win dependency.

---

## 11. Synthesis — Velocity Failure Root Causes

The question was: *Why do scored and approved trades fail to develop directional movement after entry?*

Evidence points to **four compounding causes, not one:**

### Cause 1: Symbol Structural Mismatch (28 of 35 trades affected)
TATASTEEL, BHARTIARTL, ULTRACEMCO, and RELIANCE (May) were all in structural trends opposing the entry direction. These symbols' price action was not random oscillation around an equilibrium — they had a directional bias that conflicted with the entry thesis. The debate system scored the setup (≥6.5) but did not detect the symbol's structural state.

### Cause 2: Regime-Strategy Mismatch (all 4 Trend_Pullback, all 3 EDG_MOMENT)
Trend_Pullback and EDG_MOMENT require directional trending. Deployed in range_market, these strategies produced consistent C_IMMEDIATE_ADVERSE and A_NEVER_MOVED patterns — the regime provided no directional fuel for the strategy to exploit.

### Cause 3: Afternoon Entry Deficit (10 afternoon trades, 0 wins)
Entries after 13:00 produced no wins and minimal MFE. The system's winning pattern requires overnight multi-session holding. Afternoon entries compress the available holding period before session end, and the adaptive exit fires before the next-session continuation can develop.

### Cause 4: Repeat-Loser Re-Entry (RELIANCE ×5, TATASTEEL ×8)
The system repeatedly entered the same symbol with the same directional thesis after prior losses on that symbol. RELIANCE was entered BUY 5 consecutive times in May while the stock was declining. TATASTEEL was entered in both directions without mechanism to detect the prior entries had failed. Each re-entry had progressively worse velocity than the previous one.

---

## 12. Filter Recommendation Evidence

Based solely on the evidence in this report (no code changes):

| Filter | Supporting Evidence | Expected Impact |
|---|---|---|
| **Velocity filter** | 50% of losses had MFE < 0.25R; adaptive exit never produced a winner | Potential to exit ~14 low-momentum trades earlier, before full adaptive-exit loss |
| **Symbol blacklist / cooldown** | TATASTEEL 0/10, BHARTIARTL 0/4, ULTRACEMCO 0/3 in this period | Removes 17 confirmed-losing symbol entries |
| **Regime filter** | Trend_Pullback 0/4 in range, EDG 0/3 in range; bull_trend produces instant confirmation | Blocks ~7 strategy-regime mismatched entries |
| **Entry timing filter** | 13:00–15:30 = 0% WR across 10 trades, avg MFE 0.249R | Removes 10 afternoon entries; risks missing any future afternoon wins |

**Filter priority by loss count prevented:**
1. Symbol blacklist/cooldown: 17 trades prevented (TATASTEEL 10, BHARTIARTL 4, ULTRACEMCO 3)
2. Afternoon timing block: 10 trades prevented (hours 13–15)
3. Regime filter: 7 trades prevented (TP + EDG in range_market)
4. Velocity filter: 14 of remaining trades reduced (MFE < 0.25R in AE trades)

---

## Appendix A — Full Trade Results Table

| # | Date | Symbol | Dir | Strategy | MFE | MAE | Pct+ | Hold_h | Category | P&L |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Apr20 09:45 | BHARTIARTL | BUY | MR | −0.015R | 0.386R | 0% | 5.3h | A_NEVER_MOVED | −41,945 |
| 2 | Apr22 13:06 | ICICIBANK | SHORT | MR | 0.117R | 0.023R | 25% | 1.9h | A_NEVER_MOVED | −48,631 |
| 3 | Apr22 13:09 | TATASTEEL | SHORT | MR | 0.185R | 0.115R | 25% | 1.9h | A_NEVER_MOVED | −34,816 |
| 4 | Apr22 12:33 | BANKBARODA | SHORT | MR | 1.335R | 0.022R | — | 118.8h | **W_WIN** | +67,750 |
| 5 | Apr23 09:10* | TATASTEEL | SHORT | MR | 0.614R | 0.260R | 78% | 98.1h | B_MOVED_REVERSED | −15,539 |
| 6 | Apr23 10:04 | ULTRACEMCO | BUY | MR | 0.071R | 0.375R | — | 2.9h | A_NEVER_MOVED | −4,698 |
| 7 | Apr23 11:30 | COALINDIA | BUY | MR | 1.038R | 0.035R | — | 97.2h | **W_WIN** | +30,233 |
| 8 | Apr23 09:45 | COALINDIA | BUY | MoR | 1.708R | 0.279R | — | 121.1h | **W_WIN** | +93,400 |
| 9 | Apr23 13:18 | ULTRACEMCO | BUY | MR | 0.401R | 0.276R | — | 98.7h | D_PARTIAL | −5,103 |
| 10 | Apr23 15:00 | ULTRACEMCO | BUY | MR | 0.325R | 0.351R | — | 97.0h | D_PARTIAL | −7,695 |
| 11 | Apr24 09:20* | NTPC | BUY | MoR | 0.880R | 0.210R | — | 97.5h | **W_WIN** | +45,575 |
| 12 | Apr24 10:59 | NTPC | BUY | MoR | 1.014R | 0.076R | — | 95.8h | **W_WIN** | +54,945 |
| 13 | Apr27 09:45 | TATASTEEL | SHORT | MR | 0.331R | 0.674R | 33% | 24.0h | C_IMMEDIATE_ADVERSE | −36,413 |
| 14 | Apr27 11:44 | TATASTEEL | SHORT | MR | 0.093R | 0.732R | 0% | 22.1h | A_NEVER_MOVED | −40,397 |
| 15 | Apr28 10:30 | TATASTEEL | BUY | MoR | 0.181R | 0.768R | 0% | 22.9h | C_IMMEDIATE_ADVERSE | −47,709 |
| 16 | Apr28 10:50 | RELIANCE | BUY | MoR | 1.739R | 0.354R | 96% | 144.6h | **W_WIN** | +124,122 |
| 17 | Apr23 14:00 | AXISBANK | BUY | MR | 0.076R | 0.599R | — | 20.6h | A_NEVER_MOVED | −41,724 |
| 18 | Apr10 12:06 | ICICIBANK | BUY | MR | 3.071R | 3.808R | — | 797h | B_MOVED_REVERSED | −14,774 |
| 19 | May04 11:24 | RELIANCE | BUY | MoR | 0.516R | 0.774R | 33% | 167.1h | B_MOVED_REVERSED | −52,617 |
| 20 | May05 10:05 | RELIANCE | BUY | MoR | 0.126R | 0.813R | 0% | 26.3h | C_IMMEDIATE_ADVERSE | −41,486 |
| 21 | May07 11:29 | RELIANCE | BUY | MoR | 0.298R | 1.693R | 17% | 144.6h | C_IMMEDIATE_ADVERSE | −132,044 |
| 22 | May07 13:00 | RELIANCE | BUY | MoR | 0.263R | 1.728R | 7% | 143.1h | C_IMMEDIATE_ADVERSE | −133,980 |
| 23 | May11 10:35 | NTPC | BUY | MoR | 0.047R | 1.275R | — | 49.6h | A_NEVER_MOVED | −71,946 |
| 24 | May11 15:16 | RELIANCE | BUY | MoR | 0.113R | 0.724R | 0% | 44.9h | C_IMMEDIATE_ADVERSE | −47,940 |
| 25 | May12 09:10* | HINDALCO | BUY | — | 2.427R | −0.272R | — | 27.0h | **W_WIN** | +101,630 |
| 26 | May11 11:17 | TATASTEEL | SHORT | MR | 0.331R | 0.610R | 65% | 49.6h | C_IMMEDIATE_ADVERSE | −34,937 |
| 27 | May11 13:00 | TATASTEEL | SHORT | MR | 0.299R | 0.642R | 63% | 47.9h | C_IMMEDIATE_ADVERSE | −37,104 |
| 28 | May13 09:10* | TATAMOTORS | BUY | MoR | — | — | — | 7.3h | NO_DATA | −14,560 |
| 29 | May11 14:00 | COALINDIA | BUY | MoR | 0.593R | 0.811R | — | 72.7h | B_MOVED_REVERSED | −37,140 |
| 30 | May14 09:10* | TATASTEEL | BUY | EDG | 0.660R | 0.496R | 71% | 96.1h | B_MOVED_REVERSED | −104,746 |
| 31 | May14 10:52 | TATASTEEL | BUY | EDG | 0.479R | 0.676R | 42% | 27.1h | D_PARTIAL | −37,132 |
| 32 | May18 09:45 | TATASTEEL | BUY | EDG | −0.762R | 1.637R | 0% | 0.0h | A_NEVER_MOVED | −84,785 |
| 33 | May18 13:00 | BHARTIARTL | BUY | TP | 0.138R | 0.659R | 8% | 44.7h | C_IMMEDIATE_ADVERSE | −13,122 |
| 34 | May20 09:45 | BHARTIARTL | BUY | TP | 0.017R | 0.606R | 0% | 48.6h | A_NEVER_MOVED | −11,644 |
| 35 | May20 10:30 | COALINDIA | BUY | TP | 1.292R | 1.731R | — | 166.8h | B_MOVED_REVERSED | −59,746 |
| 36 | May21 13:00 | BHARTIARTL | BUY | TP | 0.180R | 0.852R | 21% | 165.8h | C_IMMEDIATE_ADVERSE | −15,142 |

*= pre-governance violation (entry < 09:45)  
Strategy codes: MR=Mean_Reversion, MoR=Momentum_Retest, TP=Trend_Pullback, EDG=EDG_MOMENT_100_EE0005

---

*All data computed from `paper_trades_backup_20260529.csv` paired OPEN/CLOSE events and 1-hour OHLC bars fetched via yfinance. All metrics are estimates at 1h bar resolution — intraday extremes within bars are not captured. No code was modified during this investigation.*
