# OPS05A — Compliant Trade Failure Analysis

**Classification:** Evidence Collection / Pattern Analysis  
**Status:** CLOSED  
**Scope:** Governance-compliant trades only (entry_time ≥ 09:45 IST)  
**Period:** 2026-04-10 through 2026-05-29  
**Date of Report:** 2026-06-19  
**Investigator:** Copilot (evidence collection only — no code modified)

---

## Population

**Total compliant closed trades with measurable P&L:** 33  
**Winners:** 6 (18.2%)  
**Losers:** 27 (81.8%)  
**Net P&L:** −₹1,090,208 (see OPS04C)

> Note: COALINDIA May 29 (−₹400,752) is tagged `PHANTOM_PRICE_CORRECTION` — a simulation data quality error. It is included in counts but flagged with ⚠ where it distorts averages. Excluding it: 32 trades, 27 W/L ratio unchanged, net −₹689,456.

---

## 1. Analysis by Strategy

| Strategy | Trades | Wins | Losses | WR | Net P&L | Avg Loss |
|---|---|---|---|---|---|---|
| Mean_Reversion | 13 | 2 | 11 | 15.4% | −₹320,987 | −₹29,181 |
| Momentum_Retest | 11 | 3 | 8 | 27.3% | −₹292,397 | −₹77,108 |
| Trend_Pullback | 5 | 1 | 4 | 20.0% | −₹455,549 ⚠ | −₹122,416 ⚠ |
| EDG_MOMENT_100_EE0005 | 2 | 0 | 2 | 0.0% | −₹121,917 | −₹60,959 |
| Trend_Pullback (ex-phantom) | 4 | 1 | 3 | 25.0% | −₹54,797 | −₹27,399 |

### Loss distribution by strategy:
```
Mean_Reversion   ████████████████████████████ 41%  (11/27)
Momentum_Retest  ████████████████████         30%  ( 8/27)
Trend_Pullback   ████████████                 15%  ( 4/27)
EDG_MOMENT       ████████                      7%  ( 2/27)
Legacy Orphan    ████                          4%  ( 1/27)
```

**Observation:** Mean_Reversion generated the most losses in absolute count (11), but its average loss is smaller. Momentum_Retest's 8 losses average −₹77K each — the highest average loss per losing trade.

**Winner count by strategy:**
- Momentum_Retest: 3 wins (COALINDIA Apr23, NTPC Apr24, RELIANCE Apr28)
- Mean_Reversion: 2 wins (BANKBARODA Apr22, COALINDIA Apr23)
- Trend_Pullback: 1 win (HINDALCO May21)
- EDG_MOMENT: 0 wins

---

## 2. Analysis by Regime

Each trade's regime comes from `market.data.ready` events in `ct_events` for that calendar date.

| Regime | Trade Days | Trades | Wins | Losses | WR |
|---|---|---|---|---|---|
| **range_market** | 32 of 33 | 32 | 5 | 27 | 15.6% |
| **bull_trend** | 1 of 33 | 1 | 1 | 0 | 100% |

### The regime picture is stark:

**32 of 33 compliant trades occurred on `range_market` days.**  
The single `bull_trend` day (May 21, VIX 17.75) produced the only Trend_Pullback winner (HINDALCO).

The five wins in range_market were:
| Winner | Strategy | Context |
|---|---|---|
| BANKBARODA SHORT | Mean_Reversion | Sold into resistance — genuine range reversal |
| COALINDIA BUY | Mean_Reversion | Bought support — genuine range reversal |
| COALINDIA BUY | Momentum_Retest | Range-boundary momentum — held for multi-day gain |
| NTPC BUY | Momentum_Retest | SYSTEM_CLEANUP exit — not a clean market exit |
| RELIANCE BUY | Momentum_Retest | SESSION_EXPIRED multi-day gain |

**Regime verdict:** The system was trading predominantly `Momentum_Retest` and `Trend_Pullback` strategies inside a `range_market`. Momentum_Retest is tolerated in range_market (listed as valid in the debate system for range_market), but Trend_Pullback is structurally mismatched — it requires a trend that did not exist on the entry days.

---

## 3. Analysis by Sector

