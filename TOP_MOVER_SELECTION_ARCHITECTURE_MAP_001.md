# TOP_MOVER_SELECTION_ARCHITECTURE_MAP_001
## IIOS Pipeline Architecture — Traced from Code
**Date:** 2026-08-14  
**Audit:** TOP_MOVER_SELECTION_AUDIT_001  
**Method:** Direct code trace — not inferred from documentation

---

## Overview: The 230 → 5–6 Pipeline

```
data/nifty500_universe.json (230 symbols)
           │
           ▼
    [Phase D — 16:45 IST]
    market_scanner.py
    Stage 1: Fetch 35-day OHLCV (yfinance)
    Stage 2: Compute technical context
    Stage 3: Quality gates
    Stage 4: Sector cap + concentration penalty
    Stage 5: Score + rank → CandidateStore (≤120 candidates)
           │
           ▼
    [Scan cycles — 09:10, 10:30, 11:30, 13:00, 14:00, 15:00 IST]
    equity_scanner_ai.py
    _prepared_watchlist() → loads CandidateStore
    _identified_setup() → generates TradeSignal per setup
           │
           ▼
    pig_enrich_signals()  ← PIGTradingAdapter (stale library.json)
           │
           ▼
    MultiAgentDebate (5 agents + optional InstitutionalDNA)
           │
           ▼
    DecisionEngine.decide() → score ≥ 6.5 → APPROVE
           │
           ▼
    PortfolioAllocationAI.compute_position_size()
           │
           ▼
    OrderManager.execute() → DhanBroker / paper_trades.csv
```

---

## A. Where the 230 Stocks Enter

**File:** `data/nifty500_universe.json`  
**Format:** JSON array, each entry: `{symbol, company_name, sector, ...}`  
**Symbols:** 230 stocks with `.NS` suffix (e.g., `HDFCBANK.NS`)  
**Sectors covered:** BANKING_FINANCE, IT, PHARMA, AUTO, METALS, FMCG, INFRA, ENERGY, TELECOM, etc.

**Entry points:**
1. `market_scanner.py::_load_universe()` — loads at 16:45 IST post-market scan
2. `equity_scanner_ai.py` — loads sector map at import time (`_SYMBOL_SECTOR_MAP`)
3. `production_readiness/ph4_universe.py` — eligible universe builder (ADV ≥ 50 Cr filter)

**Universe rebuilds:** Every Monday at 08:30 IST via `_do_weekly_universe_rebuild()` in orchestrator.

**Historical limitation:** `nifty500_universe.json` is a STATIC snapshot. Survivorship bias applies — delistings and index changes are not reflected historically. No point-in-time universe reconstruction exists (see PTUE design document for planned fix).

---

## B. How Candidates Are Generated

**Phase D (16:45 IST) — `market_scanner.py::run_scan()`:**

```
For each symbol in 230 universe:
  1. Fetch 35-day OHLCV
  2. Compute technical context:
       - RSI(14) — Wilder-smoothed
       - ATR(14) = mean(high-low) over 14 bars
       - resistance_20d = max(high) over 20 bars
       - support_20d = min(low) over 20 bars
       - volume_ratio = today_volume / 20d_avg_volume
       - adv_crore = daily traded value (Cr)
  3. Quality gates:
       - MIN_HISTORY_DAYS = 15 (skip if fewer)
       - MIN_ATR_PCT = 0.3% (skip if too illiquid)
       - MAX_ATR_PCT = 8.0% (skip if too volatile)
       - MIN_VOLUME_RATIO = 0.2 (skip if too illiquid)
  4. Compute composite score (see Section C)
  5. Apply sector cap: max 20% of final candidates per sector
  6. Apply concentration penalty: 5% per day after day 3 in consecutive selection
  7. Score floor: MIN_PREPARED_SCORE = 0.55 (drop below this)
  8. Hard cap: MAX_PREPARED_CANDIDATES = 120
  9. Write to CandidateStore (JSON file)
```

