# MOVER_DISCOVERY_ARCHITECTURE_MAP_002
## Discovery Boundary Trace — Where Stocks Disappear
**Date:** 2026-08-14  
**Audit:** MOVER_DISCOVERY_AUDIT_002  
**Method:** Traced from actual production code — market_scanner.py, equity_scanner_ai.py, decision_engine.py

---

## Complete Pipeline Map: Where a Stock Can Disappear

```
230 symbols in data/nifty500_universe.json
           │
           │  GATE 0: Universe construction
           │  Threshold: symbols actually in nifty500_universe.json
           │  Missing symbols = GONE (20 of 230 have no OHLCV history in replay.db)
           ↓
210 symbols with OHLCV history
           │
           │  GATE 1: Data quality (MIN_HISTORY_DAYS = 15)
           │  Threshold: < 15 trading-day records → SKIP
           │  Reversible: YES (wait for more history)
           ↓
~208 symbols pass data quality
           │
           │  GATE 2: Liquidity floors
           │  Threshold: ATR% < 0.3% → SKIP (too illiquid)
           │  Threshold: ATR% > 8.0% → SKIP (too volatile)
           │  Threshold: 3d_vol / 20d_avg_vol < 0.2 → SKIP
           │  Reversible: YES (volume normalizes)
           ↓
~195-200 symbols pass liquidity
           │
           │  GATE 3: Bucket classification
           │  BREAKOUT bucket: LTP within 2% below resistance_20d (BREAKOUT_PROXIMITY_PCT=0.02)
           │  PULLBACK bucket: LTP within 4% above support_20d (PULLBACK_PROXIMITY_PCT=0.04)
           │  OVERSOLD bucket: RSI ≤ 40 (OVERSOLD_RSI_MAX=40.0)
           │  OVERBOUGHT bucket: RSI ≥ 65 (OVERBOUGHT_RSI_MIN=65.0) → SHORT candidate
           │  VOLUME_EXPAND bucket: volume_ratio ≥ 1.8
           │  NO BUCKET = LOW SCORE (not explicitly filtered, but scored low)
           │  Reversible: YES (price moves create new bucket membership)
           ↓
Bucket-scored candidates
           │
           │  GATE 4: Composite score floor
           │  Threshold: score < 0.55 (MIN_PREPARED_SCORE) → DROPPED
           │  Score formula: breakout_quality + volume_evidence + RSI_positioning +
           │                 trend_clarity + sector_conviction (weighted combination)
           │  Reversible: YES (price/volume change)
           ↓
~60-120 candidates above floor
           │
           │  GATE 5: Sector diversification cap
           │  Threshold: SECTOR_MAX_FRACTION = 20% → max 24 of 120 from any sector
           │  Applied: sorted by score DESC, sector count enforced
           │  Reversible: YES (other sector members score lower)
           ↓
≤120 candidates (MAX_PREPARED_CANDIDATES) → CandidateStore
           │
           │  TTL: valid_until_utc = scan_time + 18h (next-day validity)
           ↓
INTRADAY SCAN CYCLES (09:10, 10:30, 11:30, 13:00, 14:00, 15:00 IST)
           │
           │  GATE 6: TTL expiry
           │  Candidates older than valid_until_utc → INVALIDATED
           │  Reversible: NO (requires new Phase D scan)
           ↓
Valid candidates for today
           │
           │  GATE 7: Breakout invalidation (equity_scanner_ai._prepared_watchlist)
           │  support_breakdown: LTP < support_20d − ATR → REMOVED
           │  failed_breakout: was above resistance, now below → REMOVED
           │  atr_shock: abs(drift) > 3.5 × ATR → REMOVED
           │  momentum_rejection: RSI was >60, now <38 → REMOVED
           │  Reversible: NO within same cycle
           ↓
Conviction-adjusted candidates
           │
           │  GATE 8: Setup identification (_identify_setup)
           │  LONG: Breakout (LTP > resistance, vol≥2×), MomentumPullback (RSI 50-65, bull),
           │        MeanReversionBounce (RSI<40, support, any regime), ResistanceRetest
           │  SHORT: HighRSIShort (RSI>65-70, vol≥1.5×, near resistance)
           │  NO MATCHING SETUP → no signal generated (silent drop)
           │  Reversible: YES (next scan cycle)
           ↓
TradeSignal objects (each with setup_type, direction, entry, stop, target)
           │
           │  GATE 9: expected_move_pct computation
           │  sig.expected_move_pct = ATR / entry × RR × 100
           │  RR_STRONG_BREAKOUT=4.0 (vol≥3×), RR_NORMAL_BREAKOUT=2.5,
           │  RR_TREND_PULLBACK=3.0 (confirmed bull), RR_DEFAULT=2.5
           │  Historical note: all replay.db era signals have 8.0 (hardcoded placeholder)
           ↓
Signals with magnitude estimate
           │
           │  GATE 10: PIG enrichment (pig_enrich_signals)
           │  Adds confidence boost if ca_pmci ≥ 0.30 in library.json
           │  Historical status: STALE — library.json never updated, near-zero effect
           ↓
PIG-enriched signals
           │
           │  GATE 11: Multi-agent debate (5-6 agents)
           │  TechnicalAnalystAI (0.30): RSI, MACD, Bollinger, support/resistance
           │  MacroAnalystAI (0.20): market regime, global context
           │  RiskDebateAI (0.25): risk-reward ratio, stop placement
           │  SentimentAI (0.15): news/social proxy
           │  RegimeDebateAI (0.10): trend/range classification
           │  InstitutionalDNAAI (0.08): PIG/DNA vote (near-zero historically)
           │  Hard reject from ANY agent → DROPPED
           │  Weighted score < 6.5 (MIN_CONFIDENCE_SCORE) → DROPPED
           │  This gate is not simulatable from replay.db (agents produce varying outputs)
           ↓
Approved signals (base_score ≥ 6.5 in signal_births)
           │
           │  GATE 12: Capital / position sizing
           │  qty = (10000 × RISK_PER_TRADE) / |entry - stop|
           │  qty = 0 → QTY_ZERO signal (not tradeable at current capital)
           │  Threshold: typically stocks >₹2000 → qty_zero
           ↓
5–6 APPROVED SIGNALS per cycle → OrderManager
```

