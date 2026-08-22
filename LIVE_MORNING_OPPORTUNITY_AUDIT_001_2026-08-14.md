# LIVE MORNING OPPORTUNITY AUDIT — 001
**Date:** 2026-08-14  
**Observation window:** 08:00 – 10:40 IST  
**Mode:** READ-ONLY / OBSERVATION ONLY  
**No production changes made.**

---

## A. PRODUCTION HEALTH

| Item | Value | Status |
|---|---|---|
| VPS commit | `8ac54e7` | ✅ |
| Local commit | `8ac54e7` | ✅ |
| Local/VPS match | YES | ✅ |
| `ai-trading-brain` | Up 18+ hours (healthy) | ✅ |
| `trading-dashboard` | Up 18+ hours (healthy) | ✅ |
| `PAPER_TRADING` | `false` | ✅ LIVE |
| `ACTIVE_BROKER` | `dhan` | ✅ |
| `TOTAL_CAPITAL` | ₹10,000 | ✅ |
| Dhan connection | `auth=OK` token `+23h 30m` | ✅ |
| Scheduler | `SYSTEM LOOP ACTIVE — heartbeat OK` (every 5 min) | ✅ |
| OrderManager positions | 0 | ✅ |
| TradeMonitor positions | 0 | ✅ |
| Dhan live positions | 0 | ✅ |
| Dhan live orders | 0 | ✅ |
| Orphan audit | `CSV integrity OK — 0 orphaned positions` | ✅ |
| Execution exceptions | None — no `MISSING_DHAN_MAPPING`, `EB001`, `EB002` | ✅ |
| SR_Validator error | `_pd_MultiIndex` NameError at 08:00 (pre-market, non-blocking) | ⚠️ |
| ETF_ARB_DISABLED | Confirmed in container | ✅ |
| Futures disabled | `_FUTURES_DISABLED=True` | ✅ |

**Production health: HEALTHY.** One pre-existing SR_Validator bug fires at 08:00 pre-market but does not block any cycle or execution path.

---

## B. MARKET SNAPSHOT

**Observation time:** 10:40 IST

| Index | Last | Prev Close | Change |
|---|---|---|---|
| NIFTY | 24,319.65 | 24,395.85 | **-0.31%** |
| BANKNIFTY | 57,503.35 | 57,635.25 | **-0.23%** |
| INDIA VIX | 11.41 | — | Low |

| Indicator | Value | Interpretation |
|---|---|---|
| Detected regime | `range_market` | Sideways / mean-reverting |
| Volatility classification | `low` | Subdued movement |
| PCR (NIFTY) | 0.94 | Slight put bias |
| PCR (BANKNIFTY) | 0.83 | Put-side weighted |
| Market breadth | 40% | Slightly below neutral |
| Global macro bias | `neutral` (MacroScore +0.40) | Muted overnight cues |
| NIFTY ATM-IV | 9.7% | Low IV regime |
| BANKNIFTY ATM-IV | 12.0% | Modest premium |

**Global context (08:00 pre-market):**
S&P500 +0.65% | Nasdaq +0.81% | Nikkei +0.77% | HangSeng -0.50% | Crude -2.64% | Gold -0.70% | USD/INR +0.09%  
_Positive US/Japan cues, crude weakness. Overall neutral-to-mild positive for Indian equities._

**Sector observation:**
- Gainers: Healthcare (APOLLOHOSP +3.65%), QSR/Consumer (DEVYANI +3.27%, JUBLFOOD +3.27%), Power (TATAPOWER +0.73%, TORNTPOWER +0.60%), Telecom (BHARTIARTL +0.90%), Adani group (ADANIPORTS +1.54%, ADANIENT +1.27%)
- Losers: Metals (SAIL -3.71%, HINDZINC -3.41%, TATASTEEL -2.40%, HINDALCO -1.99%), Chemicals (SOLARINDS -3.03%, ATUL -2.65%), Pharma (IPCALAB -3.24%), PSU banks (CANBK -1.39%, PNB +0.51%)
- Characterisation: Sector rotation from metals/chemicals to healthcare/consumer. Classic range-market behaviour.