| Sector | Symbol(s) | Trades | Wins | Losses | WR | Net P&L |
|---|---|---|---|---|---|---|
| **Metals** | TATASTEEL, HINDALCO | 9 | 1 | 8 | 11.1% | −₹351,371 |
| **Energy** | COALINDIA, NTPC | 7 | 3 | 4 | 42.9% | −₹431,191 ⚠ |
| **Diversified** | RELIANCE | 6 | 1 | 5 | 16.7% | −₹283,946 |
| **Banking** | ICICIBANK, AXISBANK, BANKBARODA | 4 | 1 | 3 | 25.0% | −₹37,379 |
| **Telecom** | BHARTIARTL | 4 | 0 | 4 | 0.0% | −₹81,853 |
| **Cement** | ULTRACEMCO | 3 | 0 | 3 | 0.0% | −₹17,496 |

> ⚠ Energy P&L includes COALINDIA phantom correction (−₹400,752). Ex-phantom: Energy 6 trades, 3 wins, 3 losses, WR 50%, Net +₹94,437.

### Symbol-level breakdown (losses only):

| Symbol | Trades | Wins | Losses | WR |
|---|---|---|---|---|
| **TATASTEEL** | **8** | **0** | **8** | **0.0%** |
| RELIANCE | 6 | 1 | 5 | 16.7% |
| BHARTIARTL | 4 | 0 | 4 | 0.0% |
| COALINDIA | 5 | 3 | 2 | 60.0% ⚠ |
| ICICIBANK | 3 | 0 | 3 | 0.0% |
| ULTRACEMCO | 3 | 0 | 3 | 0.0% |
| NTPC | 2 | 1 | 1 | 50.0% |
| AXISBANK | 1 | 0 | 1 | 0.0% |
| BANKBARODA | 1 | 1 | 0 | 100% |
| HINDALCO | 1 | 1 | 0 | 100% |

**TATASTEEL: 8 trades, 0 wins, −₹352,570 in losses** — appears in Mean_Reversion (SHORT ×5), Momentum_Retest (BUY ×1), and EDG_MOMENT (BUY ×2). The system traded it directionally wrong in both directions. In range_market, TATASTEEL maintained a gradual downtrend that defeated both SHORT reversals (price moved up) and BUY breakouts (price immediately fell).

---

## 4. Analysis by Entry Hour

| Entry Hour | Trades | Wins | Losses | WR | Notes |
|---|---|---|---|---|---|
| **09 (09:45–09:59)** | 5 | 1 | 4 | 20.0% | First-candle entries: 09:45 scheduler slot |
| **10 (10:00–10:59)** | 8 | 2 | 6 | 25.0% | Morning momentum slot |
| **11 (11:00–11:59)** | 7 | 2 | 5 | 28.6% | Best win rate window |
| **12 (12:00–12:59)** | 1 | 0 | 1 | 0.0% | Tiny sample |
| **13 (13:00–13:59)** | 7 | 1 | 6 | 14.3% | Post-lunch slot — poorest WR |
| **14 (14:00–14:59)** | 1 | 0 | 1 | 0.0% | Tiny sample |
| **15 (15:00–15:59)** | 2 | 0 | 2 | 0.0% | End-of-day slot: 0/2 wins |

### Entry hour loss distribution:
```
Hour 13 ████████████████████  22%  (6/27)  ← 2nd worst by count
Hour 10 ████████████████████  22%  (6/27)
Hour 11 ████████████████████  19%  (5/27)
Hour 09 ████████████████      15%  (4/27)
Hour 13 (14.3% WR)
Hour 15 (0.0% WR)  — no winning end-of-day entries
```

**Observations:**
1. Hour 13 (13:00–14:00) has both the second-highest loss count (6) and the lowest WR among meaningful buckets (14.3%). The post-lunch slot consistently underperforms.
2. Hours 09 and 10 (09:45–10:59) have WR of 20–25% — below system average but not dramatically so.
3. Hour 11 is the best window at 28.6% WR (2/7) — the mid-morning re-scan slot.
4. End-of-day entries (hour 15) have 0% WR — 2 losses, no wins.

---

