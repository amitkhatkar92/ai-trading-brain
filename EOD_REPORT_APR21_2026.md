# EOD Report — April 21, 2026
**AI Trading Brain | Paper Trading Mode | Capital: ₹10,000,000**

---

## 1. System Status

| Metric | Value |
|---|---|
| Market open | 09:15 IST |
| Market close | 15:30 IST |
| Final system state | HEALTHY ✅ |
| Container restarts today | ~10 (debugging session, last stable at 13:19) |
| Monitoring ticks (post-fix) | Every 5 min, 13:24 → 15:29 = 26 clean ticks |
| EOD learning | ⚠️ FAILED (see Issues below) |

### Restart Timeline
| Time | Reason |
|---|---|
| 09:05 | Pre-market catch-up start |
| 10:34 | Restart for scan retry fix |
| 10:42 | Second scan fix restart |
| 11:02 | Third scan fix restart |
| 11:07 | Fourth scan fix restart |
| 11:48 | Fifth scan fix restart |
| 12:54 | Live price wiring deployment |
| 13:01 | NIFTY → `^NSEI` routing fix |
| 13:16 | `seed_ltp` + Dhan options chain deployment |
| 13:19 | Dhan OptionsChain conversion fix (final stable) |

---

## 2. Market Context

| Indicator | Value |
|---|---|
| NIFTY spot (close) | ~24,581 |
| INDIA VIX | 17.6 (medium volatility) |
| Regime | `bull_trend` |
| PCR | 1.06 (slightly put-heavy → cautious optimism) |
| Market breadth | 61% |
| Global sentiment | Neutral (+0.009 score, 40% confidence) |
| Meta-strategy top pick | `Breakout_Volume` |
| MRPM dominant regime | `range_market` |

Note: Meta-learning model fell back to MRPM (regime-policy map) — k-NN predictor did not have sufficient fitted data to produce a direct prediction.

---

## 3. Deep Scan Execution

All 8 scheduled scan slots executed today (many via catch-up on restart).

| Slot | Scan Name | Execution Time(s) |
|---|---|---|
| 09:05 | `market_open_regime` | 12:05 (catch-up) |
| 09:10 | `first_opportunity_scan` | 09:10, 10:34, 10:42, 11:02, 11:07, 11:48, 11:56, 12:05 |
| 09:20 | `strategy_evaluation` | 11:49, 11:56, 12:05 |
| 10:30 | `mid_morning_scan` | 10:30, 10:34, 10:42, 11:02, 11:07, 11:49, 11:56, 12:05 |
| 11:30 | `mid_session_scan` | 11:49, 11:56, 12:05 |
| 13:00 | `afternoon_scan` | ~13:00+ |
| 14:00 | `early_afternoon_scan` | 14:00 (confirmed via cycle logs) |
| 15:00 | `closing_analysis` | ~15:00 |

Catch-up fires were triggered on each restart because the scan scheduler replays all missed slots since last execution. The scan retry mechanism (up to 3×) functioned correctly throughout.

---

## 4. Trade Activity

### Opportunity Density (ODM)

| Cycle | Signals | Approved | Density | Tier |
|---|---|---|---|---|
| 09:10 | 8 | 1 | 25.0% | NORMAL |
| 09:45 | 8 | 1 | 30.4% | NORMAL |
| 10:30 | 12 | 1 | 41.7% | NORMAL |
| 10:30 (2) | 28 | 1 | 33.3% | NORMAL |
| 10:42 | 12 | 1 | 20.6% / 17.6% | NORMAL |
| 11:02 | 16 | 1 | 32.4% / 45.7% | NORMAL |

Approval rate was consistently ~1/cycle (tight RiskGuard + capital allocation cap). Signal density was healthy across all cycles, averaging 30-40%.

### New Positions Opened Today