**Next-day scan cycle — `equity_scanner_ai.py::scan()`:**

```
1. _prepared_watchlist() → loads CandidateStore (≤120 records)
2. For each prepared candidate:
   a. Check valid_until_utc (TTL expiry — skip if expired)
   b. Check breakout invalidation:
      - support_breakdown: LTP < support − ATR
      - failed_breakout: was above resistance, returned below
      - atr_shock: drift > 3.5×ATR
      - momentum_rejection: RSI was >60, now <38
   c. Apply conviction decay (in-memory, not persisted):
      - vol_collapse (ratio <0.4): ×0.840
      - momentum_extreme (RSI >72 or <28): ×0.910
      - vol_compression (ATR/LTP <0.5%): ×0.925
      - strong_breakout (vol≥3×, near resistance): ×0.988
      - vol_continuation (vol≥2×): ×0.972
      - normal: ×0.980
3. Sector re-rank by live sector leaders (if available)
4. Run _identify_setup() for each candidate
5. Phase H: 20% exploration budget from static watchlist
```

---

## C. How Candidate Scores Are Calculated

**Phase D scanner score (from `market_scanner.py::_process_symbol()`):**

```
bucket = classify_bucket(rsi, volume_ratio, breakout_proximity, pullback_proximity)
  BREAKOUT:        LTP within 2% of resistance (BREAKOUT_PROXIMITY_PCT = 0.02)
  PULLBACK:        LTP within 4% of support in bull regime
  OVERSOLD:        RSI ≤ 40 (OVERSOLD_RSI_MAX = 40.0)
  OVERBOUGHT:      RSI ≥ 65 (OVERBOUGHT_RSI_MIN = 65.0) → SHORT candidate
  VOLUME_EXPAND:   volume_ratio ≥ 1.8

score = weighted_combination(
  breakout_quality,   # how cleanly price approaches resistance
  volume_evidence,    # volume ratio above threshold
  rsi_positioning,    # RSI in optimal zone per bucket
  trend_clarity,      # price position in 20-day range
  sector_conviction   # sector-level rotation strength
)
```

**Score is in [0, 1] range.** Values above `MIN_PREPARED_SCORE = 0.55` pass to CandidateStore.

**Intraday score adjustments:**
- Conviction decay multipliers applied per cycle (×0.840 to ×0.988)
- Sector re-rank re-orders candidates but does not change base score

---

## D. Where Knowledge Is Used

### D1. PlatformIntelligenceGateway (PIG)

**File:** `market_learning/pig_integration.py::PIGTradingAdapter`  
**Integration points:**
1. **Opportunity enrichment:** `pig_enrich_signals()` at orchestrator line ~1566
   - Adds confidence boost to signals where `ca_pmci ≥ 0.30`
   - PIGQuery result: direction probability, signal strength, institutional alignment
2. **Debate vote:** `pig_build_vote()` at orchestrator line ~2528
   - Produces `InstitutionalDNAAI` vote (weight 0.08 in DecisionEngine)
   - Vote cast only when `ca_pmci ≥ 0.30`

**Data source:** `data/mls/consensus/library.json` — **STATIC, never updated during trading**  
**Root cause (confirmed):** MLS pipeline (MarketObserver → PopulationClassifier → DNADiscoveryEngine → DNAConsensusEngine) is never called from the orchestrator. Library.json is stale.  
**Practical effect:** PIG contribution is near-zero (library empty or stale).

### D2. KnowledgeProvider (Research Infrastructure)

**File:** `autonomous_research/knowledge_provider.py`  
**Used by:** ResearchCoordinator, GapDetector, ARS pipeline  
**NOT used in live trading decision path.** Does not affect scan(), debate(), or DecisionEngine.

### D3. StrategyHealthMonitor / LearningEngine

**File:** `learning_system/strategy_health_monitor.py`  
**Used by:** PRR-001 Phase 1 — blocks DECAYING edges (132/259 = 51% blocked)  
**Effect:** Strategies with declining edge statistics are suppressed before reaching the debate

