# MOP-001 — Meaningful Opportunity Discovery & Selection Architecture Audit
**Date:** 2026-08-13  
**Mode:** READ-ONLY | OBSERVATION ONLY  
**Prepared by:** Copilot — architecture audit  
**Production changes:** NONE  
**Strategy changes:** NONE  
**Orders placed:** 0  

---

## Executive Summary

The current IIOS architecture partially supports the target objective but has three structural gaps that prevent it from being a "meaningful-move-first" selection system.

| Capability | Status | Evidence |
|---|---|---|
| Universe → candidate discovery | **READY** | 230-symbol universe, nightly scanner, 120-candidate pool |
| Technical candidate scoring | **READY** | Score 0–1 based on proximity, vol, RSI quality |
| Regime-aware selection | **PARTIAL** | Regime IS read by `_identify_setup()`, NOT by scorer |
| Direction (LONG vs SHORT) | **PARTIAL** | LONG only; SHORT architecture exists but disconnected |
| Magnitude estimation | **MISSING** | Score cannot distinguish +0.1% from +5% opportunity |
| Knowledge-integrated selection | **MISSING** | DNA exists in DB but never called by live selection |
| Final 5–6 selection logic | **PARTIAL** | Capital-constrained, but capital eliminates by price not quality |
| Top-20 feedback loop | **PARTIAL** | ILC audits daily, but findings never re-enter scorer |

---

## Phase 1 — Current Pipeline Trace

### 1.1 Complete Pipeline Architecture

```
230-symbol universe (data/nifty500_universe.json)
    │
    ▼ [16:45 IST daily]
market_scanner.py:run_scan()                          DISCOVERY LAYER
    │ _process_symbol() per stock: RSI, ATR, support/resistance, vol_ratio
    │ _compute_base_score() → score in [0.0, 1.0]
    │ _classify_buckets() → ['breakout','trend_pullback','overbought_short_watch',…]
    │ Concentration penalty (streak > 3 days → –5%/day, max –30%)
    │ Sector cap (max 20% per sector)
    │ Score floor (>= 0.55)
    │ Absolute cap (max 120 candidates)
    ▼
data/daily_candidates.json                            CANDIDATE STORE
    │ Schema: {symbol, base_ltp, resistance, support, rsi, vol_ratio,
    │          adv_crore, atr14, atr_pct, buckets, score, sector, index,
    │          conviction_decay, valid_until_utc, lifecycle_state}
    │ No target_price, no expected_move, no DNA score, no magnitude field
    ▼ [each intraday cycle: 09:45, 10:30, etc.]
equity_scanner_ai.py:scan()                           SIGNAL GENERATION
    │ _prepared_watchlist() loads CandidateStore
    │ Conviction decay applied in-memory (vol_collapse: ×0.84, normal: ×0.98)
    │ Sector re-rank by snapshot.sector_leaders
    │ For each candidate → _identify_setup(stock, snapshot)
    │   ├─ RSI, price, vol_ratio, stop_dist checks per strategy type
    │   ├─ Returns TradeSignal{symbol, entry, stop, target, confidence, direction}
    │   └─ NO DNA lookup, NO knowledge lookup
    ▼
List[TradeSignal]                                     SIGNAL POOL
    │ Fields: symbol, entry_price, stop_loss, target_price,
    │         confidence (5.5–9.5), direction, strategy_name, atr
    │ No expected_move, no magnitude_score, no DNA_confidence
    ▼
strategy_lab:MetaStrategyController                   STRATEGY MATCHING
    │ Checks if strategy is enabled, not disabled by SHM
    │ Applies per-strategy confidence threshold
    ▼
risk_control:CapitalRiskEngine.allocate()             CAPITAL ALLOCATION
    │ Deployable = f(regime, VIX, portfolio drawdown)
    │ Quality sort: sorted by confidence + (0.01 × qty)
    │ Budget per strategy from _STRATEGY_SHARE dict
    │ Position size: qty = min(qty_by_risk, qty_by_budget)
    │ qty_by_risk = (budget × MAX_RISK_PCT) / |entry – stop|
    │ MAX_POSITIONS = 8 hard cap
    │ Rejection reasons: ZERO_BUDGET, QTY_ZERO, SL_TOO_TIGHT, EXPOSURE_CAP
    ▼
risk_control:RiskManagerAI                            RISK VALIDATION
    │ RR check (min 2.0×), confidence threshold, correlation, portfolio heat
    ▼
execution_engine:OrderManager                         EXECUTION
    │ Paper trade journal: data/paper_trades.csv
    │ Broker routing (Dhan or simulation)
    ▼
TRADE
```

### 1.2 Source File Reference Map