| Time | Symbol | Direction | Qty | Entry | SL | Target | Strategy |
|---|---|---|---|---|---|---|---|
| 09:10 | COALINDIA | BUY | 4,486 | 441.75 | 426.15 | ? | Mean_Reversion |
| 10:30 | TATASTEEL | SHORT | 11,727 | 213.18 | 220.38 | ? | Mean_Reversion |
| 11:49 | HDFCBANK | BUY | 3,096 | 807.25 | 779.05 | 877.75 | Mean_Reversion |

Note: A second HDFCBANK BUY (3096 → 3101 qty, entry 811.40, SL 783.20) appears in the 15:30 carry list with strategy `Momentum_Retest`. This may be a duplicate from the 11:49 execution re-evaluated at a higher price, or a separate signal. Investigate Apr 22.

### Positions Closed Today

**None.** All 7 positions carrying into Apr 22.

### Lifetime Realized P&L

| Symbol | Direction | P&L | Date | Event |
|---|---|---|---|---|
| BHARTIARTL | ? | −₹41,945 | Apr 20 | adaptive_exit |

---

## 5. EOD Carry State (15:30 close)

| Symbol | Direction | Qty | Entry | Close LTP | SL | R-Mult | Strategy | Notes |
|---|---|---|---|---|---|---|---|---|
| NIFTY | SELL | 43 | 864.91 | 24,581* | 1,729.82 | **−27.42R** ❌ | Bull_Call_Spread | *LTP shows SPOT not premium |
| ICICIBANK | BUY | 1,643 | 1,373.00 | 1,385.60 | 1,324.40 | +0.26R | Momentum_Retest | |
| COALINDIA | BUY | 4,490 | 441.40 | 443.05 | 425.80 | +0.11R | Mean_Reversion | Apr 20 carry |
| COALINDIA | BUY | 4,486 | 441.75 | 443.05 | 426.15 | +0.08R | Mean_Reversion | Opened today |
| TATASTEEL | SHORT | 11,727 | 213.18 | 211.60 | 220.38 | +0.22R | Mean_Reversion | |
| HDFCBANK | BUY | 3,096 | 807.25 | 812.00 | 779.05 | +0.17R | Mean_Reversion | |
| HDFCBANK | BUY | ~3,096 | 811.40 | 812.00 | 783.20 | +0.02R | Momentum_Retest | Investigate |

**NIFTY R-mult is wrong**: The carry state display used NIFTY spot (24,581) instead of the options synthetic premium (501.85). This is a display bug only — the monitoring `check_all()` correctly received 501.85 throughout the afternoon post fix. The R-mult and SL values shown for NIFTY in the carry log are meaningless.

### Estimated Unrealized P&L (corrected, at close)

Using actual options premium for NIFTY (501.85), market close prices for equities:

| Position | Calc | Est. P&L |
|---|---|---|
| NIFTY SELL 43 | (864.91 − 501.85) × 43 | **+₹15,611** |
| ICICIBANK BUY 1,643 | (1,385.6 − 1,373.00) × 1,643 | **+₹20,698** |
| COALINDIA BUY 4,490 | (443.05 − 441.40) × 4,490 | **+₹7,409** |
| COALINDIA BUY 4,486 | (443.05 − 441.75) × 4,486 | **+₹5,832** |
| TATASTEEL SHORT 11,727 | (213.18 − 211.60) × 11,727 | **+₹18,529** |
| HDFCBANK BUY 3,096 | (812.00 − 807.25) × 3,096 | **+₹14,706** |
| **Total Unrealized** | | **+₹82,785** |

All 6 core positions in positive territory at close. No stop-loss breaches.

---

## 6. Today's Key Findings & Learnings

### Finding 1: LTPGuard Entry-Anchoring Incompatible with Options Positions

**What happened:** LTPGuard initializes its baseline at `entry_price` and rejects any feed price that deviates more than 20% from that baseline. For an equity that entered at ₹100 and moves to ₹118, this is correct. For a NIFTY options position that entered at ₹864.91 and the premium legitimately decayed to ₹501.85 (−42%), LTPGuard permanently rejected the correct price on every tick.

