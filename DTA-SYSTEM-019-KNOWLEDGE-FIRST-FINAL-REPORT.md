# DTA-SYSTEM-019 — Knowledge-First Architecture
## Final Implementation Report

**Status:** COMPLETE  
**Commit:** `d03a545`  
**VPS:** `root@178.18.252.24` — both containers `Up (healthy)`  
**Tests:** 15/15 PASS  
**Date:** 2026-08-29

---

## 1. Root Cause

`_identify_setup()` in `opportunity_engine/equity_scanner_ai.py` acted as a **strategy filter** rather than a feature extractor. It returned `(None, reason_code)` for 6 setup-specific conditions, preventing those stocks from ever entering the `signals` list that feeds KDA.

Since `master_orchestrator.py` only calls `run_knowledge_shadow()` on signals in the `signals` list, any stock blocked by `_identify_setup()` was **architecturally invisible to KDA**.

### Evidence from 2026-08-28 live session

| Stock | Gain | KEL entries | Rejection reason | KDA ever called? |
|-------|------|-------------|-----------------|-----------------|
| KPITTECH | +3.29% | 408 | `bull_gate` (RSI=47, vol=0.49) | **NO** |
| TECHM | +2.49% | 376 | `bull_gate` (RSI=50, vol=0.49) | **NO** |
| ELGIEQUIP | +5.01% | 558 | Not in watchlist cycle | NO |
| PERSISTENT | +3.24% | 470 | Not in watchlist cycle | NO |

KEL evidence: `BULL+BUY+ge2` class — 7,209 entries, avg T+1 = **+2.055%**, win rate **74%** — was systematically unreachable because the most common bull-trend path (RSI ~45, mild uptrend, low volume) hit `bull_gate`.

---

## 2. Signal Flow (Before / After)

### Before (broken)
```
_identify_setup()
  → (None, "bull_gate")      ← stock deleted from pipeline
  → (None, "rsi_neutral")    ← stock deleted from pipeline
  → (None, "breakout_vol_low") ← deleted
  → (None, "breakout_rsi_hi") ← deleted
  → (None, "retest_rsi_oob") ← deleted
  → (None, "bounce_price_hi") ← deleted
  
scan() signals = []          ← KDA never called for these stocks
```

### After (fixed)
```
_identify_setup()
  → (TradeSignal[knowledge_referred], "knowledge_referred")  ← stock PASSES

scan() signals = [knowledge_referred signal]
  → StrategyLab (shadow / context)
  → KDA: run_knowledge_shadow(signal)
      → KEL evidence lookup
      → KNOWLEDGE_BUY / KNOWLEDGE_WAIT / KNOWLEDGE_HOLD
  → If KNOWLEDGE_BUY: → CRE → RiskGuardian → OrderManager → broker
  → If KNOWLEDGE_WAIT: no execution (KDA authority preserved)
```

---

## 3. Changes Made

### `opportunity_engine/equity_scanner_ai.py`

**6 strategy gates replaced:**

| Old | New | Context label |
|-----|-----|--------------|
| `return None, "bull_gate"` | `return self._build_knowledge_referred_signal(..., "bull_gate"), "knowledge_referred"` | in_bull_trend but trend_pullback conditions not met |
| `return None, "rsi_neutral"` | `return self._build_knowledge_referred_signal(..., "rsi_neutral"), "knowledge_referred"` | RSI 46-66, price mid-range |
| `return None, "breakout_vol_low"` | `return self._build_knowledge_referred_signal(..., "breakout_vol_low"), "knowledge_referred"` | ltp > resistance, vol_ratio < min |
| `return None, "breakout_rsi_hi"` | `return self._build_knowledge_referred_signal(..., "breakout_rsi_hi"), "knowledge_referred"` | breakout + vol ok but RSI ≥ 75 |
| `return None, "retest_rsi_oob"` | `return self._build_knowledge_referred_signal(..., "retest_rsi_oob"), "knowledge_referred"` | retest zone, RSI outside 50-65 |
| `return None, "bounce_price_hi"` | `return self._build_knowledge_referred_signal(..., "bounce_price_hi"), "knowledge_referred"` | RSI ≤ 45 but price above support zone |

**New helper method added** (lines ~2168–2230):

```python
def _build_knowledge_referred_signal(self, stock, snapshot, scanner_context) -> TradeSignal:
    """
    Generate a knowledge_referred TradeSignal for candidates that pass
    data-quality gates but don't match any predefined setup pattern.
    strategy_name='knowledge_referred' ensures the signal reaches KDA.
    """
    # Confidence: 5.0-6.5 (below pattern-matched range of 5.5-9.5)
    # Direction: BUY — KDA may issue KNOWLEDGE_WAIT → no execution
    # RR: RR_DEFAULT (2.5) ATR-based; KDA empirical levels override if VALIDATED
    # notes: f"scanner_context:{scanner_context}" — context for KDA scoring
```

**EdgeTelemetry block updated** (line ~1458):  
`knowledge_referred` signals now classified as `_setup = "knowledge_referred"` in `[EdgeTelemetry]` log instead of being misclassified as another setup type.

---

## 4. Safety Invariants — Confirmed Unchanged