| Layer | File | Key Function | Line |
|---|---|---|---|
| Universe | `opportunity_engine/market_scanner.py` | `_builtin_universe()` | ~870 |
| Scoring | `opportunity_engine/market_scanner.py` | `_compute_base_score()` | ~847 |
| Bucketing | `opportunity_engine/market_scanner.py` | `_classify_buckets()` | ~917 |
| Candidate store | `opportunity_engine/candidate_store.py` | `CandidateStore.write()` | ~135 |
| Signal generation | `opportunity_engine/equity_scanner_ai.py` | `EquityScannerAI.scan()` | ~1273 |
| Setup identification | `opportunity_engine/equity_scanner_ai.py` | `_identify_setup()` | ~1913 |
| Capital allocation | `risk_control/capital_risk_engine.py` | `CapitalRiskEngine.allocate()` | ~177 |
| Quality sort | `risk_control/capital_risk_engine.py` | `_cre_quality_score()` | ~245 |
| Position sizing | `risk_control/capital_risk_engine.py` | `_size_position()` | ~619 |
| BML feedback | `institutional_learning/ilc_market_audit.py` | ILC daily cycle | — |
| DNA (disconnected) | `production_readiness/ph2_short_dna.py` | `get_short_dna_confidence_boost()` | ~148 |

---

## Phase 2 — Existing "Opportunity" Logic Inventory

### 2.1 Scanner `score` Field

**What it measures:** Breakout/setup proximity + volume activity + RSI quality

**Formula** (`market_scanner.py:_compute_base_score()`):
```python
score = (
    proximity_score * 0.40 +   # how close to resistance/support
    vol_score       * 0.30 +   # volume_ratio (higher = better)
    rsi_score       * 0.20 +   # RSI 35–65 preferred; extremes penalised
    atr_score       * 0.10     # ATR in useful range (0.5–4% of price)
)
```

**Status in live selection:** ✅ Used for initial ranking within scanner; then overwritten by conviction decay in `_prepared_watchlist()`. DOES affect which candidates survive to `_identify_setup()`.

**Does it distinguish +0.1% from +5%?** NO. A breakout candidate that historically produces 0.1% moves scores the same as one that produces 5% moves, if they have similar proximity/vol/RSI.

### 2.2 Signal `confidence` Field

**What it measures:** Composite of `5.5 + vol_ratio * factor + rsi_deviation * factor`

**Formula** (`equity_scanner_ai.py:_identify_setup()`):
```python
# Mean reversion bounce:
confidence = min(6.0 + vol_ratio, 9.5)

# Breakout:
confidence = round(min(5.5 + vol_ratio * 0.4 + (rsi - 50) / 25.0, 9.0), 2)

# Trend pullback:
confidence = round(min(5.8 + vol_ratio * 0.3 + (56 - rsi) / 20.0, 9.0), 2)
```

**Status in live selection:** ✅ Used in `_cre_quality_score()` for signal sorting inside CRE, and as the primary gate in RiskManagerAI. **This is the final selection determinant.**

**Does it distinguish magnitude?** NO. A low-ATR stock with high vol_ratio (suggesting small but reliable move) gets the same confidence boost as a high-ATR stock.

### 2.3 `target_price` / R:R

**What it measures:** Mechanical target = `entry + RR_multiplier × ATR × ATR_STOP_MULT`

**Formula** (`equity_scanner_ai.py:_identify_setup()`):
```python
stop_dist = max(atr * ATR_STOP_MULTIPLIER, ltp * 0.010)
target_price = round(ltp + RR_DEFAULT * stop_dist, 2)  # RR_DEFAULT = 2.5
```

**Status in live selection:** Target distance is computed but NOT used for ranking or selection. It only determines whether RR >= 2.0 minimum passes the RiskManager gate.

**Does it estimate probability of reaching target?** NO. It is a fixed multiplier, not a distribution estimate.

### 2.4 `buckets` Field (breakout, trend_pullback, overbought_short_watch, etc.)

**What it measures:** Setup-type classification from `_classify_buckets()`

**Status in live selection:** ✅ Partially — `conviction_decay` value depends on whether "breakout" is in buckets (0.30 vs 0.15). However, `_identify_setup()` does NOT read the `buckets` field from the prepared candidate — it re-evaluates price/RSI/vol independently.

**Finding:** The scanner computes buckets, but `_identify_setup()` ignores them. There is no direct bucket → setup routing.

### 2.5 `adv_crore` (Average Daily Value in Crore)

**What it measures:** Average daily traded value. Proxy for liquidity AND institutional interest.

**Status in live selection:** Used only as a minimum liquidity gate (≥₹50Cr). NOT used to prefer larger-cap/more-liquid opportunities.

**Does it correlate with magnitude?** YES — empirically, stocks with higher ADV tend to produce more reliable moves when a setup triggers. But this is not used in scoring.

### 2.6 `atr_pct` (ATR as % of price)

**What it measures:** Expected daily volatility range as a percentage.

