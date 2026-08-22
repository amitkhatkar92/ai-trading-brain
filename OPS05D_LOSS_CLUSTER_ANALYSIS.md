# OPS05D — Loss Cluster Analysis

**Classification:** Evidence Collection / Failure Decomposition  
**Status:** CLOSED  
**Scope:** All closed trades with measurable P&L, Apr 10 – May 29 2026 (35 trades)  
**Supplemental:** June 2026 EOD aggregates (16 trades, individual records unrecoverable — CSV reset Jun 16)  
**Data sources:** `paper_trades_backup_20260529.csv`, `control_tower.db` ct_events, `trading_brain.db` system_logs  
**MFE/MAE method:** 1h OHLC bars via yfinance; excursions measured in R multiples  
**Date of Report:** 2026-06-19  
**Investigator:** Copilot (evidence collection only — no code modified)

---

## Executive Summary

**35 closed trades** were classified into four mutually exclusive failure clusters. Winners (7) were excluded from clustering. 28 losses were fully classified.

| Metric | Value |
|---|---|
| Total trades | 35 |
| Wins | 7 (20.0%) |
| Losses | 28 (80.0%) |
| Gross wins | +₹517,655 |
| Gross losses | −₹1,254,953 |
| Net P&L | −₹737,298 |
| Overall profit factor | 0.412 |

**The single most damaging cluster is A_NEVER_MOVED**, accounting for 50% of all losses and ₹545,985 in damage. Eliminating this cluster alone improves net P&L by ₹545,985 (+74% improvement), raises win rate from 20.0% to 33.3%, and nearly doubles profit factor from 0.412 to 0.730. Root cause: **SYMBOL_SELECTION** — instruments were chosen that had no directional velocity at entry.

---

## Cluster Definitions

| Cluster | Definition | Operationalisation |
|---|---|---|
| **A_NEVER_MOVED** | MFE < 0.25R — price never provided meaningful favorable movement | mfe_r < 0.25 |
| **B_MOVED_REVERSED** | MFE ≥ 0.5R AND trade closed at a loss — moved well then reversed | mfe_r ≥ 0.5 AND pnl < 0 |
| **C_IMMEDIATE_ADVERSE** | MAE occurs before favorable excursion AND never establishes directional advantage | mfe_r ≥ 0.25 AND mae_r > mfe_r × 2 AND pct_bars_positive < 25% |
| **D_PARTIAL** | MFE ≥ 0.25R but < 0.5R (below meaningful reversal threshold) AND loss | 0.25 ≤ mfe_r < 0.5 AND pnl < 0 |

> Priority applied in order: A → C → B → D (mutual exclusion by rule hierarchy).

---

## Step 1 — Cluster Classification

| Cluster | Count | % of Losses |
|---|---|---|
| A_NEVER_MOVED | **14** | **50.0%** |
| B_MOVED_REVERSED | 6 | 21.4% |
| C_IMMEDIATE_ADVERSE | 2 | 7.1% |
| D_PARTIAL | 6 | 21.4% |
| **Total losses** | **28** | **100%** |

```
A_NEVER_MOVED        ████████████████████████████████████████████  50%  (14)
B_MOVED_REVERSED     ████████████████████                          21%  ( 6)
D_PARTIAL            ████████████████████                          21%  ( 6)
C_IMMEDIATE_ADVERSE  ████████                                        7%  ( 2)
```

---

## Step 2 — Cluster Statistics

### Overall baseline

| Metric | Value |
|---|---|
| Gross wins | +₹517,655 |
| Gross losses | −₹1,254,953 |
| Net P&L | −₹737,298 |
| Win rate | 20.0% |
| Profit factor | 0.412 |

---

### A_NEVER_MOVED (n=14, 50.0% of losses)

| Metric | Value |
|---|---|
| Count | 14 |
| % of losses | 50.0% |
| Total P&L | −₹545,985 |
| Average P&L | −₹38,999 |
| Average MFE | 0.040R |
| Average MAE | 0.683R |
| Average holding time | 32.7h |
| % of gross losses | 43.5% |
| Cluster PF (gross wins ÷ cluster losses) | 0.948 |

**Interpretation:** This cluster contributes almost half the total losses. The average MFE of 0.040R means these trades *barely moved* — the price was essentially below or at entry for the entire holding period. The 32.7h average hold means positions were kept alive for 1–2 sessions without any favorable development. The adaptive exit correctly closed many of these, but the problem was accepting the entry in the first place.

---

### B_MOVED_REVERSED (n=6, 21.4% of losses)

| Metric | Value |
|---|---|
| Count | 6 |
| % of losses | 21.4% |
| Total P&L | −₹284,562 |
| Average P&L | −₹47,427 |
| Average MFE | 1.124R |
| Average MAE | 1.313R |
| Average holding time | 233.0h |
| % of gross losses | 22.7% |
| Cluster PF | 1.819 |

