# KNOWLEDGE_TO_OPPORTUNITY_AUDIT_001
**Date:** 2026-08-13  
**Scope:** READ-ONLY — zero production changes  
**Trigger:** BML-001 / Predictive Universe Test identified 6 C-class stocks (scored PREDICTED but zero opportunity generated)  
**Author:** AI Trading Brain Audit Agent  
**Status:** FINAL

---

## EXECUTIVE SUMMARY

On 2026-08-13 the Broad Market Learning (BML-001) audit identified 6 stocks classified as **C** — the system HAD prior knowledge about them (they existed in the observable universe) but generated **zero trading opportunities**.

This audit traces every stage from knowledge existence to opportunity delivery for each stock, identifies every loss point, and maps them to architectural gaps versus unused existing capabilities.

**Key finding: No single root cause. There are three distinct failure classes operating in parallel:**

| Class | Description | C-stocks affected |
|---|---|---|
| **F-1: Universe Selection** | Stock existed in universe but not selected as prepared candidate | ASTRAL, KAYNES, EASEMYTRIP, PCJEWELLER |
| **F-2: Short Direction Routing** | Strategy layer has no path for SHORT equity signals in RANGE_MARKET | HINDALCO, KAYNES, INFY + all others with SHORT direction |
| **F-3: Dead-End Capability** | Working capability (ph2_short_dna, Setup 4, PIG) that exists but is wired only to EOD reporting, not the live pipeline | ALL 6 stocks |

**Existing but unused capabilities that could reduce the miss rate:**
1. Setup 4 (high_rsi_short) in equity_scanner_ai.py — generates SHORT signals, but strategy router drops them
2. ph2_short_dna.evaluate_short_dna() — 55 loser INSTITUTIONAL patterns — wired to EOD PRR only
3. overbought_short_watch bucket in market_scanner — computed but used as score PENALTY, not short-candidate promotion
4. institutional_dna.db SHORT DNA — `volume_spike` conf=1.0 (69 evidence events) — not consumed by live pipeline

**Genuine capability gaps:**
1. No momentum-continuation-SHORT scanner setup (declining stocks with elevated volume)
2. No SHORT equity strategy in MetaStrategyController RANGE_MARKET map
3. Market_scanner actively penalises overbought stocks instead of routing them to short queue

---

## 1. SIX-STOCK TRACE TABLE

| Symbol | Direction | BML Class | In Universe | In Aug-11 Candidates | Learning Registry | Prior DNA | Loss Point(s) |
|---|---|---|---|---|---|---|---|
| ASTRAL | LONG (breakout) | C | YES (market_scanner universe, line 579) | NO | None | None | F-1: Not in prepared candidates on Aug-12 scan |
| KAYNES | SHORT (overbought fade) | C | YES (market_scanner universe, line 581) | NO | None | None | F-1 + F-2: Not in candidates; overbought score penalty; no SHORT strategy path |
| HINDALCO | SHORT (overbought fade) | C | YES (equity_scanner BASE_WATCHLIST) | Unknown | PGA-EB51FF6E (PENDING, 2026-08-07) | 0 (dna_count=0) | F-2 + F-3: Stale resistance level; no SHORT strategy in RANGE_MARKET; DNA action unexecuted |
| PCJEWELLER | SHORT (momentum decline) | C | YES (market_scanner universe, line 611) | NO | None | None | F-1 + F-2: Not in candidates; no declining-momentum SHORT scanner |
| EASEMYTRIP | SHORT (momentum decline) | C | YES (market_scanner universe, line 616) | NO | None | None | F-1 + F-2: Not in candidates; declining stock ≠ overbought → Setup 4 wrong direction |
| INFY | SHORT (IT sector decline) | C | YES (equity_scanner BASE_WATCHLIST) | Unknown | PGA-152D8969 (PENDING, 2026-08-07) | 0 (dna_count=0) | F-2 + F-3: Low volume (0.26x) fails all setups; no IT-short scanner; DNA action unexecuted |

---

## 2. ASTRAL — MOMENTUM CONTINUATION LONG

### Stock Profile (2026-08-13)
- Sector: INFRA (NIFTY200)  
- Aug-11 close: 1424.90 | Aug-12 close: 1464.45 (+2.74%) | Aug-13 open: 1499.00  
- Aug-13 intraday: +2.40%, rel_vol: 2.75x, gap: +2.36%  
- Signal type: LONG breakout continuation — this is a BUY opportunity, not a short

### Process-1 Assessment (Can IIOS know?)
ASTRAL IS in `market_scanner.py` full universe:
```python
{"symbol": "ASTRAL", "yahoo_ticker": "ASTRAL.NS", "sector": "INFRA", "index": "NIFTY200"}
# market_scanner.py line 579
```
ASTRAL is also in the broader stock pools. IIOS CAN observe ASTRAL. **Process-1: SOLVABLE.**

### Process-2 Assessment (Can IIOS generate an opportunity?)
The strategy routing is favourable. `Breakout_Volume` and `Momentum_Retest` are BOTH active in RANGE_MARKET regime. Setup 1 (Breakout with Volume) in `equity_scanner_ai.py` requires:
- `ltp > resistance` (ASTRAL gapped above resistance: Aug-13 open 1499 vs resistance ~1465)
- `vol_ratio >= 2.0` (ASTRAL had 2.75x — passes)
- `RSI < 75` (after +2.74% on Aug-12, RSI was ~58-65 range — likely passes)

**If ASTRAL had been in the Aug-12 prepared candidates, Setup 1 would have fired a BUY signal, Breakout_Volume would have been selected, and the signal would have passed BacktestingAI (no backtest data → allowed through per `result is None` → True).**

### Exact Loss Point
**The Aug-12 EOD market_scanner did not include ASTRAL in the top-57 prepared candidates.**

Cause: On Aug-11, ASTRAL at 1424.9 was not in an active setup condition:
- RSI was likely neutral (50-60 range) — not oversold (no bounce bounce) and not overbought (no short candidate)
- Not at resistance (still ~2.8% below the zone ASTRAL broke on Aug-13)
- Volume was ordinary (the 2.75x spike occurred on Aug-13, not Aug-11/12)