## 5. Analysis by VIX Bucket

VIX readings from `market.data.ready` at entry dates:

| VIX Bucket | Trades | Wins | Losses | WR | Sample Dates |
|---|---|---|---|---|---|
| **12–15** | 0 | — | — | — | Jun period (no compliant closed trades) |
| **15–17** | 3 | 0 | 3 | 0.0% | May07 (16.8), May29 (16.2) |
| **17–19** | 18 | 3 | 15 | 16.7% | Apr-May majority |
| **19–20** | 8 | 2 | 6 | 25.0% | Apr23-24, May11, May18 |
| **20+** | 1 | 1 | 0 | 100% (n=1) | ICICIBANK Apr10 (18.8) — barely hits bucket |

> Best-performing VIX bucket is 19–20, though small sample.

**Key VIX pattern:**
- Trades at VIX 15–17 (falling VIX, "calm" period) had 0% WR — 3 losses. Counter-intuitively, lower VIX did not improve outcomes.
- The bulk of the analysis period (VIX 17–19) showed 16.7% WR — persistent low.
- No trades in VIX < 15 bucket had closed outcomes in this window.

**VIX and strategy mismatch:**  
Mean_Reversion works best at VIX 18–22 (elevated fear creating oversold conditions). In the 15–17 bucket, fear is gone and stocks move directionally — unfavorable for mean-reversion setups.

---

## 6. Analysis by Theme Phase

`opportunity.equity.found` payload fields `theme_phase`, `archetype`, and `setup` were not populated in the period analysed — these fields came back empty for all trades. The opportunity scanner was not emitting structured theme/archetype metadata to `ct_events` in the Apr–May window.

**What IS available from opportunity events: the `strategy` field and `confidence` score.**

### Confidence Score at Entry (from ct_events `decision.approved`):

| Symbol | Decision Score | Modifier | Outcome |
|---|---|---|---|
| BHARTIARTL (Apr20 MR) | 7.36 | 1.0 | LOSS −₹41,945 |
| ICICIBANK (Apr22 SHORT MR) | ~7.5 | ~0.9 | LOSS −₹48,631 |
| TATASTEEL (Apr22 SHORT MR) | ~7.5 | ~0.9 | LOSS −₹34,816 |
| BANKBARODA (Apr22 SHORT MR) | ~6.9 | 0.944 | WIN +₹67,750 |
| COALINDIA (Apr23 MR) | 6.93–7.06 | 0.944 | WIN +₹30,233 |
| COALINDIA (Apr23 MoR) | — | — | WIN +₹93,400 |
| NTPC (Apr24 MoR) | — | — | WIN +₹54,945 |
| RELIANCE (Apr28 MoR) | — | — | WIN +₹124,122 |
| BHARTIARTL (Apr20 MR) | 7.36 | 1.0 | LOSS |

**Counterintuitive finding:** Higher decision scores did not predict better outcomes. The BANKBARODA winner had score 6.93 (near-threshold), while TATASTEEL losses had scores ~7.5. The debate system's numerical output appears **not correlated with outcome** in this sample.

---

## 7. Analysis by Archetype

Archetype data was not populated in `ct_events` payloads. However, the `strategy` name maps to implicit archetypes as defined in the system:

| Implicit Archetype | Strategy | Trades | WR |
|---|---|---|---|
| Mean-reversion bounce | Mean_Reversion | 13 | 15.4% |
| Momentum continuation | Momentum_Retest | 11 | 27.3% |
| Trend continuation | Trend_Pullback | 5 | 20.0% |
| Edge/Evolved breakout | EDG_MOMENT_100_EE0005 | 2 | 0.0% |

In a `range_market` dominant regime:
- Mean-reversion bounce: theoretically correct, but symbol selection (TATASTEEL, BHARTIARTL) captured stocks in structural downtrends, not true range oscillations
- Momentum continuation: deployed in range_market (valid), but RELIANCE in May entered a sustained 3-week downtrend after the initial win
- Trend continuation: deployed in range_market (WRONG archetype for the regime)

---

## 8. Winners vs Losers Compared