**Status in live selection:** Used as a gate (< 8%); contributes to scanner score via `atr_score`. NOT used to estimate magnitude.

**Does it estimate expected move?** Partially — ATR × RR_multiplier = `target_distance`. But this is not presented as a magnitude estimate.

### 2.7 DNA / Knowledge (institutional_dna.db)

**What it measures:** Historically validated institutional patterns (volume_spike confidence=1.0 etc.)

**Status:**
- `institutional_dna.db` EXISTS in `data/mls/`
- `production_readiness/ph2_short_dna.py:get_short_dna_confidence_boost()` EXISTS
- `_identify_setup()` does **NOT** call `get_short_dna_confidence_boost()`
- IDR was empty on VPS at time of BML-001 audit (2026-08-11)
- DNA is STORED but NOT CONNECTED to live selection

**Status verdict:** `KNOWLEDGE_EXISTS` but NOT `KNOWLEDGE_IS_CONNECTED`

### 2.8 Regime from MarketIntelligence

**What it measures:** RANGE_MARKET, BULL_TREND, BEAR_MARKET, VOLATILE

**Status in live selection:** ✅ CONNECTED. `snapshot.regime` is passed to `_identify_setup()` and directly gates strategy types:
- RANGE_MARKET → MeanReversion, OverboughtShortWatch
- BULL_TREND → TrendPullback, Breakout
- Each strategy has regime compatibility conditions

### 2.9 MetaLearning RegimeStrategyMap

**What it measures:** Historical win-rate per strategy per regime

**Status in live selection:** Influences which strategies are ENABLED (via SHM and governance), but does NOT directly affect candidate scoring or selection ranking.

### 2.10 EMP (Early Move Prediction) Framework

**What it measures:** Previous-day scanner hit rate for becoming top-5/10/20 movers

**Status:** ✅ Exists in `early_move_audit/`. Computes top-N capture metrics.
**Status in live selection:** NOT connected. EMP is an external audit tool that runs post-market. Its outputs do NOT feed back into scanner scoring.

---

## Phase 3 — Discovery vs Selection: Are They Separated?

### 3.1 Current State

**They are MIXED.** The current pipeline merges discovery and selection into a single step:

| Step | Expected role | Actual role |
|---|---|---|
| `market_scanner.py:run_scan()` | Discovery (which stocks are interesting?) | Also pre-selects by scoring 0–1, setting score floor 0.55, sector cap |
| `equity_scanner_ai.py:_identify_setup()` | Selection (which of the interesting stocks have a live tradeable setup?) | Also determines direction, entry, stop, and confidence |

The candidate `score` is simultaneously:
- A discovery quality indicator (higher score → more interesting)
- A proxy for urgency (setup proximity drives score)
- An implicit strategy selector (breakout proximity score >> range score)

**There is no explicit "opportunity watchlist" layer** between discovery and trade selection. A stock either passes into `_identify_setup()` (possibly producing a signal) or exits the pipeline at the CandidateStore boundary.

### 3.2 The Specific Gap

```
CURRENT:
Universe → scanner_score → if score >= 0.55 → _identify_setup() → if setup found → signal

TARGET:
Universe → discovery_score → opportunity_pool → knowledge_enrichment → selection_score → signal
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                             THIS INTERMEDIATE LAYER DOES NOT EXIST
```

The `overbought_short_watch` bucket in market_scanner.py (~line 935) is the closest architectural ancestor of the missing opportunity pool — it labels stocks but provides no downstream routing. As documented in KNOWLEDGE_TO_OPPORTUNITY_AUDIT_001, the `premarket_refiner.py` has a registered slot for this bucket at 09:00 IST, but no enrichment or routing logic is implemented.

---

## Phase 4 — Magnitude Test

### 4.1 Can Current Scoring Distinguish +0.1% from +5%?

**Short answer: NO.**

| Mechanism | Present? | Affects selection? | Estimates magnitude? |
|---|---|---|---|
| `target_price` (mechanical) | ✅ | ❌ (only for RR gate) | ❌ (fixed multiplier) |
| `atr_pct` (volatility proxy) | ✅ | ❌ (only for gate) | Indirectly (ATR ≈ 1-day move) |
| `adv_crore` (liquidity) | ✅ | ❌ (only for gate) | ❌ |
| `vol_ratio` (volume spike) | ✅ | ✅ (adds to confidence) | Marginally (high vol_ratio → larger expected move, but not quantified) |
| Historical magnitude distribution | ❌ | — | — |
| ATR × RR = expected move | ✅ (computable) | ❌ (not exposed as field) | Partially (ATR IS the best available magnitude proxy) |
| DNA move magnitude history | ❌ | — | — |

### 4.2 The ATR Opportunity

ATR(14) is already computed for every candidate and available on the signal. It IS the best available magnitude proxy. A stock with ATR% = 3.5% has roughly 3.5× larger expected daily move than one with ATR% = 1.0%.