The market_scanner score for ASTRAL on Aug-11 was insufficient to rank in the top-57. The Aug-12 scan (which would have seen the +2.74% close) should have boosted its score. Without the Aug-12 candidates file we cannot confirm, but the ZERO attrition records for ASTRAL confirm it was not in the pipeline on Aug-13.

### Summary
| Stage | Status | Evidence |
|---|---|---|
| IIOS Universe | PRESENT | market_scanner.py line 579 |
| Aug-11 Prepared Candidates | ABSENT | 0 attrition records on Aug-13 |
| Scanner Setup (if present) | WOULD_FIRE (Setup 1) | vol_ratio 2.75x, gap 2.36% |
| Strategy Route (if signal) | WOULD_PASS (Breakout_Volume active) | MetaStrategyController RANGE_MARKET map |
| Root Loss Point | F-1: Candidate selection | Score not high enough on Aug-11 scan |

---

## 3. KAYNES — OVERBOUGHT FADE SHORT

### Stock Profile (2026-08-13)
- Sector: ELECTRONICS (NIFTY200)  
- Aug-11 close: 3717.70 | Aug-12 close: 3828.05 (+2.97%) | Aug-13 decline  
- Signal type: SHORT on overbought momentum fade  
- rel_vol: unknown from BML raw data

### Process-1 Assessment
KAYNES IS in `market_scanner.py` universe:
```python
{"symbol": "KAYNES", "yahoo_ticker": "KAYNES.NS", "sector": "ELECTRONICS", "index": "NIFTY200"}
# market_scanner.py line 581
```
**Process-1: SOLVABLE.**

### Process-2 Assessment
This is where the system fundamentally fails for short candidates.

**Loss Point A — Overbought score penalty (market_scanner.py):**

The market_scanner's RSI score formula:
```python
# market_scanner.py ~line 890
rsi_score = max(0.0, 1.0 - (rsi - 65.0) / 35.0)
```
A stock with RSI=70 gets `rsi_score = 1.0 - (5/35) = 0.857`. A stock with RSI=40 gets `rsi_score = 1.0`. Overbought stocks are **penalised relative to neutral/oversold**. After KAYNES +2.97% on Aug-12, its RSI would be elevated (likely 65-72), giving it a lower rsi_score than neutral stocks — making it **less likely** to crack the top-57.

The `overbought_short_watch` bucket IS tagged in market_scanner (line ~934: `if rsi >= OVERBOUGHT_RSI_MIN: buckets.append("overbought_short_watch")`), but this bucket is **observational only** — it does NOT boost score, does NOT create a separate short candidate queue, and does NOT route to any SHORT opportunity path.

**Loss Point B — Strategy routing gap:**

Even if KAYNES cleared the candidate selection, Setup 4 (High RSI Short) requires `rsi >= 67 AND ltp >= resistance * 0.99`. If Setup 4 fires, it sets:
```python
strategy_name = "high_rsi_short"
```

The `StrategyGeneratorAI._assign()` check:
```python
if signal.strategy_name in STRATEGY_PARAMS:  # False — "high_rsi_short" not in STRATEGY_PARAMS
```
Falls through to `_pick_strategy()`. For RANGE_MARKET + SHORT direction:
```python
# strategy_generator_ai.py _pick_strategy() RANGE_MARKET block
# No branch for direction == SHORT
# Falls to: return evolved or _choose(["Mean_Reversion"])
```
`Mean_Reversion` is the SHORT-direction fallback. If Mean_Reversion is disabled (governance deadlock: G-001 on 2026-08-13), the signal is dropped with `STRATEGY_DISABLED` rejection.

**Loss Point C — MetaStrategyController RANGE_MARKET map:**

Current `_REGIME_MAP[RANGE_MARKET]`:
```python
["Mean_Reversion", "Iron_Condor_Range", "Futures_Basis_Arb",
 "ETF_NAV_Arb", "Breakout_Volume", "Momentum_Retest", "Trend_Pullback"]
```
`"High_RSI_Short"` is **absent**. Even if the strategy were in STRATEGY_PARAMS, it would not be in the active set for RANGE_MARKET.

### Summary
| Stage | Status | Evidence |
|---|---|---|
| IIOS Universe | PRESENT | market_scanner.py line 581 |
| Aug-11 Candidates | ABSENT | Score penalised by elevated RSI |
| Scanner Setup (if in candidates) | CONDITIONAL | Setup 4 needs RSI≥67 + near resistance |
| Strategy Route (if signal) | BROKEN | high_rsi_short ∉ STRATEGY_PARAMS → reassigned to Mean_Reversion → dropped if disabled |
| Root Loss Points | F-1 (score penalty) + F-2 (routing gap) | overbought_score formula; no SHORT strategy in RANGE_MARKET |

---

## 4. HINDALCO — OVERBOUGHT FADE SHORT

### Stock Profile (2026-08-13)
- Sector: METALS  
- Aug-11 close: 1049.10 | Aug-12 close: 1078.50 (+2.80%) | Aug-13 intraday -2.06%  
- In BASE_WATCHLIST of equity_scanner_ai.py with: `base_ltp: 967.45, resistance: 1008.94` (static, from ~July 10)  
- In learning registry: PGA-EB51FF6E — "moved +4.2% with zero DNA coverage" (2026-08-07), status=PENDING, executed=false

### Process-1 Assessment
HINDALCO is directly in the scanner's `_BASE_WATCHLIST`:
```python
{"symbol": "HINDALCO", "base_ltp": 967.45, "resistance": 1008.94, ...}
# equity_scanner_ai.py ~line 116
```
Additionally, the learning registry flagged HINDALCO on 2026-08-07 — the system KNEW it had zero DNA coverage for a stock that was already moving. **Process-1: PRESENT.**

### Process-2 Assessment
**Loss Point A — Stale resistance levels:**