**Interpretation:** These trades DID develop meaningful favorable excursion (avg 1.124R — well past the 0.5R threshold). The problem is that they reversed completely and closed at a loss, while holding for an average of 233 hours (9+ trading days). The highest individual MFE in this cluster is ICICIBANK Apr10 at 3.071R (a position that reached 3× risk before reversing). These are the hardest losses emotionally — they were winning, then given back.

---

### C_IMMEDIATE_ADVERSE (n=2, 7.1% of losses)

| Metric | Value |
|---|---|
| Count | 2 |
| % of losses | 7.1% |
| Total P&L | −₹266,024 |
| Average P&L | −₹133,012 |
| Average MFE | 0.280R |
| Average MAE | 1.711R |
| Average holding time | 143.9h |
| % of gross losses | 21.2% |
| Cluster PF | 1.946 |

**Interpretation:** Only 2 trades, but they are the most catastrophic per-trade losses in the dataset (avg −₹133,012 each — 3.4× the A_NEVER_MOVED average). The MAE of 1.711R means both positions went against by nearly 2× the full risk amount. These are RELIANCE May07 ×2 — entered into a sharp decline, held for 143h (6 days) each, closed at near-full stop loss. The price was below entry for 83–93% of the entire hold. The cluster PF of 1.946 is deceptive: it means eliminating this cluster saves ₹266K, but since there are only 2 trades, small-sample effects dominate.

---

### D_PARTIAL (n=6, 21.4% of losses)

| Metric | Value |
|---|---|
| Count | 6 |
| % of losses | 21.4% |
| Total P&L | −₹158,383 |
| Average P&L | −₹26,397 |
| Average MFE | 0.361R |
| Average MAE | 0.538R |
| Average holding time | 57.4h |
| % of gross losses | 12.6% |
| Cluster PF | 3.268 |

**Interpretation:** The smallest-damage cluster per-trade (avg −₹26,397). These positions moved 0.25–0.5R in the right direction but stalled before developing further momentum. The low MAE (0.538R) suggests these were not hostile environments — the instrument just stopped moving. Time-based exits (SESSION_EXPIRED or adaptive) closed them at small losses. The cluster's PF of 3.268 is the highest — meaning wins earn 3.27× more per unit than D_PARTIAL loses per unit. This cluster is the least destructive.

---

## Step 3 — Symbol Analysis Per Cluster

### A_NEVER_MOVED — top symbols

| Symbol | n | Net P&L | Notes |
|---|---|---|---|
| **TATASTEEL** | **4** | **−₹207,707** | Largest single-symbol contributor; all MFE < 0.20R |
| BHARTIARTL | 4 | −₹81,853 | Avg MFE = −0.015R (negative); 0% bars positive in 2 of 4 entries |
| RELIANCE | 2 | −₹89,427 | May05 and May11 — entered during RELIANCE decline |
| NTPC | 1 | −₹71,946 | May11: 0.047R MFE vs 1.275R MAE — full stop in 2 days |
| ICICIBANK | 1 | −₹48,631 | Apr22 13:06 SHORT — price went up immediately |
| AXISBANK | 1 | −₹41,724 | Apr23 14:00 — afternoon entry, never moved |
| ULTRACEMCO | 1 | −₹4,698 | Smallest in cluster; REPLACEMENT exit |

### B_MOVED_REVERSED — top symbols

| Symbol | n | Net P&L | Notes |
|---|---|---|---|
| **TATASTEEL** | **2** | **−₹120,285** | Apr23 SHORT (MFE=0.614R) + May14 BUY EDG (MFE=0.660R) |
| COALINDIA | 2 | −₹96,886 | May11 (MoR, 0.593R) + May20 (TP, 1.292R — biggest B reversal) |
| RELIANCE | 1 | −₹52,617 | May04: reached 0.516R then 167h hold through decline |
| ICICIBANK | 1 | −₹14,774 | Apr10 legacy: reached 3.071R over 797h then reversed |

### C_IMMEDIATE_ADVERSE — top symbols

| Symbol | n | Net P&L | Notes |
|---|---|---|---|
| **RELIANCE** | **2** | **−₹266,024** | May07 ×2: MAE=1.69R/1.73R; 7–17% bars positive; entered during sharp decline |

### D_PARTIAL — top symbols

| Symbol | n | Net P&L | Notes |
|---|---|---|---|
| **TATASTEEL** | **4** | **−₹145,585** | Apr27 SHORT (0.331R), May11 SHORT ×2, May14 BUY (0.479R — nearest to B) |
| ULTRACEMCO | 2 | −₹12,798 | Apr23 ×2: moved 0.33–0.40R then SESSION_EXPIRED |