| Gate | Type | Status |
|------|------|--------|
| `high_atr` in `_identify_setup()` | Data quality (ATR% > 4.0%) | **UNCHANGED** — still returns `(None, "high_atr")` |
| `bear_market` in `_identify_setup()` | Regime safety block | **UNCHANGED** — still returns `(None, "bear_market")` |
| KDA `KNOWLEDGE_WAIT` / `KNOWLEDGE_HOLD` | Knowledge decision authority | **UNCHANGED** — KDA retains full veto |
| CRE (CapitalRiskEngine) | Position sizing / risk gate | **UNCHANGED** — mandatory downstream |
| RiskGuardian | Kill-switch (VIX>45, daily loss>2%) | **UNCHANGED** — mandatory downstream |
| `opportunity_id` lineage | scanner → LOL → KDA → broker | **UNCHANGED** — generated once in scan() for all signals including knowledge_referred |

No existing interfaces changed. No new wiring required. The change is entirely inside `_identify_setup()` and the new `_build_knowledge_referred_signal()` helper.

---

## 5. `knowledge_referred` Signal Properties

```python
TradeSignal(
    strategy_name   = "knowledge_referred",
    direction       = SignalDirection.BUY,       # scanner is long-only universe
    strength        = SignalStrength.WEAK,        # below pattern-matched signals
    confidence      = 5.0–6.5,                  # below pattern-matched 5.5–9.5
    entry_price     = ltp,
    stop_loss       = ltp - ATR-based stop_dist,
    target_price    = ltp + 2.5 × stop_dist,    # RR_DEFAULT = 2.5
    notes           = "scanner_context:{reason}", # e.g. "scanner_context:bull_gate"
    # ... standard atr, adv_crore, entry_zone fields
)
```

**Confidence formula:**
```
base = 5.0
vol_boost = min(vol_ratio × 0.30, 0.80)  # volume contribution
rsi_boost = 0.40 if rsi > 60 else (0.20 if rsi ≥ 45 else 0.0)
confidence = min(base + vol_boost + rsi_boost, 6.5)
```

**Downstream path** (identical to all other signals):
1. scan() assigns `opportunity_id` (UUID4)
2. EdgeTelemetry logged with `setup_type=knowledge_referred`
3. MOP-RC-001 observer records signal observation
4. StrategyLab receives signal → likely REJECT (no backtest pattern) but KDA path is independent
5. KDA `run_knowledge_shadow()` receives signal with all market context
6. If `KNOWLEDGE_BUY` → enters `_kda_authorized` set → proceeds to CRE
7. If `KNOWLEDGE_WAIT/HOLD` → no execution

---

## 6. What This Does NOT Change

- **Scanner universe**: Still limited to `~162` prepared candidates. ELGIEQUIP and PERSISTENT were not scanned Friday because they weren't in the cycle's prepared watchlist. That is a separate gap (universe coverage) not addressed here.
- **Bear market BUY evaluation**: `bear_market` gate preserved — KDA is not called for BUY signals in BEAR_MARKET regime. Addressed separately if needed.
- **Strategy-based confidence ranking**: KDA uses its own KEL evidence scoring. knowledge_referred confidence (5.0–6.5) is a scanner-level feature, not a KDA gate.
- **No new file wiring**: `scan_no_signal_observer.py`, `klp_outcome_engine.py`, `filter_funnel_audit.py` unchanged — they operate correctly on the new signal set.

---

## 7. Test Results

**File:** `test_dta_system_019_knowledge_first.py` (15 tests)

```
TOTAL: 15  PASS: 15  FAIL: 0  EXIT: 0
```

| Test | Scenario | Result |
|------|----------|--------|
| T001 | bull_gate → knowledge_referred (KPITTECH/TECHM) | PASS |
| T002 | rsi_neutral → knowledge_referred (RSI 50 mid-range) | PASS |
| T003 | breakout_vol_low → knowledge_referred (low-volume breakout) | PASS |
| T004 | breakout_rsi_hi → knowledge_referred (RSI=76 overbought breakout) | PASS |
| T005 | retest_rsi_oob → knowledge_referred (retest zone, RSI=42) | PASS |
| T006 | bounce_price_hi → knowledge_referred (oversold, price above support) | PASS |
| T007 | high_atr → None **(data quality gate preserved)** | PASS |
| T008 | bear_market → None **(regime safety gate preserved)** | PASS |
| T009 | breakout → signal_found (existing setup intact) | PASS |
| T010 | trend_pullback → signal_found (existing setup intact) | PASS |
| T011 | mean_reversion_bounce → signal_found (existing setup intact) | PASS |
| T012 | price geometry invariant: target > entry > stop > 0 (all 6 contexts) | PASS |
| T013 | strategy_name is exactly "knowledge_referred" | PASS |
| T014 | notes contains scanner_context label | PASS |
| T015 | confidence in [5.0, 6.5] | PASS |

---

## 8. Deployment

```
Commit: d03a545
Branch: main
VPS: root@178.18.252.24

Containers (docker compose ps):
  ai-trading-brain      Up (healthy)
  trading-dashboard     Up (health: starting → healthy within 30s)
```

Pull log: `3a50660..d03a545  main → origin/main` confirmed on VPS.

---

## 9. Remaining Gap

This fix ensures **every candidate that reaches `_identify_setup()` and passes data-quality gates gets KDA evaluation**. However, two of the four missed outperformers (ELGIEQUIP +5.01%, PERSISTENT +3.24%) were **not in the scan cycle's watchlist** on 2026-08-28. Their absence is a separate issue in the universe-building and prepared-candidate selection pipeline, not in `_identify_setup()`.

**DTA-SYSTEM-019 is closed.** The pre-KDA strategy gate has been removed. A stock must NOT be prevented from reaching the knowledge system merely because it does not fit a predefined strategy pattern — this is now architecturally enforced.
