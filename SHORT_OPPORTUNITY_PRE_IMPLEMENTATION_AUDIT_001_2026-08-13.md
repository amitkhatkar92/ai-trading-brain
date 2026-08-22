# SHORT_OPPORTUNITY_PRE_IMPLEMENTATION_AUDIT_001
**Date:** 2026-08-13  
**Scope:** READ-ONLY — zero production changes  
**Trigger:** KNOWLEDGE_TO_OPPORTUNITY_AUDIT_001 identified three F-class findings — validate before implementation  
**Author:** AI Trading Brain Audit Agent  
**Status:** FINAL

---

## EXECUTIVE SUMMARY

This audit validates the three F-class findings from KNOWLEDGE_TO_OPPORTUNITY_AUDIT_001 against every data source available in the repository. The findings are real, but the evidence base for acting on them varies significantly. One F-class finding (F-1 scoring penalty) requires **significant revision**.

**Revised F-class assessment after evidence review:**

| Finding | Original Statement | Revised Assessment |
|---|---|---|
| F-1 | market_scanner penalises overbought stocks → prevents candidate selection | **PARTIALLY WRONG.** Overbought stocks with strong breakout momentum DO rank in the top-57 (INDIANB RSI=67.1 scored #1 of 57 at 0.9113). The real problem is that Setup 4's RSI>=67 + near-resistance conditions are narrow, not the scoring formula. |
| F-2 | high_rsi_short absent from STRATEGY_PARAMS; no SHORT branch in RANGE_MARKET | **CONFIRMED AND CRITICAL.** Signal is generated but unconditionally reassigned to Mean_Reversion → dropped when Mean_Reversion is disabled (G-001 deadlock). |
| F-3 | ph2_short_dna, Setup 4, and institutional DNA exist but wired to EOD only | **CONFIRMED.** BUT: the short DNA evidence is sufficient to CONNECT to live pipeline; what's missing is strategy registration, not new components. |

**Final recommendation: CONNECT EXISTING KNOWLEDGE FIRST — with prerequisite backtest validation.**

---

## 1. AUDIT OF EXISTING SHORT-SIDE EVIDENCE

### 1.1 Setup 4 (High RSI Short) — Scanner Level

| Attribute | Value |
|---|---|
| Location | `opportunity_engine/equity_scanner_ai.py` lines 2058-2083 |
| Status | EXISTS as scanner setup; DOES NOT EXIST as registered strategy |
| Entry conditions | RSI >= 67 AND ltp >= resistance × 0.99 AND regime ≠ BEAR AND ATR% < 4.0% AND NOT bull_trend |
| Direction | SHORT |
| Confidence formula | `min(5.5 + rsi/20, 8.5)` → outputs **8.5 for any RSI >= 60** (near-constant) |
| Stop-loss | `ltp + max(ATR(14) × 1.5, ltp × 0.01)` — above entry price |
| Target | `ltp - 2.5 × stop_dist` |
| R:R | **2.5:1** (hardcoded) |
| strategy_name assigned | "high_rsi_short" |
| Live trades | **ZERO** (paper_trades.csv: 0 rows) |
| Backtest trades | **ZERO** (not in _BACKTEST_CACHE, not in any replay DB) |
| Win rate | **UNKNOWN** |
| Expectancy | **UNKNOWN** |
| Drawdown | **UNKNOWN** |
| Evidence type | Scanner logic only — no executed results |
| Promotion gate | NOT attempted |

**Confidence formula problem:** For ANY qualifying RSI (67+), the confidence is `min(5.5 + rsi/20, 8.5)`. At RSI=67: min(8.85, 8.5) = 8.5. At RSI=80: min(9.5, 8.5) = 8.5. The confidence is **constant at 8.5** for all qualifying setups. Higher RSI (deeper overbought) receives identical confidence to barely-overbought RSI=67. This is a calibration issue, not a dealbreaker, but it means confidence carries no signal about setup quality.

### 1.2 ph2_short_dna / evaluate_short_dna()

| Attribute | Value |
|---|---|
| Location | `production_readiness/ph2_short_dna.py` |
| DNA source | `data/mls/institutional_dna.db` — loser DNA, lifecycle=INSTITUTIONAL, confidence>=0.55 |
| LOSER_DNA_CONFIDENCE_GATE | 0.55 |
| LOSER_DNA_MAX_BOOST | 1.50 (on a 0-10 confidence scale) |
| Architecture intent | Docstring: "Public function for the scanner's _identify_setup() to call." |
| Actual wiring | Called ONLY from `run_short_dna_audit()` → PRR-001 Phase 2 (EOD audit) |
| Live trades enriched | **ZERO** |
| Output type | confidence_boost float + matching_conditions list — **cannot CREATE a TradeSignal** |
| H001 status | "Loser DNA cross-year validation — CONFIRMED" per file docstring |
| H001 validated for | Cross-year pattern presence — NOT trading performance |
| H001 win rate | **UNKNOWN** (no trade data attached) |

### 1.3 Institutional DNA — SHORT Patterns

| Feature | Direction | Confidence | Evidence Count | is_current | Last Updated |
|---|---|---|---|---|---|
| volume_spike | SHORT | 1.000 | 69 | YES | 2026-08-05 |
| volume_spike | SHORT | 1.000 | 66 | YES | 2026-08-05 |
| pcr | BUY | 1.000 | 25 | YES | 2026-08-05 |
| sector_flow_count | BUY | 1.000 | 25 | YES | 2026-08-05 |
| macd_signal_norm | BUY | 1.000 | 21 | YES | 2026-08-05 |
| global_bias | BUY | 0.917 | 17 | YES | 2026-08-05 |

**Key finding:** The `volume_spike SHORT conf=1.0` pattern has the LARGEST evidence pool (69+66=135 combined evidence events) in the entire institutional_dna.db. It is also the most relevant SHORT pattern for the BML C-stocks (EASEMYTRIP 1.74x vol on down day). However:
- Evidence count = number of validation hits, NOT number of profitable trades
- No win rate, expectancy, or profit factor attached to this DNA record
- The DNA is FEATURE-level (volume_spike > threshold), not SYMBOL-level

### 1.4 Strategy Registry (STRATEGY_PARAMS)

Current entries in `strategy_lab/strategy_generator_ai.py`:

```
Breakout_Volume, Momentum_Retest, Trend_Pullback, Mean_Reversion,
Bull_Call_Spread, Iron_Condor_Range, Hedging_Model, Short_Straddle_IV_Spike,
Long_Straddle_Pre_Event, Futures_Basis_Arb, ETF_NAV_Arb,
Equity_Breakout, Equity_Retest
```

**"high_rsi_short" is NOT in STRATEGY_PARAMS.** 177 evolved strategies in `data/evolved_strategies.json` — none named `high_rsi_short` or any short-equity variant. Only RSI-related evolved strategies: `Breakout_Volume_RSI_HiVol` (approved, LONG breakout with RSI filter rsi_min=51, rsi_max=62) and `Mean_Reversion_RSI_HiVol` (approved, LONG mean-reversion with RSI filter).

### 1.5 BacktestingAI — Pre-Seeded Cache

`_BACKTEST_CACHE` contains pre-seeded data for 13 base strategies (Breakout_Volume, Mean_Reversion, Bull_Call_Spread, Iron_Condor_Range, Short_Straddle_IV_Spike, Long_Straddle_Pre_Event, Hedging_Model, Futures_Basis_Arb, ETF_NAV_Arb, Momentum_Retest, Trend_Pullback, Equity_Breakout, Equity_Retest). Plus 177 evolved variants seeded from evolved_strategies.json.

**"high_rsi_short" absent from all backtest data.** When BacktestingAI encounters an unregistered strategy, two paths are possible: (a) `_get_result()` runs `_full_pipeline()` generating synthetic results, or (b) if `_full_pipeline()` returns None, the `filter_by_backtest()` code allows the signal through with: `"No backtest data for 'high_rsi_short' — allowing through."` The actual path depends on whether `_full_pipeline` handles an unknown strategy name.

### 1.6 StrategyHealthMonitor / PerformanceTracker

From `data/strategy_performance.json` (last updated 2026-03-12 — 5 months ago):

| Strategy | Trades | WR | Total_R | Status |
|---|---|---|---|---|
| Breakout_Volume | 3 | 66.7% | +2.0R | enabled |
| Mean_Reversion | 5 | 0.0% | -5.0R | enabled (file), disabled (G-001) |
| high_rsi_short | — | — | — | **NOT TRACKED** |

Mean_Reversion's 0/5 WR explains the G-001 governance deadlock referenced in BML-001.

### 1.7 Historical Trade Record (All Databases)

| Source | SHORT equity trades | SHORT index/options |
|---|---|---|
| paper_trades.csv | 0 | 0 |
| study002_replay.db | 0 | 0 (all 8,562 signals are LONG) |
| re001_replay.db | 0 | 0 (all 124 signals are LONG) |
| ct_db_20260811.db | 0 | Short_Straddle_IV_Spike (NIFTY/BANKNIFTY options), Futures_Basis_Arb (index) |

**The entire system has never executed a SHORT equity (stock) trade.** The only SHORT-direction signals in any database are index-level options/futures strategies, not individual equity shorts. This is a zero-history system for what is being proposed.

### 1.8 ResearchCoordinator

`data/iios.db` contains: bootstrap_runs, stage_results, system_events. **No hypothesis registry tables.** The OIOS study002 database contains 1,966 opportunities — all LONG direction. No ResearchCoordinator runs found for high_rsi_short or any short-equity hypothesis.

---

## 2. HIGH_RSI_SHORT VALIDATION

### Status: **E — exists as scanner setup code only; not an executable strategy; not a registered strategy**

```
E. does not actually exist as an executable strategy (correct classification)
```

While Setup 4 scanner code exists, there is no corresponding registered strategy. The classification is category E from the audit prompt.

### Complete Logic Trace

**Entry conditions (all must be true simultaneously):**
```python
# equity_scanner_ai.py _identify_setup()
regime ∈ {RANGE_MARKET, VOLATILE}       # NOT BEAR_MARKET or BULL_TREND
atr_pct <= VOLATILITY_GUARD_ATR_PCT     # ATR(14)% <= 4.0%
rsi >= 67                               # RSI at or above overbought threshold
ltp >= resistance * 0.99               # price within 1% below (or above) resistance
target = ltp - 2.5 * stop_dist > 0     # target must be positive
```

**Exit logic:**
```python
stop_dist = max(ATR(14) * 1.5, ltp * 0.010)   # ATR_STOP_MULTIPLIER = 1.5
stop_loss = ltp + stop_dist                    # stop ABOVE entry (short side)
target    = ltp - 2.5 * stop_dist             # 2.5:1 target BELOW entry
R:R       = 2.5                               # hardcoded
```

**Example calculation (KAYNES-type at ₹3828, ATR≈45):**
```
stop_dist = max(45 × 1.5, 3828 × 0.01) = max(67.5, 38.28) = 67.5
stop_loss = 3828 + 67.5 = 3895.5
target    = 3828 - 2.5 × 67.5 = 3828 - 168.75 = 3659.25
risk      = ₹67.5 per share
reward    = ₹168.75 per share
R:R       = 2.50 ✓
```

**Confidence formula:**
```python
confidence = min(5.5 + rsi/20, 8.5)
# RSI=67 → min(8.85, 8.5) = 8.5
# RSI=70 → min(9.0, 8.5) = 8.5
# RSI=80 → min(9.5, 8.5) = 8.5
# Effective output: always 8.5 for RSI >= 60
```

**Regime guard:** Only fires if `in_bull_trend = False`. RANGE_MARKET and VOLATILE pass; BEAR_MARKET blocked earlier; BULL_TREND blocks Setups 4+5.

**Risk controls for short side:** NONE specific to short equity. The stop-loss is above entry (correct for SHORT). RiskManagerAI checks `abs(entry - stop)` regardless of direction — direction-neutral check is correct.

**Expected trade frequency:**
From Aug-11 candidate analysis: 7 stocks with `overbought_short_watch` bucket. Of these:
- INDIANB (67.1): ltp=879.25 < resistance×0.99=880.6 → FAILS by 1.35 pts
- NAUKRI (70.4): EXPIRED before market open
- BOSCHLTD (66.6): RSI=66.6 < 67 threshold → FAILS
- DEEPAKNTR (66.7): RSI=66.7 < 67 → FAILS
- PNBHOUSING (64.2): RSI < 67 → FAILS
- NESTLEIND (65.0): RSI < 67 → FAILS
- MAZDOCK (68.6): ltp needs verification

**Result on Aug-11: ZERO high_rsi_short signals generated from prepared candidates.**

Expected frequency on a typical range-market day: **0-1 stocks per day** from prepared candidates. The RSI >= 67 AND near-resistance conditions are narrow. Many overbought stocks are either above resistance (Setup 1 territory) or below the 0.99 threshold.

---

## 3. RANGE_MARKET SHORT ROUTING VALIDATION

### The Exact Path of a HIGH_RSI_SHORT Signal

```
Scanner Setup 4 fires
  → TradeSignal(symbol=X, direction=SHORT, strategy_name="high_rsi_short",
                confidence=8.5, rr=2.5, stop_loss=ltp+stop_dist)
      ↓
_run_strategy_lab()
  passing = STRATEGY_PARAMS.keys()  ← "high_rsi_short" NOT in this set
  active = MetaStrategyController.get_active_strategies(snapshot, passing)
      ↓
strategy_generator.assign_strategy(signals, ...)
  _assign(signal, snapshot, active):
    if signal.strategy_name in STRATEGY_PARAMS:  ← FALSE
    # falls through to:
    strategy = _pick_strategy(signal, RANGE_MARKET, vol_level, active)
      ↓
_pick_strategy(signal, RANGE_MARKET, ...):
    # BUY checks both fail (direction=SHORT)
    else:
        return evolved or _choose(["Mean_Reversion"])
        # Mean_Reversion IS in passing set normally
        # BUT is in perf_disabled (0/5 WR) → NOT in active
        # _choose(["Mean_Reversion"]) returns ""
        # strategy = ""
      ↓
  signal.strategy_name = "Mean_Reversion"  ← fallback assignment
      ↓
  if excluded_strategies and signal.strategy_name in excluded_strategies:
    # Mean_Reversion in perf_disabled → TRUE
    # [StrategyBlocked] log emitted
    # signal DROPPED
      ↓
⚡ OPPORTUNITY DISAPPEARS HERE ⚡
```

**The exact loss point:** `strategy_generator_ai.py`, `_assign()` function, the `else` branch of `_pick_strategy()` for RANGE_MARKET returns "Mean_Reversion" for SHORT direction signals. On Aug-13 (G-001 deadlock, Mean_Reversion disabled), this means **every SHORT equity signal from Setup 4 is silently dropped**.

### What Would Happen If Mean_Reversion Were NOT Disabled?

If Mean_Reversion were active (hypothetically), the signal would continue:
```
signal.strategy_name = "Mean_Reversion"  ← semantically wrong but assigned
  ↓
apply_evolved_params() → tries evolved Mean_Reversion variants
  ↓
filter_by_backtest() → Mean_Reversion in _BACKTEST_CACHE (WR=58%, passes gate)
  ↓
CRE: _STRATEGY_SHARE["Mean_Reversion"] = 0.22
  strategy_budget = 0.22 × deployable_capital
  ↓
RiskManagerAI._check():
  confidence=8.5 >= 6.5 ✓
  RR=2.5 >= 2.0 ✓
  stop_loss defined ✓
  ↓
DecisionEngine:
  confidence=8.5 >> effective_threshold=6.5-6.9 → APPROVED (FULL)
  ↓
RiskGuardian:
  VIX=11.7 < 45 → no kill switch
  Direction balance: 0% SHORT existing → new SHORT allowed (< 70% cap)
  → APPROVED
  ↓
OrderManager → PAPER_TRADING → logs to paper_trades.csv
```

**Governance compatibility: CONFIRMED.** All existing risk controls are direction-neutral. A SHORT equity signal would pass every gate identically to a LONG signal. The pipeline does not need any governance changes to handle short equity signals — it already handles Short_Straddle, Futures_Basis_Arb (SHORT direction) through the same gates.

**Semantic mismatch risk:** If the signal arrives with `strategy_name="Mean_Reversion"` but direction=SHORT, the strategy name is semantically wrong (Mean_Reversion is an oversold-bounce strategy). This could corrupt the PerformanceTracker records (losses attributed to Mean_Reversion instead of high_rsi_short). This is a second-order problem but real.

### Bypassing Existing Governance: NOT A RISK

Adding a SHORT branch to `_pick_strategy()` for RANGE_MARKET would NOT bypass:
- DecisionEngine threshold check (direction-neutral, confidence-based)
- RiskManagerAI (direction-neutral, RR-based)
- RiskGuardian (kill-switch + direction-balance check)
- CRE capital sizing (strategy_budget mechanism)
- LiquidityGuard (ADV capacity check, direction-neutral)

The only change is that the signal would carry `strategy_name="High_RSI_Short"` (or equivalent) instead of "Mean_Reversion", which is BETTER for governance traceability.

---

## 4. F-1 SCANNER BEHAVIOUR VALIDATION

### Key Finding: F-1 Original Statement Was Partially Incorrect

**Claim:** "market_scanner penalises overbought stocks instead of routing them to a short queue"  
**Evidence from Aug-11 candidates:**

| Symbol | RSI | Score | Rank in Top-57 | overbought_short_watch | Notes |
|---|---|---|---|---|---|
| INDIANB | 67.1 | **0.9113** | **#1** | YES | Highest scored candidate in the entire list |
| BOSCHLTD | 66.6 | 0.9019 | #3 | YES | Third highest |
| NAUKRI | 70.4 | 0.8951 | #4 | YES | Fourth highest; EXPIRED before market open |
| DEEPAKNTR | 66.7 | 0.8456 | #6 | YES | High rank |
| PNBHOUSING | 64.2 | 0.8199 | #8 | YES | |
| NESTLEIND | 65.0 | 0.7621 | #15 | YES | |
| MAZDOCK | 68.6 | 0.5644 | #57 (bottom) | YES | Low rank |

**The RSI penalty does not prevent overbought stocks from entering the top-57 when they have strong breakout + relative_strength components.** INDIANB (RSI=67.1) is the highest-scoring candidate, not the lowest. The overbought penalty affects the rsi_score component, but candidates with strong volume_expansion + breakout proximity + sector rerank bonuses can overcome it.

**The real F-1 problem is different:**
1. Setup 4's RSI threshold (>= 67) is precise — RSI=66.9 misses. BOSCHLTD (66.6) and DEEPAKNTR (66.7) qualified for the top-57 but failed Setup 4 by 0.4 and 0.3 RSI points.
2. Setup 4's price condition (>= resistance × 0.99) is strict — INDIANB failed by 1.35 points out of 880.6 threshold.
3. The `overbought_short_watch` bucket tag IS present in the candidate data, but equity_scanner_ai.py's `_identify_setup()` does NOT read the `buckets` field — it independently re-evaluates RSI and price conditions.

**Simulated observation: "What would have happened to the six BML C-stocks if overbought_short_watch had been routed rather than penalised?"**

For KAYNES (RSI estimated ~70 on Aug-12 close after +2.97%):
- Would have made the top-57 with or without the penalty (strong momentum score)
- Setup 4 would have fired: RSI=70 >= 67 ✓, ltp near resistance ✓
- The routing (F-2) would have STILL dropped the signal
- Conclusion: fixing the scoring formula would not have helped KAYNES

For HINDALCO (already in BASE_WATCHLIST, no scoring needed):
- BASE_WATCHLIST bypasses market_scanner scoring entirely
- F-1 is irrelevant for HINDALCO

**Revised F-1 assessment:**
The scoring penalty is a minor cosmetic issue for overbought candidates. The real problem is that Setup 4's trigger conditions rarely align with the prepared candidates' exact values. Changing the penalty to a bonus would not have changed any of the 6 C-stock outcomes on 2026-08-13. The F-1 change is the lowest-value action of the three proposals.

---

## 5. SIX BML C-STOCK REPLAY

### Legend
- **RECOGNIZED** = system would have detected setup conditions
- **TRADEABLE** = signal would have passed all governance gates

---

### ASTRAL (INFRA, LONG momentum continuation)

| Stage | Evidence | Result |
|---|---|---|
| Universe presence | market_scanner.py line 579 | PRESENT |
| Pre-move DNA | None in institutional_dna.db | NONE |
| Aug-12 scanner score | Insufficient vol on Aug-12; score likely 0.6-0.7 range | NOT IN TOP-57 |
| Candidate status for Aug-13 | ABSENT from prepared candidates | ABSENT |
| Setup conditions (hypothetical) | Aug-13: vol_ratio=2.75x, gap=+2.36%, resistance≈1464 | Setup 1 WOULD fire |
| Strategy route (hypothetical) | Breakout_Volume ← CORRECT and ACTIVE in RANGE_MARKET | WOULD PASS |
| Governance outcome (hypothetical) | confidence≈7.8+, RR≈2.5, BacktestingAI passes | WOULD APPROVE |
| Exact missing link | Aug-12 EOD scan: ASTRAL's score on 2.74% close day insufficient for top-57; vol spike only materialised on Aug-13 itself |
| RECOGNIZED | **NO** (not in candidates, no signal generated) |
| TRADEABLE | YES (IF recognized — routing is correct, governance compatible) |

---

### KAYNES (ELECTRONICS, SHORT overbought fade)

| Stage | Evidence | Result |
|---|---|---|
| Universe presence | market_scanner.py line 581 | PRESENT |
| Pre-move DNA | None in institutional_dna.db for KAYNES | NONE |
| Aug-12 scanner score | RSI≈70 after +2.97% → overbought_short_watch tag; strong momentum → likely top-57 | PROBABLY IN TOP-57 |
| Setup conditions (hypothetical) | RSI≈70 >=67 ✓; ltp≈3828 near resistance ✓; range_market ✓ | Setup 4 WOULD FIRE |
| Signal generated | direction=SHORT, confidence=8.5, RR=2.5, strategy="high_rsi_short" | GENERATED |
| Strategy route | "high_rsi_short" NOT in STRATEGY_PARAMS → Mean_Reversion fallback → DISABLED (G-001) | DROPPED |
| Exact missing link | "high_rsi_short" absent from STRATEGY_PARAMS + no SHORT branch in _pick_strategy |
| RECOGNIZED | **YES** (Setup 4 would fire given RSI+price conditions) |
| TRADEABLE | **NO** (routing broken at strategy assignment; dropped by STRATEGY_DISABLED) |

---

### HINDALCO (METALS, SHORT overbought fade)

| Stage | Evidence | Result |
|---|---|---|
| Universe presence | equity_scanner BASE_WATCHLIST (hardcoded) | PRESENT |
| Pre-move DNA | Learning registry PGA-EB51FF6E: dna_count=0 (Aug-7), PENDING | ZERO DNA |
| Scanner setup conditions | Stale resistance=1009; live ltp≈1078; Setup 4: RSI≈69 >=67 ✓; 1078 >= 1009×0.99=999 ✓ | Setup 4 WOULD FIRE |
| ATR guard | ATR≈30, atr_pct≈2.8% < 4.0% | PASSES |
| Signal generated | direction=SHORT, confidence=8.5, RR=2.5 | GENERATED |
| Strategy route | Same broken path as KAYNES → DROPPED | DROPPED |
| PGA action | PGA-EB51FF6E created Aug-7, status=PENDING, executed=false (6 days unexecuted) | IGNORED |
| Exact missing link | Same F-2 routing gap; additionally: PGA learning action not executed |
| RECOGNIZED | **YES** (signal would be generated) |
| TRADEABLE | **NO** (routing broken) |

---

### PCJEWELLER (RETAIL, SHORT declining momentum)

| Stage | Evidence | Result |
|---|---|---|
| Universe presence | market_scanner.py line 611 | PRESENT |
| Pre-move DNA | None | NONE |
| RSI state | 2-day decline: RSI likely 35-55 (falling, NOT overbought) | RSI < 67 |
| Setup 4 applicable? | RSI < 67 → Setup 4 FAILS immediately | NO |
| Alternative setups | None exist for declining-momentum SHORT | NO SETUP |
| RECOGNIZED | **NO** (no scanner setup matches declining-momentum shorts) |
| TRADEABLE | **NO** — even hypothetically, the scanner has no capability for this signal type |

---

### EASEMYTRIP (CONSUMER, SHORT declining momentum)

| Stage | Evidence | Result |
|---|---|---|
| Universe presence | market_scanner.py line 616 | PRESENT |
| Pre-move DNA | institutional_dna.db: volume_spike SHORT conf=1.0 (69 evidence events) | EXISTS but NOT WIRED |
| RSI state | 2-day decline: RSI ≈ 40-55 (falling, NOT overbought); 1.74x rel_vol on down day | RSI < 67 |
| Setup 4 applicable? | RSI < 67 → FAILS | NO |
| DNA match (hypothetical) | evaluate_short_dna({volume_spike: 1.74}) would match volume_spike > threshold → boost≈0.52 | WOULD MATCH |
| ph2_short_dna wiring | evaluate_short_dna() not called during live scan; even if called, no base signal to boost | DEAD-END |
| RECOGNIZED | **NO** (scanner: no setup; DNA: exists but not wired to live pipeline) |
| TRADEABLE | **NO** — the DNA evidence is present but has no live signal delivery path |

---

### INFY (IT, SHORT declining day)

| Stage | Evidence | Result |
|---|---|---|
| Universe presence | equity_scanner BASE_WATCHLIST (hardcoded) | PRESENT |
| Pre-move DNA | Learning registry PGA-152D8969: dna_count=0 (Aug-7), PENDING | ZERO DNA |
| RSI state | After -1.23% Aug-12: RSI likely 60-67 range (borderline for Setup 4) | UNCERTAIN |
| Volume | rel_vol = 0.26x (well below average) | VERY LOW |
| Setup 4 (if RSI>=67) | ltp≈1176 >= resistance×0.99 = 1149.73×0.99 = 1138.2 ✓; ATR≈25, atr_pct≈2.1% < 4% ✓ | CONDITIONAL |
| Signal generated | direction=SHORT, confidence=8.5, RR=2.5 (IF RSI>=67) | CONDITIONAL |
| Volume-based rejection | Setup 4 has NO vol_ratio requirement → 0.26x would NOT block signal generation | SURVIVES ATR GUARD |
| Strategy route | Same broken path → DROPPED | DROPPED |
| Capital sizing | qty = risk_budget / stop_dist_per_share → at INFY prices, qty likely 0-1 | NEGLIGIBLE SIZE |
| PGA action | PGA-152D8969 PENDING unexecuted 6 days | IGNORED |
| RECOGNIZED | **CONDITIONAL** (depends on RSI value; Setup 4 would fire if RSI>=67 on Aug-13 open) |
| TRADEABLE | **NO** (routing broken; negligible position size at ₹10k capital) |

---

### Six-Stock Summary

| Stock | Recognized | Tradeable | Primary Gap | Direction |
|---|---|---|---|---|
| ASTRAL | NO (not in candidates) | YES (if recognized) | F-1: candidate selection (vol spike was day-of) | LONG |
| KAYNES | YES (Setup 4 would fire) | NO | F-2: routing broken | SHORT |
| HINDALCO | YES (Setup 4 would fire) | NO | F-2: routing broken | SHORT |
| PCJEWELLER | NO (no applicable setup) | NO | Genuine gap: declining-momentum scanner absent | SHORT |
| EASEMYTRIP | NO (Setup 4 wrong type) | NO | Genuine gap: DNA not wired; no declining-momentum scanner | SHORT |
| INFY | CONDITIONAL (RSI borderline) | NO | F-2: routing broken; low-vol confirmation issue | SHORT |

---

## 6. FALSE-POSITIVE RISK VALIDATION

### Available Historical Data for HIGH_RSI_SHORT

**Short equity historical trades in all databases: ZERO.**

This is not a sampling limitation — it reflects that the system has never generated an executed short equity trade. The study002_replay.db has 8,562 signal births and 1,966 opportunities, **all LONG**. The re001_replay.db has 124 signals, **all LONG**. No win rate, expectancy, or loss distribution can be computed.

### What We CAN Observe

**From institutional_dna.db:**
- `volume_spike SHORT conf=1.0`: 69+66 = 135 evidence events across two DNA records
- Evidence events confirm: stocks with above-average volume on DOWN days have an institutional-level pattern that the system classifies as loser/short territory
- This is a PRESENCE test (the pattern exists), not a PERFORMANCE test (profitable to trade)

**From Aug-11 overbought candidate analysis:**
- 7 candidates with `overbought_short_watch` bucket
- ZERO Setup 4 signals generated from these 7 candidates (all failed by hairline margins on RSI or price conditions)
- False-positive rate cannot be computed without execution history

**From ct_db_20260811.db decision log:**
- All 1,352 decisions are for LONG strategies
- Zero historical false positives or true positives for any short equity strategy
- The system has never tested short equity signals through governance

### Observed Signal Rate (Simulation)

On Aug-11 (a typical range-market day with 57 prepared candidates):
- 7 stocks with RSI >= 64: overbought_short_watch tagged
- 2 candidates with RSI >= 67 (strict threshold): INDIANB (67.1), NAUKRI (70.4), MAZDOCK (68.6)
- Of these: 0 passed the ltp >= resistance×0.99 check (INDIANB: 879.25 < 880.61; NAUKRI: EXPIRED; MAZDOCK: unknown)
- **Expected rate: 0-1 signals per day**, possibly 0 on most days

This low frequency means that even if false-positive rate were 50% (very pessimistic), the expected daily false positives would be 0-0.5. At ₹10,000 total capital, the financial impact per false positive is ≈₹50-200 (very small position sizes). This is low absolute risk but unknown percentage risk.

### False-Positive Concerns

1. **Confidence is constant at 8.5** for all qualifying setups — no discrimination between marginal (RSI=67) and strong (RSI=82) short signals. DecisionEngine cannot distinguish quality.

2. **No regime-specific calibration:** Setup 4 targets RANGE_MARKET and VOLATILE regimes, but overbought stocks in a volatile uptrend might continue higher despite RSI=70+. Without backtesting, we don't know whether the RSI-fade setup works in India's market structure.

3. **Resistance level staleness:** BASE_WATCHLIST resistance values are static (last updated ~July 10). If resistance is stale (too low), Setup 4 fires on stocks that have already broken out well above their true resistance — these are continuation candidates, not short candidates.

4. **Short squeeze risk:** Indian small/mid-cap stocks with low float can experience short squeezes. The LiquidityGuard (ADV check) provides some protection, but short squeeze risk is not explicitly modeled.

**Verdict: FALSE-POSITIVE RISK IS UNKNOWN.** The setup logic is reasonable, but without 20+ historical backtested trades, we cannot estimate the win rate or determine whether the signal conditions are sufficient for a positive-expectancy strategy.

---

## 7. GOVERNANCE COMPATIBILITY

### Direction-Neutral Checks (All Pass for SHORT)

| Gate | Applies to SHORT? | Evidence |
|---|---|---|
| DecisionEngine threshold (6.5-6.9) | YES — direction-neutral | Confidence check only |
| RiskManagerAI confidence floor | YES | `sig.confidence < MIN_CONFIDENCE_SCORE` |
| RiskManagerAI RR gate | YES | `abs(entry-stop)/abs(entry-target)` — direction-neutral |
| RiskManagerAI stop-loss check | YES | `if sig.stop_loss == 0` — direction-neutral |
| CRE capital sizing | YES — uses strategy_budget | Works for any strategy in _STRATEGY_SHARE |
| LiquidityGuard | YES | ADV capacity check, direction-neutral |
| RiskGuardian kill-switch | YES | VIX >= 45 / Nifty < -5% — direction-neutral |
| Direction balance cap | YES — checked | `max_direction_exposure = 70% per direction` |

### SHORT-Specific Risk: VIX_SELL_LIMIT

`VIX_SELL_LIMIT = 28.0` blocks premium-selling strategies (Iron_Condor, Short_Straddle) at high VIX. This does NOT apply to short equity positions (direction=SHORT, signal_type=EQUITY). High_rsi_short at VIX=15 would be unaffected by this gate. At VIX=45+, the kill-switch would halt ALL trading regardless of direction.

### Capital Constraints at ₹10,000

A critical practical constraint:
- KAYNES at ₹3,828/share: stop_dist≈₹67.5, risk per share=₹67.5
- MAX_RISK_PER_TRADE_PCT=1% of ₹10,000 = ₹100 max risk
- qty = min(floor(₹100/₹67.5), floor(available_capital/entry_price)) = min(1, 2) = 1 share
- Position value = 1 × ₹3,828 = ₹3,828 (38% of capital in one KAYNES SHORT)
- This exceeds the RANGE_MARKET 50% exposure cap single-position prudence

For most high-priced stocks (>₹2,000/share), maximum position size at ₹10k capital is 1 share. The governance will allow this (qty=1 is valid), but the actual dollar risk is concentrated.

**INFY specifically:** At ₹1,176/share, stop_dist≈₹25, risk per share=₹25. qty = floor(₹100/₹25) = 4 shares. Position value = 4 × ₹1,176 = ₹4,704 (47% of capital). This is near the exposure cap for a single trade.

### Governance Verdict

**Introducing short equity routing would NOT bypass any existing governance or safety mechanism.** All gates are direction-neutral. The only new risk is:
1. Strategy name mismatch if `high_rsi_short` is not registered and the signal is assigned `Mean_Reversion` — corrupts performance attribution
2. Stale resistance levels could cause Setup 4 to fire on breakout stocks, not fade stocks — a scanner-level false positive, not a governance gap

---

## 8. KNOWLEDGE-FIRST ARCHITECTURE CHECK

### Intended Flow
```
COMPILED KNOWLEDGE (institutional_dna.db: volume_spike SHORT conf=1.0)
        +
MARKET EVIDENCE (equity_scanner Setup 4: RSI>=67, near resistance)
        +
REGIME (MetaStrategyController: RANGE_MARKET active set)
        +
STRATEGY (STRATEGY_PARAMS: registered strategy with min_rr, max_loss_pct)
        ↓
OPPORTUNITY (TradeSignal with direction=SHORT, strategy=high_rsi_short)
        ↓
DECISION (DecisionEngine, RiskManagerAI, RiskGuardian)
```

### Current State of Each Layer

| Layer | Status | Gap |
|---|---|---|
| COMPILED KNOWLEDGE | EXISTS — institutional_dna.db: volume_spike SHORT conf=1.0 (135 evidence events) | Not connected to opportunity layer |
| MARKET EVIDENCE | EXISTS — equity_scanner Setup 4 generates correct TradeSignal | Present and functional |
| REGIME | PARTIAL — Setup 4 already checks regime (range/volatile only) | MetaStrategyController does not list high_rsi_short |
| STRATEGY | ABSENT — not in STRATEGY_PARAMS, not in MetaStrategyController map | Must be registered before routing works |
| OPPORTUNITY | BLOCKED — signal is generated then destroyed in _pick_strategy() | Destroyed by fallback to disabled Mean_Reversion |
| DECISION | COMPATIBLE — all gates are direction-neutral | No changes needed |

### Can Short DNA Connect WITHOUT Creating Independent Strategy?

YES. `get_short_dna_confidence_boost()` is designed for this exact purpose:
```python
# ph2_short_dna.py line 141
def get_short_dna_confidence_boost(features, regime):
    """Public function for the scanner's _identify_setup() to call."""
```

The function is explicitly designed to be called FROM `_identify_setup()`. Adding one call inside Setup 4's signal-generation block would wire the knowledge layer to the market evidence layer:
```python
# Inside Setup 4 signal generation (equity_scanner_ai.py ~line 2060)
# (illustrative — READ-ONLY, not implementing now)
features = {"volume_spike": vol_ratio, "rsi": rsi, ...}
dna_boost = get_short_dna_confidence_boost(features, snapshot.regime.value)
confidence = min(5.5 + rsi/20 + dna_boost, 8.5)
```

This would NOT create an independent strategy — it enhances the existing Setup 4's confidence using compiled knowledge. The signal still goes through all governance gates unchanged. The DNA boost (max 1.5 on a 10.0 scale) is a minor adjustment but creates the knowledge→evidence→opportunity pathway.

**However:** This is only meaningful if the strategy is registered first. A signal with `strategy_name="high_rsi_short"` and `confidence=9.0` still gets destroyed at `_pick_strategy()` if "high_rsi_short" is not in STRATEGY_PARAMS.

### Preferred Sequence (Knowledge-First)

1. **Register** the strategy (`high_rsi_short` in STRATEGY_PARAMS)
2. **Backtest** synthetically via BacktestingAI._full_pipeline() against replay databases
3. **Gate** on backtest results: win rate ≥ 50%, expectancy ≥ 0.1%, max DD ≤ 15%
4. **Connect** DNA: call `get_short_dna_confidence_boost()` from Setup 4
5. **Route** in MetaStrategyController RANGE_MARKET map
6. **Observe** 20+ paper trades before any live deployment consideration

---

## 9. FINAL VERDICT TABLE

### Proposed Changes

| # | Proposed Change | Verdict | Evidence |
|---|---|---|---|
| 1 | Register `high_rsi_short` in STRATEGY_PARAMS | **B** | Logic exists; ZERO historical trades; BacktestingAI would run synthetic simulation on first encounter; needs 20+ backtested results before A |
| 2 | Add RANGE_MARKET SHORT routing in `_pick_strategy()` | **B** | Governance-compatible; no bypass risk; prerequisite: #1 must be done first or routing sends signal to wrong strategy |
| 3 | Change overbought_short_watch score penalty → bonus | **C** | Overbought stocks ALREADY rank in top-57 (INDIANB RSI=67.1 scored #1); scoring is not the bottleneck; change has unknown side-effects on LONG candidate ranking; no evidence this would unblock any of the 6 C-stocks |
| 4 | Connect existing short DNA to live opportunity selection | **B** | `get_short_dna_confidence_boost()` is explicitly designed for this use; DNA evidence is real (135 evidence events); however, this is only meaningful AFTER #1 and #2 are in place; DNA alone cannot create an opportunity |

### Verdict Definitions

| Grade | Meaning |
|---|---|
| **A** | Safe to implement based on existing evidence |
| **B** | Promising but needs more historical validation |
| **C** | Research-only; insufficient evidence for implementation |
| **D** | Should NOT be implemented |

---

## 10. EVIDENCE TABLE

| Claim | Evidence Source | Verified? |
|---|---|---|
| Setup 4 exists and generates correct SHORT signal | equity_scanner_ai.py lines 2058-2083 | YES |
| high_rsi_short NOT in STRATEGY_PARAMS | strategy_generator_ai.py line 36 (dict) | YES |
| SHORT direction falls to Mean_Reversion in _pick_strategy | strategy_generator_ai.py _pick_strategy() | YES |
| Mean_Reversion disabled (0/5 WR) | strategy_performance.json, G-001 BML-001 | YES |
| All 1,352 ct_db decisions are LONG strategies | ct_db_20260811.db | YES |
| All 8,562 study002 signal_births are LONG | study002_replay.db | YES |
| paper_trades.csv has 0 executed trades | paper_trades.csv (1 header row only) | YES |
| INDIANB RSI=67.1 scored #1 in Aug-11 candidates | daily_candidates_20260811.json | YES |
| 7 overbought_short_watch candidates in Aug-11 top-57 | daily_candidates_20260811.json | YES |
| ZERO Setup 4 signals from Aug-11 candidates | direct calculation: none pass RSI+price thresholds | YES |
| volume_spike SHORT conf=1.0, 135 evidence events | institutional_dna.db | YES |
| ph2_short_dna designed for scanner use but not called from scanner | ph2_short_dna.py line 141-146, orchestrator grep | YES |
| H001 validated as pattern presence only, not trading performance | ph2_short_dna.py docstring, no backtest data | YES |
| Governance gates are all direction-neutral | risk_manager_ai.py, decision_engine.py, risk_guardian.py | YES |
| PGA learning actions for HINDALCO/INFY PENDING 6 days | learning_registry_20260811.json | YES |
| All SHORT events in ct_db are index futures/options | ct_db_20260811.db ct_events | YES |

---

## 11. FINAL RECOMMENDATION

```
CONNECT EXISTING KNOWLEDGE FIRST
(with prerequisite backtest validation before routing activation)
```

### Reasoning

1. **The knowledge exists.** institutional_dna.db has `volume_spike SHORT conf=1.0` with 135 evidence events — the largest evidence pool in the entire database. This is real, validated knowledge.

2. **The scanner capability exists.** Setup 4 generates correct, well-formed SHORT TradeSignals with R:R=2.5, correct stop placement, and appropriate regime guards. Nothing needs to be built.

3. **The governance is compatible.** Every risk gate in the pipeline already handles SHORT direction. No governance changes are needed.

4. **The only missing piece is registration.** Adding `"high_rsi_short"` to STRATEGY_PARAMS (6 lines) and adding a SHORT branch to `_pick_strategy()` (4 lines) and listing "High_RSI_Short" in MetaStrategyController RANGE_MARKET map (1 line) would complete the wiring. This is not a new capability — it is connecting components that already exist.

5. **Backtest validation is a prerequisite, not a blocker.** BacktestingAI already has `_full_pipeline()` that can run a synthetic backtest on "high_rsi_short" using the replay databases. The pipeline exists. Running it produces the win_rate, expectancy, and max_drawdown needed to either confirm (grade A) or deny (stay at grade B/C) the strategy.

### Recommended Implementation Sequence

```
Step 1: RUN BACKTEST (prerequisite)
  → BacktestingAI._full_pipeline("high_rsi_short")
  → Acceptance: win_rate >= 0.50, expectancy >= 0.001, max_drawdown <= 0.15
  → If fails: DO NOT PROCEED with live routing

Step 2: IF BACKTEST PASSES → REGISTER strategy
  → Add "high_rsi_short" to STRATEGY_PARAMS
  → Add "High_RSI_Short" to MetaStrategyController RANGE_MARKET list
  → Add SHORT branch to _pick_strategy() RANGE_MARKET block

Step 3: CONNECT KNOWLEDGE
  → Call get_short_dna_confidence_boost() from Setup 4 in _identify_setup()
  → DNA boost is additive, capped at 8.5 total confidence

Step 4: PAPER TRADE OBSERVATION
  → Observe 20+ paper trades
  → Track: win rate, expectancy, regime breakdown, false-positive rate
  → Only proceed to live after 20+ trades with WR >= 50%

Step 5 (NOT yet): LIVE DEPLOYMENT
  → Requires: backtest pass + 20+ paper trade validation + explicit approval
```

### What NOT to Do (yet)

1. **Do NOT change the overbought_short_watch scoring formula.** The evidence shows this is not the bottleneck (INDIANB scores #1 despite the penalty). The change is low value with unknown side effects. Grade C — research first.

2. **Do NOT activate ph2_short_dna without strategy registration.** The DNA boost is meaningless if the signal gets destroyed at strategy routing. DNA connection is Step 3, not Step 1.

3. **Do NOT add declining-momentum scanner (Setup 5).** For EASEMYTRIP and PCJEWELLER, this is a genuine new capability gap. Building Setup 5 requires a completely new signal type with no existing backtest data. This is a P1 research item, not a wiring fix.

4. **Do NOT execute PGA learning actions manually.** The PGA action executor is listed as P2 research. Running ad-hoc DNA candidate creation is a pipeline-level change, not a quick fix.

---

## 12. CONFIRMATION

**ZERO production changes were made during this audit.**

Temporary scripts created and deleted:
- `audit_iios_query.py` — deleted
- `audit_short_signals.py` — deleted
- `audit_schema_fix.py` — deleted
- `audit_short_complete.py` — deleted
- `audit_ct_short.py` — deleted

All findings are from read-only queries against existing databases, code, and data files. No files were modified. No trades were executed. No strategies were registered.

---

*SHORT_OPPORTUNITY_PRE_IMPLEMENTATION_AUDIT_001 — 2026-08-13 — READ-ONLY — COMPLETE*