### Symbols appearing in multiple clusters

| Symbol | Clusters | Total n | Total P&L | Implication |
|---|---|---|---|---|
| **TATASTEEL** | A + B + D | 10 | −₹473,577 | All failure modes; dominant cross-cluster loser |
| **RELIANCE** | A + B + C | 5 | −₹408,067 | Apr win, then ALL three loss types in May |
| ICICIBANK | A + B | 2 | −₹63,405 | Short Apr22 (A), legacy Apr10 (B) |
| ULTRACEMCO | A + D | 3 | −₹17,496 | Small losses; scattered pattern |

**TATASTEEL is the only symbol present in three clusters (A, B, D) — 10 trades and 0 wins.** It manifests differently at different entry times: Apr22 (immediate no-move SHORT), Apr23 (moved then reversed SHORT), Apr27-28 (immediate adverse BUY), May11 (partial SHORTS), May14 (partial BUY near B boundary), May18 (immediate full stop BUY). This cross-cluster presence is the strongest symbol blacklist signal in the dataset.

---

## Step 4 — Regime Analysis Per Cluster

| Cluster | range_market | bull_trend | bear_market | volatile |
|---|---|---|---|---|
| A_NEVER_MOVED | 14/14 (100%) | 0 | 0 | 0 |
| B_MOVED_REVERSED | 6/6 (100%) | 0 | 0 | 0 |
| C_IMMEDIATE_ADVERSE | 2/2 (100%) | 0 | 0 | 0 |
| D_PARTIAL | 6/6 (100%) | 0 | 0 | 0 |

**All 28 losses occurred on `range_market` days.** The regime provides zero variance — it is not a differentiating factor between clusters. Regime is the background condition, not the cluster-level discriminator.

**However, the regime is relevant at the strategy level:** B_MOVED_REVERSED is directly attributable to the range oscillation behaviour — positions moved 1R+ then reversed because `range_market` mean-reverts before any trend reaches 2.5R target. This is the regime contribution to B cluster specifically.

**Implication:** A regime filter by itself would block all trades (since all occurred in range_market). The regime filter must be strategy-specific — Trend_Pullback and EDG_MOMENT should not execute in range_market; Mean_Reversion and Momentum_Retest can, but with modified targets and symbol filters.

---

## Step 5 — Entry Time Analysis Per Cluster

### Overall by window

| Window | n | WR | Net P&L |
|---|---|---|---|
| 09:15–10:00 | 9 | 33.3% | −₹54,467 |
| 10:00–13:00 | 16 | 25.0% | −₹275,577 |
| **13:00–15:30** | **10** | **0.0%** | **−₹407,255** |

---

### A_NEVER_MOVED by window

| Window | n | % of cluster | Net P&L |
|---|---|---|---|
| 09:15–10:00 | 3 | 21.4% | −₹138,374 |
| 10:00–13:00 | 6 | 42.9% | −₹221,379 |
| 13:00–15:30 | 5 | 35.7% | −₹186,232 |

A_NEVER_MOVED is spread across all windows. It is not exclusively an afternoon problem — morning entries also produced no-move outcomes. The cause is not timing; it is symbol selection.

---

### B_MOVED_REVERSED by window

| Window | n | % of cluster | Net P&L |
|---|---|---|---|
| 09:15–10:00 | 2 | 33.3% | −₹120,285 |
| 10:00–13:00 | 3 | 50.0% | −₹127,136 |
| 13:00–15:30 | 1 | 16.7% | −₹37,140 |

B_MOVED_REVERSED occurs most in the morning-to-midday window (10:00–13:00), suggesting the initial favorable move happens in the morning session and the reversal completes over subsequent days.

---

### C_IMMEDIATE_ADVERSE by window

| Window | n | % of cluster | Net P&L |
|---|---|---|---|
| 10:00–13:00 | 1 | 50.0% | −₹132,044 |
| 13:00–15:30 | 1 | 50.0% | −₹133,980 |

Both C_IMMEDIATE trades were RELIANCE BUY at 11:29 and 13:00 on May07 — consecutive entries on the same day in the same declining instrument.

---

### D_PARTIAL by window

| Window | n | % of cluster | Net P&L |
|---|---|---|---|
| 09:15–10:00 | 1 | 16.7% | −₹36,413 |
| 10:00–13:00 | 2 | 33.3% | −₹72,068 |
| 13:00–15:30 | 3 | 50.0% | −₹49,902 |

D_PARTIAL is skewed toward afternoon entries (50% in 13:00–15:30). Afternoon entries that develop a partial move face a compressed time window — the session ends before the target can be reached, and SESSION_EXPIRED closes them at small losses.

