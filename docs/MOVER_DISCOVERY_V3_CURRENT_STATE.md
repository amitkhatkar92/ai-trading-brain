# MOVER_DISCOVERY_V3 — Current Production State
**Date:** 2026-08-14  
**Source:** Direct code trace — opportunity_engine/market_scanner.py, opportunity_engine/equity_scanner_ai.py

---

## Current Discovery Architecture

```
nifty500_universe.json (230 symbols)
           │
           │  Phase D scanner — runs at 16:45 IST daily
           │  entry point: opportunity_engine/market_scanner.py::run_scan()
           ↓
_batch_fetch()
  yfinance 35d OHLCV in chunks of 50 symbols
  Rate-limited: 2s between chunks
           │
           ↓
_process_symbol() [per symbol]
  Extracts: close[], high[], low[], volume[]
           │
           │  GATE 1: Data quality
           │  MIN_HISTORY_DAYS = 15 (line 76)
           │  Reject if fewer than 15 trading-day records
           │
           │  GATE 2: Liquidity floors
           │  MIN_ATR_PCT = 0.3  (line 77)
           │  MAX_ATR_PCT_GATE = 8.0  (line 78)
           │  MIN_VOLUME_RATIO = 0.2  (line 79)
           │  All three are hard reject — symbol returns None
           │
           │  Computes: resistance_20d = max(high[-20:])
           │            support_20d    = min(low[-20:])
           │            rsi_14         (Wilder RSI)
           │            atr_14         (True Range avg)
           │            atr_pct        = atr_14 / ltp * 100
           │            volume_ratio   = vol[-1] / avg(vol[-20:])
           ↓
_classify_buckets() [soft scoring, not hard gate]
  BREAKOUT:   ltp within 2% below resistance_20d (BREAKOUT_PROXIMITY_PCT=0.02)
  PULLBACK:   ltp within 4% above support_20d in bull regime (PULLBACK_PROXIMITY_PCT=0.04)
  OVERSOLD:   RSI ≤ 40 (OVERSOLD_RSI_MAX=40.0)
  OVERBOUGHT: RSI ≥ 65 (OVERBOUGHT_RSI_MIN=65.0) → SHORT candidate
  VOLUME_EXPAND: volume_ratio ≥ 1.8 (VOLUME_EXPANSION_MIN=1.8)
  
  Each bucket adds weight to score.
  Stock with NO bucket gets low base score.
           │
           │  Composite score = weighted sum of bucket contributions
           ↓
run_scan() [aggregate + filter]
  Concentration penalty: −5%/day after 3 consecutive days selected
  Sort by score DESC
  Sector cap: SECTOR_MAX_FRACTION = 0.20 (max 20% from any sector)
  Hard score floor: MIN_PREPARED_SCORE = 0.55
  Hard count cap: MAX_PREPARED_CANDIDATES = 120
           │
           ↓
CandidateStore.write()
  Writes to data/prepared_candidates.json
  valid_until_utc = scan_time + 18h
           │
           │  Intraday scan cycles: 09:10, 10:30, 11:30, 13:00, 14:00, 15:00 IST
           │  entry point: equity_scanner_ai.py::scan()
           ↓
_live_watchlist() → live LTP fetch (Dhan or yfinance fallback)
           │
           │  GATE 6: TTL check — skip if past valid_until_utc
           │  GATE 7: Invalidation conditions:
           │    support_breakdown: ltp < support_20d - atr
           │    failed_breakout:   ltp < resistance_20d (after being above)
           │    atr_shock:         |drift| > 3.5 × atr
           │    momentum_rejection: RSI was >60, now <38
           ↓
_identify_setup() [setup classification]
  Returns None if no setup matches — SIGNAL NOT GENERATED.
  
  LONG setups (4 types):
    1. Breakout_Strategy:       ltp > resistance_20d AND vol ≥ 2.0×
    2. MomentumPullback:        RSI in [50,65], ltp > support, bull regime
    3. MeanReversionBounce:     RSI < 40, ltp within 3% above support_20d
    4. ResistanceRetest:        prior breakout 3-10d ago, pulled back to R-as-S

  SHORT setup (1 type):
    5. HighRSIShort:            RSI > 65-70, vol ≥ 1.5×, near resistance
           │
           ↓
TradeSignal created
  expected_move_pct computed:
    = (ATR / entry_price) × RR_factor × 100
    RR_STRONG_BREAKOUT = 4.0 (vol ≥ 3×)
    RR_NORMAL_BREAKOUT = 2.5
    RR_TREND_PULLBACK  = 3.0 (bull trend)
    RR_DEFAULT         = 2.5
    
    ** NOTE: In replay.db era (2021-2025), this was 8.0 HARDCODED
       See AUDIT_002 finding: MAGNITUDE_SELECTION_FAILURE
           │
           ↓
Multi-agent debate (5-6 agents, threshold 6.5)
           │
           ↓
OrderManager → 5-6 candidates per cycle
```

---

## Current Production Thresholds (do NOT change)