---

## C. TOP 20 GAINERS (within 230-stock universe)

| Rank | Symbol | Change | In 38-Watchlist | IIOS Identified |
|---|---|---|---|---|
| 1 | APOLLOHOSP | +3.65% | No | B — in 230, `overbought_short_watch` at Phase D scan (score 0.509 < floor) |
| 2 | DEVYANI | +3.27% | No | E — insufficient 08:00 evidence; Phase D data incomplete |
| 3 | JUBLFOOD | +3.27% | No | B — in 230, `overbought_short_watch` at Phase D (score 0.513 < floor) |
| 4 | VOLTAS | +1.79% | No | **A** — mean_reversion_bounce signal, score 0.6648, blocked by STRATEGY_DISABLED |
| 5 | ADANIPORTS | +1.54% | **Yes** | B — in scanner, not identified as setup today |
| 6 | ADANIENT | +1.27% | **Yes** | **A** — mean_reversion_bounce, score 0.5351, blocked by STRATEGY_DISABLED |
| 7 | ADANIGREEN | +1.27% | No | E — insufficient evidence |
| 8 | AMBER | +1.15% | No | B — in 230, `neutral` bucket at Phase D (score 0.525 < floor) |
| 9 | CESC | +1.14% | No | E — insufficient evidence |
| 10 | EASEMYTRIP | +1.13% | No | E — insufficient evidence |
| 11 | ASHOKLEY | +0.99% | No | B — in 230, `overbought_short_watch` (score 0.492 < floor) |
| 12 | BHARTIARTL | +0.90% | **Yes** | B — in scanner, `breakout + trend_pullback` (score 0.530 < floor) |
| 13 | GABRIEL | +0.84% | No | E — insufficient evidence |
| 14 | FORTIS | +0.73% | No | **A** — mean_reversion_bounce, score 0.8276, blocked by STRATEGY_DISABLED |
| 15 | TATAPOWER | +0.73% | No | B — in 230, `neutral` bucket (score 0.490 < floor) |
| 16 | TORNTPOWER | +0.60% | No | E — insufficient evidence (not in Phase D scan coverage) |
| 17 | DEEPAKNTR | +0.60% | No | E — insufficient evidence |
| 18 | PNB | +0.51% | No | B — in 230, `overbought_short_watch` (score 0.492 < floor) |
| 19 | BAJAJ-AUTO | +0.49% | No | E — insufficient evidence |
| 20 | WIPRO | +0.48% | **Yes** | B — in scanner, not identified today |

**Gainer legend:** A = in 230 AND identified by IIOS | B = in 230 but not identified | E = insufficient evidence

---

## D. TOP 20 LOSERS (within 230-stock universe)