### D4. Strategy Knowledge (DECAYING Edge Gate)

**PRR-001 Phase 1:** `knowledge_provider.list_edges()` — blocks strategies tagged DECAYING  
**Effect:** 132/259 edges blocked; only VALID/IMPROVING edges reach OrderManager

---

## E. Where Strategy Is Used

**Strategy assignment** — in `_identify_setup()` via `strategy_name` field:
- `Breakout_Strategy` — LTP above resistance, high volume
- `MomentumPullback` — RSI 50-65 pullback in bull regime
- `MeanReversionBounce` — RSI < 40, at support in any regime
- `ResistanceRetest` — broken resistance acting as new support
- `HighRSIShort` — RSI > 65-70, near resistance (SHORT direction)

**Strategy health gate** — `StrategyHealthMonitor.is_healthy(strategy_name)`
- Win rate below threshold → strategy suppressed
- Controlled by `learning_db.json` (updated by LearningEngine daily)

**Debate vote** — `StrategyDebateAI` agent (weight: 0.25 in AGENT_WEIGHTS)
- Assesses strategy fitness for current conditions
- Interacts with `StrategyHealthMonitor`

**DecisionEngine thresholds:**
```python
AGENT_WEIGHTS = {
  "TechnicalAnalystAI": 0.30,
  "MacroAnalystAI":     0.20,
  "RiskDebateAI":       0.25,
  "SentimentAI":        0.15,
  "RegimeDebateAI":     0.10,
  "InstitutionalDNAAI": 0.08,  # only present if PIG has data
}
MIN_CONFIDENCE_SCORE = 6.5  # threshold for APPROVE
```

---

## F. Where Direction Is Determined

**Location:** `equity_scanner_ai.py::_identify_setup()`

**LONG (BUY) conditions:**
1. `Breakout`: LTP > resistance, volume_ratio ≥ vol_ratio_min (default 2.0)
2. `MomentumPullback`: RSI 50-65, bull regime (TRENDING_UP), price above support
3. `MeanReversionBounce`: RSI < 40, at support, bull/sideways regime
4. `ResistanceRetest`: recently broken resistance now acting as support

**SHORT conditions:**
1. `HighRSIShort`: RSI > 65-70, volume_ratio ≥ 1.5, near resistance
   - Only active when PRR-001 Phase 2 SHORT DNA is operative (added 2026-08-07)

**Historical note (replay.db):** ALL 57,037 signals in replay.db have `expected_move_direction = 'LONG'`. SHORT signal generation was added post-PRR-001 (2026-08-07). The replay.db era (2021-2025) has zero SHORT signals.

---

## G. Where Magnitude Is Represented

**Location:** `equity_scanner_ai.py::scan()` after `_identify_setup()`:
```python
sig.expected_move_pct = sig.atr / sig.entry_price * sig.risk_reward_ratio * 100
```

**RR ratios used:**
- `RR_STRONG_BREAKOUT = 4.0` (volume_ratio ≥ 3.0)
- `RR_NORMAL_BREAKOUT = 2.5`
- `RR_TREND_PULLBACK = 3.0` (confirmed bull trend)
- `RR_DEFAULT = 2.5`

**Critical finding:** `expected_move_pct` in replay.db = **8.0 for ALL 57,037 signals** (hardcoded constant, not a per-signal prediction). This was a design placeholder. The ATR×RR formula was added later (MOP-RC-001, 2026-08-13) — not present in the replay.db generation era.

---

## H. Where expected_move_pct Is Available

1. `signal_births.expected_move_pct` — stored in replay.db (ALL = 8.0, not meaningful)
2. Live trading: `sig.expected_move_pct` computed in scan() post-MOP-RC-001
3. `signal_births.consensus_score_at_birth` — debate consensus [0,1] is more meaningful than expected_move_pct

---

## I. Where Capital Constraint Is Applied