---

## Rejection Stage Summary

| Gate | Name | Type | Threshold | Recoverable |
|------|------|------|-----------|-------------|
| 0 | Universe construction | Hard | Missing from nifty500_universe.json | No (until Monday rebuild) |
| 1 | Data quality | Hard | < 15 trading-day OHLCV records | Yes (next scan cycle) |
| 2 | Liquidity floors | Hard | ATR% <0.3% or >8%, vol_ratio <0.2 | Yes (conditions change) |
| 3 | Bucket classification | Soft | No qualifying bucket = low score | Yes |
| 4 | Score floor | Hard | Composite score < 0.55 | Yes (next scan cycle) |
| 5 | Sector cap | Hard | >20% of candidates from one sector | Yes (other sector members drop) |
| 6 | TTL expiry | Hard | Past valid_until_utc | No (until next Phase D at 16:45) |
| 7 | Breakout invalidation | Hard | Support break, ATR shock, RSI rejection | No (that cycle) |
| 8 | Setup identification | Soft | No matching setup pattern | Yes (next scan cycle) |
| 9 | Magnitude estimate | Info | expected_move_pct (was 8.0 hardcoded) | N/A |
| 10 | PIG enrichment | Soft | library.json stale | Historically stale |
| 11 | Multi-agent debate | Hard | score < 6.5, or any hard reject | Yes (next scan cycle) |
| 12 | Capital sizing | Hard | qty = 0 at current capital | Yes (capital increase) |

---

## Critical Discovery Boundaries

### Boundary A: 230 → CandidateStore (Gates 0–5)

**This is where 84% of missed movers are lost.**

Stock must have:
1. OHLCV history ≥ 15 days
2. ATR% in [0.3%, 8.0%]  
3. Volume ratio ≥ 0.2
4. Composite score ≥ 0.55 — which requires BEING in one of: BREAKOUT, PULLBACK, OVERSOLD, or VOLUME_EXPAND bucket
5. Not displaced by sector cap

**The fundamental constraint:** A stock that is consolidating quietly (RSI 45-55, volume ratio <1.8, not near resistance/support extremes) scores LOW even if it is about to break out. The scanner rewards stocks already showing setup criteria — not stocks about to show them.

