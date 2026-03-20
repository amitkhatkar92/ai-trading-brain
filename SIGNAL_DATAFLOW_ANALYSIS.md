# Signal Data Flow Analysis: OpportunityEngine → StrategyLab → BacktestingAI

**Date:** March 20, 2026  
**Issue:** Signals passing from OpportunityEngine show "signals = 24 / approved = 0" in filter_by_backtest()

---

## 1. Signal Generation (OpportunityEngine → EquityScannerAI)

**File:** `opportunity_engine/equity_scanner_ai.py` (lines 199–320)

### TradeSignal Creation
When the equity scanner discovers a setup, it creates a **TradeSignal object with these attributes:**

```python
sig = TradeSignal(
    symbol          = stock["symbol"],           # e.g., "RELIANCE"
    direction       = SignalDirection.BUY,       # Direction (BUY/SELL/SHORT)
    signal_type     = SignalType.EQUITY,
    strength        = SignalStrength.STRONG,
    entry_price     = ltp,
    stop_loss       = round(ltp - stop_dist, 2),
    target_price    = round(ltp + 2.5 * stop_dist, 2),
    quantity        = 1,                        # Placeholder (Risk Engine overwrites)
    confidence      = 6.0,                      # 0–10 scale
    source_agent    = "EquityScannerAI",
    atr             = atr,                      # ATR(14) proxy
    adv_crore       = adv_crore,               # Average Daily Volume (₹ crore)
    entry_zone_low  = round(..., 2),
    entry_zone_high = round(..., 2),
)
```

### ⚠️ KEY POINT 1: TradeSignal Has NO Backtest Attributes
- **No:** `signal.win_rate`, `signal.drawdown`, `signal.wf_consistency`, `signal.overfit_ratio`, `signal.cross_market_rate`
- **Reason:** These are **strategy-level metrics**, not signal-level metrics
- At creation, `signal.strategy_name = "unassigned"` (default)

---

## 2. Strategy Assignment (StrategyLab → StrategyGeneratorAI)

**File:** `strategy_lab/strategy_generator_ai.py` (lines 98–170)

### The assign_strategy() Flow

```python
def assign_strategy(self, signals: List[TradeSignal], snapshot: MarketSnapshot):
    """For each signal, determine which strategy should trade it."""
    enriched = []
    for signal in signals:
        assigned = self._assign(signal, snapshot, active)  # ← Strategy name added here
        if assigned:
            enriched.append(assigned)
    return enriched
```

### Inside _assign()
```python
# Case 1: Signal already has a strategy_name (rare)
if signal.strategy_name in STRATEGY_PARAMS:
    evolved = self._best_evolved_variant(signal.strategy_name, active, min_signal_rr=rr)
    if evolved:
        signal.strategy_name = evolved
    return signal

# Case 2: Signal has no strategy — auto-assign based on regime
strategy = self._pick_strategy(signal, regime, vol_level, active)
if strategy:
    signal.strategy_name = strategy  # ← ASSIGNED HERE
else:
    signal.strategy_name = "Mean_Reversion"  # fallback
return signal
```

### ⚠️ KEY POINT 2: strategy_name Is Assigned or Falls Back
- If regime → strategy logic selects a strategy, `signal.strategy_name` is set
- If no match found, defaults to `"Mean_Reversion"` (or `"Bull_Call_Spread"` for options)
- **Signals now have a strategy_name** but **still NO backtest attributes**

---

## 3. Evolved Parameters Application (StrategyEvolutionAI)

**File:** `strategy_lab/strategy_evolution_ai.py`

### What apply_evolved_params() Does
```python
evolved = self.strategy_evolution.apply_evolved_params(matched)
```

- Loads `data/evolved_strategies.json`
- For each signal, checks if its assigned strategy has an evolved variant
- Applies parameter tweaks (RSI filter, volume ratio thresholds, etc.) to the signal's ATR/entry zone logic
- **Does NOT add backtest metrics to the signal object**

### ⚠️ KEY POINT 3: Still NO Signal-Level Backtest Attributes
- Evolved variants are **parameter sets**, not backtest results
- Backtest results are still strategy-level metrics in `BacktestResult` objects

---

## 4. Backtest Filtering (BacktestingAI)

**File:** `strategy_lab/backtesting_ai.py` (lines 254–320)

### filter_by_backtest() Processing