**However**: `_identify_setup()` only uses ATR to set stop distance. It does NOT present `ATR × RR_DEFAULT` as an "opportunity magnitude score". Two signals with identical confidence can have 3.5× different expected move magnitudes.

### 4.3 What Exists That Could Be Used

The following are already computed but NOT used in selection ranking:

1. `atr14` (in candidate store and on signal via `sig.atr`)
2. `atr_pct` (in candidate store)
3. `target_distance = |target_price − entry_price|` — derivable from signal fields
4. `adv_crore` — proxy for "does institutional money care about this stock?"

**RESEARCH CANDIDATE:** `opportunity_magnitude_score = atr_pct × vol_ratio × adv_factor`
This would distinguish a TATASTEEL at atr_pct=3.5% + vol_ratio=2.5× from an ITC at atr_pct=0.8% + vol_ratio=1.1×, without changing any existing signals or governance.

---

## Phase 5 — Capital-Constrained Final Selection

### 5.1 How IIOS Reduces Many → Few

The pipeline has **two selection bottlenecks**:

**Bottleneck 1 — Scanner score floor** (market_scanner.py)
- All 230 stocks → ~80–120 pass score ≥ 0.55 → stored in CandidateStore

**Bottleneck 2 — Strategy matching + capital sizing** (CRE + RiskControl)
- 24–80 candidates enter `_identify_setup()` each cycle
- Typically 1–15 produce signals (from live session data)
- CRE quality-sorts by `confidence`, then:
  - Allocates budget per strategy type
  - Sizes by risk formula: `qty = (budget × MAX_RISK_PCT) / stop_dist`
  - Hard cap: MAX_POSITIONS = 8
- Actual daily trades: 0–3 (given current strategy disable state)

### 5.2 Is There a Dedicated Top-N Selector?

**No explicit top-N selector exists.** The effective selection is emergent:
1. Confidence determines sort order in CRE
2. Capital budget determines whether a high-confidence signal gets QTY > 0
3. MAX_POSITIONS = 8 is the only explicit cap

### 5.3 The Price-vs-Quality Problem

**Finding (source: `capital_risk_engine.py:_size_position()`):**
```python
qty_by_budget = int(budget / sig.entry_price)
qty = min(qty_by_risk, qty_by_budget)
```

On ₹10,000 total capital:
- Strategy budget ≈ ₹2,200 (22% of deployable for MeanReversion)
- INFY at ₹1,068: `qty_by_budget = 2200 / 1068 = 2`
- BANKBARODA at ₹251: `qty_by_budget = 2200 / 251 = 8`

If INFY's stop is ₹25 away: `qty_by_risk = (2200 × 0.02) / 25 = 1` → passes, qty=1
If BANKBARODA's stop is ₹5 away: `qty_by_risk = (2200 × 0.02) / 5 = 8` → passes, qty=8

**Key problem for magnitude capture:** A high-conviction INFY signal with 3× expected move may get smaller qty (1 share) than a weaker BANKBARODA signal with 1.2× expected move (8 shares), purely because of price. The actual capital deployed per trade is similar, but the magnitude of opportunity is different.

### 5.4 LONG and SHORT Candidates

**Short candidates do NOT compete in the same pool.** The current `_identify_setup()` produces SHORT signals only for the disabled `high_rsi_short` path. No other SHORT strategy is active. LONG candidates only compete with other LONG candidates. If SHORT signals were enabled, they would enter the same CRE pool and compete on confidence score.

### 5.5 Capital Allocation Timing

Capital constraint happens **AFTER** opportunity discovery and signal generation. The sequence is:
```
Discovery (scanner score) → Setup (TradeSignal) → Capital (CRE) → Risk (RiskManager) → Trade
```

A high-quality opportunity can be eliminated at the capital stage (QTY_ZERO) even if it was the highest-scoring candidate. Capital constraint does NOT see the full opportunity set before limiting — it only sees signals that passed `_identify_setup()`.

---

## Phase 6 — Top-20 Gainer/Loser Feedback Loop

### 6.1 Existing Feedback Infrastructure

| Component | File | Capability | Connected to live selection? |
|---|---|---|---|
| ILC market audit | `institutional_learning/ilc_market_audit.py` | Daily top-20 vs universe audit | NO — EOD only, reporting only |
| EMP (early move prediction) | `early_move_audit/emp_predictive.py` | Top-5/10/20 capture rate, hit rate lift | NO — external audit tool |
| BML daily report | `data/market_coverage/BML_001*.md` | Manual BML cycle with BML classification | NO — manual report only |
| StrategyPerformanceTracker | `learning_system/strategy_performance_tracker.py` | Win rate per strategy, auto-disable | Partially — disables poor strategies |
| DNA discovery engine | `data/mls/institutional_dna.db` | Patterns from historical movers | NO — not connected to scanner |