| Constant | File | Value | Purpose |
|----------|------|-------|---------|
| `MIN_PREPARED_SCORE` | market_scanner.py:64 | 0.55 | Hard score floor after bucket scoring |
| `MAX_PREPARED_CANDIDATES` | market_scanner.py:65 | 120 | Hard cap on candidate count |
| `SECTOR_MAX_FRACTION` | market_scanner.py:69 | 0.20 | Max 20% per sector |
| `MIN_HISTORY_DAYS` | market_scanner.py:76 | 15 | Min OHLCV history |
| `MIN_ATR_PCT` | market_scanner.py:77 | 0.3 | Illiquid rejection |
| `MAX_ATR_PCT_GATE` | market_scanner.py:78 | 8.0 | Too-volatile rejection |
| `MIN_VOLUME_RATIO` | market_scanner.py:79 | 0.2 | Low-liquidity rejection |
| `BREAKOUT_PROXIMITY_PCT` | market_scanner.py:87 | 0.02 | BREAKOUT bucket threshold |
| `PULLBACK_PROXIMITY_PCT` | market_scanner.py:88 | 0.04 | PULLBACK bucket threshold |
| `OVERSOLD_RSI_MAX` | market_scanner.py:89 | 40.0 | OVERSOLD bucket RSI threshold |
| `OVERBOUGHT_RSI_MIN` | market_scanner.py:90 | 65.0 | OVERBOUGHT/SHORT threshold |
| `VOLUME_EXPANSION_MIN` | market_scanner.py:91 | 1.8 | Volume expansion bucket |
| `CONCENTRATION_PENALTY_START_DAYS` | market_scanner.py:83 | 3 | Concentration penalty start |
| `CONCENTRATION_PENALTY_PER_DAY` | market_scanner.py:84 | 0.05 | 5% per day penalty |
| `SCANNER_SHADOW_MODE` | market_scanner.py:60 | False (prod) | Shadow mode switch |
| `RR_STRONG_BREAKOUT` | equity_scanner_ai.py:73 | 4.0 | RR for strong breakout |
| `RR_NORMAL_BREAKOUT` | equity_scanner_ai.py:74 | 2.5 | RR for normal breakout |
| `RR_TREND_PULLBACK` | equity_scanner_ai.py:75 | 3.0 | RR for pullback |
| `RR_DEFAULT` | equity_scanner_ai.py:76 | 2.5 | Default RR |

---

## expected_move_pct — Source and Status

**File:** `opportunity_engine/equity_scanner_ai.py`, line 1421  
**Historical source:** `oios/data/sector_conviction_writer.py` (comment: `expected_move_pct = 8.0 per MAS Section 5`)  
**Status:** Formula computes ATR × RR ÷ price correctly in current code.  
**Historical status:** In replay.db era (2021–2025), ALL signal_births records show `expected_move_pct = 8.0` — hardcoded, not computed.  
**Confirmed by:** MOVER_DISCOVERY_AUDIT_002 leakage tests and magnitude analysis.

V3 must NOT treat this as a learned predictive feature for historical data.

---

## Confirmed Bottlenecks (from AUDIT_002)

| Bottleneck | Root Cause | File/Location | AUDIT_002 Evidence |
|------------|-----------|----------------|-------------------|
| G1: Pre-breakout accumulation not detected | Bucket scoring requires stock ALREADY in setup state | market_scanner.py `_classify_buckets()` | 81% Group A miss rate |
| G2: Volume expansion as hard gate | VOLUME_EXPANSION_MIN=1.8 hard threshold | market_scanner.py:91 | 92.8% of Group A had vol_ratio <1.8 |
| G3: Resistance proximity hard gate | BREAKOUT_PROXIMITY_PCT=0.02 (2%) | market_scanner.py:87 | 88.4% of Group A >2% from resistance |
| G4: No RSI 40–65 zone coverage | Only OVERSOLD (<40) and OVERBOUGHT (>65) have buckets | market_scanner.py:89-90 | 30.7% of Group A had RSI 45-55 |
| G5: No ATR% in scoring | atr_pct computed but not used in composite score | market_scanner.py `_process_symbol()` | atr_pct lift 1.21× in AUDIT_002 |
| G6: DOWN discovery minimal | Only HighRSIShort; no momentum-based DOWN | equity_scanner_ai.py `_identify_setup()` | All 57,037 signals LONG |
| G7: Sector pre-rotation not used at 16:45 | Sector leaders loaded only at intraday scan | equity_scanner_ai.py | Architecture gap |
| G8: MLS pipeline orphaned | MarketObserver/DNA not scheduled | library.json static | zero DNA contribution |
| G9: Magnitude hardcoded | expected_move_pct = 8.0 in historical data | signal_births | Confirmed by leakage test |

---

## Key Files

| File | Role |
|------|------|
| `opportunity_engine/market_scanner.py` | Phase D scanner — bucket scoring, candidate selection |
| `opportunity_engine/equity_scanner_ai.py` | Intraday scanner — setup identification, signal generation |
| `opportunity_engine/candidate_store.py` | CandidateStore — reads/writes prepared_candidates.json |
| `opportunity_engine/mop_rc001_observer.py` | MOP-RC-001 observational probe (append-only JSONL) |
| `data/nifty500_universe.json` | Universe — rebuilt weekly on Monday 08:30 |
| `data/prepared_candidates.json` | Scanner output — candidates for next trading day |
| `data/replay.db` | SQLite: ohlcv_daily, signal_births, universe_stocks |
| `models/trade_signal.py` | TradeSignal model — `expected_move_pct` field |
| `config.py` | System configuration constants |