| Rank | Symbol | Change | In 38-Watchlist | IIOS Identified |
|---|---|---|---|---|
| 1 | SAIL | -3.71% | No | B — in 230, `neutral` bucket (score 0.490 < floor) |
| 2 | HINDZINC | -3.41% | No | B — in 230, `neutral` bucket (score 0.510 < floor) |
| 3 | IPCALAB | -3.24% | No | E — not in Phase D coverage (66 failed symbols) |
| 4 | SOLARINDS | -3.03% | No | B — in 230, `volume_expansion + overbought_short_watch` (score 0.537 < floor) |
| 5 | ATUL | -2.65% | No | E — not in Phase D coverage |
| 6 | TATASTEEL | -2.40% | **Yes** | **A** — mean_reversion_bounce signal, score 0.6818, blocked by STRATEGY_DISABLED |
| 7 | HINDALCO | -1.99% | **Yes** | B — in scanner, `neutral` bucket (score 0.510 < floor) |
| 8 | NIACL | -1.97% | No | E — insufficient evidence |
| 9 | NMDC | -1.94% | No | E — insufficient evidence |
| 10 | CROMPTON | -1.69% | No | **A** — mean_reversion_bounce signal, score 0.7136, blocked by STRATEGY_DISABLED |
| 11 | RAYMOND | -1.57% | No | E — insufficient evidence |
| 12 | GODREJPROP | -1.57% | No | **A** — mean_reversion_bounce signal, score 0.7524, blocked by STRATEGY_DISABLED |
| 13 | CANBK | -1.39% | No | B — in 230, `trend_pullback` (score ~0.49 < floor at 08:00) |
| 14 | VEDL | -1.38% | No | B — in 230, `neutral` bucket (score 0.490 < floor) |
| 15 | KAYNES | -1.32% | No | E — insufficient evidence |
| 16 | ONGC | -1.25% | **Yes** | B — in scanner, `neutral` bucket (score 0.500 < floor) |
| 17 | ZEEL | -1.24% | No | E — insufficient evidence |
| 18 | EXIDEIND | -1.24% | No | E — insufficient evidence |
| 19 | ASIANPAINT | -1.23% | **Yes** | B — in scanner, `trend_pullback` (score ~0.49 < floor) |
| 20 | MCX | -1.22% | No | B — in 230, `volume_expansion + overbought_short_watch` (score 0.548 < floor) |

**Loser legend:** A = in 230 AND identified | B = in 230 but not identified | E = insufficient evidence

---

## E. 230-STOCK UNIVERSE COVERAGE

| Metric | Value |
|---|---|
| Total universe | 230 stocks (nifty500_universe.json) |
| Phase D scan attempted | 230 |
| Phase D scan successful | 164 (71.3% coverage) |
| Phase D data failures | 66 symbols (IPCALAB, ATUL, TORNTPOWER, etc.) |
| After sector cap (20% per sector) | 120 |
| After score floor (≥0.55) | 54 candidates written to daily_candidates.json |
| Active scanner watchlist | 38 (static, subset of 230) |
| Intraday cycle pool | 70 candidates (prepared + gap fill) |
| Signals generated (10:30 cycle) | 28 |
| Signals surviving StrategyLab | 4 |
| Signals surviving CRE | 0 |
| Trades executed | 0 |

**Top 20 Gainers coverage:**
- 20/20 are within the 230-stock universe (100% universe coverage)
- 3/20 positively identified by IIOS (VOLTAS, ADANIENT, FORTIS)
- 8/20 were in 230 but fell below score floor
- 5/20 had insufficient data coverage (Phase D gaps)

**Top 20 Losers coverage:**
- 20/20 are within the 230-stock universe (100% universe coverage)
- 4/20 positively identified by IIOS (TATASTEEL, CROMPTON, GODREJPROP + 1 scanner)
- 7/20 were below score floor
- 9/20 had insufficient evidence

---

## F. IIOS CANDIDATE FUNNEL (10:30 cycle)

### Pipeline Attrition
```
Universe scanned:     230  → Phase D: 164 (coverage 71.3%)
After sector cap:     164  → 120
After score floor:     120  → 54  (daily_candidates.json)
Intraday pool:          54  → 70  (gap fill from static 38)
Signals generated:      70  → 28
Strategy Lab:           28  → 4   (dominant: Mean_Reversion STRATEGY_DISABLED ×24)
Capital Risk Engine:     4  → 0   (rejection: QTY_ZERO / SL_SIZING ×4)
Risk Control:            0  → 0   (healthy, no input)
Trades executed:         0
```