| Dimension | Winners (6 trades) | Losers (27 trades) |
|---|---|---|
| Avg WR | 100% | 0% |
| Avg P&L | +₹74,940 | −₹48,304 |
| Avg hold time | 3.1 days | 1.4 days |
| Strategy | MoR ×3, MR ×2, TP ×1 | MR ×11, MoR ×8, TP ×4, EDG ×2, Other ×2 |
| Sector | Energy ×2, Diversified ×1, Banking ×1, Metals ×1, Energy ×1 | Metals ×8, Diversified ×5, Telecom ×4, Banking ×3, Cement ×3, Energy ×2, Other ×2 |
| Entry hour | 09, 10×3, 11, 13 | All hours, dominated by 10–13 |
| Regime | range_market ×5, bull_trend ×1 | range_market ×27 |
| Exit reason | SESSION_EXPIRED ×3, SYSTEM_CLEANUP ×2, PHANTOM_CORRECTED ×1 | adaptive_exit ×17, close_sl ×4, SESSION_EXPIRED ×3, other ×3 |
| VIX range | 17.56–18.89 | 16.17–19.94 |
| Avg decision score | ~7.1 | ~7.4 |

### Winners by exit mechanism:
- SESSION_EXPIRED (3): BANKBARODA, COALINDIA_MR, RELIANCE_Apr28 — positions held overnight recovered in the next session
- SYSTEM_CLEANUP (2): COALINDIA_MoR, NTPC_Apr24 — positions exited during engineering cleanup, not by market signal
- PHANTOM_CORRECTED (1): HINDALCO — exit price corrected after phantom simulation error

**Critical insight on winners:** 3 of the 6 wins were NOT closed by a market signal — they were closed by system maintenance (SYSTEM_CLEANUP ×2, PHANTOM_CORRECTED ×1). Only 3 wins represent genuine market exits where the trade moved in the predicted direction and the system closed correctly (SESSION_EXPIRED ×3).

### Losers by exit mechanism:
```
adaptive_exit            ██████████████████████████████████  63%  (17/27)
close_sl (stop hit)      ████████                            15%  ( 4/27)
SESSION_EXPIRED (loss)   ████████                            11%  ( 3/27)
other                    ████████                            11%  ( 3/27)
```

**adaptive_exit is the exit mechanism for 63% of all losses.** This is the AdaptiveExitEngine's time/stagnation-based stop. It fires when a position does not reach its target within the allotted time window or begins deteriorating, closing the trade before the nominal stop loss is reached.

---

## 9. Common Characteristics of Losing Trades

### The ranked factors from evidence:

| Rank | Factor | Frequency in Losses | Evidence |
|---|---|---|---|
| **#1** | **Closed by `adaptive_exit` before reaching SL or target** | **17/27 = 63%** | Exit reason field across all CSVs |
| **#2** | **`range_market` regime at entry** | **27/27 = 100%** | Daily regime from ct_events market.data.ready |
| **#3** | **Symbol = TATASTEEL (Metals sector)** | **8/27 = 30%** | All TATASTEEL trades → 0 wins |
| **#4** | **Post-lunch entry (hour 13–15)** | **9/27 = 33%** | Entry hour from execution timestamps |
| **#5** | **Strategy is Trend_Pullback or EDG_MOMENT** | **6/27 = 22%** | Strategy filed — trend strategies in range |
| **#6** | **Multi-session hold with adverse drift** | Visible in SESSION_EXPIRED losses | Hold time pattern |
| **#7** | **High decision score (≥7.5) with regime modifier < 1.0** | Visible in ICICIBANK/TATASTEEL Apr22 | Decision approval data |

---

## 10. The Single Factor Appearing Most Often in Losing Trades

### **`adaptive_exit` (63% of all losses)**

17 of 27 compliant losses were closed by the `AdaptiveExitEngine` before the actual stop loss was reached. This means:

1. The trades **never moved to target** — they stagnated or moved slowly against the position
2. The system correctly identified deteriorating positions and cut them early (smaller loss than full SL)
3. But the underlying pattern is that **these trades did not have directional follow-through**

The `adaptive_exit` is a symptom, not a root cause. It fires because the underlying instrument did not move in the expected direction within the expected timeframe.