**Entry timing summary:** The 13:00–15:30 window is 0% WR across all trades, but it contains a mix of A, C, and D cluster losses. Blocking afternoon entries would primarily eliminate D_PARTIAL and some A_NEVER_MOVED, but would not meaningfully address B_MOVED_REVERSED (which enters in the morning).

---

## Step 6 — Strategy Analysis Per Cluster

### Win distribution by strategy (baseline)

| Strategy | Total n | Wins | WR | Gross Win P&L |
|---|---|---|---|---|
| Mean_Reversion | 15 | 2 | 13.3% | +₹97,983 |
| Momentum_Retest | 13 | 5 | 38.5% | +₹419,672 |
| Trend_Pullback | 4 | 0 | 0.0% | ₹0 |
| EDG_MOMENT_100_EE0005 | 3 | 0 | 0.0% | ₹0 |

---

### A_NEVER_MOVED by strategy

| Strategy | n | % of cluster | Net P&L | Strategy WR |
|---|---|---|---|---|
| Mean_Reversion | 6 | 42.9% | −₹212,210 | 13.3% |
| Momentum_Retest | 4 | 28.6% | −₹209,082 | 38.5% |
| Trend_Pullback | 3 | 21.4% | −₹39,908 | 0.0% |
| EDG_MOMENT_100_EE0005 | 1 | 7.1% | −₹84,785 | 0.0% |

A_NEVER_MOVED spans all 4 strategies. Even Momentum_Retest (best overall strategy at 38.5% WR) produces A_NEVER_MOVED losses — 4 of its 8 losses are in this cluster. The symbol problem overrides the strategy: Momentum_Retest on TATASTEEL (Apr28) and RELIANCE (May05, May11) all produced zero favorable movement despite the strategy's generally higher WR.

---

### B_MOVED_REVERSED by strategy

| Strategy | n | % of cluster | Net P&L | Strategy WR |
|---|---|---|---|---|
| Momentum_Retest | 2 | 33.3% | −₹89,757 | 38.5% |
| Mean_Reversion | 2 | 33.3% | −₹30,313 | 13.3% |
| EDG_MOMENT_100_EE0005 | 1 | 16.7% | −₹104,746 | 0.0% |
| Trend_Pullback | 1 | 16.7% | −₹59,746 | 0.0% |

B_MOVED_REVERSED is strategy-agnostic for different reasons: Mean_Reversion reverses because range_market cycles eventually mean-revert in the other direction; Trend_Pullback reverses because there was no sustained trend to ride; EDG_MOMENT reached 0.66R then reversed as the evolved pattern's edge dissipated.

---

### C_IMMEDIATE_ADVERSE by strategy

| Strategy | n | % of cluster | Net P&L | Strategy WR |
|---|---|---|---|---|
| Momentum_Retest | 2 | 100% | −₹266,024 | 38.5% |

Both C_IMMEDIATE trades are Momentum_Retest on RELIANCE in May07. The strategy selected a continuation entry while RELIANCE was in a sharp multi-day decline. This is Momentum_Retest operating on stale momentum signals — the "momentum" it detected was the Apr28 win, but by May07 the price structure had completely reversed.

---

### D_PARTIAL by strategy

| Strategy | n | % of cluster | Net P&L | Strategy WR |
|---|---|---|---|---|
| Mean_Reversion | 5 | 83.3% | −₹121,251 | 13.3% |
| EDG_MOMENT_100_EE0005 | 1 | 16.7% | −₹37,132 | 0.0% |

D_PARTIAL is predominantly Mean_Reversion. This confirms the pattern seen in OPS05B: Mean_Reversion does generate partial moves in range_market, but the RR=2.5 target is too far for range oscillations to reach.

---

## Step 7 — Damage Ranking

**Formula:** Damage Score = abs(total_pnl) × frequency_pct

| Rank | Cluster | abs(P&L) | Frequency | Damage Score |
|---|---|---|---|---|
| **#1** | **A_NEVER_MOVED** | **₹545,985** | **50.0%** | **27,299,244** |
| #2 | B_MOVED_REVERSED | ₹284,562 | 21.4% | 6,089,625 |
| #3 | D_PARTIAL | ₹158,383 | 21.4% | 3,389,395 |
| #4 | C_IMMEDIATE_ADVERSE | ₹266,024 | 7.1% | 1,888,768 |

**Damage score visualisation:**

```
A_NEVER_MOVED        ████████████████████████████████████████████████████████  27.3M
B_MOVED_REVERSED     ████████████████████████                                    6.1M
D_PARTIAL            ████████████████                                            3.4M
C_IMMEDIATE_ADVERSE  ██████████                                                  1.9M
```

**Note on C_IMMEDIATE_ADVERSE:** Its damage score ranks last despite having the second-largest total P&L loss (₹266,024) because its frequency is only 7.1% (2 trades). The formula penalises low-frequency events because rare events cannot be addressed by systematic filters — they require case-specific detection. A_NEVER_MOVED's dominance is driven by both its high frequency AND meaningful loss per trade.