The BASE_WATCHLIST stores static values: `base_ltp=967.45, resistance=1008.94`. These values appear to be from approximately July 10. By Aug-13, HINDALCO was trading at 1072-1078, meaning:
- `ltp (1072) >> resistance (1009)` → HINDALCO appears to be in Setup 1 (Breakout) territory, not Setup 4 (High RSI Short)
- Setup 1 requires `vol_ratio >= 2.0` — but HINDALCO's Aug-12 intraday relative volume was unknown
- If HINDALCO was assessed as a Breakout setup (BUY), it would route to Breakout_Volume and potentially fire

However: HINDALCO's Aug-13 move was -2.06% (DOWN). A declining stock after a breakout above resistance is a classic **bull trap / fade** setup. The scanner looks for this in Setup 4. But with stale resistance at 1009 and live price at 1072, the scanner DOES see `ltp >= resistance * 0.99` (Setup 4 condition), AND if RSI is ≥67 after the Aug-12 +2.80% day, Setup 4 WOULD fire — generating a SHORT signal.

**Loss Point B — Same routing failure as KAYNES (F-2):**

The `high_rsi_short` signal would follow the same broken path: NOT in STRATEGY_PARAMS → reassigned to Mean_Reversion → dropped if disabled.

**Loss Point C — PGA learning action never executed:**

The learning registry (PGA-EB51FF6E, created 2026-08-07) documents:
```json
{
  "action_type": "create_dna_candidate",
  "symbol": "HINDALCO",
  "description": "moved +4.2% with zero DNA coverage",
  "status": "PENDING",
  "executed": false
}
```
The system identified that HINDALCO moves without DNA coverage as early as Aug-7 — 6 days before this audit. The corrective action (`create_dna_candidate` targeting IDR) was never executed. If DNA coverage had been built, the IDR/PIG pathway could have contributed additional signal confidence.

### Summary
| Stage | Status | Evidence |
|---|---|---|
| IIOS Universe | PRESENT | BASE_WATCHLIST + learning registry |
| Scanner Setup (Setup 4) | CONDITIONAL | Would fire if RSI≥67 after +2.80% Aug-12 move |
| Strategy Route (if signal) | BROKEN | Same F-2 routing gap as KAYNES |
| DNA Coverage | ZERO | PGA action PENDING/unexecuted for 6 days |
| Root Loss Points | F-2 (routing) + F-3 (dead-end DNA action) | |

---

## 5. PCJEWELLER — DECLINING MOMENTUM SHORT

### Stock Profile (2026-08-13)
- Sector: RETAIL (NIFTY500)  
- Aug-12 close: 9.80 | Aug-13 close: 9.64 (-1.63%) | 2-day decline pattern  
- rel_vol: unknown from BML raw data

### Process-1 Assessment
PCJEWELLER IS in `market_scanner.py` universe:
```python
{"symbol": "PCJEWELLER", "yahoo_ticker": "PCJEWELLER.NS", "sector": "RETAIL", "index": "NIFTY500"}
# market_scanner.py line 611
```
**Process-1: SOLVABLE.**

### Process-2 Assessment
PCJEWELLER presents a different failure mode from KAYNES/HINDALCO. This stock was in **2-day sequential decline** (not overbought — it was weakening). This means:
- RSI was FALLING, likely below 65 → does NOT trigger `overbought_short_watch` bucket
- Setup 4 (High RSI Short) requires RSI ≥ 67 → does NOT apply
- The stock is NOT overbought — it is in a downtrend continuation

**The scanner has NO setup for declining-momentum shorts (stocks in multi-day downtrend with elevated relative volume).** This is a genuine capability gap, not a wiring issue.

Additionally, PCJEWELLER is a small-cap NIFTY500 stock at ₹9.64/share. The scanner likely has liquidity/ADV filters that would further reduce the chance of selection.

**Loss Point: F-1 (not in prepared candidates) + genuine scanner capability gap.**

### Summary
| Stage | Status | Evidence |
|---|---|---|
| IIOS Universe | PRESENT | market_scanner.py line 611 |
| Applicable Scanner Setup | NONE | Setup 4 requires high RSI; PCJEWELLER was declining |
| Root Loss Points | F-1 + Genuine Gap | No declining-momentum SHORT scanner setup |

---

## 6. EASEMYTRIP — DECLINING MOMENTUM SHORT

### Stock Profile (2026-08-13)
- Sector: CONSUMER (NIFTY500)  
- Aug-12 close: 6.47 | Aug-13 close: 6.27 (-3.09%) | 2-day decline  
- rel_vol: 1.74x — elevated volume on a declining day

### Process-1 Assessment
EASEMYTRIP IS in `market_scanner.py` universe:
```python
{"symbol": "EASEMYTRIP", "yahoo_ticker": "EASEMYTRIP.NS", "sector": "CONSUMER", "index": "NIFTY500"}
# market_scanner.py line 616
```
**Process-1: SOLVABLE.**

### Process-2 Assessment
Identical failure class to PCJEWELLER. EASEMYTRIP was in a 2-day decline:
- Aug-11 → Aug-12: -1.39% (6.56 → 6.47)
- Aug-12 → Aug-13: -3.09% (6.47 → 6.27)

RSI on Aug-13 was likely in the 35-50 range (declining). This does NOT trigger Setup 4 (RSI ≥ 67). The relevant signal would be: "stock declining for 2+ days with 1.74x volume on the decline day = institutional distribution / continued selling."

The system has no scanner setup for this pattern. The closest available mechanism — `ph2_short_dna.evaluate_short_dna()` — contains the `volume_spike SHORT conf=1.0` DNA pattern that would match this (elevated volume on a down day), but:
1. It is only called at EOD during PRR-001 Phase 2
2. It generates a `confidence_boost` for existing signals — it cannot CREATE a new TradeSignal
3. There was no TradeSignal for EASEMYTRIP to boost

**Loss Point: F-1 (not in prepared candidates) + F-3 (dead-end capability) + genuine gap (no declining-momentum scanner).**

### Summary
| Stage | Status | Evidence |
|---|---|---|
| IIOS Universe | PRESENT | market_scanner.py line 616 |
| Applicable Scanner Setup | NONE | Declining stock with elevated volume — no scanner setup |
| ph2_short_dna match | WOULD_MATCH in theory | volume_spike SHORT conf=1.0 in institutional_dna.db |
| ph2_short_dna wiring | DEAD-END | Only called at EOD PRR; cannot create new signals |
| Root Loss Points | F-1 + F-3 + Genuine Gap | |