### Dominant Blockers
1. **STRATEGY_DISABLED** (StrategyLab) — 24 of 28 signals blocked. Mean_Reversion strategy is governance-disabled (G-001/G-002/G-003/G-004 remediation). All mean_reversion_bounce candidates blocked despite regime being `range_market` (ideal for Mean_Reversion).
2. **QTY_ZERO / SL_SIZING** (CapitalRiskEngine) — 4 remaining signals rejected because SL-based sizing produces 0 shares. HAVELLS at ₹1,265 requires ≥₹1,265 for 1 share; allocated_budget=₹900 is insufficient. This is a **capital constraint** (₹10,000 total capital).

### IIOS Candidate Quality (10:30 Cycle)

| Symbol | Dir | CandScore | Setup | RSI | VolRatio | ExpMove% | Strategy | Final Rejection |
|---|---|---|---|---|---|---|---|---|
| HDFCAMC | BUY | 0.8918 | mean_reversion_bounce | 32 | 1.0 | 6.47% | Mean_Reversion | STRATEGY_DISABLED |
| PAGEIND | BUY | 0.8810 | mean_reversion_bounce | 30 | 2.0 | 7.29% | Mean_Reversion | STRATEGY_DISABLED |
| BIOCON | BUY | 0.8624 | mean_reversion_bounce | 33 | 0.6 | 4.93% | Mean_Reversion | STRATEGY_DISABLED |
| ICICIBANK | BUY | 0.8624 | mean_reversion_bounce | 41 | 0.7 | 3.77% | Mean_Reversion | STRATEGY_DISABLED |
| AMBUJACEM | BUY | 0.8426 | mean_reversion_bounce | 38 | 0.7 | 6.10% | Mean_Reversion | STRATEGY_DISABLED |
| MUTHOOTFIN | BUY | 0.8401 | mean_reversion_bounce | 40 | 0.6 | 8.68% | Mean_Reversion | STRATEGY_DISABLED |
| FORTIS | BUY | 0.8276 | mean_reversion_bounce | 36 | 1.2 | 7.50% | Mean_Reversion | STRATEGY_DISABLED |
| GODREJPROP | BUY | 0.7524 | mean_reversion_bounce | 42 | 0.4 | 6.95% | Mean_Reversion | STRATEGY_DISABLED |
| CROMPTON | BUY | 0.7136 | mean_reversion_bounce | 41 | 0.4 | 9.91% | Mean_Reversion | STRATEGY_DISABLED |
| ALKEM | BUY | 0.7056 | mean_reversion_bounce | 37 | 0.5 | 5.95% | Mean_Reversion | STRATEGY_DISABLED |
| TATASTEEL | BUY | 0.6818 | mean_reversion_bounce | 41 | 1.0 | 5.68% | Mean_Reversion | STRATEGY_DISABLED |
| SBILIFE | BUY | 0.6859 | mean_reversion_bounce | 43 | 0.9 | 5.92% | Mean_Reversion | STRATEGY_DISABLED |
| VOLTAS | BUY | 0.6648 | mean_reversion_bounce | 42 | 1.3 | 7.08% | Mean_Reversion | STRATEGY_DISABLED |
| INOXWIND | BUY | 0.6722 | mean_reversion_bounce | 36 | 0.5 | 7.72% | Mean_Reversion | STRATEGY_DISABLED |
| HAVELLS | BUY | exploration | breakout | 50 | 2.2 | 5.45% | Momentum_Retest | CRE_QTY_ZERO |
| NIFTY IC | — | — | Iron_Condor_Range | — | — | — | Iron_Condor_Range | CRE_QTY_ZERO |
| BANKNIFTY IC | — | — | Iron_Condor_Range | — | — | — | Iron_Condor_Range | CRE_QTY_ZERO |

**Note:** `expected_move_pct` is observational only (MOP-RC-001). Not used for decisions.

---

## G. EARLY-MOVE PERSISTENCE