```python
def filter_by_backtest(self, signals: List[TradeSignal]) -> List[TradeSignal]:
    approved_signals = []
    
    for signal in signals:
        # KEY LOOKUP: signal.strategy_name → BacktestResult
        result = self._get_result(signal.strategy_name)
        
        if result is None:
            log.warning("No backtest data for '%s' — allowing through.",
                       signal.strategy_name)
            approved_signals.append(signal)
            continue
        
        # SCORE: Check 6 metrics on the RESULT, not the SIGNAL
        score = 0
        if result.win_rate >= MIN_WIN_RATE:               score += 1  # ← From RESULT
        if result.expectancy >= MIN_EXPECTANCY:           score += 1  # ← From RESULT
        if result.max_drawdown <= MAX_DRAWDOWN:           score += 1  # ← From RESULT
        if result.wf_consistency >= MIN_WF_CONSISTENCY:   score += 1  # ← From RESULT
        if result.cross_market_pass_rate >= threshold:    score += 1  # ← From RESULT
        if result.overfitting_ratio <= MAX_OVERFITTING:   score += 1  # ← From RESULT
        
        # DECISION: score >= 2 (FORCED MODE for debugging)
        if score >= 2:
            # ATTRIBUTE BOOST (added only after approval)
            boost = (0.5 * result.sharpe) / max(result.overfitting_ratio, 1.0)
            signal.confidence = min(10.0, signal.confidence + round(boost, 2))
            approved_signals.append(signal)
        else:
            log.info("REJECTED: score too low (%d/6)", score)
    
    return approved_signals
```

### ⚠️ KEY POINT 4: Backtest Metrics Are Strategy-Level
- **signal.win_rate does NOT exist** — it's `result.win_rate`
- **signal.drawdown does NOT exist** — it's `result.max_drawdown`
- **signal.wf_consistency does NOT exist** — it's `result.wf_consistency`
- **signal.overfit_ratio does NOT exist** — it's `result.overfitting_ratio`
- **signal.cross_market_rate does NOT exist** — it's `result.cross_market_pass_rate`

---

## 5. Where Backtest Results Come From

**File:** `strategy_lab/backtesting_ai.py` (lines 720–1000)

### The _get_result() Method
```python
def _get_result(self, strategy_name: str) -> Optional[BacktestResult]:
    if strategy_name not in _BACKTEST_CACHE:
        _BACKTEST_CACHE[strategy_name] = self._full_pipeline(strategy_name)
    return _BACKTEST_CACHE.get(strategy_name)
```

### The _BACKTEST_CACHE
- **Pre-seeded at init** with hardcoded results for ~11 base strategies
- Example:
  ```python
  _BACKTEST_CACHE["Trend_Pullback"] = BacktestResult(
      strategy_name="Trend_Pullback",
      win_rate=0.60,              # 60% OOS
      max_drawdown=0.08,          # 8%
      expectancy=0.006,           # 0.6% per trade
      wf_consistency=0.80,        # 4/5 folds profitable
      cross_market_pass_rate=0.75,
      overfitting_ratio=1.20,
  )
  ```

- **For evolved variants:** Computed on-the-fly if not in cache

---

## 6. The "signals = 24 / approved = 0" Problem

### Root Cause Analysis

The issue **"signals = 24 / approved = 0"** occurs when:

**Option A: strategy_name is missing or None**
- If signals never got a strategy_name assigned (e.g., assign_strategy() failure)
- Then `self._get_result(None)` or `self._get_result("")` returns nothing
- Signal is not even added to approved list

**Option B: strategy_name doesn't match cache**
- If `strategy_name = "MyCustomStrategy"` but not in `_BACKTEST_CACHE`
- Then `_get_result()` tries `self._full_pipeline("MyCustomStrategy")`
- This generates a random simulation that likely fails strict gates
- Previously: ALL signals rejected by AND logic (6/6 required)
- Now (March 2026 fix): Should pass with 4/6 scoring

**Option C: Threshold is still too strict (unlikely after March 2026 fix)**
- Old: 6 AND conditions (all must pass) → ~0% approval
- New: 4/6 scoring → ~70% approval expected

### The Actual Fix Applied (March 2026)