### 6.2 Can the Feedback Answer the 10 Questions?

| Question | Answerable now? | What's needed |
|---|---|---|
| 1. Was stock in universe? | ✅ YES — ILC classifies all 40 (20+20) daily | Nothing |
| 2. Was it discovered before the move? | ⚠️ PARTIAL — only if it was in daily_candidates.json | Requires candidate store audit vs BML top-20 |
| 3. Was it in candidate pool? | ✅ YES — data/daily_candidates.json is queryable | Requires cross-referencing with top-20 |
| 4. Was it selected? | ✅ YES — paper_trades.csv + order logs | Queryable |
| 5. Predicted direction? | ✅ YES — on TradeSignal.direction | Queryable from logs |
| 6. Actual direction? | ✅ YES — from daily close prices | Queryable via yfinance |
| 7. Actual magnitude? | ✅ YES — close % change | Queryable |
| 8. Rank/score at selection time? | ⚠️ PARTIAL — score in CandidateStore (not on signal) | Score is stored in candidates.json but NOT on TradeSignal |
| 9. Which selected stocks performed worse? | ⚠️ PARTIAL — requires joining signal log + outcome | No existing join mechanism |
| 10. Which movers were missed? | ✅ YES — BML already computes this | Already exists in BML report |

### 6.3 Feedback Loop Status

The feedback loop CAN be measured but the measurement does NOT re-enter selection logic:
- ILC learns that a stock was a top-20 mover → logs it to `institutional_dna.db` (if ILC cycle generates a DNA pattern)
- DNA pattern sits in DB → not queried during live selection
- EMP measures scanner hit rate → not fed back to scanner scoring

**The loop is open at the return edge: measurement → (void) rather than measurement → scorer update.**

---

## Phase 7 — Correct Future Metrics (Feasibility Assessment)

All 10 metrics are feasible with existing data. None require new production code to MEASURE; they require only a reporting layer.

| Metric | Feasibility | Existing Data Source |
|---|---|---|
| 1. Pre-move Discovery Rate | ✅ Feasible | daily_candidates.json vs top-20 movers |
| 2. Candidate Coverage | ✅ Feasible | CandidateStore read() |
| 3. Top-5/6 Opportunity Capture | ✅ Feasible | paper_trades + close prices |
| 4. Meaningful Move Capture | ✅ Feasible | close % vs `MOVER_THRESHOLD = 2%` (BML) |
| 5. Directional Accuracy | ✅ Feasible | signal direction vs actual close direction |
| 6. Magnitude Capture | ✅ Feasible | actual |return%| of selected vs universe top movers |
| 7. Missed Opportunity Rate | ✅ Feasible | BML top-20 ∩ not-in-candidates |
| 8. Selection Efficiency | ✅ Feasible | |actual return| of selected vs all candidates |
| 9. Capital-adjusted Opportunity Capture | ✅ Feasible | position_value × return% vs universe ranking |
| 10. Long-vs-Short Balance | ⚠️ Partial | LONG only today; SHORT pool needs enabling |

### 7.1 Recommended Primary Metric

> "Mean absolute move of top-6 selected stocks over the next trading session"

This is more meaningful than directional accuracy because:
- It directly captures magnitude value
- It is indifferent to whether the move was up or down (for a system intending to trade both)
- It can be compared against: (a) universe median, (b) top-20 median, (c) random-6 baseline

**Baseline calculation is already possible with existing data without any code changes.**

### 7.2 The Missing "Meaningful Move" Definition

The BML framework already defines a "significant mover" as `|daily_return| >= 2%`. This definition is consistent across ILC, BML, and the KTOV-002 study. It should be used as the primary discovery threshold.

---

## Phase 8 — Daily Ground-Truth Report Feasibility

### 8.1 Can a Daily Observation Report Be Produced?

**Yes, with read-only tooling.** The following data is already available:

| Field | Source | Availability |
|---|---|---|
| A. Universe (230 stocks) | `data/nifty500_universe.json` | ✅ Always available |
| B. Top-20 gainers/losers | yfinance daily download | ✅ Post 15:30 IST |
| C. Pre-move discovery | `data/daily_candidates.json` (timestamped) | ✅ If scanner ran previous day |
| D. Candidate pool | `data/daily_candidates.json` | ✅ |
| E. Selected 5–6 | `data/paper_trades.csv` | ✅ (paper mode) |
| F. Actual move | yfinance close vs prev close | ✅ |
| G. Selected vs non-selected | Join E + F | ✅ Derivable |
| H. Missed movers | B minus D | ✅ Derivable |

### 8.2 Failure Mode Classification (Phase 8 of task spec)