**Consequence (pre-fix):** NIFTY P&L was frozen at entry. Exit logic (SL, trailing stop) was blind to actual premium level. The system was unknowingly managing a "ghost" position.

**Fix:** `seed_ltp(order_id, price)` method added to `TradeMonitor`. Called in `_do_monitor` immediately before `check_all()`, after computing the Black-Scholes synthetic premium. LTPGuard baseline slides to the current premium each tick — it now detects tick-to-tick spikes (true bad data) rather than entry-to-now drift (normal options theta decay).

**Generalization:** Any options sell position held for multiple days will face natural premium decay of 30-60%+. LTPGuard must always be seeded with the current model price for options, never anchored to entry.

**Files changed:** `trade_monitoring/trade_monitor.py`, `orchestrator/master_orchestrator.py`

---

### Finding 2: NIFTY Symbol Routing Bug (yfinance uses `^NSEI`)

**What happened:** `get_multiple_quotes("NIFTY")` was called with the bare symbol. yfinance requires `^NSEI` for the NIFTY index. The returned price dict had no `NIFTY` key, so the monitor's price dict was missing NIFTY entirely.

**Consequence:** From 09:10 → 13:01, monitoring ran with only 4 prices (ICICIBANK, TATASTEEL, COALINDIA, HDFCBANK). NIFTY was completely invisible to `check_all()`.

**Fix:** `_INDEX_YF_MAP = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "INDIAVIX": "^INDIAVIX"}` used for both the fetch list and the reverse-mapping dict. Confirmed at 13:06 tick: "Passing 5 live prices" including NIFTY.

**Files changed:** `orchestrator/master_orchestrator.py`

---

### Finding 3: Two OptionsChain Classes Co-exist — Conversion Layer Required

**What happened:** `dhan.get_options_chain()` returns `base_feed.OptionsChain`. This class uses `.spot_price` (not `.spot`), `.contracts[]` (not `.calls`/`.puts`), `.expiry` as a string (not `.dte` as an integer). `options_feed._fetch_live()` expected `options_feed.OptionsChain` format.

**Consequence:** Naive usage caused `AttributeError` on first Dhan options chain attempt. System fell through to Black-Scholes synthetic (which worked), but Dhan live chain was never used.

**Fix:** Full conversion block in `_fetch_live()` Path 1 — iterates `.contracts`, computes B-S greeks, builds proper `options_feed.OptionsChain`. Dhan chain is now Path 1 (primary); yfinance is Path 2 (fallback); Black-Scholes is Path 3 (synthetic always available).

**Status:** Dhan API appears to return empty `.contracts` in current subscription tier (OHLC blocked 451). System transparently falls to B-S synthetic. No error, no user impact.

**Files changed:** `data_feeds/options_feed.py`

---

### Finding 4: EOD Learning Task Failure — `mean requires at least one data point`

**What happened:** The `eod_learning` task at 15:35 failed with `statistics.mean requires at least one data point`. The LearningEngine processed 3 trades but the StrategyPerformanceTracker had 0.00R for all strategies (carry positions not yet closed — no realized R-multiples).

**Root cause:** `statistics.mean([])` is called somewhere in the performance aggregation path when all trades in the current day have 0.00R (open, not closed). The `mean()` call needs an `if not data: return 0.0` guard.

**Impact:** EOD learning did not complete. Strategy win rates and expectancy for Apr 21 were not persisted. This is a bug to fix for Apr 22.

**File to fix:** `learning_system/learning_engine.py` or `learning_system/strategy_performance_tracker.py` — find the bare `statistics.mean()` call and add empty-list guard.

---

### Finding 5: NIFTY Carry State Shows Spot Price, Not Options Premium