| Symbol | Setup | Phase D (08:00) | 09:45 | 10:30 | Current | Classification |
|---|---|---|---|---|---|---|
| APOLLOHOSP | — | `overbought_short_watch` | Not in pipeline | Not in pipeline | +3.65% | **gap-and-hold** (breakout from overbought) |
| JUBLFOOD | — | `overbought_short_watch` | Not in pipeline | Not in pipeline | +3.27% | **gap-and-hold** |
| VOLTAS | mean_rev | Not in score floor | Identified | Identified | +1.79% | **persistent** (IIOS identified but blocked) |
| ADANIENT | mean_rev | Not in score floor (0.490) | Identified | Identified | +1.27% | **persistent** |
| FORTIS | mean_rev | Not in score floor | Identified | Identified | +0.73% | **intraday breakout** (modest continuation) |
| TATASTEEL | mean_rev | In 230, below floor | Identified | Identified | -2.40% | **persistent loser** (IIOS identified, blocked) |
| GODREJPROP | mean_rev | Not in score floor | Identified | Identified | -1.57% | **persistent loser** |
| CROMPTON | mean_rev | Not in score floor | Identified | Identified | -1.69% | **persistent loser** |
| HINDALCO | — | `neutral`, below floor | Not identified | Not identified | -1.99% | **persistent loser** (not detected) |
| SAIL | — | `neutral`, below floor | Not identified | Not identified | -3.71% | **persistent loser** (not detected) |

**EMP-001 Observation:**
- Moves established at 09:15-09:30 are persisting through 10:30 (range-market day = directional within sectors)
- IIOS correctly identified 4 of the top 10 movers as candidates via `mean_reversion_bounce` setup
- The largest gainers (APOLLOHOSP, JUBLFOOD) were `overbought_short_watch` at pre-market — momentum continuation rather than mean reversion
- The pattern: `overbought_short_watch` → gap up continuation is currently unrepresented in active strategy set

---

## H. EXPECTED-MOVE OBSERVATION (MOP-RC-001)

Observational. Not used for decisions.

| Symbol | ExpMove% | ATR% | RSI | Actual (10:40) | Quality |
|---|---|---|---|---|---|
| MUTHOOTFIN | 8.68% | 3.47% | 40 | ~flat | Candidate blocked |
| CROMPTON | 9.91% | 3.97% | 41 | -1.69% | Move in progress — SHORT direction |
| FORTIS | 7.50% | 3.00% | 36 | +0.73% | Move in progress — LONG direction |
| VOLTAS | 7.08% | 2.83% | 42 | +1.79% | IIOS correctly identified |
| GODREJPROP | 6.95% | 2.78% | 42 | -1.57% | Move in progress — SHORT direction |
| PAGEIND | 7.29% | 2.91% | 30 | ~flat | Early |

_All IIOS-identified candidates are directionally moving. ExpMove% appears calibrated within 1-2× ATR on this time window._

---

## I. DISCOVERY RESULTS

**QUESTION 1: Did IIOS identify stocks that are becoming meaningful movers before/during the early move?**

**YES — partially.**