From `SCORE_LOGIC_FIX_MARCH2026.md`:
- **Changed threshold from:** `passes_gate = all([wr≥MIN_WR, exp≥MIN_EXP, dd≤MAX_DD, wf≥MIN_WF, xmkt≥MIN_X, ov≤MAX_OV])`
- **Changed threshold to:** `score >= 4 out of 6`
- **Result:** ✅ 187 pre-seeded strategies now pass gates; 24/24 signals approved

### Why Signals Might Still Show 0/24 After Fix

1. **Strategy assignment failure**: Signals still have `strategy_name="unassigned"` or invalid name
2. **Cache not loaded**: `_BACKTEST_CACHE` empty or missing strategy
3. **Regression in assign_strategy()**: The logic that assigns strategy names broke
4. **Old code still running**: Cache was not reloaded after fix

---

## 7. Data Flow Diagram

```
OpportunityEngine (Layer 3)
    │
    ├─ EquityScannerAI
    │  └─ Creates TradeSignal(symbol, entry_price, ..., strategy_name="unassigned")
    │     [24 signals]
    │
    ▼
StrategyLab (Layer 4)
    │
    ├─ StrategyGeneratorAI.assign_strategy()
    │  └─ For each signal: signal.strategy_name = regime-based strategy name
    │     [24 signals with strategy_name assigned]
    │
    ├─ StrategyEvolutionAI.apply_evolved_params()
    │  └─ Apply parameter tweaks (RSI filter, volume threshold)
    │     [24 signals with evolved params]
    │
    ├─ BacktestingAI.filter_by_backtest()
    │  ├─ For each signal:
    │  │   result = _get_result(signal.strategy_name)  ← Lookup BacktestResult
    │  │   score = count(6 metrics from result)
    │  │   if score >= 2:  approved ✓
    │  │   else:           rejected ✗
    │  │
    │  └─ Returns approved list
    │     [Expected: ~16–20 approved, depending on strategy mix]
    │     [Actual (problem): 0 approved]
    │
    ▼
RiskControl → Debate → Execution
```

---

## 8. Summary: Backtest Attributes and Signals

### ❌ Don't Exist on Signals:
- `signal.win_rate`
- `signal.drawdown`
- `signal.wf_consistency`
- `signal.overfit_ratio`
- `signal.cross_market_rate`

### ✅ Exist on BacktestResult (retrieved by strategy_name):
- `result.win_rate`
- `result.max_drawdown`
- `result.wf_consistency`
- `result.overfitting_ratio`
- `result.cross_market_pass_rate`

### The Actual Signal Attributes:
1. **Core trade logic:** symbol, direction, entry_price, stop_loss, target_price, quantity
2. **Risk metrics:** atr, adv_crore, entry_zone_low, entry_zone_high
3. **Quality indicators:** confidence (0–10), risk_reward_ratio
4. **Routing:** strategy_name, source_agent, timestamp

---

## 9. Diagnostic Checklist

If signals are still showing 0/24 approved after filter_by_backtest():

- [ ] **Check 1:** Do signals have `strategy_name` assigned?
  - Add logging in `assign_strategy()` output
  - Print first signal.strategy_name before filter_by_backtest() call

- [ ] **Check 2:** Is `_BACKTEST_CACHE` populated?
  - Log cache size in BacktestingAI.__init__
  - Print first 3 strategy names in cache

- [ ] **Check 3:** Are strategy names matching?
  - Log every `_get_result()` lookup: strategy_name → found/not-found
  - Check for typos or case mismatches (e.g., "Mean_Reversion" vs "mean_reversion")

- [ ] **Check 4:** Are gate thresholds reasonable?
  - Current: 4/6 scoring (66.7% quality)
  - Log actual score for rejected signals: e.g., "REJECTED score=1/6"

- [ ] **Check 5:** Are evolved variants being applied correctly?
  - StrategyEvolutionAI.apply_evolved_params() should preserve strategy_name
  - Check for None returns

---

## 10. Recommendations

1. **Always populate strategy_name early**: Ensure every signal exiting StrategyLab assigns a valid name
   
2. **Validate strategy_name matches cache**: Add a pre-filter before filter_by_backtest() to catch mismatches

3. **Log all lookups**: Include a line in _get_result() that logs cache hit/miss AND score

4. **Add signal attribute checks**: Verify signals have required fields (symbol, strategy_name, confidence) before each layer

5. **Don't add backtest metrics to signals**: Keep result properties separate from signal properties—only boost confidence if approved