---

## 7. INFY — IT SECTOR SHORT

### Stock Profile (2026-08-13)
- Sector: IT  
- Aug-12 close: ~1176 (after -1.23%) | Aug-13: -1.47% intraday  
- rel_vol: 0.26x — well below average volume  
- In equity_scanner BASE_WATCHLIST: `base_ltp: 1068.00, resistance: 1149.73`  
- In learning registry: PGA-152D8969 (2026-08-07) — "moved +1.3% with zero DNA coverage", PENDING

### Process-1 Assessment
INFY is in the BASE_WATCHLIST AND has a learning registry action. The system has been aware of INFY's zero DNA coverage since Aug-7. **Process-1: PRESENT.**

### Process-2 Assessment
**Loss Point A — Low volume eliminates all setups:**

INFY's rel_vol was 0.26x — extremely low. Every scanner setup has a minimum volume requirement:
- Setup 1 (Breakout): `vol_ratio >= 2.0` → 0.26x fails hard
- Setup 2 (Momentum Retest): `vol_ratio >= 1.2` → 0.26x fails
- Setup 3 (Trend Pullback): volume-based → 0.26x fails
- Setup 4 (High RSI Short): also has volume confirmation — 0.26x likely fails

Low-volume declining days are quiet distribution, not actionable via volume-based setups.

**Loss Point B — Static resistance stale (same as HINDALCO):**

BASE_WATCHLIST: `base_ltp=1068, resistance=1149.73`. Actual INFY price on Aug-13 was ~1159-1176. The live price is NEAR resistance (1149). After a -1.23% day on Aug-12, if RSI was still elevated (62-67), Setup 4 conditions might be borderline. But with rel_vol=0.26x, the signal would still fail.

**Loss Point C — PGA learning action never executed (same as HINDALCO):**

PGA-152D8969 flagged INFY on Aug-7 for zero DNA coverage. Status: PENDING, executed=false for 6 days.

**Loss Point D — No IT sector short scanner:**

Unlike HINDALCO (metals) where the international context (Hang Seng -1.33%, metals weakness) was a strong signal, INFY's decline was IT-sector-specific. There is no sector-specific short scanner that uses global IT index context (NASDAQ weak → IT sector short candidates).

### Summary
| Stage | Status | Evidence |
|---|---|---|
| IIOS Universe | PRESENT | BASE_WATCHLIST + learning registry |
| Scanner Setup (all) | FAIL | rel_vol=0.26x fails minimum volume for all 4 setups |
| DNA Coverage | ZERO | PGA action PENDING/unexecuted 6 days |
| Root Loss Points | F-2 (routing would fail) + F-3 (dead-end DNA) + genuine low-volume gap | |

---

## 8. EXISTING DNA / KNOWLEDGE AVAILABILITY

### institutional_dna.db State
- Location: `data/mls/institutional_dna.db` (176KB, last modified 2026-08-05)
- Total DNA records: 124
- Schema version: 1.0 (created 2026-08-05, R-013)
- Audit log: last update 2026-08-05 11:41:41 UTC (8 days before this audit)

### DNA Breakdown by Direction

| Direction | Top Features | Confidence | Evidence Count |
|---|---|---|---|
| BUY | pcr, sector_flow_count | 1.0 | 25 |
| BUY | macd_signal_norm | 1.0 | 21 |
| SHORT | volume_spike | 1.0 | 69 |
| SHORT | volume_spike | 1.0 | 66 |
| BUY | global_bias | 0.917 | 17 |

The `volume_spike SHORT conf=1.0` DNA pattern is highly relevant to EASEMYTRIP (1.74x rel_vol on down day) and PCJEWELLER. This pattern EXISTS in the database. It is NOT being consumed during live trading.

### DNA Staleness
- institutional_dna.db was last updated 2026-08-05 — 8 calendar days (6 trading days) before this audit
- The DRE (DNAReinforcementEngine) last ran on 2026-08-05
- No evidence of re-run after the Aug-11 learning spike (Hang Seng events, metals sector events)
- DNA patterns are not stale at the FEATURE level (volume_spike conf=1.0 is a structural pattern)
- But SECTOR-SPECIFIC context from Aug-11 global events is not reflected in any DNA update

### Symbol-Level DNA Coverage
- HINDALCO: dna_count=0 (confirmed by learning registry PGA-EB51FF6E baseline_metrics)
- INFY: dna_count=0 (confirmed by learning registry PGA-152D8969 baseline_metrics)
- ASTRAL, KAYNES, PCJEWELLER, EASEMYTRIP: No learning registry entries → zero DNA coverage assumed

The institutional_dna.db stores FEATURE-level DNA (volume_spike, sector_flow_count, etc.) not SYMBOL-level DNA. Symbol-level DNA would come from the IDR (Institutional DNA Registry) subsystem via the `create_dna_candidate` action — which has been PENDING but unexecuted for 6 days.

---

## 9. MLS PIPELINE HEALTH

### What is Running

| Component | Status | Evidence |
|---|---|---|
| AMLS (AutonomousMarketLearningScheduler) | RUNNING (EOD) | `AMLS_ENABLED=True` in config.py line 360 |
| DRE (DNAReinforcementEngine) | RUNNING (EOD) | institutional_dna.db updated 2026-08-05, DRE audit log confirmed |
| MLC (MarketLearningCoordinator) | RUNNING (EOD) | data/mls/mlc/ directory exists |
| PRR (ProductionReadinessReporter) | RUNNING (EOD ~15:35) | prr_runner confirmed in orchestrator |

### What is NOT Running

| Component | Status | Evidence |
|---|---|---|
| MarketObserver | NOT SCHEDULED | Not in master_orchestrator run_full_cycle |
| PopulationClassifier | NOT SCHEDULED | Not in orchestrator; data/mls/classifications/ ABSENT |
| DNADiscovery | NOT SCHEDULED | Not in orchestrator; data/mls/dna/ ABSENT |
| DNAConsensus | NOT SCHEDULED | data/mls/consensus/ EXISTS but EMPTY |
| PIGTradingAdapter (live contribution) | INACTIVE | ConsensusLibrary (library.json) MISSING → PIG.is_available()=False |