---

## Step 8 — Counterfactuals

### Scenario A — Remove all A_NEVER_MOVED

| Metric | Baseline | Scenario A | Delta |
|---|---|---|---|
| Trade count | 35 | 21 | −14 |
| Wins | 7 | 7 | 0 |
| Win rate | 20.0% | **33.3%** | **+13.3pp** |
| Net P&L | −₹737,298 | **−₹191,313** | **+₹545,985** |
| Profit factor | 0.412 | **0.730** | **+0.318** |

### Scenario B — Remove all B_MOVED_REVERSED

| Metric | Baseline | Scenario B | Delta |
|---|---|---|---|
| Trade count | 35 | 29 | −6 |
| Win rate | 20.0% | 24.1% | +4.1pp |
| Net P&L | −₹737,298 | −₹452,736 | +₹284,562 |
| Profit factor | 0.412 | 0.533 | +0.121 |

### Scenario C — Remove all C_IMMEDIATE_ADVERSE

| Metric | Baseline | Scenario C | Delta |
|---|---|---|---|
| Trade count | 35 | 33 | −2 |
| Win rate | 20.0% | 21.2% | +1.2pp |
| Net P&L | −₹737,298 | −₹471,274 | +₹266,024 |
| Profit factor | 0.412 | 0.523 | +0.111 |

### Scenario D — Remove all D_PARTIAL

| Metric | Baseline | Scenario D | Delta |
|---|---|---|---|
| Trade count | 35 | 29 | −6 |
| Win rate | 20.0% | 24.1% | +4.1pp |
| Net P&L | −₹737,298 | −₹578,915 | +₹158,383 |
| Profit factor | 0.412 | 0.472 | +0.060 |

### Counterfactual comparison

```
Delta Net P&L by scenario:
Scenario A (remove A)  ████████████████████████████████████████████  +₹545,985
Scenario B (remove B)  ██████████████████████                        +₹284,562
Scenario C (remove C)  █████████████████████                         +₹266,024
Scenario D (remove D)  ████████████                                  +₹158,383

Delta Win Rate by scenario:
Scenario A  +13.3pp  (20.0% → 33.3%)
Scenario B  + 4.1pp  (20.0% → 24.1%)
Scenario C  + 1.2pp  (20.0% → 21.2%)
Scenario D  + 4.1pp  (20.0% → 24.1%)

Delta Profit Factor by scenario:
Scenario A  +0.318  (0.412 → 0.730)
Scenario B  +0.121  (0.412 → 0.533)
Scenario C  +0.111  (0.412 → 0.523)
Scenario D  +0.060  (0.412 → 0.472)
```

**Scenario A produces the largest improvement across all three metrics** — it is the only scenario that nearly doubles the profit factor. Even after removing 14 trades, win rate increases substantially because all 7 wins are preserved while 14 losing trades are removed.

---

## Step 9 — Root Cause Hypotheses

### A_NEVER_MOVED — SYMBOL_SELECTION + LOW_VELOCITY

**Primary root cause:** `SYMBOL_SELECTION`  
**Secondary root cause:** `LOW_VELOCITY` / `SECTOR_WEAKNESS`

The instruments selected for these 14 entries had no directional velocity at the time of entry:

- **BHARTIARTL:** 4 entries, avg MFE = −0.015R (negative — price was below entry the entire time). The instrument was in a structural decline throughout Apr–May. BUY signals were generated against the prevailing trend.
- **TATASTEEL (4 of 14):** SHORT entries in Apr22 and Apr27 produced MFE < 0.2R — the stock moved up rather than down in range_market. BUY entry in Apr28 had MFE=0.181R — entered long the day after TATASTEEL had already reversed.
- **RELIANCE (2 of 14):** May05 (0.126R) and May11 (0.113R) — both entered while RELIANCE was declining. Momentum_Retest was firing on stale positive momentum from the Apr28 win.
- **NTPC (1 of 14):** May11 0.047R MFE vs 1.275R MAE — entered into a gap-down session. The instrument had no buying interest.

**Evidence:** pct_bars_positive < 15% average for A_NEVER_MOVED. The price was almost never above entry. These are not "trades that tried and failed" — they are entries where the instrument was already moving adversely.

**Explicitly NOT:** This is not primarily a regime_mismatch issue — Mean_Reversion is theoretically valid in range_market. The failure is which stocks the opportunity scanner selects, not the strategy category. BANKBARODA SHORT (Apr22) is Mean_Reversion in the same regime and is a clean +₹67,750 win with MFE=1.335R.

---

### B_MOVED_REVERSED — REVERSAL_RISK + TARGET_TOO_FAR