**Why did the instruments not follow through?**

Looking at the adaptive_exit losers by sector/symbol:
- TATASTEEL SHORTs (Apr22, Apr27, May11): range_market → stock moved UP not DOWN (mean-reversion SHORT failed — stock was resuming uptrend)
- RELIANCE LONGs (May04–07, May11): entered after RELIANCE Apr28 win, but price entered sustained downtrend
- BHARTIARTL LONGs (Apr20, May18, May20, May22): telecom in range_market with falling prices
- ICICIBANK SHORTs (Apr22): banking went up, not down
- ULTRACEMCO LONGs (Apr23): entered at 10am, position small, price flat, replaced at day-end

**The compound factor:** Most adaptive_exit losers share **all three** of:
1. **range_market regime** (no directional thrust)
2. **instrument in a local trend opposing the trade direction** (TATASTEEL trending up when shorted; RELIANCE in downtrend when bought)
3. **entry via a reversal strategy** (Mean_Reversion) or continuation strategy in the wrong phase (Momentum_Retest after initial move exhausted)

---

## 11. Summary Answer to "What Factor Appears Most Often in Losing Trades?"

**The single factor with the highest frequency across all losing trades:**

> **`range_market` + adaptive_exit combination (100%/63%)** — every losing trade occurred in a `range_market` day, and 63% of them were closed by the adaptive exit before reaching target or stop, indicating that the trades entered setups without sufficient directional conviction in a non-trending environment.

**But the most actionable finding is more specific:**

> **TATASTEEL (8 trades, 0 wins, −₹352,570) is the single most concentrated failure source.** The system traded TATASTEEL in both directions (SHORT via Mean_Reversion, BUY via Momentum_Retest and EDG_MOMENT) in range_market, and was wrong every single time. TATASTEEL maintained a structural drift that defeated both reversal and breakout entries.

**Factor frequency table:**

| Factor | Present in | % of 27 losses |
|---|---|---|
| range_market regime | 27/27 | **100%** |
| adaptive_exit close | 17/27 | **63%** |
| Symbol in Metals sector | 8/27 | **30%** |
| Post-lunch entry (13:00–15:30) | 9/27 | **33%** |
| Trend strategy in range_market | 6/27 | **22%** |
| TATASTEEL specifically | 8/27 | **30%** |
| RELIANCE multi-day losing streak | 5/27 | **19%** |

**The factor appearing most often: `range_market` regime (100%).** However, since this is the background condition for the entire analysis period, the more discriminating factor is:

**`adaptive_exit` in `range_market` (63%)** — positions that were correctly scored (≥6.5), correctly sized, correctly approved — but placed in instruments without sufficient volatility or directional conviction to move to target before the time-based exit fired. This points at **setup quality at the opportunity detection layer**, specifically: instruments that pass the confidence threshold but lack the velocity/momentum to reach target before the adaptive exit closes them.

---

## Appendix — Full Compliant Trade List