**File:** `risk_control/portfolio_allocation_ai.py::PortfolioAllocationAI`  
**Formula:** `qty = (account_equity × RISK_PER_TRADE) / abs(entry_price - stop_loss)`  
**Capital:** `TOTAL_CAPITAL = 10,000 INR` (config)  
**Effect:** For low-priced stocks, qty may be substantial. For high-priced stocks (>₹2000), qty may = 0.

**QTY_ZERO signals:** Signal is predicted but cannot be traded at current capital.  
**Important:** QTY_ZERO is a tradeability constraint, NOT a prediction failure.

---

## J. Where Final Candidate Selection Occurs

**Multi-stage selection:**

| Stage | Component | Selection Criterion |
|-------|-----------|---------------------|
| 1 | `market_scanner.py` | Score ≥ 0.55, sector cap 20%, top 120 by score |
| 2 | `_prepared_watchlist()` | TTL valid, not invalidated, conviction decay applied |
| 3 | `_identify_setup()` | Meets setup criteria (breakout, pullback, etc.) |
| 4 | `DecisionEngine.decide()` | Weighted debate score ≥ 6.5 |
| 5 | `PortfolioAllocationAI` | qty > 0 (capital feasibility) |
| 6 | `OrderManager.execute()` | Signal freshness ≤ 15 days (PRR-001 Phase 3) |

**There is NO explicit "20 UP + 20 DOWN" pool.** The pipeline generates signals from matching setups, not from a fixed-size ranked pool. On a typical day the prepared universe contains 80-120 candidates; scan() generates 0-15 signals; after debate typically 0-5 are approved.

---

## Key Architecture Gaps (Confirmed)

| Gap | Impact |
|-----|--------|
| MLS pipeline never scheduled | PIG vote is near-zero (stale/empty library) |
| expected_move_pct = 8.0 hardcoded in replay.db era | Magnitude prediction is not working historically |
| ALL signals in replay.db are LONG | Cannot evaluate DOWN selection with Model A |
| Universe is static snapshot | Survivorship bias in historical analysis |
| No "20 UP + 20 DOWN" pool generation | Pipeline produces setup-driven signals, not ranked top-N |
| Sector leaders arrive at scan time (intraday) | Sector rerank not available at pre-market selection |
| DECAYING edge gate blocks 51% of strategy edges | Strategy contributes negatively by blocking many IIOS signals |

---

## Data Sources for Historical Audit

| Source | Content | Date Range | Coverage |
|--------|---------|-----------|----------|
| `data/replay.db::ohlcv_daily` | OHLCV for 210-211 symbols | 2021-01-01 to 2025-12-30 | 1,235 trading dates |
| `data/replay.db::signal_births` | 57,037 IIOS signals (all LONG) | 2021-02-05 to 2025-12-30 | 209 unique symbols |
| `data/replay.db::universe_stocks` | 230 symbols + sectors | Static | 230 symbols |
| `data/replay.db::archetype_versions` | Strategy DNA archetypes | — | 7 distinct archetypes |

**Archetype distribution:**
- `DNA_1B_SECTOR_PRE_BKT`: 22,901 (40%) — sector breakout pre-confirmation
- `DNA_1A_MOMENTUM_CONT`: 16,070 (28%) — momentum continuation  
- `DNA_1A_SECTOR_BKT`: 8,372 (15%) — sector breakout
- `DNA_1B_QUIET_ACCUMULATION`: 3,963 (7%) — quiet accumulation phase
- `DNA_1A_52W_HIGH_EXPAND`: 3,790 (7%) — 52-week high expansion
- `DNA_1B_LOW_NOISE_STRENGTH`: 1,107 (2%) — low noise strength
- `DNA_1A_RESULTS_FOLLOWTHR`: 834 (1%) — results follow-through

**Regime distribution (signal births):**
- SIDEWAYS: 29,193 (51%)
- TRENDING_UP: 26,498 (46%)
- TRENDING_DOWN: 1,346 (2%)