**Primary root cause:** `TARGET_TOO_FAR` / `REVERSAL_RISK`  
**Secondary root cause:** `REGIME_MISMATCH` (range_market oscillation amplitude < target distance)

These trades had genuine initial favorable movement (avg MFE=1.124R) — the entry thesis was at least partially correct. The failure is that the target (2.5R) was never reached before range_market mean-reversion pulled the price back.

- **COALINDIA May20 TP:** Reached 1.292R then reversed to −₹59,746 (MAE=1.731R). The favorable move was real but the 2.5R target required the stock to move 1.25× further than it ever did.
- **TATASTEEL Apr23 SHORT:** MFE=0.614R — the SHORT worked initially, but price reversed upward within 98 hours. Range_market provided the initial reversal signal but then the stock resumed its prior uptrend.
- **RELIANCE May04:** MFE=0.516R, then 167h hold as price trended down. Initial 0.5R move happened; then Momentum_Retest held the position while it deteriorated.
- **ICICIBANK Apr10 legacy:** MFE=3.071R over 797 hours — trade was 3R favorable then reversed to a loss. Extreme overheld session-expired trade.

**The core problem:** In `range_market`, price oscillations typically have amplitude 0.5–1.5R from entry. The 2.5R target requires the equivalent of a full trending move in a non-trending environment. B_MOVED_REVERSED trades correctly identified the direction but the target was set for a trend that never materialised.

**Explicitly NOT:** Not symbol_selection — COALINDIA, RELIANCE, and ICICIBANK can all move 1R+. Not entry_timing — B trades enter at various times. The problem is target calibration for the regime.

---

### C_IMMEDIATE_ADVERSE — REGIME_MISMATCH + ENTRY_TIMING (stale signal)

**Primary root cause:** `REGIME_MISMATCH` / `SYMBOL_SELECTION` (sequential re-entry)  
**Secondary root cause:** `MARKET_BREADTH` (sectoral decline during India-Pakistan conflict escalation, May 2026)

Both C_IMMEDIATE trades are RELIANCE BUY on May07:

- May07 11:29: Entry at ₹1,329, MAE=1.693R (price fell ₹133 per share), held 144h, pct_bars_positive=16.7%
- May07 13:00: Entry at ₹1,373, MAE=1.728R (price fell ₹136 per share), held 143h, pct_bars_positive=6.9%

RELIANCE entered a sustained 3-week decline beginning May04. Momentum_Retest scored RELIANCE positively because it detected the Apr28 large win (+₹124,122 at 1.739R MFE) and extrapolated continuation. By May07, the underlying trend had reversed. The decision engine was scoring on lagged context — the "momentum" being tested was 9 days stale.

**Two consecutive BUY entries on the same declining symbol on the same day** (11:29 and 13:00) represent a failure of the duplicate/consecutive entry detection. The second entry at 13:00 had 6.9% bars positive — the price was below entry for 93% of the hold.

**Explicitly NOT:** Not target_too_far — price never moved favorably, so target distance was irrelevant. Not entry_timing in isolation — the 11:00 and 13:00 windows are both used, but the core issue is the direction was wrong, not when it was entered.

---

### D_PARTIAL — TARGET_TOO_FAR + LOW_VELOCITY (stagnation)

**Primary root cause:** `TARGET_TOO_FAR`  
**Secondary root cause:** `LOW_VELOCITY` (position stagnated after initial move)

D_PARTIAL trades moved 0.25–0.5R — directionally correct, but velocity stalled before the 2.5R target. These are mostly SESSION_EXPIRED or adaptive_exit closures — not reversals.

- **ULTRACEMCO Apr23 ×2:** Reached 0.401R and 0.325R respectively, then stagnated across 98+ hour holds. ULTRACEMCO was oscillating in a tight range around the entry price — the initial move was the range extent, not a breakout.
- **TATASTEEL May11 SHORTs (0.331R ×2 and 0.299R):** Shorted near the top of a range, got partial downside, then price oscillated back within range. The short thesis was valid at the range boundary but the extent of the move was < 0.5R.
- **TATASTEEL May14 EDG (0.479R):** Came closest to B threshold — 0.479R in 27 hours then reversed. This is the borderline case.

**The D_PARTIAL cluster confirms that RR=2.5 is too optimistic for range_market.** In a range, the typical realisable excursion is 0.5–1.0R. A target at 2.5R requires the instrument to travel 5–10× beyond where range reversions begin. SESSION_EXPIRED closes D_PARTIAL trades before they can either reach target or be stopped — they simply expire unfulfilled.

**Explicitly NOT:** Not symbol_selection (ULTRACEMCO did move, just not far enough). Not entry_timing. The problem is the asymmetry between the expected-move magnitude of range_market and the target distance.

---