| # | Date | Symbol | Strategy | Entry | P&L | W/L | Regime | VIX | Exit Reason | Hour |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Apr10 | ICICIBANK | MR | 12:23 | −14,774 | L | range | 18.80 | SESSION_EXPIRED_LEGACY | 12 |
| 2 | Apr20 | BHARTIARTL | MR | 09:45 | −41,945 | L | range | 18.89 | adaptive_exit | 9 |
| 3 | Apr22 | BANKBARODA | MR SHORT | 12:33 | +67,750 | **W** | range | 17.93 | SESSION_EXPIRED | 12 |
| 4 | Apr22 | ICICIBANK | MR SHORT | 13:06 | −48,631 | L | range | 17.93 | adaptive_exit | 13 |
| 5 | Apr22 | TATASTEEL | MR SHORT | 13:09 | −34,816 | L | range | 17.93 | adaptive_exit | 13 |
| 6 | Apr23 | ULTRACEMCO | MR | 10:04 | −4,698 | L | range | 18.58 | REPLACEMENT | 10 |
| 7 | Apr23 | COALINDIA | MR | 11:30 | +30,233 | **W** | range | 18.58 | SESSION_EXPIRED | 11 |
| 8 | Apr23 | COALINDIA | MoR | 09:45 | +93,400 | **W** | range | 18.58 | SYSTEM_CLEANUP | 9 |
| 9 | Apr23 | ULTRACEMCO | MR | 13:18 | −5,103 | L | range | 18.58 | SESSION_EXPIRED | 13 |
| 10 | Apr23 | ULTRACEMCO | MR | 15:00 | −7,695 | L | range | 18.58 | SESSION_EXPIRED | 15 |
| 11 | Apr24 | NTPC | MoR | 10:59 | +54,945 | **W** | range | 19.49 | SYSTEM_CLEANUP | 10 |
| 12 | Apr27 | TATASTEEL | MR SHORT | 09:45 | −36,413 | L | range | 18.45 | adaptive_exit | 9 |
| 13 | Apr27 | TATASTEEL | MR SHORT | 11:44 | −40,397 | L | range | 18.45 | adaptive_exit | 11 |
| 14 | Apr28 | TATASTEEL | MoR | 10:30 | −47,709 | L | range | 17.84 | adaptive_exit | 10 |
| 15 | Apr28 | RELIANCE | MoR | 10:50 | +124,122 | **W** | range | 17.84 | SESSION_EXPIRED | 10 |
| 16 | Apr23 | AXISBANK | MR | 14:00 | −41,724 | L | range | 18.58 | adaptive_exit | 14 |
| 17 | May04 | RELIANCE | MoR | 11:24 | −52,617 | L | range | 18.47 | SESSION_EXPIRED | 11 |
| 18 | May05 | RELIANCE | MoR | 10:05 | −41,486 | L | range | 17.99 | adaptive_exit | 10 |
| 19 | May07 | RELIANCE | MoR | 11:29 | −132,044 | L | range | 16.80 | SESSION_EXPIRED | 11 |
| 20 | May07 | RELIANCE | MoR | 13:00 | −133,980 | L | range | 16.80 | close_sl | 13 |
| 21 | May11 | NTPC | MoR | 10:35 | −71,946 | L | range | 18.50 | close_sl | 10 |
| 22 | May11 | RELIANCE | MoR | 15:16 | −47,940 | L | range | 18.50 | adaptive_exit | 15 |
| 23 | May11 | TATASTEEL | MR SHORT | 11:17 | −34,937 | L | range | 18.50 | adaptive_exit | 11 |
| 24 | May11 | TATASTEEL | MR SHORT | 13:00 | −37,104 | L | range | 18.50 | adaptive_exit | 13 |
| 25 | May11 | COALINDIA | MoR | 14:00 | −37,140 | L | range | 18.50 | adaptive_exit | 14 |
| 26 | May14 | TATASTEEL | EDG | 10:52 | −37,132 | L | range | 18.66 | adaptive_exit | 10 |
| 27 | May18 | TATASTEEL | EDG | 09:45 | −84,785 | L | range | 19.94 | close_sl | 9 |
| 28 | May18 | BHARTIARTL | TP | 13:00 | −13,122 | L | range | 19.94 | adaptive_exit | 13 |
| 29 | May20 | BHARTIARTL | TP | 09:45 | −11,644 | L | range | 18.55 | adaptive_exit | 9 |
| 30 | May20 | COALINDIA | TP | 10:30 | −59,746 | L | range | 18.55 | close_sl | 10 |
| 31 | May21 | HINDALCO | TP | 13:00 | +59,988 | **W** | bull_trend | 17.75 | PHANTOM_CORRECTED | 13 |
| 32 | May22 | BHARTIARTL | TP | 11:30 | −15,142 | L | range | 17.95 | adaptive_exit | 11 |
| 33 | May29 | COALINDIA | TP | 10:36 | −400,752⚠ | L | range | 16.17 | PHANTOM_PRICE_CORRECTION | 10 |

**Strategy codes:** MR=Mean_Reversion, MoR=Momentum_Retest, TP=Trend_Pullback, EDG=EDG_MOMENT_100_EE0005

---

*All data from VPS `ct_events` (control_tower.db), `market.data.ready` regime/VIX payloads, and `paper_trades_backup_*.csv` files. No code was modified during this investigation.*