| Failure class | What it means | Can be detected? |
|---|---|---|
| UNIVERSE_FAILURE | Significant mover NOT in 230-symbol universe | ✅ — ILC already classifies this |
| DISCOVERY_FAILURE | In universe, NOT in daily_candidates.json | ✅ — cross-reference |
| SELECTION_FAILURE | In candidates, NOT in final signals | ✅ — strategy/regime rejection logs |
| DIRECTION_FAILURE | In signals, wrong direction predicted | ✅ — signal direction vs actual return sign |
| MAGNITUDE_FAILURE | In signals, correct direction but tiny move | ✅ — |actual_return| < 1% |
| CAPITAL_CONSTRAINT | In signals, QTY_ZERO due to price | ✅ — CRE rejection logs tag QTY_ZERO |

**Finding:** All six failure classes can be classified from existing log data without production changes.

---

## Phase 9 — Knowledge-First Requirement Audit

### 9.1 What Knowledge Exists vs What Is Connected

| Knowledge Type | Exists? | Connected to live selection? | Affects ranking? |
|---|---|---|---|
| DNA patterns (vol_spike, loser_dna) | ✅ `institutional_dna.db` | ❌ NOT connected | ❌ |
| Regime (RANGE/BULL/BEAR/VOLATILE) | ✅ `MarketIntelligence` snapshot | ✅ Connected | ✅ Gates strategy type |
| Sector leaders (intraday rotation) | ✅ `snapshot.sector_leaders` | ✅ Connected | ✅ Sector re-rank |
| Historical win rate per strategy | ✅ `StrategyPerformanceTracker` | ✅ Partially (auto-disable) | ⚠️ Binary (on/off) |
| MetaLearning regime→strategy weights | ✅ `regime_strategy_map.py` | ✅ Partially (strategy priority) | ⚠️ Indirect |
| False breakout tracker | ✅ `data_feeds/false_breakout_tracker` | ✅ Connected | ✅ Removes invalidated candidates |
| ATR distribution history | ❌ Not stored | — | — |
| Historical magnitude per setup | ❌ Not stored | — | — |
| Event calendar (earnings, macro) | ❌ Not integrated | — | — |
| Options PCR / market sentiment | ✅ snapshot fields | ⚠️ Partial — regime calc only | ⚠️ Indirect |

### 9.2 The Knowledge Paradox

The original IIOS design intent is that trades should be based on **compiled knowledge**, not raw signals. But the current live selection path (`_identify_setup()`) is purely technical:
```
RSI condition + price relative to S/R + vol_ratio condition → TradeSignal
```

The compiled knowledge (DNA, historical patterns, win rates) exists elsewhere in the system but is not queried at signal generation time. The regime IS incorporated — that is meaningful. But the richer knowledge layer (DNA, historical magnitude, sector event context) is not.

### 9.3 Status Summary

```
KNOWLEDGE_EXISTS:     DNA, ATR history, win rates, sector context
KNOWLEDGE_IS_CONNECTED: Regime, sector_leaders, false_breakout, win rates (binary)
KNOWLEDGE_AFFECTS_SELECTION: Regime (strategy gate), sector (rank order)

NOT CONNECTED:   DNA confidence boost
NOT CONNECTED:   Historical magnitude distribution per setup type  
NOT CONNECTED:   Opportunity magnitude score (ATR × vol_ratio)
```

---

## Phase 10 — Final Verdict

### 10.1 Architecture Capability Grades

| Capability | Grade | Evidence |
|---|---|---|
| **A. DISCOVERY** | **PARTIAL** | Scanner surfaces stocks with technical setups; no magnitude bias; 100% universe coverage |
| **B. OPPORTUNITY CANDIDATE GENERATION** | **PARTIAL** | 120-candidate pool exists; scored but magnitude-blind |
| **C. MEANINGFUL-MOVE ESTIMATION** | **MISSING** | No expected-move field; ATR available but not used as magnitude selector |
| **D. FINAL 5–6 SELECTION** | **PARTIAL** | Capital-constrained, confidence-ranked; price can displace quality |
| **E. KNOWLEDGE-INTEGRATED SELECTION** | **MISSING** | Regime connected; DNA, historical magnitude not connected |
| **F. TOP-20 GAINER/LOSER FEEDBACK** | **PARTIAL** | ILC measures coverage; feedback does not re-enter scorer |
| **G. CAPITAL-AWARE SELECTION** | **READY** | CRE correctly sizes and caps; QTY_ZERO behaviour is correct |

### 10.2 What Already Works

1. **Universe coverage** — 230 stocks with nightly OHLCV refresh; 100% coverage of NSE liquid universe.
2. **Technical candidate pre-qualification** — Score-based filter removes 70% of universe as low-quality. Setup proximity, volume, RSI quality all contribute.
3. **Regime integration** — `snapshot.regime` genuinely changes which strategies activate. RANGE vs BULL produces different strategy mixes.
4. **Sector re-rank** — Intraday sector leaders move relevant candidates to top of evaluation queue.
5. **Concentration penalty** — Prevents the same stock from dominating every day.
6. **Breakout invalidation** — Removes structurally failed setups before they generate signals.
7. **Capital governance** — MAX_POSITIONS = 8, regime-adjusted deployment, drawdown reducers.
8. **ILC feedback measurement** — Daily top-20 coverage audit exists and runs automatically.