### ConsensusLibrary Gap
The `data/mls/consensus/` directory was created (it exists) but `library.json` was never written. The PIGTradingAdapter reads this file to enrich signals with consensus scores. Without it:
- PIG initialises but returns empty results
- All signals pass through PIG with zero enrichment
- PIG's contribution to confidence scoring is zero

### Why AMLS/DRE Running BUT MarketObserver NOT Running
These are two DIFFERENT pipelines:
- **AMLS/DRE pathway**: `MLC → AMLS → DRE → institutional_dna.db (feature-level patterns)`
- **MarketObserver pathway**: `MarketObserver → PopulationClassifier → DNADiscovery → DNAConsensus → ConsensusLibrary → PIGTradingAdapter`

The AMLS/DRE pipeline is the reinforcement/statistical learning loop — it updates DNA patterns based on historical trade evidence. It IS running.

The MarketObserver pipeline is the real-time market intelligence loop — it observes daily market snapshots, classifies populations, discovers new DNA candidates, and publishes consensus to the library. It IS NOT running. This is why `library.json` is never written and PIG has nothing to consume.

### Impact on 2026-08-13 Trading
- PIG contributed ZERO signal enrichment
- No MarketObserver snapshots captured institutional flow patterns for Aug-11/12 events
- The `volume_spike SHORT conf=1.0` DNA in institutional_dna.db correctly describes what happened on Aug-13 (EASEMYTRIP/PCJEWELLER had elevated volume on down days) but this pattern was never surfaced to the live pipeline

---

## 10. PIG CONSUMPTION PATH

### PIG Architecture Review

The PIGTradingAdapter (Population Intelligence Gateway) is intended to:
1. Read consensus patterns from `data/mls/consensus/library.json`
2. Match live signal features against population consensus
3. Add confidence boost to matching signals
4. Add advisory caution to anti-consensus signals

### Current State

```
data/mls/consensus/
└── (empty — library.json does not exist)
```

PIG.is_available() returns False. All calls to PIG from the live pipeline return null enrichment.

### Root Cause

The ConsensusLibrary is written by `DNAConsensus.publish()` — the final stage of the MarketObserver pipeline. Since MarketObserver is NOT scheduled, DNAConsensus never runs, and `library.json` is never written.

The last PIG contribution to live trading: **never** (library.json has never existed in production).

### Impact
For 2026-08-13, even if the 6 C-stocks had generated signals:
- PIG would NOT have added the `volume_spike SHORT conf=1.0` DNA match for EASEMYTRIP/PCJEWELLER
- PIG would NOT have added sector-correlation warnings for HINDALCO/INFY
- The confidence scores would have been purely scanner-derived (no population intelligence layer)

---

## 11. PROCESS-1 ASSESSMENT (Universe Coverage)

**Process-1 Question:** Can IIOS know about these stocks before they move?

| Stock | Answer | Basis |
|---|---|---|
| ASTRAL | YES | market_scanner.py universe (confirmed) |
| KAYNES | YES | market_scanner.py universe (confirmed) |
| HINDALCO | YES | equity_scanner BASE_WATCHLIST + learning registry |
| PCJEWELLER | YES | market_scanner.py universe (confirmed) |
| EASEMYTRIP | YES | market_scanner.py universe (confirmed) |
| INFY | YES | equity_scanner BASE_WATCHLIST + learning registry |

**Process-1 Verdict: 6/6 = 100% universe coverage. The system CAN know about all 6 stocks.**

This confirms the Predictive Universe Test conclusion: **the universe process works**. The failure is entirely in Process-2 (opportunity generation).

---

## 12. PROCESS-2 ASSESSMENT (Opportunity Generation)

**Process-2 Question:** Given the universe knowledge, can IIOS generate an opportunity?

| Stock | Answer | Primary Barrier |
|---|---|---|
| ASTRAL | YES IF prepared candidate | Candidate selection failure (score not high enough on Aug-12 scan) |
| KAYNES | NO (with current code) | overbought_score penalty prevents candidate selection; high_rsi_short not routed |
| HINDALCO | NO (with current code) | high_rsi_short not in STRATEGY_PARAMS; SHORT direction has no RANGE_MARKET strategy path |
| PCJEWELLER | NO (no capability) | No scanner setup for declining momentum; stock was NOT overbought |
| EASEMYTRIP | NO (no capability) | No scanner setup for declining momentum; volume_spike SHORT DNA not wired to live pipeline |
| INFY | NO (rel_vol=0.26x) | Low volume fails all scanner setups; same routing gaps as HINDALCO |

**Process-2 Verdict: 0/6 = 0% opportunity generation. System needs three distinct fixes.**

---

## 13. EXACT LOSS POINTS

### LP-001: overbought_score_penalty (market_scanner.py)
**Location:** `opportunity_engine/market_scanner.py` ~line 890  
**Code:**
```python
rsi_score = max(0.0, 1.0 - (rsi - 65.0) / 35.0)
```
**Impact:** Every stock with RSI > 65 gets a LOWER overall score. Stocks approaching resistance after a strong prior day (KAYNES +2.97%, HINDALCO +2.80%) get penalised. They are less likely to crack top-57 candidates. The `overbought_short_watch` bucket tag at line ~934 is computed but does NOT create a separate short scoring track.

### LP-002: high_rsi_short not in STRATEGY_PARAMS (strategy_generator_ai.py)
**Location:** `strategy_lab/strategy_generator_ai.py` line 36 (STRATEGY_PARAMS dict)  
**Impact:** Any signal arriving with `strategy_name = "high_rsi_short"` (from Scanner Setup 4) falls through to `_pick_strategy()`. The SHORT direction branch in RANGE_MARKET defaults to "Mean_Reversion". If Mean_Reversion is disabled (governance deadlock), the signal is dropped with `STRATEGY_DISABLED`.