## June 2026 Supplementary Context

**16 closed trades in June 2026. Individual records unrecoverable from CSV (reset Jun 16).**

| Date | Trades | Wins | Net P&L | Notes |
|---|---|---|---|---|
| Jun 04 | 1 | 0 | −₹27,622 | Probable GODREJCP or DRREDDY opened Jun04, closed same day |
| Jun 05 | 1 | 0 | −₹24,244 | MARICO/SBILIFE/NAUKRI series |
| Jun 08 | 5 | 2 | +₹49,002 | Multi-session batch from Jun03–05 closures |
| Jun 11 | 2 | 2 | +₹335,800 | Large wins — probable BANKBARODA+multi-session held 1 week |
| Jun 15 | 1 | 0 | −₹26,563 | JSWSTEEL or TITAN — loss |
| Jun 16 | 6 | 2 | −₹15,160 | Mixed day; net loss |
| **Total** | **16** | **6** | **+₹291,213** | |

**June WR: 37.5%** — substantially better than Apr-May 20.0%.

**Key observation:** June's symbol universe is different (GODREJCP, BANKBARODA, MRF, MARICO, BHARATFORG, PIDILITIND — not TATASTEEL, BHARTIARTL, or repeated RELIANCE). This supports the SYMBOL_SELECTION hypothesis: switching symbols improved WR immediately. June's +₹291,213 net is likely dominated by the Jun11 large win batch (₹335,800), but the 37.5% WR suggests fewer A_NEVER_MOVED outcomes in June.

**Cannot classify June trades into A/B/C/D clusters** — MFE/MAE data requires individual trade records with entry/exit prices and price history, which the reset CSV cannot provide.

---

## Step 10 — Final Conclusion

### Question: "If only one cluster could be eliminated, which would improve performance most?"

### Answer: **A_NEVER_MOVED**

**Evidence:**

| Argument | Data |
|---|---|
| Highest frequency | 50% of all losses (14 of 28) |
| Highest total damage | −₹545,985 (43.5% of gross losses) |
| Highest damage score | 27,299,244 — 4.5× the second-place cluster |
| Counterfactual WR improvement | +13.3pp (20.0% → 33.3%) — largest WR gain |
| Counterfactual PF improvement | +0.318 (0.412 → 0.730) — nearly double |
| Counterfactual net P&L gain | +₹545,985 — largest absolute improvement |
| Root cause addressability | SYMBOL_SELECTION — directly addressable via symbol scoring, blacklist, or velocity gate |

**The A_NEVER_MOVED cluster is not a product of bad luck or unusual market conditions.** It represents systematic entries into instruments that had zero favorable velocity from the moment of entry. The average MFE of 0.040R means the price was essentially flat-to-adverse for the entire holding period. These are positions where the entry premise was structurally wrong — the instrument had already reversed, was trending against the thesis, or had no buying interest at all.

**Secondary finding:** C_IMMEDIATE_ADVERSE produces the largest per-trade average loss (−₹133,012) but with only 2 trades it has the lowest damage score. Both instances are the same symbol (RELIANCE) on the same day (May07), entered twice consecutively into a declining instrument. This is addressable by consecutive-entry detection rather than cluster-level filtering.

**The June data provides confirming evidence:** switching away from TATASTEEL and BHARTIARTL in June improved WR to 37.5%. This happened without any code change — simply different symbol opportunities presented. This is the strongest real-world validation that A_NEVER_MOVED is driven by SYMBOL_SELECTION, not strategy or regime.

---

## Appendix — Full Trade Cluster Table