### 10.3 What Is Disconnected

| Disconnected component | Where it lives | What connects it to selection |
|---|---|---|
| Short DNA (`get_short_dna_confidence_boost()`) | `ph2_short_dna.py` | Needs call from `_identify_setup()` |
| Institutional DNA patterns | `institutional_dna.db` | Needs query in `_identify_setup()` or scorer |
| Historical magnitude distribution | Not stored | Needs a magnitude_db from replay data |
| EMP top-N lift statistics | `early_move_audit/` | Needs a feedback path to scanner scoring |
| ILC learning outcomes | `institutional_dna.db` | DB exists but IDR empty on VPS |

### 10.4 What Is Missing (No Equivalent Exists)

| Missing capability | Impact | Notes |
|---|---|---|
| Magnitude estimator | Cannot distinguish +0.1% from +5% opportunities | ATR × vol_ratio is the natural proxy |
| Opportunity pool (separate from signal pool) | Discovery and selection are conflated | `overbought_short_watch` slot in premarket_refiner.py is the intended hook |
| Multi-directional opportunity ranking | LONG and SHORT opportunities not in same pool | Architecture supports it; SHORT disabled |
| "Meaningful move" probability per candidate | Core to the target objective | Needs historical magnitude distribution |
| Post-selection magnitude feedback | ILC measures occurrence, not magnitude of missed move | Needs |actual_return| added to ILC record |

### 10.5 What Must NOT Be Changed

| Component | Why protected |
|---|---|
| `risk_guardian/risk_guardian.py` | Kill-switch; wrong change = real money loss |
| `strategy_lab/backtesting_ai.py` | WFT quality gates calibrated |
| `validation_engine/` | 6-stage promotion pipeline; governs strategy eligibility |
| `risk_control/capital_risk_engine.py:_MAX_POSITIONS` | Proven risk control; changing could over-expose |
| `_STRATEGY_SHARE` dict in CRE | Capital allocation fractions are deliberate |
| `MIN_CONFIDENCE_SCORE` in config | Governance gate; lowering enables poor signals |
| `overbought_short_watch` score penalty | Correctly penalises RSI extremes for LONG scoring |

### 10.6 Smallest Next Research/Implementation Step

The single smallest intervention that would move the architecture toward the target objective, without touching any protected module:

> **RESEARCH CANDIDATE: MOP-RC-001**
> 
> Add `expected_move_pct` and `magnitude_score` as computed-but-non-gating fields to the `TradeSignal` dataclass.
> 
> Formula: `expected_move_pct = sig.atr / sig.entry_price × RR_multiplier × 100`
> Formula: `magnitude_score   = atr_pct × sqrt(vol_ratio) × log(adv_crore / 50)`
> 
> These would be OBSERVATIONAL ONLY at first — logged in `[EdgeTelemetry]` but not used for selection. After 30 days of logging, the correlation between `magnitude_score` and actual next-day `|close_return_pct|` can be measured to determine whether magnitude_score is a valid predictor.
> 
> This change:
> - Does NOT modify governance, capital allocation, or confidence gates
> - Does NOT enable any disabled strategy
> - Provides ground truth for future magnitude-aware selection
> - Costs < 10 lines of code in `_identify_setup()`

---

## Appendix A — Candidate Data Structure (current)

Fields present in `data/daily_candidates.json` after nightly scan:

```json
{
  "symbol":            "TATASTEEL",
  "yahoo_ticker":      "TATASTEEL.NS",
  "base_ltp":          191.19,
  "resistance":        200.42,
  "support":           181.96,
  "rsi":               44.6,
  "volume_ratio":      0.8,
  "adv_crore":         524,
  "atr14":             4.31,
  "atr_pct":           2.25,
  "atr_anchored":      false,
  "buckets":           ["trend_pullback"],
  "score":             0.7234,
  "conviction_decay":  0.15,
  "sector":            "METALS",
  "index":             "NIFTY50",
  "strategy":          "pending_scan",
  "lifecycle_state":   "ACTIVE",
  "data_trust_score":  1.0,
  "conviction_score":  0.0,
  "momentum_state":    "neutral",
  "breakout_state":    "below_resistance"
}
```

**Missing fields for target objective:**
- `expected_move_pct` — not present
- `magnitude_score` — not present
- `dna_confidence` — not present
- `historical_move_distribution` — not present
- `opportunity_direction` — not present (separate from trade direction)

---

## Appendix B — Signal Data Structure (current)