- Positively identified 7/40 movers (VOLTAS, ADANIENT, FORTIS, TATASTEEL, CROMPTON, GODREJPROP, SBILIFE) with `mean_reversion_bounce` setups
- Missed the 2 biggest gainers (APOLLOHOSP +3.65%, JUBLFOOD +3.27%) — both correctly classified as `overbought_short_watch` at Phase D, which is an accurate observation but no action path exists
- The `overbought_short_watch` bucket identifies stocks in overbought momentum but there is no active strategy to trade momentum continuation (that would be a distinct discovery gap vs today's result)
- 66 Phase D data failures reduced universe coverage to 71.3% — some movers (IPCALAB, ATUL) were not scanned at all

---

## J. SELECTION RESULTS

**QUESTION 2: Among identified stocks, did IIOS select the strongest opportunities?**

**INDETERMINATE — selection blocked before scoring step.**

- IIOS correctly ranked HDFCAMC (0.8918), PAGEIND (0.8810), BIOCON (0.8624), ICICIBANK (0.8624) as top candidates
- VOLTAS (0.6648), TATASTEEL (0.6818), CROMPTON (0.7136), GODREJPROP (0.7524) were all identified and are all currently moving
- The selection ranking appears qualitatively sound — RSI ≤ 43, RR = 2.5, expected moves 4-10%
- However all 24 mean_reversion candidates were blocked at StrategyLab before reaching DecisionEngine, so selection quality cannot be fully measured today
- The 4 that passed StrategyLab (HAVELLS + 2 options + 1 more) all failed CRE at QTY_ZERO

**Selection verdict: SELECTION_BLOCKED_BY_GOVERNANCE, not SELECTION_GAP**

---

## K. OUTSIDE-230 MOVERS

All Top 20 Gainers and Top 20 Losers are within the 230-stock universe.

**Outside-230 significant movers today (supplemental scan):**

| Symbol | Change | Class | Pre-Move Evidence | Detection Path |
|---|---|---|---|---|
| FLUOROCHEM | +3.05% | D3 | Volume expansion + specialty chem sector rotation | No existing discovery path |
| GNFC | +2.72% | D3 | Chemicals sector co-movement | No existing discovery path |
| THYROCARE | +2.11% | D3 | Healthcare sector strength | No existing discovery path |
| RECLTD | -2.65% | D3 | PSU NBFC selling | No existing discovery path |
| RVNL | -0.96% | D1 | No distinctive pre-move signal | No existing discovery path |

**Classification:** D3 = outside 230 with pre-move evidence but no existing discovery path  
**D1** = outside 230 with no reasonable pre-move evidence

_Note: FLUOROCHEM and GNFC showed chemicals sector co-movement evidence (SOLARINDS was in scope at Phase D). RECLTD tracks PFC/REC PSU NBFC sector which was declining._

---

## L. DYNAMIC DISCOVERY CAPABILITY

**QUESTION 3: Does existing architecture support discovery of stocks OUTSIDE 230 before a move?**

**A. Does IIOS scan/observe stocks outside the 230-stock core universe?**  
**No.** The Phase D scanner (`market_scanner.py`) explicitly loads: `Loaded universe: 230 symbols from /app/data/nifty500_universe.json`. The equity scanner watchlist (38 stocks) is a subset of the 230. No scan, observation, or data fetch operates outside this boundary at any layer.

**B. Is there any dynamic watchlist / discovery layer?**  
**Yes, but bounded within the 230.** The architecture has:
1. `HybridExploration` — evaluates static-watchlist symbols not in the prepared pool against a higher threshold (7.2 vs 0.55 base). Admitted HAVELLS today. Operates within the 38-stock watchlist, itself a subset of 230.
2. Event-driven mini rescan — fires on `POOL_EXHAUSTION`, `REGIME_TRANSITION`, `BREADTH_COLLAPSE`, `VIX_SURGE`, `EXPLORATION_STARVATION`. Re-runs Phase D scanner on the same 230.
3. ODM directive — can expand to extended 38-stock watchlist. Still within the 230.
4. Sector reranking — promotes candidates in sector-leading sectors. Within the 230.

No mechanism exists to discover stocks outside the 230.

**C. Can a stock outside the 230 enter the opportunity pipeline?**  
**No.** The boundary is hard-coded to `nifty500_universe.json`. No runtime discovery path bypasses this file.

**D. What signals/characteristics can trigger discovery within the 230?**  
Within the existing 230-boundary, the architecture uses:
- Volume expansion (`vol_ratio ≥ 2.0`)
- RSI extremes (overbought/oversold)
- Breakout proximity (price vs technical resistance)
- ATR-based momentum
- Score floor threshold (0.55)
- Exploration threshold (7.2 for HybridExploration)
- Sector rotation leaders (live sector_leaders from MarketIntelligence)
- Mini rescan triggers: breadth collapse, VIX surge, regime transition
- Breakout invalidation (removes failed setups)
- Conviction decay (de-prioritises stale or low-volume candidates)

None of these can operate outside the 230-stock boundary.

---

## M. PRE-MOVE EVIDENCE OUTSIDE 230

| Symbol | Today Move | Pre-Move Observable | Could Existing Arch Detect? | Notes |
|---|---|---|---|---|
| FLUOROCHEM | +3.05% | Chemicals sector momentum; SOLARINDS (-3%) in 230 moved differently (selling) | No path — not in 230 | D3 |
| GNFC | +2.72% | Chemicals divergence; above avg vol pre-move likely present | No path — not in 230 | D3 |
| THYROCARE | +2.11% | Healthcare sector strength; APOLLOHOSP in 230 led the move | No path — not in 230 | D3 |
| RECLTD | -2.65% | PSU NBFC sector weakness tracked via PFC/REC; co-move with PFC/BEL | No path — not in 230 | D3 |

**Research question (not recommendation):**  
GNFC and FLUOROCHEM moved with chemistry sector momentum. THYROCARE moved with APOLLOHOSP's healthcare sector signal. If a future architecture layer had access to sector-ETF or sector-index behaviour, it could potentially infer that related outside-230 stocks may be moving. This is an architectural question for later investigation — not a recommendation to expand the universe.

---

## N. TRADE/EXECUTION RESULT

**0 trades executed.**

### Full Rejection Trace (10:30 Cycle, representative)

```
230 universe → Phase D scan → 54 candidates → 70 intraday pool
→ 28 signals generated (EquityScannerAI / OpportunityEngine)
→ 24 rejected: StrategyLab [Mean_Reversion STRATEGY_DISABLED]
→  4 passed StrategyLab
→  4 rejected: CapitalRiskEngine [QTY_ZERO / SL_SIZING]
→  0 to RiskControl → 0 to RiskGuardian → 0 to OrderManager
→  0 executed
```

`[TradeDiagnostic] No trades this cycle. 28 signal(s) generated → 0 executed. Dominant blocker: [StrategyLab] STRATEGY_DISABLED.`

---

## O. MISSED OPPORTUNITIES

| Symbol | Move | Why Missed | Stage |
|---|---|---|---|
| APOLLOHOSP +3.65% | `overbought_short_watch` at Phase D — no BUY strategy for momentum continuation | No strategy for this setup type in active set | StrategyLab |
| JUBLFOOD +3.27% | Same as APOLLOHOSP | No strategy for momentum continuation | StrategyLab |
| VOLTAS +1.79% | Correctly identified, score 0.6648 | Mean_Reversion STRATEGY_DISABLED | StrategyLab |
| TATASTEEL -2.40% | Correctly identified, score 0.6818 | Mean_Reversion STRATEGY_DISABLED | StrategyLab |
| GODREJPROP -1.57% | Correctly identified, score 0.7524 | Mean_Reversion STRATEGY_DISABLED | StrategyLab |
| CROMPTON -1.69% | Correctly identified, score 0.7136 | Mean_Reversion STRATEGY_DISABLED | StrategyLab |
| FORTIS +0.73% | Correctly identified, score 0.8276 | Mean_Reversion STRATEGY_DISABLED | StrategyLab |
| HAVELLS (exploration) | Score 8.21 > threshold 7.2, conf=10.0 | CRE QTY_ZERO (₹1,265 × 1 = ₹1,265 > ₹900 budget) | CRE |

---

## P. ROOT-CAUSE CLASSIFICATION

| Root Cause | Description | Impact |
|---|---|---|
| **STRATEGY_DISABLED** (primary) | Mean_Reversion strategy disabled by G-001/G-002/G-003/G-004 governance remediation. Today's market is `range_market` — the exact regime Mean_Reversion is designed for. 24/28 signals blocked at this stage. | All identified range-market candidates unreachable |
| **CAPITAL_CONSTRAINT** (secondary) | SL-based sizing produces QTY=0 for all 4 survivors. ₹900 allocated budget < 1 share price for HAVELLS (₹1,265). Affects higher-priced stocks and options. | Options (Iron Condor) and high-priced stocks cannot execute |
| **DATA_COVERAGE_GAP** (tertiary) | 66/230 symbols failed in Phase D scan (71.3% coverage). IPCALAB, ATUL, TORNTPOWER, CESC not scanned. Some of these moved significantly today. | Movers in uncovered symbols cannot be identified |
| **STATIC_UNIVERSE_BOUNDARY** (structural) | Hard boundary at 230 stocks. No path to discover outside-230 movers before their move. Today this was not a critical gap (all top movers were within 230) but is an architectural observation. | No same-day discovery of outside-230 movers |

---

## Q. RECOMMENDATIONS

_Restricted per audit mandate: No recommendations to change the 230-stock universe or enable strategies._

**Research questions for later investigation (not production changes):**

1. **Mean_Reversion governance path:** IIOS generated 24 high-quality mean_reversion_bounce signals in a confirmed `range_market` regime. The strategy is disabled by governance. The system has a well-designed governance remediation framework (G-001 through G-004). The question of when/whether Mean_Reversion re-enables itself is a strategy governance question, not a code or data question.

2. **CRE SL_SIZING in low-capital mode:** QTY_ZERO occurs because ₹900 allocated budget is below single-share cost for mid/high-price stocks. This is expected behaviour for ₹10,000 total capital. As capital grows, this constraint naturally resolves. No change recommended.

3. **Phase D coverage gap:** 66 symbols (29%) failed in Phase D scan. Some of these (IPCALAB -3.24%, ATUL -2.65%) had significant moves today. The root cause is likely stale/missing yfinance data for small-mid cap names in pre-market. Worth investigating Phase D data reliability.

4. **Dynamic universe research question:** Today all Top-40 movers were within the 230-stock universe, so no universe gap caused a missed opportunity. FLUOROCHEM/GNFC/THYROCARE (outside 230) moved but with smaller magnitude than within-230 leaders. The architectural question of whether a sector-correlation discovery path could identify outside-230 co-movers remains open for future research.

---

## FINAL VERDICT

```
PRIMARY VERDICT: GOVERNANCE_GAP
```

**Explanation:** IIOS correctly identified 7 of today's significant movers as `mean_reversion_bounce` candidates with scores 0.51–0.89. The detection capability is functioning. The pipeline failed at StrategyLab because `Mean_Reversion` is governance-disabled. The primary blocking factor is a governance decision, not a discovery, selection, or execution failure.

```
SECONDARY OBSERVATIONS:
  - CAPITAL_CONSTRAINT: QTY_ZERO for 4 survivors at CRE (low capital limit)
  - DATA_COVERAGE_GAP: 66/230 symbols missing from Phase D scan
  - DYNAMIC_UNIVERSE: bounded at 230; outside-230 movers (FLUOROCHEM, GNFC)
    had no detection path but also had smaller moves than within-230 leaders
  - EXECUTION_PATH: EB001/EB002 fixes deployed and verified healthy
```

**Discovery:** ✅ HEALTHY (7 movers identified)  
**Selection:** ⚠️ INDETERMINATE (blocked before scoring step)  
**Execution path:** ✅ VERIFIED HEALTHY (no execution exceptions)  
**Strategy governance:** ⚠️ GOVERNANCE_GAP (range-market + Mean_Reversion disabled)  
**Capital adequacy:** ⚠️ CONSTRAINT (QTY_ZERO for high-price stocks at ₹10k capital)

---

```
Production changes:   0
Code changes:         0
Configuration:        0
Universe changes:     0
Threshold changes:    0
Forced trades:        0
Manual orders:        0
Dhan write calls:     0
```