**What happened:** The 15:30 `[Orchestrator] CARRY` log for NIFTY showed `ltp=24,581.05` (spot price) and `r_mult=−27.42R`. The monitoring `check_all()` correctly received `501.85` throughout the afternoon.

**Root cause:** The carry display log reads LTP from `_last_good_ltp` via a different code path that doesn't apply the options synthetic — it falls back to the raw last-known price for NIFTY which, in the carry restoration path, is the spot price from `^NSEI`.

**Impact:** Display only — no trading decisions are made from the carry log. However, the NIFTY SL in the carry log (`sl=1,729.82`) is also incorrect. The actual stop-loss level needs to be verified against the options contract's stop parameters.

**Action for Apr 22:** Verify NIFTY SELL stop-loss is correctly set relative to options premium (501.85), not spot price. The carry display issue is cosmetic but the SL may need to be re-seeded.

---

## 7. System Health Summary

### Post-Fix Monitoring (13:24 → 15:29)

All 26 monitoring ticks from 13:24 to market close showed:
- 5/5 live prices accepted by `check_all()` every tick
- No LTPGuard rejections for NIFTY (seed_ltp working)
- DataGuard stale warnings for COALINDIA and HDFCBANK (yfinance data lag, cosmetic)
- No stop-losses triggered
- No VIX kill-switch activations (VIX 17.6, threshold 45)

### Full Cycle Performance

| Cycle | Total | Slowest Layer |
|---|---|---|
| #4 (13:19) | 550ms | MarketIntelligence (429ms) |
| #5 (13:19) | 582ms | MarketIntelligence (478ms) |
| #6 (14:00) | 4,737ms | GlobalIntelligence (2,366ms) |
| #7 (14:00) | 2,948ms | GlobalIntelligence (2,284ms) |

Cycles 4 and 5 reflect the optimized state (cache warm). Cycles 6 and 7 reflect a GlobalIntelligence cache miss at the 14:00 full cycle (global data re-fetch). All cycles within CRIT thresholds (12,000ms for GlobalIntelligence, 5,000ms default).

---

## 8. Action Items for April 22

| Priority | Action | File |
|---|---|---|
| 🔴 HIGH | Fix `statistics.mean([])` crash in EOD learning | `learning_system/learning_engine.py` |
| 🟡 MED | Verify NIFTY SELL SL is anchored to options premium (not spot) | `orchestrator/master_orchestrator.py` |
| 🟡 MED | Investigate duplicate HDFCBANK BUY (2 positions in carry at close) | `data/paper_trades.csv` |
| 🟢 LOW | Fix NIFTY carry display: use `seed_ltp` value instead of raw LTP | `orchestrator/master_orchestrator.py` |
| 🟢 LOW | Check Dhan `option_chain()` subscription tier for contract data | Dhan API |

---

## 9. Day Summary

**What worked:**
- 3 new positions opened cleanly by the strategy engine (all Mean_Reversion)
- Scan scheduler executed all 8 slots across multiple restarts
- Live price wiring: 5 symbols tracked every 5 min from 12:59 onward
- Post-fix monitoring: clean, no false rejections, no stop-out errors
- All 7 positions at day close are in positive unrealized territory (+₹82,785 estimated)

**What failed:**
- LTPGuard permanently blocked NIFTY options price for 4 hours (13:06 → 13:16, partially repaired; pre-fix window 09:10 → 13:01)
- EOD learning crashed (`mean` on empty list) — no strategy weights updated
- NIFTY symbol routing missing from 09:10 → 13:01 (1h51m blind)
- Multiple restarts during market hours due to active debugging

**What was learned:**
- Options positions require tick-to-tick LTPGuard seeding — entry-anchored baseline is fundamentally wrong for options
- yfinance index symbols must always use `^NSEI` / `^NSEBANK` mapping
- Two OptionsChain classes exist; always convert when crossing the `base_feed` → `options_feed` boundary
- EOD learning must handle empty trade lists gracefully (all-open days will always have this problem)