Fields on `TradeSignal` when it exits `_identify_setup()`:

```
symbol:        str     e.g. "TATASTEEL"
direction:     LONG | SHORT
entry_price:   float
stop_loss:     float
target_price:  float   = entry + RR × stop_dist
confidence:    float   [5.5 – 9.5]  (vol_ratio + RSI bonus)
strategy_name: str
atr:           float   (ATR(14) absolute value)
quantity:      int     0 until CRE fills it
```

**Missing fields for target objective:**
- `expected_move_pct` — not present (derivable from `atr / entry_price × RR × 100`)
- `magnitude_score` — not present
- `opportunity_rank` — not present (scanner rank at generation time)
- `dna_boost` — not present

---

## Appendix C — Key Constant Reference

| Constant | Value | File | Meaning |
|---|---|---|---|
| `MAX_PREPARED_CANDIDATES` | 120 | `config.py` / `market_scanner.py` | Max candidates in store |
| `MIN_PREPARED_SCORE` | 0.55 | `config.py` / `market_scanner.py` | Scanner score floor |
| `SECTOR_MAX_FRACTION` | 0.20 | `market_scanner.py` | Max 20% from one sector |
| `_MAX_POSITIONS` | 8 | `capital_risk_engine.py` | Hard position cap |
| `RR_DEFAULT` | 2.5 | `equity_scanner_ai.py` | Default risk:reward |
| `OVERBOUGHT_RSI_MIN` | 65.0 | `market_scanner.py` | overbought_short_watch gate |
| `ATR_STOP_MULTIPLIER` | (from config) | `equity_scanner_ai.py` | Stop distance = ATR × this |
| `MOVER_THRESHOLD (BML)` | 2.0% | BML convention | "Significant mover" definition |

---

## Appendix D — Research Candidates Identified

| ID | Description | Files affected | Priority |
|---|---|---|---|
| MOP-RC-001 | Add `expected_move_pct` + `magnitude_score` as observational-only fields on TradeSignal | `equity_scanner_ai.py:_identify_setup()` | FIRST |
| MOP-RC-002 | Add `|actual_close_return_pct|` to ILC record for magnitude feedback | `institutional_learning/ilc_market_audit.py` | SECOND |
| MOP-RC-003 | Create daily ground-truth report comparing daily_candidates.json vs BML top-20 | New reporting script (read-only) | SECOND |
| MOP-RC-004 | Connect DNA confidence boost to scanner candidate score as observational field | `opportunity_engine/market_scanner.py` | THIRD (after RC-001 proven) |
| MOP-RC-005 | Magnitude-weighted selection: sort CRE by `confidence × expected_move_pct` instead of `confidence` alone | `risk_control/capital_risk_engine.py:_cre_quality_score()` | FOURTH (after RC-001 + RC-002 validated) |

All research candidates require a governance study before implementation. RC-005 in particular modifies a protected-adjacent function and requires explicit user approval.

---

```
[MOP-001 ARCHITECTURE AUDIT SUMMARY]

Discovery:                     PARTIAL — 100% universe coverage; magnitude-blind
Opportunity candidate pool:    PARTIAL — 120 candidates scored; no magnitude ranking
Meaningful-move estimation:    MISSING — ATR available but not used for magnitude
Final 5–6 selection:           PARTIAL — confidence + capital; price can displace quality
Knowledge-integrated selection: MISSING — regime connected; DNA/magnitude not connected
Top-20 feedback loop:          PARTIAL — ILC measures coverage; not wired to scorer
Capital-aware selection:       READY — CRE correctly governs budget and position count

What already works:
  - Full 230-stock universe with nightly refresh
  - Scored candidate pool (up to 120)
  - Regime-gated strategy selection
  - Sector rotation integration
  - Breakout invalidation
  - Concentration penalty
  - Capital governance (MAX_POSITIONS, drawdown reducers)
  - ILC coverage measurement

What is disconnected:
  - DNA knowledge (exists, not called)
  - EMP hit-rate statistics (measured, not fed back)
  - Magnitude estimation (ATR exists, not exposed)

What is missing:
  - expected_move_pct field on signals and candidates
  - Opportunity layer separate from trade signal layer
  - Magnitude-weighted selection (MOP-RC-001 prerequisite)
  - Post-selection magnitude feedback to scorer

What must not be changed:
  - risk_guardian (kill-switch)
  - backtesting_ai / validation_engine (promotion gates)
  - _MAX_POSITIONS, _STRATEGY_SHARE, MIN_CONFIDENCE_SCORE

Smallest next step:
  MOP-RC-001 — Add observational expected_move_pct to TradeSignal
  (< 10 lines, no governance impact, provides measurement base)

Production changes: NONE
Orders:            0
```

---

*This document is read-only research. No production code was modified.*  
*Audit ID: MOP-001*  
*Executed: 2026-08-13*