### LP-003: no SHORT direction path in _pick_strategy RANGE_MARKET (strategy_generator_ai.py)
**Location:** `strategy_lab/strategy_generator_ai.py` `_pick_strategy()` function, RANGE_MARKET block  
**Code (current):**
```python
elif regime == RegimeLabel.RANGE_MARKET:
    if signal.signal_type == SignalType.EQUITY:
        if (signal.direction == SignalDirection.BUY and signal.strength.value == "strong"):
            return evolved or _choose(["Breakout_Volume", "Mean_Reversion"])
        elif (signal.direction == SignalDirection.BUY and signal.confidence >= 7.0):
            return evolved or _choose(["Momentum_Retest", "Trend_Pullback", "Mean_Reversion"])
        else:
            return evolved or _choose(["Mean_Reversion"])  # ← SHORT signals fall here
```
**Impact:** SHORT direction signals in RANGE_MARKET silently get "Mean_Reversion" as fallback. No dedicated strategy for SHORT equity trades in range markets.

### LP-004: ph2_short_dna wired to EOD only (orchestrator/production_readiness)
**Location:** `production_readiness/ph2_short_dna.py` + `orchestrator/master_orchestrator.py` ~line 5665  
**Impact:** `evaluate_short_dna()` with 55 loser DNA patterns is ONLY called from PRR-001 Phase 2 (EOD reporting). It generates a `confidence_boost` scalar — but there is no TradeSignal in the live pipeline to apply this boost to. The short DNA capability is entirely isolated from the live trading cycle.

### LP-005: ConsensusLibrary never written (MLS pipeline gap)
**Location:** `data/mls/consensus/library.json` — file does not exist  
**Impact:** PIGTradingAdapter returns zero enrichment. All signals miss the population intelligence layer. The `volume_spike SHORT conf=1.0` pattern (69 evidence events) is never surfaced.

### LP-006: PGA learning actions never executed (learning registry)
**Location:** `data/learning_registry_20260811.json`, records PGA-EB51FF6E (HINDALCO) and PGA-152D8969 (INFY)  
**Impact:** Both records have `executed=false`, `status=PENDING`. The system identified these stocks as needing DNA coverage on 2026-08-07. Six days later, the action is still unexecuted. If executed, IDR would have built symbol-level DNA candidates that PIG could use to enrich signals.

### LP-007: No declining-momentum SHORT scanner (genuine capability gap)
**Scope:** equity_scanner_ai.py  
**Impact:** Stocks in 2+ day sequential decline with elevated volume (EASEMYTRIP 1.74x, PCJEWELLER, INFY pattern) have no applicable scanner setup. Setup 4 (High RSI Short) targets overbought REVERSAL, not declining CONTINUATION. These are entirely different signal types.

---

## 14. RECURRING EVIDENCE

The following failure modes appeared in multiple stocks, indicating systemic issues rather than one-off misses:

| Pattern | Stocks | Count |
|---|---|---|
| F-2: No SHORT equity strategy in RANGE_MARKET | KAYNES, HINDALCO, PCJEWELLER, EASEMYTRIP, INFY | 5/6 |
| F-1: Not in prepared candidates (score penalty or near-miss) | ASTRAL, KAYNES, PCJEWELLER, EASEMYTRIP | 4/6 |
| F-3: Existing SHORT capability dead-ended to EOD only | ALL 6 | 6/6 |
| PGA learning action PENDING/unexecuted | HINDALCO, INFY | 2/6 |
| Zero symbol-level DNA coverage | ALL 6 | 6/6 |
| PIG contribution = zero (ConsensusLibrary missing) | ALL 6 | 6/6 |

The most impactful recurring failure is **F-2: no SHORT strategy routing in RANGE_MARKET**. On a range market day (NIFTY oscillating, VIX=11.7), SHORT setups on overbought individual stocks are the natural trading opportunity. The system has no mechanism to capture these.

---

## 15. ARCHITECTURE GAPS

### GAP-001: Asymmetric scorer in market_scanner (CRITICAL)
The market_scanner has asymmetric scoring: oversold stocks get bonus score (bounce candidates), overbought stocks get penalty score (nothing). There is no "overbought_short_candidates" queue with positive scoring for RSI > 65 in the context of multi-day momentum.

**Effect:** Short setups are systematically under-represented in prepared candidates.

### GAP-002: Missing HIGH_RSI_SHORT strategy definition (CRITICAL)
`STRATEGY_PARAMS` does not contain `"high_rsi_short"`. The equity_scanner_ai generates signals with this strategy name (Setup 4 exists and works), but the strategy layer has no entry for it. This is an unfinished integration — Setup 4 was built but the corresponding STRATEGY_PARAMS entry was never added.

### GAP-003: No SHORT direction path in _pick_strategy RANGE_MARKET (CRITICAL)
`_pick_strategy()` has explicit BUY paths (strong signal → Breakout_Volume, moderate confidence → Momentum_Retest, default → Mean_Reversion). There is no explicit SHORT path. SHORT signals fall to the Mean_Reversion default — a strategy designed for LONG oversold bounce, not SHORT overbought fade. This is a semantic mismatch even before the disabled-strategy problem.

### GAP-004: ph2_short_dna isolated from live pipeline (HIGH)
The `evaluate_short_dna()` function exists, is sophisticated, and uses validated institutional loser DNA. But it was built as an EOD AUDIT tool (PRR-001 Phase 2), not as a live signal enrichment tool. The architectural bridge between short DNA evaluation and live opportunity creation does not exist.

### GAP-005: MarketObserver chain never activated (HIGH)
The PopulationClassifier → DNADiscovery → DNAConsensus → ConsensusLibrary → PIG chain was designed to provide real-time market intelligence to the live pipeline. None of these components are scheduled. PIG gets zero input. The infrastructure exists but is dormant.

### GAP-006: No declining-momentum scanner (MEDIUM)
The scanner has 4 setups: Breakout (BUY), Momentum_Retest (BUY near resistance), Trend_Pullback (BUY on pullback), High_RSI_Short (SHORT overbought reversal). There is no "Setup 5: Declining Momentum Short" for stocks in multi-day downtrend with volume expansion. This is a genuine gap.