| # | Date | Symbol | Dir | Strategy | Cluster | MFE | MAE | Hold | P&L | Regime |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Apr10 | ICICIBANK | BUY | MR | B_MOVED_REVERSED | 3.071R | 3.808R | 797h | −14,774 | range |
| 2 | Apr20 | BHARTIARTL | BUY | MR | **A_NEVER_MOVED** | −0.015R | 0.386R | 5h | −41,945 | range |
| 3 | Apr22 | BANKBARODA | SHORT | MR | **WIN** | 1.335R | 0.022R | 119h | +67,750 | range |
| 4 | Apr22 | ICICIBANK | SHORT | MR | **A_NEVER_MOVED** | 0.117R | 0.023R | 2h | −48,631 | range |
| 5 | Apr22 | TATASTEEL | SHORT | MR | **A_NEVER_MOVED** | 0.185R | 0.115R | 2h | −34,816 | range |
| 6 | Apr23 | TATASTEEL | SHORT | MR | B_MOVED_REVERSED | 0.614R | 0.260R | 98h | −15,539 | range |
| 7 | Apr23 | COALINDIA | BUY | MoR | **WIN** | 1.708R | 0.279R | 121h | +93,400 | range |
| 8 | Apr23 | ULTRACEMCO | BUY | MR | **A_NEVER_MOVED** | 0.071R | 0.375R | 3h | −4,698 | range |
| 9 | Apr23 | COALINDIA | BUY | MR | **WIN** | 1.038R | 0.035R | 97h | +30,233 | range |
| 10 | Apr23 | ULTRACEMCO | BUY | MR | D_PARTIAL | 0.401R | 0.276R | 99h | −5,103 | range |
| 11 | Apr23 | AXISBANK | BUY | MR | **A_NEVER_MOVED** | 0.076R | 0.599R | 21h | −41,724 | range |
| 12 | Apr23 | ULTRACEMCO | BUY | MR | D_PARTIAL | 0.325R | 0.351R | 97h | −7,695 | range |
| 13 | Apr24 | NTPC | BUY | MoR | **WIN** | 0.880R | 0.210R | 97h | +45,575 | range |
| 14 | Apr24 | NTPC | BUY | MoR | **WIN** | 1.014R | 0.076R | 96h | +54,945 | range |
| 15 | Apr27 | TATASTEEL | SHORT | MR | D_PARTIAL | 0.331R | 0.674R | 24h | −36,413 | range |
| 16 | Apr27 | TATASTEEL | SHORT | MR | **A_NEVER_MOVED** | 0.093R | 0.732R | 22h | −40,397 | range |
| 17 | Apr28 | TATASTEEL | BUY | MoR | **A_NEVER_MOVED** | 0.181R | 0.768R | 23h | −47,709 | range |
| 18 | Apr28 | RELIANCE | BUY | MoR | **WIN** | 1.739R | 0.354R | 145h | +124,122 | range |
| 19 | May04 | RELIANCE | BUY | MoR | B_MOVED_REVERSED | 0.516R | 0.774R | 167h | −52,617 | range |
| 20 | May05 | RELIANCE | BUY | MoR | **A_NEVER_MOVED** | 0.126R | 0.813R | 26h | −41,486 | range |
| 21 | May07 | RELIANCE | BUY | MoR | **C_IMMEDIATE_ADVERSE** | 0.298R | 1.693R | 145h | −132,044 | range |
| 22 | May07 | RELIANCE | BUY | MoR | **C_IMMEDIATE_ADVERSE** | 0.263R | 1.728R | 143h | −133,980 | range |
| 23 | May11 | NTPC | BUY | MoR | **A_NEVER_MOVED** | 0.047R | 1.275R | 50h | −71,946 | range |
| 24 | May11 | TATASTEEL | SHORT | MR | D_PARTIAL | 0.331R | 0.610R | 50h | −34,937 | range |
| 25 | May11 | TATASTEEL | SHORT | MR | D_PARTIAL | 0.299R | 0.642R | 48h | −37,104 | range |
| 26 | May11 | COALINDIA | BUY | MoR | B_MOVED_REVERSED | 0.593R | 0.811R | 73h | −37,140 | range |
| 27 | May11 | RELIANCE | BUY | MoR | **A_NEVER_MOVED** | 0.113R | 0.724R | 45h | −47,940 | range |
| 28 | May12 | HINDALCO | BUY | MoR | **WIN** | 2.427R | −0.272R | 27h | +101,630 | bear |
| 29 | May14 | TATASTEEL | BUY | EDG | B_MOVED_REVERSED | 0.660R | 0.496R | 96h | −104,746 | range |
| 30 | May14 | TATASTEEL | BUY | EDG | D_PARTIAL | 0.479R | 0.676R | 27h | −37,132 | range |
| 31 | May18 | TATASTEEL | BUY | EDG | **A_NEVER_MOVED** | −0.762R | 1.637R | 0h | −84,785 | range |
| 32 | May18 | BHARTIARTL | BUY | TP | **A_NEVER_MOVED** | 0.138R | 0.659R | 45h | −13,122 | range |
| 33 | May20 | BHARTIARTL | BUY | TP | **A_NEVER_MOVED** | 0.017R | 0.606R | 49h | −11,644 | range |
| 34 | May20 | COALINDIA | BUY | TP | B_MOVED_REVERSED | 1.292R | 1.731R | 167h | −59,746 | range |
| 35 | May22 | BHARTIARTL | BUY | TP | **A_NEVER_MOVED** | 0.180R | 0.852R | 166h | −15,142 | range |

**Strategy codes:** MR=Mean_Reversion, MoR=Momentum_Retest, TP=Trend_Pullback, EDG=EDG_MOMENT_100_EE0005  
**Bold clusters = loss clusters highlighted for analysis focus**

---

*All metrics computed from `paper_trades_backup_20260529.csv` OPEN/CLOSE pairs, 1h OHLC bars via yfinance, and `ct_events market.data.ready` regime data. No code was modified during this investigation.*