### Boundary B: CandidateStore → signal_births (Gates 6–8)

**This is where the remaining ~8-12% of discovered candidates fail to generate signals.**

Most common failures:
- Setup criteria not met at intraday scan time (price not at threshold)
- Invalidation triggers before setup confirmation
- Exploration budget (Phase H) limited to 20% — non-prepared symbols rarely selected

### Boundary C: signal_births → OrderManager (Gates 11–12)

**This is where ~33% of IIOS signals are blocked.**

Gate 11 (debate) is the primary filter here. `base_score` distribution shows average 6.09 — slightly below the 6.5 threshold. Approximately 50% of signals are rejected at debate.

### Key Scanner Limitations (confirmed in code)

1. **Bucket-centric scoring**: Only stocks already in a breakout/pullback/oversold/overbought state score highly. A quiet accumulation phase cannot score high before the breakout begins.

2. **20-day resistance/support as hard boundaries**: The scanner cannot identify stocks forming a NEW resistance level (horizontal consolidation near NEW highs).

3. **No multi-day setup recognition**: Scanner evaluates each day independently. A 5-day squeeze pattern (narrowing Bollinger bands) is not detected as a single signal.

4. **Volume threshold absolute not relative**: VOLUME_EXPANSION_MIN=1.8 is an absolute ratio floor. Sector-relative volume (is this stock's volume high vs its own sector average?) is not computed.

5. **No sector pre-rotation**: Sector context arrives as `sector_leaders` at intraday scan time, not at 16:45 Phase D scoring. Sector rotation signals that exist at end-of-day are not used for candidate selection.

6. **Single-direction bucket for each threshold**: BREAKOUT bucket (RSI ~55-65) vs OVERSOLD bucket (RSI <40). Stocks at RSI 42-50 (beginning to recover from oversold) do not clearly belong to any bucket.

7. **Concentration penalty prevents re-selection**: Stocks selected for 3+ consecutive days get score penalty (5%/day), which can drive good setups below the 0.55 floor.

8. **No gap detection**: Overnight gap (open >> previous close) is not a scoring factor. Gap-and-continue patterns are invisible.

9. **Static 20-day lookback**: Both resistance_20d and support_20d use a fixed 20-day window. A stock with its 52-week high set 21+ days ago loses that information from the lookback.

10. **No relative strength ranking**: A stock in the top 5th percentile of universe momentum is treated identically to one in the 40th percentile (same bucket threshold).

---

## Scanner Score Formula (Reconstructed from Code)

```
score = Σ(component × weight)

Components identified:
  breakout_quality   = f(resistance_proximity, volume_confirmation)
  volume_evidence    = f(volume_ratio, volume_trend_consistency)
  rsi_positioning    = f(RSI vs bucket optimal zone)
  trend_clarity      = f(price position in 20d range, momentum direction)
  sector_conviction  = f(sector_leader alignment, sector relative return)

ABSENT from score:
  ✗ absolute momentum magnitude (how fast is it moving?)
  ✗ volatility expansion (is ATR expanding from a squeeze?)
  ✗ relative strength vs universe percentile
  ✗ sector pre-rotation (sector starting to outperform market)
  ✗ multi-day pattern recognition
  ✗ NIFTY market context at scoring time
  ✗ gap or overnight range expansion
```

---

## What Happens to a Quiet Strong Mover

**Scenario:** Stock X has been trading quietly for 3 weeks. RSI = 48. Volume ratio = 1.1. Price is 5% below 20-day resistance. On the day before it makes a +4% move, the stock shows:
- RSI: 50 (no bucket match — not BREAKOUT, not PULLBACK, not OVERSOLD)
- Volume: 1.2× average (not VOLUME_EXPAND)
- Price: 5% from resistance (not within 2% → not BREAKOUT bucket)
- Momentum 5d: +0.8% (not strong enough to score highly)

**Result:** Score ≈ 0.30-0.45 → BELOW MIN_PREPARED_SCORE = 0.55 → NEVER enters CandidateStore → NEVER generates signal → NEVER enters debate → **MISSED AT GATE 4.**

This is the primary discovery mechanism failure. The scanner cannot detect preparation phase before the move.

---

## equity_scanner_ai.py Setup Logic (Gate 8 Detail)

```
_identify_setup(stock, snapshot) evaluates:

LONG conditions checked in order:
1. Breakout: LTP > resistance_20d AND vol ≥ 2.0× avg → "Breakout_Strategy"
   → REQUIRES: price already above resistance (too late for pre-move detection)
   
2. MomentumPullback: RSI in [50,65], price > support, bull regime
   → REQUIRES: RSI already in momentum zone
   
3. MeanReversionBounce: RSI < 40, near support (LTP within 3% above support)
   → REQUIRES: RSI already oversold
   
4. ResistanceRetest: recent breakout (3-10d ago), price pulled back to resistance-as-support
   → REQUIRES: prior breakout event in memory

SHORT conditions:
5. HighRSIShort: RSI > 65-70, vol ≥ 1.5×, near resistance

CRITICAL GAP:
  None of these setups detect pre-breakout accumulation.
  "Near breakout" (within 2%) is the closest — but only if price is already within 2%.
  A stock 5% below resistance cannot generate any of these setups.
```

---

## MLS Pipeline Status (Confirmed from Code)

```
MLS pipeline (Market Learning System):
  MarketObserver:       NOT scheduled (orphaned)
  PopulationClassifier: NOT scheduled (orphaned)
  DNADiscoveryEngine:   NOT scheduled (orphaned)
  DNAConsensusEngine:   NOT scheduled (orphaned)
  
library.json (consensus data store):
  Status: STATIC — never updated during trading
  Last meaningful content: unknown (possibly empty)
  PIG vote weight: 0.08 (but near-zero contribution)

What MLS would have provided (if running):
  - Historical archetype detection: which stocks show "institutional accumulation" DNA
  - Population-level consensus: what fraction of similar-archetype signals succeeded
  - Dynamic DNA updates: learning from recent signal outcomes
  
Confirmed: The 8% institutional DNA vote was effectively 0% throughout the
evaluated period (2021-2025) because library.json was never updated.
```

---

## Sector Timing Gap

```
CURRENT FLOW:
  16:45 → Phase D scanner (scores candidates WITHOUT sector pre-rotation context)
  09:10+ → Intraday: sector_leaders loaded → candidates re-ranked by sector strength
  
PROBLEM: Candidate pool is FIXED before sector leaders arrive.
  If Sector X is rotating but no Sector X stocks scored ≥ 0.55 at 16:45,
  none will be in the pool to be re-ranked the next morning.
  
EXAMPLE:
  METALS sector shows pre-rotation signal (closing price, volume) at 16:45.
  But individual metal stocks score 0.45-0.52 (below floor).
  Next morning metals open up 2-3%.
  All metal stocks are MISSED — they were never in the candidate pool.
```

---

## Confirmed Architectural Gaps (Priority Ordered)

| Gap ID | Description | Pipeline Stage | Evidence |
|--------|-------------|----------------|---------|
| G1 | Pre-breakout accumulation not detected | Gate 3/4 | AUDIT_001: 84% A_NOT_IN_POOL |
| G2 | Sector pre-rotation not used at Phase D | Gate 5 | Code trace: sector_leaders loaded only intraday |
| G3 | Volume expansion threshold absolute not sector-relative | Gate 3 | Code: VOLUME_EXPANSION_MIN=1.8 (fixed, not relative) |
| G4 | MLS/DNA never updated | Gate 10/11 | Library.json static, never written |
| G5 | No multi-day pattern recognition | Gate 3/8 | Code: single-day evaluation only |
| G6 | No relative strength ranking | Gate 4 | Code: score formula lacks universe_percentile |
| G7 | 20-day lookback misses longer context | Gate 3/8 | 20d window fixed; 52w context absent |
| G8 | Gap/overnight expansion invisible | Gate 3/8 | No gap detection in scanner code |
| G9 | Concentration penalty may expire legitimate setups | Gate 4 | CONCENTRATION_PENALTY_PER_DAY=5%, starts day 3 |
| G10 | DOWN detection architecture is minimal | Gates 3/8 | Only HighRSIShort setup; no momentum-down or sector-breakdown |