### GAP-007: PGA learning actions not wired to execution (MEDIUM)
The learning registry correctly identified HINDALCO and INFY on Aug-7 as needing DNA candidates. But `executed=false` after 6 days means the PGA system generates observations but has no automated execution path. Actions require manual intervention or a scheduled execution agent.

### GAP-008: Static resistance levels not refreshed (LOW-MEDIUM)
BASE_WATCHLIST in equity_scanner_ai.py has hardcoded `resistance` values from ~July 10. By Aug-13, stocks like HINDALCO (+11% since then) and INFY (+10% since then) have live prices well above the static resistance. While the market_scanner's nightly scan updates prepared candidates with fresh levels, the BASE_WATCHLIST fallback uses stale data.

---

## 16. EXISTING CAPABILITY CURRENTLY UNUSED

These components EXIST and WORK but are NOT wired to the live trading path:

### UC-001: Scanner Setup 4 (High RSI Short) — PARTIALLY WIRED
**Location:** `opportunity_engine/equity_scanner_ai.py` lines 2058-2083  
**Capability:** Generates SHORT signals for stocks at resistance with RSI ≥ 67  
**What exists:** Signal generation code (complete, tested)  
**What's missing:** STRATEGY_PARAMS entry for "high_rsi_short"; SHORT branch in `_pick_strategy()` RANGE_MARKET block; "High_RSI_Short" in MetaStrategyController RANGE_MARKET map  
**Fix complexity:** LOW — 3 targeted additions, no new components

### UC-002: ph2_short_dna.evaluate_short_dna() — ISOLATED
**Location:** `production_readiness/ph2_short_dna.py`  
**Capability:** Evaluates stocks against 55 loser INSTITUTIONAL DNA patterns, produces confidence boost  
**What exists:** Full implementation, validated DNA, called from PRR-001  
**What's missing:** Integration into live cycle (e.g., call from _run_opportunity_engine() to boost SHORT signal confidence); bridge to create actual TradeSignal (not just boost scalar)  
**Fix complexity:** MEDIUM — requires architectural decision on where in cycle to inject

### UC-003: overbought_short_watch bucket — COMPUTED BUT NOT USED
**Location:** `opportunity_engine/market_scanner.py` ~line 934  
**Capability:** Labels overbought stocks (RSI ≥ 65) with "overbought_short_watch" tag  
**What exists:** Bucket tagging code  
**What's missing:** A separate short-candidate scoring track that BOOSTS (rather than penalises) high-RSI stocks when the market regime is range; routing of overbought_short_watch candidates to Setup 4 input queue  
**Fix complexity:** LOW-MEDIUM — requires score formula change + candidate routing

### UC-004: institutional_dna.db SHORT DNA — PRESENT BUT NOT CONSUMED
**Location:** `data/mls/institutional_dna.db`  
**Capability:** `volume_spike SHORT conf=1.0` with 69 evidence events — directly applicable to EASEMYTRIP/PCJEWELLER pattern  
**What exists:** Database, AMLS/DRE pipeline that maintains it, DNA records  
**What's missing:** MarketObserver chain to publish to ConsensusLibrary; PIGTradingAdapter receiving valid ConsensusLibrary input  
**Fix complexity:** HIGH — requires MarketObserver pipeline activation

---

## 17. GENUINE CAPABILITY GAPS (NEW BUILD REQUIRED)

### CG-001: Declining-Momentum SHORT Scanner (Setup 5)
**Description:** A scanner setup for stocks in multi-day sequential decline with volume expansion. Pattern: close[n-1] < close[n-2], close[n] < close[n-1], vol_ratio > 1.5, RSI declining from 45-65 range.  
**Stocks this would help:** EASEMYTRIP, PCJEWELLER, INFY (on declining volume days)  
**Priority:** P1

### CG-002: Sector Context → Short Candidate Routing
**Description:** Use GlobalIntelligence sector context (e.g., metals weak because Hang Seng -1.33%) to automatically elevate SHORT priority for stocks in the affected sector. Currently GlobalIntelligence runs and produces sector data but this is not fed back into candidate selection.  
**Stocks this would help:** HINDALCO (metals sector alignment with Hang Seng)  
**Priority:** P2

### CG-003: PGA Action Executor
**Description:** Automated executor for `create_dna_candidate` actions in the learning registry. Currently PGA flags stocks that need DNA coverage but execution is manual/never. An executor would trigger IDR.create_candidate() for PENDING actions.  
**Stocks this would help:** HINDALCO, INFY (had PENDING actions for 6 days)  
**Priority:** P2

### CG-004: Low-Volume Declining Stock Framework
**Description:** INFY on Aug-13 had rel_vol=0.26x — all volume-based scanner setups fail. For large-cap liquid stocks (INFY market cap ~₹5L crore), even 0.26x relative volume is meaningful institutional activity. A separate low-volume framework for large-cap declining stocks would address this gap.  
**Priority:** P3

---

## 18. RECOMMENDED RESEARCH PRIORITIES

### P0 — Fix broken wiring (existing capability, low effort)

**P0-001: Add "high_rsi_short" to STRATEGY_PARAMS**
```
File: strategy_lab/strategy_generator_ai.py
Change: Add to STRATEGY_PARAMS dict — {"min_rr": 2.0, "max_loss_pct": 0.02}
Add: "High_RSI_Short" to MetaStrategyController RANGE_MARKET strategy list
Add: SHORT direction path in _pick_strategy() RANGE_MARKET block
Stocks unblocked: KAYNES, HINDALCO (if overbought conditions met)
Risk: LOW — no new components, completing existing unfinished integration
```

**P0-002: Fix overbought_short_watch scoring in market_scanner**
```
File: opportunity_engine/market_scanner.py
Change: When RSI >= OVERBOUGHT_RSI_MIN AND regime is range_market, apply a 
        BONUS score (not penalty) to flag as short candidate
        Add separate "short_candidates" queue alongside long candidates
Stocks unblocked: KAYNES (candidate selection)
Risk: LOW-MEDIUM — score formula change affects candidate ranking
```

### P1 — Activate dormant capability (existing infrastructure, medium effort)

**P1-001: Activate MarketObserver pipeline to populate ConsensusLibrary**
```
Components: MarketObserver, PopulationClassifier, DNADiscovery, DNAConsensus
Action: Schedule in master_orchestrator at post-market slot (16:15 IST)
Effect: library.json gets written → PIG becomes active → SHORT DNA patterns surfaced
Stocks unblocked: EASEMYTRIP, PCJEWELLER (volume_spike SHORT conf=1.0)
Risk: MEDIUM — new scheduling, verify each component initialises correctly
```

**P1-002: Wire ph2_short_dna to live opportunity evaluation**
```
File: production_readiness/ph2_short_dna.py → opportunity_engine or orchestrator
Action: Call evaluate_short_dna() during live scan cycle for stocks with declining 
        RSI + elevated volume; use output to ELEVATE confidence OR create advisory signal
Effect: 55 loser DNA patterns feed into intraday opportunity assessment
Risk: MEDIUM — requires architectural decision on signal creation vs enrichment
```

**P1-003: Build Scanner Setup 5 (Declining Momentum Short)**
```
File: opportunity_engine/equity_scanner_ai.py
Setup: close[-1] < close[-2] < close[-3] (3-day decline), vol_ratio >= 1.5, 
       RSI in 35-65 range (not oversold, confirming decline not bounce)
Output: strategy_name="Declining_Momentum_Short", direction=SHORT
Stocks unblocked: EASEMYTRIP, PCJEWELLER, INFY
Risk: MEDIUM-HIGH — new signal type, requires backtesting before activation
```

### P2 — Strengthen learning execution

**P2-001: Execute PENDING PGA learning actions**
```
Registry entries: PGA-EB51FF6E (HINDALCO), PGA-152D8969 (INFY)
Action: Run IDR.create_candidate() for both stocks
Effect: Symbol-level DNA created; future moves will have DNA coverage
Risk: LOW — existing IDR infrastructure, no pipeline change
```

**P2-002: Add PGA execution agent to orchestrator EOD slot**
```
File: orchestrator/master_orchestrator.py (EOD slot)
Action: After learning_registry update, execute PENDING actions with status=PENDING 
        and confidence=EXPERIMENTAL, executing oldest-first
Effect: Learning registry becomes actionable, not just observational
Risk: LOW-MEDIUM — controlled by confidence/category gates
```

**P2-003: Refresh BASE_WATCHLIST resistance levels monthly**
```
File: opportunity_engine/equity_scanner_ai.py (BASE_WATCHLIST)
Action: Script to auto-update base_ltp/resistance from last N-day high analysis
Effect: HINDALCO/INFY get current resistance levels
Risk: LOW — maintenance task, no architectural change
```

### P3 — Research (requires study before implementation)

**P3-001: Sector context → candidate priority**
```
Research: Does GlobalIntelligence sector data correlate with next-day individual 
          stock moves in the same sector? If Hang Seng metals -1.33%, do NSE metals 
          decline the following day with statistical significance?
If confirmed: Feed GlobalIntelligence sector bias into market_scanner candidate weighting
```

**P3-002: Low-volume large-cap framework**
```
Research: Is rel_vol < 0.3 on a large-cap declining day (INFY) still a tradeable 
          signal? What is the signal reliability vs noise ratio?
If confirmed: Add a separate large-cap declining scanner that ignores rel_vol threshold
```

---

## 19. PRODUCTION CHANGE SUMMARY

**ZERO production changes were made during this audit.**

All findings are READ-ONLY observations from code review and data queries. No files were modified. No trades were executed. The `audit_dna_query.py` and `audit_dna_query2.py` temporary scripts should be deleted after review.

---

## 20. APPENDIX: CODE REFERENCES

| Finding | File | Line/Location |
|---|---|---|
| Setup 4 (High RSI Short) | `opportunity_engine/equity_scanner_ai.py` | line 2058 |
| overbought_short_watch bucket | `opportunity_engine/market_scanner.py` | ~line 934 |
| overbought RSI score penalty | `opportunity_engine/market_scanner.py` | ~line 890 |
| STRATEGY_PARAMS (no high_rsi_short) | `strategy_lab/strategy_generator_ai.py` | line 36 |
| _pick_strategy RANGE_MARKET block | `strategy_lab/strategy_generator_ai.py` | _pick_strategy() |
| MetaStrategyController RANGE_MARKET map | `strategy_lab/meta_strategy_controller.py` | _REGIME_MAP |
| BacktestingAI result=None → allow through | `strategy_lab/backtesting_ai.py` | line 298-303 |
| ph2_short_dna in orchestrator (EOD only) | `orchestrator/master_orchestrator.py` | ~line 5665 |
| ASTRAL in market_scanner universe | `opportunity_engine/market_scanner.py` | line 579 |
| KAYNES in market_scanner universe | `opportunity_engine/market_scanner.py` | line 581 |
| PCJEWELLER in market_scanner universe | `opportunity_engine/market_scanner.py` | line 611 |
| EASEMYTRIP in market_scanner universe | `opportunity_engine/market_scanner.py` | line 616 |
| HINDALCO in equity_scanner BASE_WATCHLIST | `opportunity_engine/equity_scanner_ai.py` | ~line 116 |
| INFY in equity_scanner BASE_WATCHLIST | `opportunity_engine/equity_scanner_ai.py` | ~line 101 |
| HINDALCO PGA registry entry | `data/learning_registry_20260811.json` | PGA-EB51FF6E |
| INFY PGA registry entry | `data/learning_registry_20260811.json` | PGA-152D8969 |
| institutional_dna.db state | `data/mls/institutional_dna.db` | 124 records, last updated 2026-08-05 |
| ConsensusLibrary missing | `data/mls/consensus/` | directory empty |
| AMLS_ENABLED = True | `config.py` | line 360 |

---

*KNOWLEDGE_TO_OPPORTUNITY_AUDIT_001 — 2026-08-13 — READ-ONLY — COMPLETE*
